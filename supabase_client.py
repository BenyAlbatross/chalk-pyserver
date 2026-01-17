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
    Accepts extra fields via **kwargs (style, semester, room_id).
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
        
        response = supabase.table("chalk_scans").insert(data).execute()
        return response
    except Exception as e:
        print(f"Database Insert Error: {e}")
        # Print full details if available
        if hasattr(e, 'details'):
             print(f"Details: {e.details}")
        if hasattr(e, 'message'):
             print(f"Message: {e.message}")
        return None

def update_scan_record(scan_id, **kwargs):
    """
    Updates an existing tracking record in the chalk_scans table.
    """
    try:
        supabase = get_supabase_client()
        data = {k: v for k, v in kwargs.items() if v is not None}
        
        if not data:
            return None
            
        # Direct update - simpler and avoids "partial insert" errors
        return supabase.table("chalk_scans").update(data).eq("id", scan_id).execute()
    except Exception as e:
        print(f"Database Update Error: {e}")
        return None

def get_scan_record(scan_id):
    """
    Fetches a single scan record by ID.
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table("chalk_scans").select("*").eq("id", scan_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Database Fetch Error: {e}")
        return None

def get_scan_by_room_id(room_id):
    """
    Fetches a single scan record by room_id.
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table("chalk_scans").select("*").eq("room_id", room_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Database Fetch Error (room_id): {e}")
        return None