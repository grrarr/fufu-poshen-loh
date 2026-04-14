"""
Render PDF pages for all flagged problems using content-based matching.
Since exams randomize question order, we match by text similarity, not Q number.
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
    reader = csv.DictReader(f)
    audit_rows = list(reader)

flagged_ids = set(int(r['problem_id']) for r in audit_rows)
print(f"Flagged problem IDs: {len(flagged_ids)}")

flagged_by_source = {}
for p in problems:
    if p['id'] in flagged_ids:
        flagged_by_source.setdefault(p['source'], []).append(p)


def source_to_pdf(source, pdf_type='Questions'):
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
    """Strip formatting for matching."""
    # Remove question number prefix
    text = re.sub(r'^\d+[\.\)]\s*', '', text)
    text = re.sub(r'\s+', ' ', text).strip().lower()
    # Remove mojibake chars
    text = re.sub(r'[^\x00-\x7f]', '', text)
    # Remove punctuation
    text = re.sub(r'[^a-z0-9 ]', '', text)
    return text


def extract_keywords(text):
    """Get distinctive words from problem text for matching."""
    norm = normalize(text)
    words = norm.split()
    # Filter out very common/short words
    stop = {'the', 'a', 'an', 'is', 'are', 'of', 'in', 'to', 'and', 'or', 'for', 'that',
            'this', 'with', 'be', 'it', 'on', 'as', 'at', 'by', 'if', 'we', 'do', 'its'}
    return [w for w in words if len(w) > 2 and w not in stop]


def find_best_page(doc, problem_text, exclude_pages=None):
    """Find the PDF page that best matches the problem text by content."""
    if exclude_pages is None:
        exclude_pages = set()

    keywords = extract_keywords(problem_text)[:15]
    if not keywords:
        return None, 0

    best_page = None
    best_score = 0

    for page_idx in range(len(doc)):
        if page_idx in exclude_pages:
            continue
        page_text = doc[page_idx].get_text()
        page_norm = normalize(page_text)

        # Count keyword hits
        hits = sum(1 for kw in keywords if kw in page_norm)
        score = hits / len(keywords) if keywords else 0

        # Also try sequence matching on first 200 chars
        prob_norm = normalize(problem_text)[:200]
        page_norm_short = page_norm[:400]
        seq_score = SequenceMatcher(None, prob_norm, page_norm_short).ratio()

        combined = score * 0.6 + seq_score * 0.4

        if combined > best_score:
            best_score = combined
            best_page = page_idx

    return best_page, best_score


os.makedirs('_audit_pages', exist_ok=True)
mapping = []

for source, probs in sorted(flagged_by_source.items()):
    pdf_path = source_to_pdf(source, 'Questions')
    review_pdf_path = source_to_pdf(source, 'Review')

    if not pdf_path or not os.path.exists(pdf_path):
        print(f"  SKIP {source} -> PDF not found: {pdf_path}")
        continue

    print(f"\n{source} ({len(probs)} flagged)")

    doc = fitz.open(pdf_path)
    review_doc = None
    if review_pdf_path and os.path.exists(review_pdf_path):
        review_doc = fitz.open(review_pdf_path)

    used_q_pages = set()
    used_r_pages = set()

    for p in probs:
        m = re.match(r'^(\d+)[\.\)]\s', p['text'].strip())
        q_num = int(m.group(1)) if m else '?'

        issue_types = [r['issue_type'] for r in audit_rows if int(r['problem_id']) == p['id']]

        # Find best matching page in Questions PDF
        best_page, score = find_best_page(doc, p['text'], used_q_pages)

        if best_page is None or score < 0.15:
            print(f"  Q{q_num}: NO MATCH (best score={score:.2f})")
            mapping.append({
                'source': source, 'q_num': q_num, 'problem_id': p['id'],
                'questions_img': 'NOT_FOUND', 'review_img': '',
                'issues': ', '.join(issue_types), 'text_len': len(p['text']),
                'match_score': f'{score:.2f}',
            })
            continue

        used_q_pages.add(best_page)

        safe_source = re.sub(r'[^a-zA-Z0-9]', '_', source).strip('_')
        filename = f"{safe_source}_Q{q_num}.png"
        pix = doc[best_page].get_pixmap(dpi=150)
        pix.save(f'_audit_pages/{filename}')

        # Find matching Review page
        review_filename = ''
        if review_doc:
            r_page, r_score = find_best_page(review_doc, p['text'], used_r_pages)
            if r_page is not None and r_score >= 0.15:
                used_r_pages.add(r_page)
                review_filename = f"{safe_source}_Q{q_num}_review.png"
                pix2 = review_doc[r_page].get_pixmap(dpi=150)
                pix2.save(f'_audit_pages/{review_filename}')

        mapping.append({
            'source': source, 'q_num': q_num, 'problem_id': p['id'],
            'questions_img': filename, 'review_img': review_filename,
            'issues': ', '.join(issue_types), 'text_len': len(p['text']),
            'match_score': f'{score:.2f}',
        })

        print(f"  Q{q_num}: {filename} (score={score:.2f}) [{', '.join(issue_types)}]")

    doc.close()
    if review_doc:
        review_doc.close()

with open('_audit_pages/_mapping.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['source', 'q_num', 'problem_id', 'questions_img', 'review_img', 'issues', 'text_len', 'match_score'])
    writer.writeheader()
    for m in mapping:
        writer.writerow(m)

found = sum(1 for m in mapping if m['questions_img'] != 'NOT_FOUND')
print(f"\nRendered {found}/{len(mapping)} pages to _audit_pages/")
