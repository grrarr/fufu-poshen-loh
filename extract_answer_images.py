"""
For every problem that lacks an explanation (cleared due to garbled math),
render the answer+explanation portion of the corresponding Review PDF page
and save as an answer image.
"""

import fitz
import json
import os
import re
import sys
import io
from difflib import SequenceMatcher

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('christopher-psl-data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
problems = data['examProblems']

GITHUB_BASE = "https://raw.githubusercontent.com/grrarr/fufu-poshen-loh/master/images/"
os.makedirs('images', exist_ok=True)


def source_to_pdf(source):
    if source == 'Module 3 - Final Exam':
        return 'brillium emails/Module 3 - Final Challenge (Review).pdf'
    m = re.match(r'Module 3 - Mini Test (\d)', source)
    if m:
        return f'brillium emails/Module 3 - W{m.group(1)} Challenge (Review).pdf'
    m = re.match(r'(.+) - Week (\d) Challenge', source)
    if m:
        return f'brillium emails/{m.group(1)} - W{m.group(2)} Challenge (Review).pdf'
    m = re.match(r'(.+) - Final Challenge', source)
    if m:
        return f'brillium emails/{m.group(1)} - Final Challenge (Review).pdf'
    return None


def source_to_img_prefix(source):
    m = re.match(r'Module (\d) - Week (\d) Challenge', source)
    if m: return f"mod{m.group(1)}-w{m.group(2)}"
    m = re.match(r'Module (\d) - Final (?:Challenge|Exam)', source)
    if m: return f"mod{m.group(1)}-final"
    m = re.match(r'Module (\d) - Mini Test (\d)', source)
    if m: return f"mod{m.group(1)}-mt{m.group(2)}"
    m = re.match(r'Workout (\w+) - Week (\d) Challenge', source)
    if m: return f"w{m.group(1).lower()}-w{m.group(2)}"
    return "unknown"


def normalize(text):
    text = re.sub(r'^\d+[\.\)]\s*', '', text)
    text = re.sub(r'\s+', ' ', text).strip().lower()
    text = re.sub(r'[^\x00-\x7f]', '', text)
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# Find all problems that need answer images
# (no explanation AND no answerImageUrl)
needs_answer_img = [p for p in problems
                    if not p.get('explanation', '').strip()
                    and not p.get('answerImageUrl', '').strip()]

print(f"Problems needing answer images: {len(needs_answer_img)}")

# Group by source
by_source = {}
for p in needs_answer_img:
    by_source.setdefault(p['source'], []).append(p)

total_saved = 0
total_failed = 0

for source, probs in sorted(by_source.items()):
    review_path = source_to_pdf(source)
    if not review_path or not os.path.exists(review_path):
        print(f"  SKIP {source} -> no Review PDF")
        total_failed += len(probs)
        continue

    print(f"\n{source} ({len(probs)} problems)")
    doc = fitz.open(review_path)
    img_prefix = source_to_img_prefix(source)

    # Build index of review pages
    review_pages = []
    for i in range(len(doc)):
        text = doc[i].get_text()
        if 'Main Question Set' in text or 'Bonus Challenge' in text:
            continue
        if len(text.strip()) < 30:
            continue
        # Get question number
        lines = text.strip().split('\n')
        q_num_pdf = None
        for line in lines[:3]:
            if line.strip().isdigit():
                q_num_pdf = int(line.strip())
                break
        if q_num_pdf is None:
            continue
        review_pages.append((i, q_num_pdf, text))

    # Match each problem to a review page
    used_pages = set()

    for p in probs:
        m = re.match(r'^(\d+)[\.\)]\s', p['text'].strip())
        q_num = int(m.group(1)) if m else 0

        prob_norm = normalize(p['text'])[:300]
        best_page_idx = None
        best_score = 0

        for page_idx, pdf_q_num, page_text in review_pages:
            if page_idx in used_pages:
                continue
            page_norm = normalize(page_text)[:400]
            score = SequenceMatcher(None, prob_norm, page_norm).ratio()

            # Keyword overlap
            bank_words = set(prob_norm.split())
            pdf_words = set(page_norm.split())
            if bank_words and pdf_words:
                overlap = len(bank_words & pdf_words) / max(len(bank_words), len(pdf_words))
                score = score * 0.5 + overlap * 0.5

            if score > best_score:
                best_score = score
                best_page_idx = page_idx

        if best_page_idx is None or best_score < 0.12:
            print(f"  Q{q_num}: NO MATCH (best={best_score:.2f})")
            total_failed += 1
            continue

        used_pages.add(best_page_idx)

        # Render the ANSWER portion of the review page (bottom ~65%)
        page = doc[best_page_idx]
        # Crop: skip the question area at top, show answer + explanation
        clip = fitz.Rect(
            page.rect.x0,
            page.rect.y0 + page.rect.height * 0.25,  # Start at 25% (after question)
            page.rect.x1,
            page.rect.y1  # To bottom
        )
        pix = page.get_pixmap(dpi=150, clip=clip)

        img_name = f"{img_prefix}-q{q_num}-answer.png"
        img_path = f"images/{img_name}"
        pix.save(img_path)

        img_url = GITHUB_BASE + img_name
        p['answerImageUrl'] = img_url
        total_saved += 1

        size_kb = os.path.getsize(img_path) / 1024
        print(f"  Q{q_num}: {img_name} ({size_kb:.0f} KB, score={best_score:.2f})")

    doc.close()

# Save
data['examProblems'] = problems
with open('christopher-psl-data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n=== Summary ===")
print(f"Answer images saved: {total_saved}")
print(f"Failed to match: {total_failed}")
has_ans_img = sum(1 for p in problems if p.get('answerImageUrl', '').strip())
has_expl = sum(1 for p in problems if p.get('explanation', '').strip())
print(f"Problems with answer images: {has_ans_img}")
print(f"Problems with text explanations: {has_expl}")
print(f"Problems with either: {sum(1 for p in problems if p.get('answerImageUrl','').strip() or p.get('explanation','').strip())}")
