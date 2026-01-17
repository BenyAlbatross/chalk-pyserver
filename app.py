import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

from chalk_processor import process_image
from supabase_client import upload_image_to_supabase

app = Flask(__name__)
CORS(app) # Enable CORS for frontend integration

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Chalk Processor API is running"}), 200

@app.route("/process", methods=["POST"])
def process_chalk():
    """
    Expects 'image' file in multipart/form-data.
    Returns JSON with 'original_url', 'processed_url', and 'scan_id'.
    """
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        # 1. Read file bytes
        image_bytes = file.read()
        
        # 2. Setup IDs and Paths
        scan_id = str(uuid.uuid4())
        filename = f"{scan_id}.jpg"
        bucket_name = os.environ.get("SUPABASE_BUCKET", "chalk-images")

        # 3. Upload ORIGINAL immediately (Safety fallback)
        print(f"Uploading original: {filename}")
        original_url = upload_image_to_supabase(
            image_bytes, 
            filename, 
            folder="originals", 
            bucket_name=bucket_name
        )

        # 4. Get Gemini Key & Process
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_key:
            return jsonify({"error": "Server misconfiguration: GEMINI_API_KEY missing"}), 500

        print(f"Processing scan: {scan_id}")
        processed_bytes = process_image(image_bytes, gemini_key)
        
        # 5. Upload PROCESSED result
        print(f"Uploading processed: {filename}")
        processed_url = upload_image_to_supabase(
            processed_bytes, 
            filename, 
            folder="processed", 
            bucket_name=bucket_name
        )
        
        return jsonify({
            "status": "success",
            "scan_id": scan_id,
            "original_url": original_url,
            "processed_url": processed_url
        }), 200

    except Exception as e:
        print(f"Processing Error: {str(e)}")
        # Even if processing fails, if we uploaded the original, 
        # we might want to return that (conceptually), but for now standard error is fine.
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)