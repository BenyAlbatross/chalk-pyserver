import os
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

from chalk_processor import process_image
from style_processor import make_ugly, make_slop, make_pretty
from supabase_client import upload_image_to_supabase, insert_scan_record, update_scan_record, get_scan_record

app = Flask(__name__)
CORS(app)

# Global Thread Pool
executor = ThreadPoolExecutor(max_workers=4)

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Chalk Processor API is running"}), 200

@app.route("/scans/<scan_id>", methods=["GET"])
def get_scan_status(scan_id):
    """
    Poll this endpoint to check if background processing is done.
    """
    record = get_scan_record(scan_id)
    if not record:
        return jsonify({"error": "Scan not found"}), 404
    
    return jsonify(record), 200

def background_processing_pipeline(scan_id, image_bytes, filename, bucket_name, gemini_key):
    """
    The main async pipeline:
    1. Extract Chalk (Gemini Vision + OpenCV)
    2. Parallel Fan-out:
       - Save Extracted
       - Create Ugly (Deep Fry)
       - Create Slop (Gemini Text)
    """
    print(f"[{scan_id}] Starting background pipeline...")
    
    try:
        # --- Step 1: Extraction ---
        print(f"[{scan_id}] Extracting chalk...")
        extracted_bytes = process_image(image_bytes, gemini_key)
        
        # Upload Extracted
        processed_url = upload_image_to_supabase(
            extracted_bytes, 
            filename, 
            folder="processed", 
            bucket_name=bucket_name
        )
        
        # Update DB: Extraction Done
        update_scan_record(scan_id, processed_url=processed_url, status="extracted")
        print(f"[{scan_id}] Extraction complete. URL: {processed_url}")

        # --- Step 2: Fan-Out (Ugly & Slop) ---
        # We can run these sequentially here or parallelize further. 
        # Sequential is safer for rate limits on Gemini/DB for now.
        
        # A. Ugly (Deep Fry)
        print(f"[{scan_id}] Frying image (Ugly)...")
        try:
            ugly_bytes = make_ugly(extracted_bytes)
            ugly_filename = f"{scan_id}_ugly.jpg"
            ugly_url = upload_image_to_supabase(
                ugly_bytes,
                ugly_filename,
                folder="processed",
                bucket_name=bucket_name
            )
            update_scan_record(scan_id, ugly_url=ugly_url)
        except Exception as e:
            print(f"[{scan_id}] Ugly generation failed: {e}")

        # B. Slop (Text Generation)
        print(f"[{scan_id}] Generating Slop...")
        try:
            slop_text = make_slop(extracted_bytes, gemini_key)
            # Assuming DB has a 'slop_text' column or similar. 
            # If not, this might need schema adjustment.
            update_scan_record(scan_id, slop_text=slop_text)
        except Exception as e:
             print(f"[{scan_id}] Slop generation failed: {e}")

        # C. Pretty (AI Reimagining)
        print(f"[{scan_id}] Beautifying (Imagen)...")
        try:
            pretty_bytes = make_pretty(extracted_bytes, gemini_key)
            pretty_filename = f"{scan_id}_pretty.jpg"
            pretty_url = upload_image_to_supabase(
                pretty_bytes,
                pretty_filename,
                folder="processed",
                bucket_name=bucket_name
            )
            update_scan_record(scan_id, pretty_url=pretty_url)
        except Exception as e:
            print(f"[{scan_id}] Prettify generation failed: {e}")

        # --- Finalize ---
        update_scan_record(scan_id, status="completed")
        print(f"[{scan_id}] Pipeline Finished.")

    except Exception as e:
        print(f"[{scan_id}] Pipeline FAILED: {e}")
        update_scan_record(scan_id, status="failed", error_message=str(e))

@app.route("/process", methods=["POST"])
def process_chalk():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Form Data
    semester = request.form.get("semester")
    scan_id = request.form.get("id") or str(uuid.uuid4())
    
    filename = f"{scan_id}.jpg"
    bucket_name = os.environ.get("SUPABASE_BUCKET", "chalk-images")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if not gemini_key:
        return jsonify({"error": "Server misconfiguration: GEMINI_API_KEY missing"}), 500

    try:
        # 1. Read Bytes immediately
        image_bytes = file.read()
        
        # 2. Upload Original (Blocking - for safety)
        original_url = upload_image_to_supabase(
            image_bytes, 
            filename, 
            folder="originals", 
            bucket_name=bucket_name
        )

        # 3. Create Initial Record
        result = insert_scan_record(
            scan_id, 
            original_url, 
            status="queued",
            semester=semester
        )

        if not result or not result.data:
            print(f"[{scan_id}] DB Insert Failed! Check schema.")
            # We continue ONLY if you want to allow processing without DB tracking,
            # but generally we should warn or fail. 
            # For now, let's allow it but log strictly, as the thread will likely fail updates.

        # 4. Offload to Background Worker
        executor.submit(
            background_processing_pipeline,
            scan_id,
            image_bytes,
            filename,
            bucket_name,
            gemini_key
        )

        # 5. Return immediately
        return jsonify({
            "status": "queued",
            "scan_id": scan_id,
            "original_url": original_url,
            "message": "Processing started in background."
        }), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)
