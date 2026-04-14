"""
Download oversized remote images, resize them to max 800px wide, save locally.
Update image URLs in the data to point to local GitHub-hosted copies.
Also fix the 1 broken URL.
"""

import json
import os
import re
import sys
import io
import urllib.request
from PIL import Image
from io import BytesIO

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

MAX_WIDTH = 800
MAX_HEIGHT = 1000
GITHUB_BASE = "https://raw.githubusercontent.com/grrarr/fufu-poshen-loh/master/images/"

with open('christopher-psl-data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

os.makedirs('images', exist_ok=True)

def download_and_resize(url, local_name):
    """Download image, resize if needed, save locally. Returns True on success."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        img_data = resp.read()
        img = Image.open(BytesIO(img_data))

        w, h = img.size
        needs_resize = w > MAX_WIDTH or h > MAX_HEIGHT

        if needs_resize:
            # Resize proportionally
            ratio = min(MAX_WIDTH / w, MAX_HEIGHT / h)
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            print(f"  Resized {w}x{h} -> {new_w}x{new_h}")
        else:
            print(f"  OK {w}x{h}, saving as-is")

        # Convert to RGB if RGBA (for smaller PNG)
        if img.mode == 'RGBA':
            # Keep as PNG for transparency
            img.save(f'images/{local_name}', 'PNG', optimize=True)
        else:
            img.save(f'images/{local_name}', 'PNG', optimize=True)

        size_kb = os.path.getsize(f'images/{local_name}') / 1024
        print(f"  Saved: images/{local_name} ({size_kb:.0f} KB)")
        img.close()
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def url_to_local_name(url):
    """Convert a remote URL to a local filename."""
    # Extract the filename from the URL
    filename = url.split('/')[-1]
    # Normalize: lowercase, replace spaces
    filename = filename.lower().replace(' ', '-')
    # Ensure PNG extension
    if not filename.endswith('.png'):
        filename = filename.rsplit('.', 1)[0] + '.png'
    return filename


# Process all problems
updated = 0
errors = 0

for p in data['examProblems']:
    for field in ['imageUrl', 'answerImageUrl']:
        url = p.get(field, '').strip()
        if not url:
            continue
        # Skip already-local images
        if 'raw.githubusercontent.com/grrarr' in url:
            continue

        local_name = url_to_local_name(url)
        local_url = GITHUB_BASE + local_name

        # Check if already downloaded
        if os.path.exists(f'images/{local_name}'):
            # Already have it, just update the URL
            p[field] = local_url
            updated += 1
            continue

        print(f"\n{p['source']} ({field}): {url}")
        if download_and_resize(url, local_name):
            p[field] = local_url
            updated += 1
        else:
            errors += 1

# Save
data['examProblems'] = data['examProblems']
with open('christopher-psl-data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n=== Summary ===")
print(f"Updated URLs: {updated}")
print(f"Errors: {errors}")

# Show final image stats
total_size = 0
count = 0
for f in os.listdir('images'):
    if f.endswith('.png'):
        path = f'images/{f}'
        total_size += os.path.getsize(path)
        count += 1

print(f"Total images in images/: {count}")
print(f"Total size: {total_size/1024/1024:.1f} MB")
