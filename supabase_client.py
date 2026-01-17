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

def insert_scan_record(scan_id, original_url, processed_url=None, status="completed", error=None, **kwargs):
    """
    Inserts a tracking record into the chalk_scans table.
    Accepts extra fields via **kwargs (style, semester).
    """
    try:
        supabase = get_supabase_client()
        data = {
            "id": scan_id,
            "original_url": original_url,
            "processed_url": processed_url,
            "status": status,
            "error_message": error,
            **kwargs
        }
        # Filter out None values to let DB defaults handle them
        data = {k: v for k, v in data.items() if v is not None}
        
        return supabase.table("chalk_scans").insert(data).execute()
    except Exception as e:
        print(f"Database Insert Error: {e}")
        return None

def update_scan_record(scan_id, **kwargs):
    """
    Updates an existing tracking record in the chalk_scans table using UPSERT.
    This helps if strict RLS policies prevent standard updates but allow inserts/upserts.
    """
    try:
        supabase = get_supabase_client()
        data = {k: v for k, v in kwargs.items() if v is not None}
        
        if not data:
            return None
            
        data['id'] = scan_id # Ensure ID is present for upsert
        
        # 1. Fetch existing
        existing = supabase.table("chalk_scans").select("*").eq("id", scan_id).execute()
        if existing.data:
            final_data = existing.data[0]
            final_data.update(data)
            return supabase.table("chalk_scans").upsert(final_data).execute()
        else:
            return supabase.table("chalk_scans").upsert(data).execute()
    except Exception as e:
        print(f"Database Update Error: {e}")
        return None