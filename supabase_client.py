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
    file_path = f"{folder}/{file_name}"
    file_options = {"content-type": "image/jpeg"}
    
    try:
        supabase.storage.from_(bucket_name).upload(
            path=file_path,
            file=image_bytes,
            file_options=file_options
        )
        
        project_url = os.environ.get("SUPABASE_URL").rstrip("/")
        public_url = f"{project_url}/storage/v1/object/public/{bucket_name}/{file_path}"
        return public_url
        
    except Exception as e:
        print(f"Supabase Upload Error ({folder}): {e}")
        raise e

def insert_scan_record(scan_id, original_url, processed_url=None, status="completed", error=None):
    """
    Inserts a tracking record into the chalk_scans table.
    """
    try:
        supabase = get_supabase_client()
        data = {
            "id": scan_id,
            "original_url": original_url,
            "processed_url": processed_url,
            "status": status,
            "error_message": error
        }
        return supabase.table("chalk_scans").insert(data).execute()
    except Exception as e:
        print(f"Database Insert Error: {e}")
        # We don't raise here to avoid crashing the whole request 
        # if just the DB logging fails, but in production you might want to.
        return None
