from PIL import Image, ImageOps
import os

# Use user's preferred icon (with removed background)
src_png = r"C:\Users\Administrator\Documents\Cursor\Parential-Control_Enterprise\installer\agent\assets\wizard_top-removebg-preview.png"
assets_dir = r"C:\Users\Administrator\Documents\Cursor\Parential-Control_Enterprise\installer\agent\assets"

if os.path.exists(src_png):
    img = Image.open(src_png)
    
    # Create ICO with multiple sizes for setup.exe icon
    icon_path = os.path.join(assets_dir, "setup_icon.ico")
    img.save(icon_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Created setup_icon.ico from wizard_top-removebg-preview.png")
    
    # Create wizard_top.bmp (55x55) for installer header
    top_img = ImageOps.fit(img, (55, 55), method=Image.Resampling.LANCZOS)
    top_bmp_path = os.path.join(assets_dir, "wizard_top.bmp")
    top_img.save(top_bmp_path)
    print(f"Created wizard_top.bmp (55x55)")
    
    print("Done! Using your preferred icon.")
else:
    print(f"Source not found: {src_png}")
