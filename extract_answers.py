"""
Extract answers and explanations from Review PDFs and match to problem bank entries.
Matches by text similarity (not question order) since exams randomize questions.
Also migrates "Answer: X" from notes to the answer field.
"""

import fitz
import json
import os
import re
import glob
from difflib import SequenceMatcher


def pdf_name_to_source(pdf_basename):
    """Map PDF basename to problem bank source name."""
    # Module 3 uses different naming in the bank
    if pdf_basename.startswith("Module 3"):
        if "Final" in pdf_basename:
            return "Module 3 - Final Exam"
        # W1 -> Mini Test 1, W2 -> Mini Test 2, etc.
        m = re.search(r'W(\d)', pdf_basename)
        if m:
            return f"Module 3 - Mini Test {m.group(1)}"

    # For all others, expand W1 -> Week 1, etc.
    m = re.search(r'W(\d)', pdf_basename)
    if m:
        expanded = pdf_basename.replace(f"W{m.group(1)}", f"Week {m.group(1)}")
        return expanded

    # Final Challenge stays as-is
    return pdf_basename


def extract_questions_from_pdf(pdf_path):
    """Extract question number, text snippet, correct answer, and explanation from a Review PDF."""
    doc = fitz.open(pdf_path)
    questions = []

    # Skip page 0 (header/summary page)
    for page_idx in range(1, len(doc)):
        text = doc[page_idx].get_text()
        if not text.strip():
            continue

        # Each question page starts with the question number
        lines = text.split('\n')

        # Find question number (first line should be a number)
        q_num = None
        for line in lines[:3]:
            stripped = line.strip()
            if stripped.isdigit():
                q_num = int(stripped)
                break

        if q_num is None:
            continue

        # Find "Your Answer", "Correct Answer", "Explanation" markers
        full_text = text

        # Extract the question text (between question number and "Your Answer")
        your_answer_pos = full_text.find('Your Answer')
        if your_answer_pos == -1:
            continue

        # Question text is everything from after the question number to "Your Answer"
        q_start = full_text.find('\n') + 1  # Skip the question number line
        question_text = full_text[q_start:your_answer_pos].strip()

        # Extract correct answer (between "Correct Answer" and "Explanation")
        correct_answer_pos = full_text.find('Correct Answer', your_answer_pos + 10)
        if correct_answer_pos == -1:
            correct_answer_pos = full_text.find('Correct Answer')

        explanation_pos = full_text.find('Explanation', correct_answer_pos + 10 if correct_answer_pos != -1 else 0)

        correct_answer = ''
        explanation = ''

        if correct_answer_pos != -1 and explanation_pos != -1:
            correct_answer = full_text[correct_answer_pos + len('Correct Answer'):explanation_pos].strip()
            explanation = full_text[explanation_pos + len('Explanation'):].strip()
        elif correct_answer_pos != -1:
            correct_answer = full_text[correct_answer_pos + len('Correct Answer'):].strip()

        # Also grab "Your Answer" for reference
        your_answer = ''
        if your_answer_pos != -1 and correct_answer_pos != -1:
            your_answer = full_text[your_answer_pos + len('Your Answer'):correct_answer_pos].strip()

        questions.append({
            'number': q_num,
            'question_snippet': question_text[:200],  # First 200 chars for matching
            'correct_answer': correct_answer,
            'explanation': explanation,
            'your_answer': your_answer,
        })

    doc.close()
    return questions


