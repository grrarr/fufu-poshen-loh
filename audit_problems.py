"""
First-pass audit of all exam problems for quality issues.
Outputs a CSV with one row per error found.
"""

import json
import csv
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('christopher-psl-data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

problems = data.get('examProblems', [])

# Group by source to get question numbers
by_source = {}
for p in problems:
    by_source.setdefault(p['source'], []).append(p)

# Build a lookup: problem id -> question number (from text prefix like "1." or position)
def get_q_num(problem):
    m = re.match(r'^(\d+)[\.\)]\s', problem['text'].strip())
    if m:
        return int(m.group(1))
    return None

errors = []

for p in problems:
    pid = p['id']
    source = p['source']
    q_num = get_q_num(p)
    q_label = f"Q{q_num}" if q_num else f"id:{pid}"
    text = p['text']

    # --- 1. Encoding corruption (mojibake) ---
    # UTF-8 decoded as Latin-1 produces sequences like Ã¢, Ã©, Ã, Â
    mojibake_patterns = [
        r'Ã[‚ƒ„…†‡ˆ‰Š‹ŒŽ''""•–—˜™š›œžŸ¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]',
        r'[ÃÂ]{2,}',  # Repeated mojibake chars
        r'â[^\w\s]{1,3}',  # â followed by control-ish chars (e.g., â€™ for apostrophe)
        r'Â[^\w\s]',  # Â followed by non-word
    ]
    for pat in mojibake_patterns:
        if re.search(pat, text):
            # Get a snippet showing the corruption
            match = re.search(pat, text)
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            snippet = text[start:end].replace('\n', ' ')
            errors.append({
                'source': source,
                'question': q_label,
                'issue_type': 'encoding_corruption',
                'detail': f'Mojibake detected: ...{snippet}...',
                'problem_id': pid,
            })
            break  # One error per type per problem

    # --- 2. Excessively long (wall of text) ---
    if len(text) > 2000:
        errors.append({
            'source': source,
            'question': q_label,
            'issue_type': 'wall_of_text',
            'detail': f'Text is {len(text)} chars (likely contains embedded explanation or duplicated content)',
            'problem_id': pid,
        })
    elif len(text) > 800:
        # Moderate length - flag if it lacks structure (no answer choices, no line breaks)
        lines = text.strip().split('\n')
        if len(lines) < 3:
            errors.append({
                'source': source,
                'question': q_label,
                'issue_type': 'long_unstructured',
                'detail': f'Text is {len(text)} chars with only {len(lines)} lines',
                'problem_id': pid,
            })

    # --- 3. Symbol issues (not mojibake, but math symbols lost/garbled) ---
    # Empty parentheses that should contain something
    if re.search(r'\(\s*\)', text) and not re.search(r'f\(\)|g\(\)|h\(\)', text):
        errors.append({
            'source': source,
            'question': q_label,
            'issue_type': 'empty_parens',
            'detail': 'Contains empty parentheses () that may be missing content',
            'problem_id': pid,
        })

    # Orphaned operators: operator at start of line (not negative sign), double operators
    if re.search(r'[+*/=]{2,}', text):
        match = re.search(r'[+*/=]{2,}', text)
        snippet = text[max(0,match.start()-10):match.end()+10].replace('\n',' ')
        errors.append({
            'source': source,
            'question': q_label,
            'issue_type': 'double_operator',
            'detail': f'Double operator: ...{snippet}...',
            'problem_id': pid,
        })

    # Blanks that should have content: multiple underscores or ___ without context
    # (This is normal for fill-in-blank, skip)

    # --- 4. Missing question stem ---
    # Check if the text has any question indicator
    has_question_mark = '?' in text
    has_choices = bool(re.search(r'\([A-E]\)', text) or re.search(r'^[A-E]\)', text, re.MULTILINE))
    has_directive = bool(re.search(r'(?i)(find|determine|evaluate|calculate|solve|compute|what|how many|which|simplify|prove|show)', text))
    has_fill_blank = '___' in text or '= ___' in text

    if not (has_question_mark or has_choices or has_directive or has_fill_blank):
        errors.append({
            'source': source,
            'question': q_label,
            'issue_type': 'no_question',
            'detail': f'No question mark, answer choices, or directive found. First 80 chars: {text[:80]}',
            'problem_id': pid,
        })

    # --- 5. Suspiciously short ---
    if len(text.strip()) < 30:
        errors.append({
            'source': source,
            'question': q_label,
            'issue_type': 'too_short',
            'detail': f'Only {len(text.strip())} chars: {text.strip()}',
            'problem_id': pid,
        })

    # --- 6. Broken answer choices ---
    # If has (A) but missing (B), (C), etc. for MC questions
    if has_choices:
        found_choices = set(re.findall(r'\(([A-E])\)', text))
        if 'A' in found_choices:
            expected = {'A', 'B', 'C', 'D'}
            missing = expected - found_choices
            if missing and len(found_choices) >= 2:
                errors.append({
                    'source': source,
                    'question': q_label,
                    'issue_type': 'incomplete_choices',
                    'detail': f'Has choices {sorted(found_choices)} but missing {sorted(missing)}',
                    'problem_id': pid,
                })

    # --- 7. Unicode oddities (not mojibake but unusual chars) ---
    # Find any non-ASCII that isn't common math/punctuation
    unusual = set()
    for ch in text:
        if ord(ch) > 127:
            # Allow common ones: em-dash, en-dash, smart quotes, degree, multiplication, division, pi, etc.
            allowed = set('\u2013\u2014\u2018\u2019\u201c\u201d\u00b0\u00d7\u00f7\u03c0\u2264\u2265\u2260\u221a\u00b2\u00b3\u00bc\u00bd\u00be\u2212\u2026\u00a0\u2248')
            if ch not in allowed:
                unusual.add(f'U+{ord(ch):04X}({ch})')
    if unusual and not any(e['problem_id'] == pid and e['issue_type'] == 'encoding_corruption' for e in errors):
        # Only flag if not already flagged as mojibake
        errors.append({
            'source': source,
            'question': q_label,
            'issue_type': 'unusual_unicode',
            'detail': f'Contains unusual chars: {", ".join(sorted(list(unusual)[:5]))}',
            'problem_id': pid,
        })

    # --- 8. Duplicated content within problem text ---
    # Check if large chunks of text are repeated within the same problem
    if len(text) > 200:
        # Split into ~100-char chunks and look for repeats
        chunks = [text[i:i+80] for i in range(0, len(text)-80, 80)]
        seen = {}
        for i, chunk in enumerate(chunks):
            normalized = chunk.strip().lower()
            if normalized in seen and i - seen[normalized] > 2:
                errors.append({
                    'source': source,
                    'question': q_label,
                    'issue_type': 'internal_duplication',
                    'detail': f'Text chunk repeated at positions {seen[normalized]*80} and {i*80}: "{chunk[:40]}..."',
                    'problem_id': pid,
                })
                break
            seen[normalized] = i


# Write CSV
csv_path = 'problem_audit.csv'
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['source', 'question', 'issue_type', 'detail', 'problem_id'])
    writer.writeheader()
    # Sort by source then question
    errors.sort(key=lambda e: (e['source'], e['question']))
    for e in errors:
        writer.writerow(e)

# Summary
print(f"Total problems checked: {len(problems)}")
print(f"Total issues found: {len(errors)}")
print(f"\nIssues by type:")
by_type = {}
for e in errors:
    by_type[e['issue_type']] = by_type.get(e['issue_type'], 0) + 1
for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
    print(f"  {t}: {count}")

# Count unique problems with issues
problem_ids_with_issues = set(e['problem_id'] for e in errors)
print(f"\nUnique problems with issues: {len(problem_ids_with_issues)} / {len(problems)} ({100*len(problem_ids_with_issues)/len(problems):.1f}%)")

print(f"\nIssues by source:")
by_source_count = {}
for e in errors:
    by_source_count[e['source']] = by_source_count.get(e['source'], 0) + 1
for s, count in sorted(by_source_count.items(), key=lambda x: -x[1]):
    print(f"  {s}: {count}")

print(f"\nSaved to {csv_path}")
