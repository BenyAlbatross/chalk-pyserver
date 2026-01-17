from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageOps
import io
import base64
import json
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

def parse_json(json_output: str):
  # Parsing out the markdown fencing
  lines = json_output.splitlines()
  for i, line in enumerate(lines):
    if line.strip() == "```json":
      json_output = "\n".join(lines[i+1:])  # Remove everything before "```json"
      output = json_output.split("```")[0]  # Remove everything after the closing "```"
      return output.strip()  # Return the extracted JSON
  # If no markdown fencing found, return the original
  return json_output.strip()

def extract_segmentation_masks(image_path: str, output_dir: str = "segmentation_outputs"):
  # Load and resize image
  im = Image.open(image_path)
  im = ImageOps.exif_transpose(im) # Correct orientation
  im.thumbnail([1024, 1024], Image.Resampling.LANCZOS)

  prompt = """
  Give the segmentation masks for the door excluding the doorframe.
  Output a JSON list of segmentation masks where each entry contains the 2D
  bounding box in the key "box_2d", the segmentation mask in key "mask", and
  the text label in the key "label". Use descriptive labels.
  """

  config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=0) # set thinking_budget to 0 for better results in object detection
  )

  response = client.models.generate_content(
    model="gemini-2.5-flash",  # Gemini 2.5 supports segmentation masks, Gemini 3 does not
    contents=[prompt, im], # Pillow images can be directly passed as inputs (which will be converted by the SDK)
    config=config
  )

  # Parse JSON response
  items = json.loads(parse_json(response.text))

  # Create output directory
  os.makedirs(output_dir, exist_ok=True)
  
  # Save the complete JSON output to a file
  json_output_path = os.path.join(output_dir, "segmentation_results.json")
  with open(json_output_path, 'w') as f:
      json.dump(items, f, indent=2)
  print(f"Saved JSON output to {json_output_path}")

  # Process each mask
  for i, item in enumerate(items):
      # Get bounding box coordinates
      box = item["box_2d"]
      y0 = int(box[0] / 1000 * im.size[1])
      x0 = int(box[1] / 1000 * im.size[0])
      y1 = int(box[2] / 1000 * im.size[1])
      x1 = int(box[3] / 1000 * im.size[0])

      # Skip invalid boxes
      if y0 >= y1 or x0 >= x1:
          continue

      # Check if mask field exists and what type it is
      if "mask" not in item:
          print(f"Warning: No mask field for {item['label']}, skipping")
          continue
      
      mask_data = item["mask"]
      
      # Handle different mask formats
      if isinstance(mask_data, list):
          # Mask is a bounding box (list of coordinates)
          print(f"Mask is a bounding box: {mask_data}")
          # Use the mask bounding box instead of box_2d if provided
          mask_y0 = int(mask_data[0] / 1000 * im.size[1])
          mask_x0 = int(mask_data[1] / 1000 * im.size[0])
          mask_y1 = int(mask_data[2] / 1000 * im.size[1])
          mask_x1 = int(mask_data[3] / 1000 * im.size[0])
          
          # Create a simple rectangular mask overlay
          overlay = Image.new('RGBA', im.size, (0, 0, 0, 0))
          overlay_draw = ImageDraw.Draw(overlay)
          
          # Draw semi-transparent rectangle
          color = (255, 0, 0, 100)  # Red with transparency
          overlay_draw.rectangle([mask_x0, mask_y0, mask_x1, mask_y1], fill=color, outline=(255, 0, 0, 255), width=3)
          
          # Save overlay
          overlay_filename = f"{item['label'].replace(' ', '_')}_{i}_overlay.png"
          composite = Image.alpha_composite(im.convert('RGBA'), overlay)
          composite.save(os.path.join(output_dir, overlay_filename))
          print(f"Saved bounding box overlay for {item['label']} to {output_dir}")
          
      elif isinstance(mask_data, str) and mask_data.startswith("data:image/png;base64,"):
          # Mask is a base64-encoded PNG
          print(f"Mask is a base64 PNG string")
          
          # Remove prefix
          png_str = mask_data.removeprefix("data:image/png;base64,")
          mask_bytes = base64.b64decode(png_str)
          mask = Image.open(io.BytesIO(mask_bytes))

          # Resize mask to match bounding box
          mask = mask.resize((x1 - x0, y1 - y0), Image.Resampling.BILINEAR)

          # Convert mask to numpy array for processing
          mask_array = np.array(mask)

          # Create overlay for this mask
          overlay = Image.new('RGBA', im.size, (0, 0, 0, 0))
          overlay_draw = ImageDraw.Draw(overlay)

          # Create overlay for the mask
          color = (255, 255, 255, 200)
          for y in range(y0, y1):
              for x in range(x0, x1):
                  if mask_array[y - y0, x - x0] > 128:  # Threshold for mask
                      overlay_draw.point((x, y), fill=color)

          # Save individual mask and its overlay
          mask_filename = f"{item['label'].replace(' ', '_')}_{i}_mask.png"
          overlay_filename = f"{item['label'].replace(' ', '_')}_{i}_overlay.png"

          mask.save(os.path.join(output_dir, mask_filename))

          # Create and save overlay
          composite = Image.alpha_composite(im.convert('RGBA'), overlay)
          composite.save(os.path.join(output_dir, overlay_filename))
          print(f"Saved mask and overlay for {item['label']} to {output_dir}")
      else:
          print(f"Warning: Unknown mask format for {item['label']}: {type(mask_data)}")

# Example usage
if __name__ == "__main__":
  extract_segmentation_masks("../sample_door_photos/IMG_3104.jpeg")
