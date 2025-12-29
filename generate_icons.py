"""
Icon Generator for StockLeague PWA
Generates app icons and screenshots needed for app installation
Run this script to create all required icons
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Create icons directory if it doesn't exist
os.makedirs('/workspaces/StockLeague/static/icons', exist_ok=True)

def create_icon(size, filename, is_maskable=False):
    """Create an app icon with StockLeague branding"""
    # Create image with gradient background
    img = Image.new('RGB', (size, size), color='#6366f1')
    draw = ImageDraw.Draw(img)
    
    # For maskable icons, use transparent background
    if is_maskable:
        img = Image.new('RGBA', (size, size), color=(99, 102, 241, 0))
        draw = ImageDraw.Draw(img)
    
    # Draw circle background
    margin = size // 8
    circle_bbox = [margin, margin, size - margin, size - margin]
    if is_maskable:
        draw.ellipse(circle_bbox, fill=(99, 102, 241, 255))
    else:
        draw.ellipse(circle_bbox, fill='#8b5cf6')
    
    # Draw chart lines (simplified stock chart)
    line_color = 'white' if not is_maskable else (255, 255, 255, 255)
    line_start = size // 4
    line_height = size // 2
    
    # Draw ascending lines (representing profit)
    points = [
        (line_start, line_start + line_height),
        (line_start + line_height // 3, line_start + line_height // 2),
        (line_start + 2 * line_height // 3, line_start + line_height // 3),
        (line_start + line_height, line_start),
    ]
    
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=line_color, width=size // 20)
    
    # Save icon
    img.save(f'/workspaces/StockLeague/static/icons/{filename}')
    print(f'✓ Created {filename} ({size}x{size})')

def create_screenshot(width, height, filename):
    """Create a screenshot mockup"""
    img = Image.new('RGB', (width, height), color='#f8fafc')
    draw = ImageDraw.Draw(img)
    
    # Header bar
    draw.rectangle([(0, 0), (width, height // 8)], fill='#6366f1')
    
    # Add text "StockLeague"
    try:
        draw.text((width // 10, height // 20), "StockLeague", fill='white')
    except:
        pass
    
    # Content area (simplified portfolio view)
    card_height = height // 6
    card_margin = width // 10
    y_pos = height // 4
    
    for i in range(3):
        # Card background
        draw.rectangle(
            [(card_margin, y_pos), (width - card_margin, y_pos + card_height)],
            fill='white',
            outline='#e2e8f0',
            width=2
        )
        y_pos += card_height + height // 20
    
    img.save(f'/workspaces/StockLeague/static/icons/{filename}')
    print(f'✓ Created {filename} ({width}x{height})')

# Generate all required icons
print('Generating StockLeague app icons...\n')

# App icons
create_icon(192, 'icon-192x192.png', is_maskable=False)
create_icon(192, 'icon-192x192-maskable.png', is_maskable=True)
create_icon(512, 'icon-512x512.png', is_maskable=False)
create_icon(512, 'icon-512x512-maskable.png', is_maskable=True)

# Additional sizes for compatibility
create_icon(144, 'icon-144x144.png', is_maskable=False)
create_icon(96, 'icon-96x96.png', is_maskable=False)
create_icon(72, 'icon-72x72.png', is_maskable=False)

# Shortcut icons
create_icon(96, 'portfolio-icon-96.png', is_maskable=False)
create_icon(96, 'trade-icon-96.png', is_maskable=False)
create_icon(96, 'leagues-icon-96.png', is_maskable=False)
create_icon(96, 'leaderboard-icon-96.png', is_maskable=False)

# Screenshots
create_screenshot(540, 720, 'screenshot-1.png')
create_screenshot(540, 720, 'screenshot-2.png')
create_screenshot(1280, 720, 'screenshot-wide.png')

print('\n✓ All icons generated successfully!')
print('Icons location: /static/icons/')
print('\nNote: These are placeholder icons. For production, replace with actual design.')
