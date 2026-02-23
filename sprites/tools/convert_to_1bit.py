import argparse
import os
from PIL import Image

def process_image(input_path, output_path, size=(200, 200), margin=10, threshold=128):
    """
    Converts an input image to a 1-bit black and white PNG at the specified size.
    """
    try:
        # Open the image
        img = Image.open(input_path)
        
        # Convert to grayscale first
        img = img.convert('L')
        
        # Calculate aspect ratio
        aspect = img.width / img.height
        
        # Calculate target dimensions accounting for margin
        target_w = size[0] - (margin * 2)
        target_h = size[1] - (margin * 2)
        
        # Determine resize dimensions keeping aspect ratio
        if aspect > 1:
            new_w = target_w
            new_h = int(target_w / aspect)
        else:
            new_h = target_h
            new_w = int(target_h * aspect)
            
        # Resize using high-quality resampling
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Create a new white image with the target size
        new_img = Image.new('L', size, 255)
        
        # Paste the resized image onto the center of the new image
        offset_x = (size[0] - new_w) // 2
        offset_y = (size[1] - new_h) // 2
        new_img.paste(img, (offset_x, offset_y))
        
        # Apply strict threshold to make it exactly 1-bit (black or white)
        # Anything below threshold becomes 0 (black), above becomes 255 (white)
        fn = lambda x: 255 if x > threshold else 0
        img_1bit = new_img.point(fn, mode='1')
        
        # Save the result
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        img_1bit.save(output_path, 'PNG')
        print(f"Successfully processed: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert an image to 1-bit 200x200 PNG for e-ink display.")
    parser.add_argument("input", help="Path to input image")
    parser.add_argument("output", help="Path to output PNG")
    parser.add_argument("--threshold", type=int, default=128, help="Threshold value (0-255) for black/white conversion")
    args = parser.parse_args()
    
    process_image(args.input, args.output, threshold=args.threshold)