def normalize_for_matching(text):
    """Normalize text for fuzzy matching - strip formatting, numbers, whitespace."""
    # Remove question number prefix like "1." or "1)"
    text = re.sub(r'^\d+[\.\)]\s*', '', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip().lower()
    # Remove punctuation except letters and digits
    text = re.sub(r'[^a-z0-9 ]', '', text)
    return text


def match_pdf_to_problems(pdf_questions, bank_problems):
    """Match PDF-extracted questions to bank problems by text similarity."""
    matches = []
    used_problem_ids = set()

    for pq in pdf_questions:
        pdf_norm = normalize_for_matching(pq['question_snippet'])
        if len(pdf_norm) < 10:
            continue

        best_match = None
        best_score = 0

        for bp in bank_problems:
            if bp['id'] in used_problem_ids:
                continue

            bank_norm = normalize_for_matching(bp['text'][:300])

            # Use SequenceMatcher for similarity
            score = SequenceMatcher(None, pdf_norm[:150], bank_norm[:150]).ratio()

            # Also try matching by question number if text in bank starts with "N."
            bank_q_num = None
            m = re.match(r'^(\d+)[\.\)]', bp['text'].strip())
            if m:
                bank_q_num = int(m.group(1))

            # Boost score if question numbers match
            if bank_q_num == pq['number']:
                score += 0.15

            if score > best_score:
                best_score = score
                best_match = bp

        if best_match and best_score > 0.3:
            matches.append({
                'problem_id': best_match['id'],
                'correct_answer': pq['correct_answer'],
                'explanation': pq['explanation'],
                'score': best_score,
                'pdf_q_num': pq['number'],
            })
            used_problem_ids.add(best_match['id'])
        else:
            print(f"    No match for PDF Q{pq['number']} (best score: {best_score:.2f})")
            print(f"      Snippet: {pq['question_snippet'][:80]}...")

    return matches


def migrate_note_answers(problems):
    """Move 'Answer: X' from note field to answer field."""
    count = 0
    for p in problems:
        note = p.get('note', '')
        if note.startswith('Answer:') or note.startswith('Answer :'):
            answer_text = re.sub(r'^Answer\s*:\s*', '', note).strip()
            if not p.get('answer'):
                p['answer'] = answer_text
                p['note'] = ''
                count += 1
    return count


def main():
    # Load problem bank
    with open('christopher-psl-data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    problems = data.get('examProblems', [])
    print(f"Loaded {len(problems)} problems")

    # Ensure all problems have answer and explanation fields
    for p in problems:
        if 'answer' not in p:
            p['answer'] = ''
        if 'explanation' not in p:
            p['explanation'] = ''

    # Step 1: Migrate "Answer: X" from notes
    migrated = migrate_note_answers(problems)
    print(f"Migrated {migrated} answers from notes")

    # Step 2: Process Review PDFs
    review_pdfs = sorted(glob.glob('brillium emails/*Review*.pdf'))
    print(f"\nProcessing {len(review_pdfs)} Review PDFs...")

    total_matched = 0
    total_extracted = 0

    for pdf_path in review_pdfs:
        basename = os.path.basename(pdf_path).replace(' (Review).pdf', '')
        source = pdf_name_to_source(basename)

        # Find matching problems in bank
        source_problems = [p for p in problems if p['source'] == source]
        if not source_problems:
            print(f"\n  SKIP {basename} -> no problems with source '{source}'")
            continue

        print(f"\n  {basename} -> '{source}' ({len(source_problems)} problems)")

        # Extract from PDF
        pdf_questions = extract_questions_from_pdf(pdf_path)
        total_extracted += len(pdf_questions)
        print(f"    Extracted {len(pdf_questions)} questions from PDF")

        # Match
        matches = match_pdf_to_problems(pdf_questions, source_problems)
        print(f"    Matched {len(matches)} questions")

        # Apply matches
        for match in matches:
            for p in problems:
                if p['id'] == match['problem_id']:
                    if not p['answer'] and match['correct_answer']:
                        p['answer'] = match['correct_answer']
                        total_matched += 1
                    if not p['explanation'] and match['explanation']:
                        p['explanation'] = match['explanation']
                    break

    # Summary
    has_answer = sum(1 for p in problems if p.get('answer'))
    has_explanation = sum(1 for p in problems if p.get('explanation'))
    print(f"\n=== Summary ===")
    print(f"Total problems: {len(problems)}")
    print(f"With answers: {has_answer}")
    print(f"With explanations: {has_explanation}")
    print(f"New answers from PDFs: {total_matched}")
    print(f"Migrated from notes: {migrated}")

    # Save
    data['examProblems'] = problems
    with open('christopher-psl-data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to christopher-psl-data.json")


if __name__ == '__main__':
    main()
