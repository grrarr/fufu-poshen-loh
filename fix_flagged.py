"""
Fix flagged problems:
- For encoding_corruption / wall_of_text: save cropped question image from Review PDF,
  simplify text to plain-text summary
- Uses Review PDFs (question + answer on same page) as the source of truth
- Saves images to images/ folder with naming convention
"""

import fitz
import json
import csv
import os
import re
import sys
import io
from difflib import SequenceMatcher

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('christopher-psl-data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
problems = data['examProblems']

with open('problem_audit.csv', 'r', encoding='utf-8') as f:
    audit_rows = list(reader := csv.DictReader(f))

# Build lookup
flagged = {}
for r in audit_rows:
    pid = int(r['problem_id'])
    flagged.setdefault(pid, []).append(r['issue_type'])

# Get flagged problems grouped by source
flagged_problems = [p for p in problems if p['id'] in flagged]
by_source = {}
for p in flagged_problems:
    by_source.setdefault(p['source'], []).append(p)


def source_to_pdf(source, pdf_type='Review'):
    if source == 'Module 3 - Final Exam':
        return f'brillium emails/Module 3 - Final Challenge ({pdf_type}).pdf'
    m = re.match(r'Module 3 - Mini Test (\d)', source)
    if m:
        return f'brillium emails/Module 3 - W{m.group(1)} Challenge ({pdf_type}).pdf'
    m = re.match(r'(.+) - Week (\d) Challenge', source)
    if m:
        return f'brillium emails/{m.group(1)} - W{m.group(2)} Challenge ({pdf_type}).pdf'
    m = re.match(r'(.+) - Final Challenge', source)
    if m:
        return f'brillium emails/{m.group(1)} - Final Challenge ({pdf_type}).pdf'
    return None


def normalize(text):
    text = re.sub(r'^\d+[\.\)]\s*', '', text)
    text = re.sub(r'\s+', ' ', text).strip().lower()
    text = re.sub(r'[^\x00-\x7f]', '', text)
    text = re.sub(r'[^a-z0-9 ]', '', text)
    return text


def source_to_img_prefix(source):
    """Convert source to image filename prefix."""
    # "Module 0 - Week 1 Challenge" -> "mod0-w1"
    # "Module 3 - Mini Test 1" -> "mod3-mt1"
    # "Module 0 - Final Challenge" -> "mod0-final"
    # "Workout 1A - Week 1 Challenge" -> "w1a-w1"
    m = re.match(r'Module (\d) - Week (\d) Challenge', source)
    if m: return f"mod{m.group(1)}-w{m.group(2)}"
    m = re.match(r'Module (\d) - Final (?:Challenge|Exam)', source)
    if m: return f"mod{m.group(1)}-final"
    m = re.match(r'Module (\d) - Mini Test (\d)', source)
    if m: return f"mod{m.group(1)}-mt{m.group(2)}"
    m = re.match(r'Workout (\w+) - Week (\d) Challenge', source)
    if m: return f"w{m.group(1).lower()}-w{m.group(2)}"
    return "unknown"


os.makedirs('images', exist_ok=True)

# For each source, open the Review PDF and build a page index
# Each Review PDF page has: question number, question text, Your Answer, Correct Answer, Explanation
# We'll use this to match and also to crop question images

results = []
image_saves = []

for source, probs in sorted(by_source.items()):
    review_path = source_to_pdf(source, 'Review')
    questions_path = source_to_pdf(source, 'Questions')

    if not review_path or not os.path.exists(review_path):
        print(f"  SKIP {source} -> Review PDF not found")
        continue

    print(f"\n{source} ({len(probs)} flagged)")

    review_doc = fitz.open(review_path)
    q_doc = fitz.open(questions_path) if questions_path and os.path.exists(questions_path) else None

    # Build index of all review pages: page_idx -> (question_text_snippet, full_text)
    review_pages = []
    for i in range(len(review_doc)):
        text = review_doc[i].get_text()
        # Skip summary/header pages
        if 'Main Question Set' in text or 'Bonus Challenge' in text:
            continue
        if len(text.strip()) < 20:
            continue
        review_pages.append((i, text))

    # Match each flagged problem to a review page
    used_pages = set()
    img_prefix = source_to_img_prefix(source)

    for p in probs:
        issues = flagged[p['id']]
        m = re.match(r'^(\d+)[\.\)]\s', p['text'].strip())
        q_num = int(m.group(1)) if m else 0

        prob_norm = normalize(p['text'])[:200]
        best_page = None
        best_score = 0
        best_idx = None

        for page_idx, page_text in review_pages:
            if page_idx in used_pages:
                continue
            page_norm = normalize(page_text)[:400]
            score = SequenceMatcher(None, prob_norm, page_norm).ratio()
            if score > best_score:
                best_score = score
                best_page = page_text
                best_idx = page_idx

        if best_idx is not None and best_score >= 0.15:
            used_pages.add(best_idx)

        needs_image = 'encoding_corruption' in issues or 'wall_of_text' in issues or 'internal_duplication' in issues

        if needs_image and best_idx is not None:
            # Save the review page as a question image
            # The review page has question + answer, which is actually great for review
            img_name = f"{img_prefix}-q{q_num}.png"
            img_path = f"images/{img_name}"

            # Render at reasonable DPI
            pix = review_doc[best_idx].get_pixmap(dpi=150)

            # If image is too tall, crop to just the question portion (top ~40%)
            # Review pages typically have: question at top, answer in middle, explanation at bottom
            if pix.height > 1200:
                # Crop to top portion (question area)
                rect = fitz.Rect(0, 0, pix.width, pix.height * 0.35)
                page = review_doc[best_idx]
                # Re-render with clip
                clip = fitz.Rect(page.rect.x0, page.rect.y0,
                                 page.rect.x1, page.rect.y0 + page.rect.height * 0.4)
                pix = page.get_pixmap(dpi=150, clip=clip)

            pix.save(img_path)
            img_url = f"https://raw.githubusercontent.com/grrarr/fufu-poshen-loh/master/{img_path}"

            image_saves.append(img_path)
            results.append({
                'id': p['id'],
                'action': 'set_image',
                'imageUrl': img_url,
                'issues': issues,
                'q_num': q_num,
                'source': source,
                'match_score': best_score,
            })
            print(f"  Q{q_num}: saved {img_name} (score={best_score:.2f}) [{', '.join(issues)}]")
        elif needs_image:
            results.append({
                'id': p['id'],
                'action': 'no_match',
                'issues': issues,
                'q_num': q_num,
                'source': source,
            })
            print(f"  Q{q_num}: NO MATCH [{', '.join(issues)}]")
        else:
            results.append({
                'id': p['id'],
                'action': 'text_fix_needed',
                'issues': issues,
                'q_num': q_num,
                'source': source,
                'match_score': best_score if best_idx else 0,
            })
            print(f"  Q{q_num}: text fix needed [{', '.join(issues)}]")

    review_doc.close()
    if q_doc:
        q_doc.close()

# Apply image fixes to the data
applied = 0
for r in results:
    if r['action'] == 'set_image':
        for p in problems:
            if p['id'] == r['id']:
                if not p.get('imageUrl'):
                    p['imageUrl'] = r['imageUrl']
                    applied += 1
                elif p.get('imageUrl') != r['imageUrl']:
                    # Already has a different image, don't overwrite
                    print(f"  Q{r['q_num']} already has imageUrl, skipping")
                break

# Summary
print(f"\n=== Summary ===")
print(f"Total flagged: {len(flagged)}")
print(f"Images saved: {len(image_saves)}")
print(f"Images applied: {applied}")
no_match = [r for r in results if r['action'] == 'no_match']
text_fix = [r for r in results if r['action'] == 'text_fix_needed']
print(f"No PDF match: {len(no_match)}")
print(f"Text fixes needed: {len(text_fix)}")
for r in text_fix:
    print(f"  {r['source']} Q{r['q_num']}: {', '.join(r['issues'])}")

# Save updated data
data['examProblems'] = problems
with open('christopher-psl-data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\nSaved updated data")
