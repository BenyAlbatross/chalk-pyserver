import requests
import sys
import os

def test_health(url):
    print(f"Testing Health Check on {url}...")
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}\n")
    except Exception as e:
        print(f"Health Check Failed: {e}\n")

def test_process(url, image_path, style="normal", scan_type="test", semester="2026"):
    print(f"Testing Image Processing on {url}/process...")
    
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        return

    files = {
        'image': open(image_path, 'rb')
    }
    
    data = {
        'style': style,
        'type': scan_type,
        'semester': semester
    }

    try:
        response = requests.post(f"{url}/process", files=files, data=data)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success! Response Data:")
            print(response.json())
        else:
            print("Failed. Error Data:")
            print(response.text)
    except Exception as e:
        print(f"Process Request Failed: {e}")

if __name__ == "__main__":
    # CONFIGURATION
    # Change this to your Render URL for remote testing: https://your-app.onrender.com
    BASE_URL = "http://localhost:5000" 
    
    # Check if a URL was provided as an argument
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1].rstrip("/")

    # IMAGE PATH
    # Provide a path to a test image here
    TEST_IMAGE = "sample_door.jpg" 
    
    if len(sys.argv) > 2:
        TEST_IMAGE = sys.argv[2]

    test_health(BASE_URL)
    
    if os.path.exists(TEST_IMAGE):
        test_process(BASE_URL, TEST_IMAGE)
    else:
        print(f"Skipping process test: File '{TEST_IMAGE}' not found.")
        print("Usage: python test_api.py [URL] [IMAGE_PATH]")
