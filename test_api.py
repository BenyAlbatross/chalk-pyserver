import requests
import sys
import os
import time
import json

def test_health(url):
    print(f"🏥 Testing Health Check on {url}...")
    try:
        response = requests.get(url)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
        return True
    except Exception as e:
        print(f"❌ Health Check Failed: {e}\n")
        return False

def poll_status(url, scan_id):
    print(f"⏳ Polling status for {scan_id}...")
    start_time = time.time()
    
    while True:
        try:
            r = requests.get(f"{url}/scans/{scan_id}")
            if r.status_code != 200:
                print(f"   Error checking status: {r.status_code}")
                time.sleep(2)
                continue
                
            data = r.json()
            status = data.get('status')
            elapsed = int(time.time() - start_time)
            
            # Print status on same line to avoid clutter
            sys.stdout.write(f"\r   [{elapsed}s] Current Status: {status.upper()}   ")
            sys.stdout.flush()
            
            if status == "completed":
                print("\n\n✅ Pipeline Finished!")
                print(json.dumps(data, indent=2))
                return True
                
            if status == "failed":
                print(f"\n\n❌ Pipeline Failed: {data.get('error_message')}")
                return False
                
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n   Polling cancelled by user.")
            return False
        except Exception as e:
            print(f"\n   Polling Error: {e}")
            return False

def test_process(url, image_path, semester="Spring 2026"):
    print(f"🚀 Testing Upload on {url}/process...")
    
    if not os.path.exists(image_path):
        print(f"❌ Error: Image not found at {image_path}")
        return

    files = {'image': open(image_path, 'rb')}
    data = {'semester': semester}

    try:
        response = requests.post(f"{url}/process", files=files, data=data)
        
        if response.status_code == 202:
            resp_data = response.json()
            scan_id = resp_data.get('scan_id')
            print(f"   ✅ Upload Accepted! Scan ID: {scan_id}")
            
            # Start Polling
            poll_status(url, scan_id)
            
        elif response.status_code == 200:
            print("   ✅ Sync Response (Old API behavior):")
            print(response.json())
        else:
            print(f"   ❌ Upload Failed: {response.status_code}")
            print(f"   {response.text}")

    except Exception as e:
        print(f"   ❌ Request Failed: {e}")

if __name__ == "__main__":
    # CONFIGURATION
    BASE_URL = "http://127.0.0.1:5001" 
    TEST_IMAGE = "IMG_3104.jpeg" 
    
    # Parse Args: python test_api.py [URL] [IMAGE]
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1].rstrip("/")
    if len(sys.argv) > 2:
        TEST_IMAGE = sys.argv[2]

    if test_health(BASE_URL):
        if os.path.exists(TEST_IMAGE):
            test_process(BASE_URL, TEST_IMAGE)
        else:
            print(f"Skipping upload: {TEST_IMAGE} not found.")