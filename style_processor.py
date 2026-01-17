import cv2
import numpy as np
import io
import os
from google import genai
from google.genai import types
from PIL import Image, ImageEnhance

def bytes_to_cv2(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def cv2_to_bytes(img_cv):
    is_success, buffer = cv2.imencode(".jpg", img_cv)
    if not is_success:
        raise ValueError("Failed to encode image")
    return io.BytesIO(buffer).read()

def make_ugly(image_bytes):
    """
    Ugly: Hyper-Drip (Pixel Sorting + Deep Fry).
    """
    img = bytes_to_cv2(image_bytes)
    h, w = img.shape[:2]
    
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    img_pil = ImageEnhance.Color(img_pil).enhance(3.0)
    img_pil = ImageEnhance.Contrast(img_pil).enhance(1.5)
    img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    small_w = w // 2 
    small = cv2.resize(img, (small_w, h))
    small_gray = cv2.resize(gray, (small_w, h))
    output = small.copy()
    
    for x in range(small_w):
        bright_indices = np.where(small_gray[:, x] > 80)[0]
        if len(bright_indices) > 0:
            last_y = bright_indices[0]
            for y in bright_indices:
                if y > last_y + 1: 
                    length = np.random.randint(10, 100)
                    end = min(h, last_y + length)
                    color = small[last_y, x]
                    output[last_y:end, x] = color
                last_y = y
            length = np.random.randint(20, 150)
            end = min(h, last_y + length)
            color = small[last_y, x]
            output[last_y:end, x] = color

    final = cv2.resize(output, (w, h))
    return cv2_to_bytes(final)

def make_pretty(image_bytes, gemini_api_key):
    """
    Pretty: Image-to-Image Generation.
    Uses [prompt, image] pattern to generate a photorealistic version.
    """
    client = genai.Client(api_key=gemini_api_key)
    pil_img = Image.open(io.BytesIO(image_bytes))
    
    prompt = "Create a high-quality, photorealistic studio photograph based on this chalk drawing. Replace the chalk lines with real objects and cinematic lighting. Make it really beautiful."

    try:
        # Using the specific Image-to-Image preview model from your list
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt, pil_img],
        )
        
        # Extract Image from parts (Inline Data)
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    return part.inline_data.data # Bytes
                    
        raise ValueError("No image part found in response")

    except Exception as e:
        print(f"Prettify failed: {e}")
        return image_bytes

def make_slop(image_bytes, gemini_api_key):
    """
    Slop: Vision-to-Text.
    Generates 5 paragraphs of text slop.
    """
    client = genai.Client(api_key=gemini_api_key)
    pil_img = Image.open(io.BytesIO(image_bytes))
    prompt = "Identify the key items in this chalk drawing. Then, write 5 paragraphs of pure AI slop about it. Tone: Corporate/LinkedIn rambling."

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=[prompt, pil_img]
        )
        # We only want the text response here
        return response.text
    except Exception as e:
        print(f"Error generating slop: {e}")
        return "Error generating slop."
