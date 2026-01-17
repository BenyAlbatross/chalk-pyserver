import os
from supabase import create_client, Client

def get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") # Recommended: Service Role Key
    
    if not url or not key:
        raise ValueError("Supabase URL or Key not found in environment variables.")
        
    return create_client(url, key)

def upload_image_to_supabase(image_bytes, file_name, bucket_name="chalk-images"):
    """
    Uploads bytes to Supabase Storage and returns the public URL.
    """
    supabase = get_supabase_client()
    
    # Upload options
    file_options = {"content-type": "image/jpeg"}
    
    try:
        # Upload (upsert=True to overwrite if exists)
        response = supabase.storage.from_(bucket_name).upload(
            path=file_name,
            file=image_bytes,
            file_options=file_options
        )
        
        # Get Public URL
        # Supabase-py 'get_public_url' might vary slightly by version, 
        # usually it's constructed or retrieved via method.
        # Direct construction is often reliable: {url}/storage/v1/object/public/{bucket}/{path}
        
        project_url = os.environ.get("SUPABASE_URL")
        public_url = f"{project_url}/storage/v1/object/public/{bucket_name}/{file_name}"
        
        return public_url
        
    except Exception as e:
        print(f"Supabase Upload Error: {e}")
        raise e
