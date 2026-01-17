import os
from supabase import create_client, Client

def get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") # Recommended: Service Role Key
    
    if not url or not key:
        raise ValueError("Supabase URL or Key not found in environment variables.")
        
    return create_client(url, key)

def upload_image_to_supabase(image_bytes, file_name, folder="processed", bucket_name="chalk-images"):
    """
    Uploads bytes to Supabase Storage in a specific folder and returns the public URL.
    """
    supabase = get_supabase_client()
    
    # Construct path: folder/filename
    file_path = f"{folder}/{file_name}"
    
    # Upload options
    file_options = {"content-type": "image/jpeg"}
    
    try:
        # Upload (upsert=True to overwrite if exists)
        response = supabase.storage.from_(bucket_name).upload(
            path=file_path,
            file=image_bytes,
            file_options=file_options
        )
        
        # Construct Public URL
        project_url = os.environ.get("SUPABASE_URL")
        # Ensure project_url doesn't have trailing slash for clean concatenation
        project_url = project_url.rstrip("/")
        public_url = f"{project_url}/storage/v1/object/public/{bucket_name}/{file_path}"
        
        return public_url
        
    except Exception as e:
        print(f"Supabase Upload Error ({folder}): {e}")
        # If it fails, we assume it might be a permission or network issue
        raise e