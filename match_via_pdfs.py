"""
Match bank problems to Review PDF pages using text similarity.
Each Review PDF page has: question at top, Your Answer, Correct Answer, Explanation.
We match the REVIEW page's question text to the bank problem text.
Then save the answer portion of that Review page as the answer image.

No reliance on question numbers or Questions PDFs.
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


def source_to_review_pdf(source):
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


def extract_review_pages(doc):
    """Extract question pages from Review PDF.
    Returns list of (page_idx, question_text_for_matching, full_text)."""
    pages = []
    for i in range(len(doc)):
        text = doc[i].get_text().strip()
        # Skip summary/header/footer pages
        if any(skip in text for skip in ['Main Question Set', 'Bonus Challenge',
               'Click here to return', 'Software by', 'Privacy Policy']):
            continue
        if len(text) < 50:
            continue
        # Must have "Your Answer" or "Correct Answer" to be a question page
        if 'Your Answer' not in text and 'Correct Answer' not in text:
            continue

        # Extract question text (everything before "Your Answer")
        ya_pos = text.find('Your Answer')
        if ya_pos > 0:
            q_text = text[:ya_pos].strip()
        else:
            q_text = text[:300].strip()

        # Remove question number from start
        q_text_clean = re.sub(r'^\d+\s*\n?', '', q_text).strip()

        pages.append((i, q_text_clean, text))
    return pages


sources = sorted(set(p['source'] for p in problems))
total_matched = 0
total_no_pdf = 0

for source in sources:
    r_path = source_to_review_pdf(source)
    if not r_path or not os.path.exists(r_path):
        source_count = sum(1 for p in problems if p['source'] == source)
        total_no_pdf += source_count
        continue

    source_problems = [p for p in problems if p['source'] == source
                       and not p.get('answerImageUrl', '').strip()]
    if not source_problems:
        continue

    print(f"\n{source} ({len(source_problems)} need answers)")

    doc = fitz.open(r_path)
    img_prefix = source_to_img_prefix(source)
    review_pages = extract_review_pages(doc)
    print(f"  Review PDF: {len(review_pages)} question pages")

    # For each bank problem, find the best matching Review page
    used_review_pages = set()

    for p in source_problems:
        bank_norm = normalize(p['text'])[:300]

        best_page_idx = None
        best_score = 0
        best_q_text = None

        for r_idx, r_q_text, r_full in review_pages:
            if r_idx in used_review_pages:
                continue

            r_norm = normalize(r_q_text)[:300]

            # Sequence matching
            seq_score = SequenceMatcher(None, bank_norm, r_norm).ratio()

            # Keyword overlap (more weight)
            bank_words = set(w for w in bank_norm.split() if len(w) > 3)
            r_words = set(w for w in r_norm.split() if len(w) > 3)
            if bank_words and r_words:
                overlap = len(bank_words & r_words) / min(len(bank_words), len(r_words))
            else:
                overlap = 0

            score = seq_score * 0.4 + overlap * 0.6

            if score > best_score:
                best_score = score
                best_page_idx = r_idx
                best_q_text = r_q_text

        # Get bank question number for filename
        m = re.match(r'^(\d+)[\.\)]\s', p['text'].strip())
        bank_q_num = int(m.group(1)) if m else 0

        if best_page_idx is None or best_score < 0.25:
            print(f"  Q{bank_q_num}: NO MATCH (best={best_score:.2f})")
            continue

        used_review_pages.add(best_page_idx)

        # Save the answer portion of the Review page
        page = doc[best_page_idx]

        # Find where "Your Answer" starts on the page to crop just the answer portion
        # We'll crop from ~20% down to bottom (skip question, show answer+explanation)
        clip = fitz.Rect(
            page.rect.x0,
            page.rect.y0 + page.rect.height * 0.2,
            page.rect.x1,
            page.rect.y1
        )
        pix = page.get_pixmap(dpi=150, clip=clip)

        img_name = f"{img_prefix}-q{bank_q_num}-answer.png"
        img_path = f"images/{img_name}"
        pix.save(img_path)

        p['answerImageUrl'] = GITHUB_BASE + img_name
        total_matched += 1

        size_kb = os.path.getsize(img_path) / 1024
        # Show first few words of both texts for verification
        bank_preview = p['text'][:60].replace('\n', ' ')
        review_preview = (best_q_text or '')[:60].replace('\n', ' ')
        print(f"  Q{bank_q_num} (score={best_score:.2f})")
        print(f"    Bank: {bank_preview}")
        print(f"    PDF:  {review_preview}")

    doc.close()

# Save
data['examProblems'] = problems
with open('christopher-psl-data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n=== Summary ===")
print(f"Answer images matched: {total_matched}")
print(f"No Review PDF: {total_no_pdf}")
has_ans_img = sum(1 for p in problems if p.get('answerImageUrl', '').strip())
print(f"Total with answer images: {has_ans_img} / {len(problems)}")
