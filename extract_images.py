"""Extract image URLs from Brillium exam review pages."""
import urllib.request
import re
import ssl

# Skip SSL verification for this scraping task
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

EXAMS = [
    ("M0 W1", "https://expii.onlinetests.app/Assess.aspx?guid=B62A8224D11846ADB0C6326DEB0EFC16&a=R1"),
    ("M0 W2", "https://expii.onlinetests.app/Assess.aspx?guid=D9F793ED26B24FE6B97C7A2EA31D8C7C&a=R1"),
    ("M0 W3", "https://expii.onlinetests.app/Assess.aspx?guid=F9D4A58AC3C54EF189E1ED1EF1F157ED&a=R1"),
    ("M0 W4", "https://expii.onlinetests.app/Assess.aspx?guid=7036969F434149F0AA83625A6AD1B96C&a=R1"),
    ("M0 Final", "https://expii.onlinetests.app/Assess.aspx?guid=5FBF777280E74BD698A98AC5B4895EF1&a=R1"),
    ("M1 W1", "https://expii.onlinetests.app/Assess.aspx?guid=685C3DBC6860441FB92233B6045AA23F&a=R1"),
    ("M1 Final", "https://expii.onlinetests.app/Assess.aspx?guid=A15503383200463CAE27714C670D2D84&a=R1"),
    ("W1B W1", "https://expii.onlinetests.app/Assess.aspx?guid=6A11C8B1827F435189337D0D7480A01A&a=R1"),
]

EXCLUDE_PATTERNS = ['logo', 'favicon', 'brillium-resources', 'brillium_resources', 'BrilliumResources']

def extract_images(html):
    """Extract question images from HTML, returning dict of question_num -> [urls]."""
    results = {}

    # Split by question-wrapper boundaries
    # Brillium uses divs with class containing "question-wrapper" or similar
    # Also try splitting by question number patterns

    # Strategy 1: Find all img tags and their surrounding context to determine question number
    # Look for question number indicators near images

    # First, let's find all images
    all_imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)

    # Filter out excluded patterns
    content_imgs = []
    for url in all_imgs:
        if not any(pat.lower() in url.lower() for pat in EXCLUDE_PATTERNS):
            content_imgs.append(url)

    if not content_imgs:
        return results

    # Strategy 2: For each content image, find what question it belongs to
    # Look for question numbering patterns before each image
    for url in content_imgs:
        # Find position of this image in HTML
        pos = html.find(url)
        if pos == -1:
            continue

        # Look backwards from the image for question number indicators
        # Common patterns: "Question 5", "Q5", "#5", question-wrapper with number
        preceding = html[max(0, pos-3000):pos]

        # Try various question number patterns (search backwards, take the last/nearest match)
        q_num = None

        # Pattern: "Question N" or "Question N."
        matches = re.findall(r'Question\s+(\d+)', preceding, re.IGNORECASE)
        if matches:
            q_num = int(matches[-1])

        # Pattern: question-number or similar class with a number
        if not q_num:
            matches = re.findall(r'question[-_]?(?:number|num|no|#)?\s*["\'>:]\s*(\d+)', preceding, re.IGNORECASE)
            if matches:
                q_num = int(matches[-1])

        # Pattern: "#N" in a heading or label context
        if not q_num:
            matches = re.findall(r'>\s*#?\s*(\d+)\s*[.</)"]', preceding)
            if matches:
                q_num = int(matches[-1])

        # Pattern: data-question or similar attribute
        if not q_num:
            matches = re.findall(r'data-question[^=]*=\s*["\']?(\d+)', preceding, re.IGNORECASE)
            if matches:
                q_num = int(matches[-1])

        # Pattern: QuestionNumber or qNum in various formats
        if not q_num:
            matches = re.findall(r'(?:QuestionNumber|qNum|qnum|q_num)\s*[=:]\s*["\']?(\d+)', preceding, re.IGNORECASE)
            if matches:
                q_num = int(matches[-1])

        if q_num:
            if q_num not in results:
                results[q_num] = []
            if url not in results[q_num]:
                results[q_num].append(url)
        else:
            # Couldn't determine question number - store with position-based key
            if 0 not in results:
                results[0] = []
            if url not in results[0]:
                results[0].append(url)

    return results


def fetch_page(url):
    """Fetch a page, following redirects."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return f"ERROR: {e}"


def main():
    total_images = 0
    for name, url in EXAMS:
        print(f"\n{'='*60}")
        print(f"FETCHING: {name}")
        print(f"URL: {url}")
        print(f"{'='*60}")

        html = fetch_page(url)

        if html.startswith("ERROR:"):
            print(f"  {html}")
            continue

        print(f"  Page size: {len(html)} bytes")

        # Quick check: how many img tags total?
        all_imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        content_imgs = [u for u in all_imgs if not any(p.lower() in u.lower() for p in EXCLUDE_PATTERNS)]
        print(f"  Total img tags: {len(all_imgs)}, Content images: {len(content_imgs)}")

        if content_imgs:
            # Show all content image URLs for debugging
            print(f"  All content image URLs found:")
            for i, u in enumerate(content_imgs):
                print(f"    [{i+1}] {u}")

        # Try structured extraction
        results = extract_images(html)

        if results:
            print(f"\n  {name}:")
            for q_num in sorted(results.keys()):
                for img_url in results[q_num]:
                    if q_num == 0:
                        print(f"    Q?: {img_url}")
                    else:
                        print(f"    Q{q_num}: {img_url}")
                    total_images += 1
        else:
            print(f"  No question images found.")

            # Debug: show a snippet of HTML around any img tags
            if content_imgs:
                print(f"\n  DEBUG - Context around first content image:")
                first_url = content_imgs[0]
                pos = html.find(first_url)
                if pos >= 0:
                    snippet = html[max(0,pos-500):pos+200]
                    # Clean up for readability
                    snippet = re.sub(r'\s+', ' ', snippet)
                    print(f"    ...{snippet[:700]}...")

    print(f"\n{'='*60}")
    print(f"TOTAL CONTENT IMAGES FOUND: {total_images}")


if __name__ == '__main__':
    main()
