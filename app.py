import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

from chalk_processor import process_image
from supabase_client import upload_image_to_supabase, insert_scan_record

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

    scan_id = str(uuid.uuid4())
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

        # 3. Get Gemini Key & Process
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_key:
            return jsonify({"error": "Server misconfiguration: GEMINI_API_KEY missing"}), 500

        processed_bytes = process_image(image_bytes, gemini_key)
        
        # 4. Upload PROCESSED result
        processed_url = upload_image_to_supabase(
            processed_bytes, 
            filename, 
            folder="processed", 
            bucket_name=bucket_name
        )
        
        # 5. Record to Database (Best Practice)
        insert_scan_record(scan_id, original_url, processed_url, status="completed")
        
        return jsonify({
            "status": "success",
            "scan_id": scan_id,
            "original_url": original_url,
            "processed_url": processed_url
        }), 200

    except Exception as e:
        error_msg = str(e)
        print(f"Processing Error: {error_msg}")
        
        # Log failure to DB if we at least have an original URL
        if original_url:
            insert_scan_record(scan_id, original_url, status="failed", error=error_msg)
            
        return jsonify({
            "error": error_msg,
            "scan_id": scan_id,
            "original_url": original_url
        }), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
