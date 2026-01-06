from PIL import Image
import os

img_path = r"C:\Users\Administrator\Documents\Cursor\Parential-Control_Enterprise\installer\agent\assets\wizard_top.png"
icon_path = r"C:\Users\Administrator\Documents\Cursor\Parential-Control_Enterprise\installer\agent\assets\setup_icon.ico"

try:
    img = Image.open(img_path)
    # Save as ICO with multiple sizes
    img.save(icon_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Successfully converted {img_path} to {icon_path}")
except Exception as e:
    print(f"Error converting: {e}")
