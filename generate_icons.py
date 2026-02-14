
import os
from PIL import Image, ImageDraw, ImageFont

def create_icon(size, filename):
    img = Image.new('RGB', (size, size), color='#29b6f6')
    d = ImageDraw.Draw(img)
    
    # Draw a simple "A" for Adore
    # Since we can't easily rely on fonts, just draw a rectangle or simple shape
    d.rectangle([(size//4, size//4), (size*3//4, size*3//4)], fill='#ffffff')
    
    img.save(filename)
    print(f"Created {filename}")

try:
    static_dir = '/home/fernando/Área de trabalho/Orcamento/static'
    create_icon(192, os.path.join(static_dir, 'icon-192.png'))
    create_icon(512, os.path.join(static_dir, 'icon-512.png'))
    print("Icons generated successfully.")
except ImportError:
    print("PIL not installed. Creating SVGs instead.")
    # Fallback to SVG if PIL is missing
    svg_content = '''<svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">
      <rect width="100%" height="100%" fill="#29b6f6"/>
      <rect x="{margin}" y="{margin}" width="{inner}" height="{inner}" fill="#ffffff"/>
    </svg>'''
    
    with open(os.path.join(static_dir, 'icon-192.svg'), 'w') as f:
        f.write(svg_content.format(size=192, margin=48, inner=96))
        
    with open(os.path.join(static_dir, 'icon-512.svg'), 'w') as f:
        f.write(svg_content.format(size=512, margin=128, inner=256))
    print("SVGs created (fallback).")
