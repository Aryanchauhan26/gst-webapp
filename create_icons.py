# Create this file: create_icons.py
import os
from PIL import Image, ImageDraw

def create_placeholder_icon(size, filename):
    """Create a simple placeholder icon."""
    # Create a purple background
    img = Image.new('RGB', (size, size), '#7c3aed')
    draw = ImageDraw.Draw(img)
    
    # Draw a simple "G" for GST
    font_size = size // 2
    draw.text((size//4, size//4), "G", fill='white', font_size=font_size)
    
    # Save the icon
    os.makedirs('static/icons', exist_ok=True)
    img.save(f'static/icons/{filename}')
    print(f"✅ Created {filename}")

# Create all required icons
if __name__ == "__main__":
    sizes = [
        (48, "icon-48x48.png"),
        (72, "icon-72x72.png"),
        (96, "icon-96x96.png"),
        (144, "icon-144x144.png"),
        (192, "icon-192x192.png"),
        (512, "icon-512x512.png")
    ]
    
    for size, filename in sizes:
        create_placeholder_icon(size, filename)
    
    print("🎉 All icons created!")