"""
ORIENTATION (for the next LLM reader)
- One job: write `christopher-psl-data.json` (the whole problem bank + progress)
  so a crash mid-write can never leave it truncated.
- Used by the one-off repair scripts: fix_flagged.py, verify_and_fix.py,
  match_via_pdfs.py, extract_answers.py, extract_answer_images.py,
  shrink_images.py (sweep item AW19, _doc-hygiene/proposals/atomic-write-sweep-2026-11-18.md).
- Invariant: bytes on disk match the old `open(path, 'w', encoding='utf-8')` +
  `json.dump(..., ensure_ascii=False, indent=2)` write exactly (text mode, so
  CRLF on Windows). Test: test_psl_io.py.
- Don't: write the real file in place. Dropbox can make os.replace fail with
  PermissionError (WinError 5) for a moment, so retry with backoff; only after
  the retries is the in-place write used as a last resort.
"""
import json
import os
import tempfile
import time

DATA_FILE = 'christopher-psl-data.json'


def save_data(data, path=DATA_FILE, retries=6):
    """Write `data` as JSON to `path` atomically (temp file + os.replace)."""
    path = os.path.abspath(path)
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(prefix='.psl-', suffix='.tmp', dir=d)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        for i in range(retries):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                time.sleep(0.25 * (2 ** i))
        # Dropbox kept the target locked: fall back to an in-place write
        # from the fully written temp copy (still never a half-built payload).
        with open(tmp, 'r', encoding='utf-8', newline='') as src:
            text = src.read()
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
