import os
import io
import json
import base64
import numpy as np
import cv2
from PIL import Image, ImageOps
from google import genai
from google.genai import types

def parse_json(json_output: str):
    """Clean markdown formatting from JSON string."""
    lines = json_output.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "```json":
            json_output = "\n".join(lines[i+1:])
            output = json_output.split("```")[0]
            return output.strip()
    return json_output.strip()

def get_gemini_segmentation(image_bytes, api_key):
    """
    Sends image to Gemini to get the door segmentation mask.
    Returns the bounding box coordinates and the mask as a numpy array.
    """
    client = genai.Client(api_key=api_key)
    
    # Load image from bytes
    im = Image.open(io.BytesIO(image_bytes))
    im = ImageOps.exif_transpose(im)
    
    # Resize for API efficiency, keep original for final processing
    # We process on a copy to match the notebook's logic
    process_im = im.copy()
    process_im.thumbnail([1024, 1024], Image.Resampling.LANCZOS)
    
    prompt = """
    Give the segmentation masks for the door excluding the doorframe.
    Output a JSON list of segmentation masks where each entry contains the 2D
    bounding box in the key "box_2d", the segmentation mask in key "mask", and
    the text label in the key "label". Use descriptive labels.
    """

    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, process_im],
            config=config
        )
        
        parsed_json = parse_json(response.text)
        items = json.loads(parsed_json)
        
        if not items:
            raise ValueError("Gemini returned no items.")
            
        # Get the first item (assuming it's the door)
        item = items[0]
        
        # --- Process Mask ---
        # We need to map the mask back to the ORIGINAL image size
        orig_w, orig_h = im.size
        proc_w, proc_h = process_im.size
        
        box = item["box_2d"] # Normalized 0-1000
        
        # Denormalize to ORIGINAL dimensions
        y1 = int(box[0] / 1000 * orig_h)
        x1 = int(box[1] / 1000 * orig_w)
        y2 = int(box[2] / 1000 * orig_h)
        x2 = int(box[3] / 1000 * orig_w)
        
        # Safety clamp
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(orig_w, x2), min(orig_h, y2)
        box_w, box_h = x2 - x1, y2 - y1
        
        mask_data = item.get("mask")
        full_mask = np.zeros((orig_h, orig_w), dtype=np.uint8)

        if mask_data and isinstance(mask_data, str) and mask_data.startswith("data:image/png;base64,"):
            # Decode base64 mask
            png_str = mask_data.removeprefix("data:image/png;base64,")
            mask_bytes = base64.b64decode(png_str)
            mask_pil = Image.open(io.BytesIO(mask_bytes))
            
            # Resize mask to fit the absolute bounding box on the ORIGINAL image
            mask_pil = mask_pil.resize((box_w, box_h), resample=Image.Resampling.NEAREST)
            mask_crop = np.array(mask_pil)
            
            # Place on full mask
            full_mask[y1:y2, x1:x2] = mask_crop
            
            # If mask is boolean/grayscale, ensure it's binary 0-255
            if len(full_mask.shape) > 2:
                full_mask = cv2.cvtColor(full_mask, cv2.COLOR_RGB2GRAY)
            # Normalize to 0 or 255
            full_mask = np.where(full_mask > 128, 255, 0).astype(np.uint8)

        else:
            # Fallback: Create rectangular mask from box if no precise mask returned
            full_mask[y1:y2, x1:x2] = 255

        return im, full_mask

    except Exception as e:
        print(f"Error in Gemini segmentation: {e}")
        raise e

def process_image(image_bytes, gemini_api_key):
    # 1. Get Image and Mask
    pil_img, mask = get_gemini_segmentation(image_bytes, gemini_api_key)
    
    # Convert PIL to OpenCV (BGR)
    img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    # 2. Find Contours & Corners (Automated)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No contours found in segmentation mask.")
        
    cnt = max(contours, key=cv2.contourArea)
    
    # Approximate contour to polygon
    epsilon = 0.02 * cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    
    # If not 4 points, use bounding rect
    if len(approx) != 4:
        rect = cv2.minAreaRect(cnt)
        box_pts = cv2.boxPoints(rect)
        approx = np.int32(box_pts)
        
    pts = approx.reshape(4, 2)
    
    # 3. Sort Points (TL, TR, BR, BL)
    # Sort by Y first
    pts = pts[np.argsort(pts[:, 1])]
    top = pts[:2]
    bottom = pts[2:]
    # Sort top by X, bottom by X
    top = top[np.argsort(top[:, 0])]
    bottom = bottom[np.argsort(bottom[:, 0])]
    # Final order: TL, TR, BR, BL
    src_pts = np.array([top[0], top[1], bottom[1], bottom[0]], dtype="float32")
    
    # 4. Perspective Warp
    out_w, out_h = 1200, 2800
    dst_pts = np.array([
        [0, 0],
        [out_w - 1, 0],
        [out_w - 1, out_h - 1],
        [0, out_h - 1]], dtype="float32")
        
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped_img = cv2.warpPerspective(img_cv, M, (out_w, out_h))
    
    # 5. Extract Chalk (Top-Hat)
    gray = cv2.cvtColor(warped_img, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    tophat_gray = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
    
    # Otsu Binary Mask
    _, binary_mask = cv2.threshold(tophat_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Cleanup noise
    clean_kernel = np.ones((2, 2), np.uint8)
    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, clean_kernel)
    
    # 6. Enhance Mask (Dilation + Closing)
    # Dilation
    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    enhanced_mask = cv2.dilate(binary_mask, dilate_kernel, iterations=2)
    
    # Closing
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    enhanced_mask = cv2.morphologyEx(enhanced_mask, cv2.MORPH_CLOSE, close_kernel)
    
    # 7. Extract Colored Chalk
    enhanced_chalk = cv2.bitwise_and(warped_img, warped_img, mask=enhanced_mask)
    
    # 8. Saturation Boost
    # Convert to HSV
    hsv = cv2.cvtColor(enhanced_chalk, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = cv2.split(hsv)
    
    # Boost
    s = s * 1.25
    s = np.clip(s, 0, 255)
    v = v * 1.2
    v = np.clip(v, 0, 255)
    
    hsv_boosted = cv2.merge([h, s, v]).astype(np.uint8)
    final_img = cv2.cvtColor(hsv_boosted, cv2.COLOR_HSV2BGR)
    
    # Encode to bytes for upload
    is_success, buffer = cv2.imencode(".jpg", final_img)
    if not is_success:
        raise ValueError("Failed to encode processed image.")
        
    return io.BytesIO(buffer).read()
