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
    """
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        # Read file bytes
        image_bytes = file.read()
        
        # Get Gemini Key
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_key:
            return jsonify({"error": "Server misconfiguration: GEMINI_API_KEY missing"}), 500

        # 1. Process Image
        processed_bytes = process_image(image_bytes, gemini_key)
        
        # 2. Upload to Supabase
        # Generate unique filename
        ext = "jpg"
        unique_name = f"{uuid.uuid4()}.{ext}"
        bucket_name = os.environ.get("SUPABASE_BUCKET", "chalk-images")
        
        public_url = upload_image_to_supabase(processed_bytes, unique_name, bucket_name)
        
        return jsonify({
            "status": "success",
            "url": public_url,
            "filename": unique_name
        }), 200

    except Exception as e:
        print(f"Processing Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # For local testing
    app.run(debug=True, port=5000)
