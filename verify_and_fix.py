"""
Verify image matches by comparing the question number shown in the Review PDF page
with the problem's content. Remove mismatched imageUrls.
Then, for each source with corrupted problems, render ALL Review PDF pages as images
and attempt proper matching using the clean PDF text against garbled bank text.
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
    audit_rows = list(csv.DictReader(f))

flagged = {}
for r in audit_rows:
    pid = int(r['problem_id'])
    flagged.setdefault(pid, []).append(r['issue_type'])


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


os.makedirs('images', exist_ok=True)

# Step 1: Clear all imageUrls that were set by fix_flagged.py for corrupted problems
# (We'll re-do the matching properly)
github_prefix = "https://raw.githubusercontent.com/grrarr/fufu-poshen-loh/master/images/"
cleared = 0
for p in problems:
    if p['id'] in flagged and 'encoding_corruption' in flagged[p['id']]:
        if p.get('imageUrl', '').startswith(github_prefix):
            # Check if this was set by our script (not manually added before)
            img_name = p['imageUrl'].replace(github_prefix, '')
            if re.match(r'mod\d|w\d', img_name):
                p['imageUrl'] = ''
                cleared += 1

print(f"Cleared {cleared} auto-assigned imageUrls from corrupted problems")

# Step 2: For each source with corrupted problems, render ALL Review PDF pages
# and build a clean text index for matching

sources_with_corruption = set()
for p in problems:
    if p['id'] in flagged and 'encoding_corruption' in flagged[p['id']]:
        sources_with_corruption.add(p['source'])

print(f"\nSources with encoding corruption: {len(sources_with_corruption)}")

total_matched = 0
total_failed = 0

for source in sorted(sources_with_corruption):
    review_path = source_to_pdf(source, 'Review')
    if not review_path or not os.path.exists(review_path):
        print(f"  SKIP {source}")
        continue

    print(f"\n{source}")
    doc = fitz.open(review_path)
    img_prefix = source_to_img_prefix(source)

    # Extract all question pages from Review PDF
    # Each page: question number (from PDF), clean text, page index
    pdf_questions = []
    for i in range(len(doc)):
        text = doc[i].get_text()
        if 'Main Question Set' in text or 'Bonus Challenge' in text:
            continue
        if len(text.strip()) < 30:
            continue
        # Get question number from the PDF page
        lines = text.strip().split('\n')
        q_num_pdf = None
        for line in lines[:3]:
            if line.strip().isdigit():
                q_num_pdf = int(line.strip())
                break
        if q_num_pdf is None:
            continue
        # Get question text (between q number and "Your Answer")
        ya_pos = text.find('Your Answer')
        if ya_pos > 0:
            q_text = text[text.find('\n')+1:ya_pos].strip()
        else:
            q_text = text[text.find('\n')+1:300].strip()

        pdf_questions.append({
            'page_idx': i,
            'q_num_pdf': q_num_pdf,
            'clean_text': q_text,
            'clean_norm': normalize(q_text),
        })

    print(f"  Found {len(pdf_questions)} questions in Review PDF")

    # Get corrupted problems for this source
    corrupted = [p for p in problems if p['source'] == source and p['id'] in flagged
                 and 'encoding_corruption' in flagged[p['id']]]

    # Match each corrupted bank problem to a PDF question
    used_pdf_pages = set()

    for p in corrupted:
        m = re.match(r'^(\d+)[\.\)]\s', p['text'].strip())
        q_num_bank = int(m.group(1)) if m else 0

        bank_norm = normalize(p['text'])[:300]

        best = None
        best_score = 0

        for pq in pdf_questions:
            if pq['page_idx'] in used_pdf_pages:
                continue

            # Compare normalized texts
            pdf_norm = pq['clean_norm'][:300]
            score = SequenceMatcher(None, bank_norm, pdf_norm).ratio()

            # Also check keyword overlap
            bank_words = set(bank_norm.split())
            pdf_words = set(pdf_norm.split())
            if bank_words and pdf_words:
                overlap = len(bank_words & pdf_words) / max(len(bank_words), len(pdf_words))
                score = score * 0.5 + overlap * 0.5

            if score > best_score:
                best_score = score
                best = pq

        if best and best_score >= 0.12:
            used_pdf_pages.add(best['page_idx'])

            # Save cropped image (question portion only)
            img_name = f"{img_prefix}-q{q_num_bank}.png"
            img_path = f"images/{img_name}"

            page = doc[best['page_idx']]
            # Crop to question area (top ~40% of page)
            clip = fitz.Rect(page.rect.x0, page.rect.y0,
                             page.rect.x1, page.rect.y0 + page.rect.height * 0.4)
            pix = page.get_pixmap(dpi=150, clip=clip)
            pix.save(img_path)

            img_url = f"{github_prefix}{img_name}"
            p['imageUrl'] = img_url
            total_matched += 1

            match_label = "GOOD" if best_score > 0.3 else "LOW"
            print(f"  Q{q_num_bank} -> PDF Q{best['q_num_pdf']} ({match_label} score={best_score:.2f}) -> {img_name}")
        else:
            total_failed += 1
            print(f"  Q{q_num_bank}: NO MATCH (best={best_score:.2f})")

    doc.close()

# Step 3: Handle the non-corruption text fixes
# For too_short and incomplete_choices, let's check the actual problems
print(f"\n=== Text Fix Problems ===")
text_fix_problems = [p for p in problems if p['id'] in flagged
                     and 'encoding_corruption' not in flagged[p['id']]]

for p in text_fix_problems:
    issues = flagged[p['id']]
    m = re.match(r'^(\d+)[\.\)]\s', p['text'].strip())
    q_num = int(m.group(1)) if m else '?'
    print(f"  {p['source']} Q{q_num}: {', '.join(issues)}")
    print(f"    Text ({len(p['text'])} chars): {p['text'][:120]}...")
    if 'too_short' in issues:
        # Check if the problem is actually complete (some are legitimately short)
        if '?' in p['text'] or '=' in p['text'] or 'evaluate' in p['text'].lower():
            print(f"    -> Looks complete despite being short")
    if 'incomplete_choices' in issues:
        choices = re.findall(r'\(([A-E])\)', p['text'])
        print(f"    -> Found choices: {choices}")

# Save
data['examProblems'] = problems
with open('christopher-psl-data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n=== Final Summary ===")
print(f"Corruption matches: {total_matched}")
print(f"Corruption no-match: {total_failed}")
print(f"Text-fix problems: {len(text_fix_problems)}")
has_img = sum(1 for p in problems if p.get('imageUrl','').strip())
print(f"Total problems with images: {has_img} / {len(problems)}")
