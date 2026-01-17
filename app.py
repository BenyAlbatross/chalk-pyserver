import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

from chalk_processor import process_image
from supabase_client import upload_image_to_supabase, insert_scan_record, update_scan_record

app = Flask(__name__)
CORS(app) # Enable CORS for frontend integration

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Chalk Processor API is running"}), 200

@app.route("/process", methods=["POST"])
def process_chalk():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Extract extra fields from form data
    # Default style to "normal" as per this pipeline's purpose
    style = request.form.get("style", "normal")
    scan_type = request.form.get("type")
    semester = request.form.get("semester")

    scan_id = request.form.get("id") or str(uuid.uuid4())
    filename = f"{scan_id}.jpg"
    bucket_name = os.environ.get("SUPABASE_BUCKET", "chalk-images")
    original_url = None

    try:
        # 1. Read file bytes
        image_bytes = file.read()
        
        # 2. Upload ORIGINAL immediately (Safety fallback)
        original_url = upload_image_to_supabase(
            image_bytes, 
            filename, 
            folder="originals", 
            bucket_name=bucket_name
        )

        # 3. Insert "PROCESSING" record immediately
        # This allows the frontend to see the scan right away
        insert_scan_record(
            scan_id, 
            original_url, 
            processed_url=None, 
            status="processing",
            style=style,
            semester=semester
        )

        # 4. Get Gemini Key & Process
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_key:
            raise ValueError("Server misconfiguration: GEMINI_API_KEY missing")

        # Note: Currently style doesn't change processing logic, 
        # but we save it as "normal" in the DB.
        processed_bytes = process_image(image_bytes, gemini_key)
        
        # 5. Upload PROCESSED result
        processed_url = upload_image_to_supabase(
            processed_bytes, 
            filename, 
            folder="processed", 
            bucket_name=bucket_name
        )
        
        # 6. Update Record to "COMPLETED"
        print(f"Finalizing record {scan_id}...")
        
        update_scan_record(
            scan_id,
            processed_url=processed_url,
            status="completed"
        )
        
        return jsonify({
            "status": "success",
            "scan_id": scan_id,
            "original_url": original_url,
            "processed_url": processed_url,
            "style": style
        }), 200

    except Exception as e:
        error_msg = str(e)
        print(f"Processing Error: {error_msg}")
        
        # If we have an ID, update the record to FAILED
        # (We might need to insert it if failure happened before step 3, 
        # but usually failures happen during processing)
        if scan_id:
            # Try updating first
            result = update_scan_record(
                scan_id,
                status="failed",
                error_message=error_msg
            )
            # If update didn't work (maybe record doesn't exist yet), insert it
            if not result or not result.data:
                 insert_scan_record(
                    scan_id, 
                    original_url, 
                    status="failed", 
                    error=error_msg,
                    style=style,
                    semester=semester
                )

        return jsonify({
            "error": error_msg,
            "scan_id": scan_id,
            "original_url": original_url
        }), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)