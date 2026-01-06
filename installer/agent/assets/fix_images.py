from PIL import Image, ImageOps
import os

ASSETS_DIR = r"C:\Users\Administrator\Documents\Cursor\Parential-Control_Enterprise\installer\agent\assets"

def process_side_image():
    # Fix "squeezed" look by cropping/resizing to fit 164x314 exactly
    target_size = (164, 314)
    path = os.path.join(ASSETS_DIR, "wizard_side.png") 
    out_path = os.path.join(ASSETS_DIR, "wizard_side.bmp")
    
    if os.path.exists(path):
        img = Image.open(path)
        # Use ImageOps.fit to fill the dimensions without distortion (center crop)
        # using a high quality downsampling filter
        img_fit = ImageOps.fit(img, target_size, method=Image.Resampling.LANCZOS)
        img_fit.save(out_path)
        print(f"Resized wizard_side to {target_size}")
    else:
        print("wizard_side.png not found")

def process_icon_and_top():
    # Use the removebg version as requested
    # Prefer PNG source if available for better transparency handling in ICO
    src_path = os.path.join(ASSETS_DIR, "wizard_top-removebg-preview.png")
    if not os.path.exists(src_path):
        src_path = os.path.join(ASSETS_DIR, "wizard_top-removebg-preview.bmp")
    
    if os.path.exists(src_path):
        img = Image.open(src_path)
        
        # 1. Create ICO
        icon_path = os.path.join(ASSETS_DIR, "setup_icon.ico")
        img.save(icon_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        print(f"Created setup_icon.ico from {src_path}")
        
        # 2. Create Top Wizard BMP (55x55)
        # Inno Setup requires BMP. Transparency issues can happen with BMP, 
        # but 32-bit BMP supports alpha channel if Inno supports it (modern usually does).
        # We will resize to check.
        top_size = (55, 55)
        top_img = ImageOps.fit(img, top_size, method=Image.Resampling.LANCZOS)
        
        # Save as BMP
        top_bmp_path = os.path.join(ASSETS_DIR, "wizard_top.bmp")
        top_img.save(top_bmp_path)
        print(f"Created wizard_top.bmp ({top_size})")

    else:
        print(f"Source file for icon not found: {src_path}")

if __name__ == "__main__":
    process_side_image()
    process_icon_and_top()
