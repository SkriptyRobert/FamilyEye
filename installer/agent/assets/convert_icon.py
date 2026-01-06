from PIL import Image
import os

# Use the newly generated clean icon
src_path = r"C:/Users/Administrator/.gemini/antigravity/brain/6ad820ba-931b-45e6-9308-7d0b730ec34d/familyeye_icon_clean_1767442550472.png"
assets_dir = r"C:\Users\Administrator\Documents\Cursor\Parential-Control_Enterprise\installer\agent\assets"

if os.path.exists(src_path):
    img = Image.open(src_path)
    
    # Create ICO with multiple sizes
    icon_path = os.path.join(assets_dir, "setup_icon.ico")
    img.save(icon_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Created setup_icon.ico")
    
    # Create wizard_top.bmp (55x55) for installer header
    from PIL import ImageOps
    top_img = ImageOps.fit(img, (55, 55), method=Image.Resampling.LANCZOS)
    top_bmp_path = os.path.join(assets_dir, "wizard_top.bmp")
    top_img.save(top_bmp_path)
    print(f"Created wizard_top.bmp (55x55)")
else:
    print(f"Source not found: {src_path}")
