# Christopher's Po-Shen Loh Progress — Claude Code Context

## What this is

An interactive progress tracker for Christopher's Po-Shen Loh math curriculum. Single HTML file hosted on GitHub Pages. Tracks completion % across 6 modules and 6 workouts, plus spaced repetition note progress and manual exam flags.

**App URL**: https://grrarr.github.io/fufu-poshen-loh/
**Repo**: https://github.com/grrarr/fufu-poshen-loh
**Source**: `index.html` (single file — React + Babel standalone, localStorage for persistence)
**Extraction Guide**: `poshen-loh-extraction-guide.md` — comprehensive reference for Claude in Chrome exam extraction sessions (see below)

---

## Overview

### The curriculum structure:
- **6 Modules** (0-5): Introduction → Algebra Basics → Geometry Tools → Algebra Tools → Combinatorics Tools → Number Theory Tools
- **6 Workouts** (1A, 1B, 2A, 3A, 4A, 5A): Aligned to modules for practice

### Tracking five things:
1. **Progress %** — Completion level (0–100%). Note: percentages can be deceptive (e.g., 98% might not mean final exam is done)
2. **Spaced rep notes** — Checkbox + comment field to track note-taking progress (e.g., "days 2-3 done, 5 and 9 needed")
3. **TODOs** — Per-module/workout checkbox + comment for action items (exams to do, formulas to write down)
4. **Manual flags** — Free-form notes for exams not done, topics needing review, etc.
5. **Exam Problem Bank** — Extracted problems from mini tests and final exams with triage workflow

---

## Using the app

### In the browser:
- **Update progress %**: Drag the slider for any module/workout
- **Toggle spaced rep notes**: Check the checkbox, then add a comment (e.g., "lessons 1-10 noted, 14-15 missing")
- **Track TODOs**: Check "Has TODOs" on any card, add notes like "need to do Exam 2, write formulas for X"
- **Add manual flags**: Write flags like "Module 0 - Exam 2 not done" and click "Add Flag"
- **Export/Import backups**: Use buttons in header toolbar
- All changes auto-save to localStorage and backup

### GitHub sync (optional):
1. Click the **GH** button in the top-right (gray if offline)
2. Paste your GitHub Personal Access Token (PAT with `repo` scope)
3. Click **Save Token**
4. Status changes to **● GH** (green, synced)
5. All future changes auto-sync to `christopher-psl-data.json` in the repo
6. Sync status and last updated timestamp shown in header
7. Click **Disconnect** to disable GitHub sync and revert to localStorage-only

**To create a GitHub PAT:**
- Go to https://github.com/settings/tokens
- Click "Generate new token (classic)"
- Scopes: check `repo` (full control of private repositories)
- Copy the token and paste into the app

### From Claude Code:
Most updates are done in the browser. If you need to manually edit data:
- Edit `index.html` → find `DEFAULT_DATA` object → update module/workout values
- Or the app syncs to `christopher-psl-data.json` which you can also edit directly
- Commit and push
- Refresh the browser to reload

---

## Rules

- **At the start of every session, display the app URL**: https://grrarr.github.io/fufu-poshen-loh/
- **Be autonomous** — Don't ask for confirmation on routine commits/pushes. Just do them.
- **Always `git push` after committing** — The app is served from GitHub Pages
- **The `DEFAULT_DATA` object is the rebuild safety net** — Keep it at the top of `index.html` with all 6 modules + 6 workouts, even if they're overridden by localStorage
- **Storage keys (DO NOT CHANGE)**:
  - `christopher-psl-v1` (primary)
  - `christopher-psl-v1-backup` (backup)
- **On load**: App tries primary storage → backup → merges with `DEFAULT_DATA` (keeps newer values)
- **No emoji or unicode in data** — Source names, problem text, and notes must be plain ASCII/standard characters only. Never include progress bars (█), emoji, or other unicode decoration in source names or problem fields. This previously bloated the JSON from 0.2 MB to 1.04 MB and broke GitHub sync.

---

## Key architectural notes

- Single `index.html` file — React 18 + Babel standalone via CDN
- `window.storage` shim wraps `localStorage`
- Percentages are tracked but **should be manually verified** — some internal structures weight final exams heavily (e.g., 1/1), so 98% ≠ final exam complete
- Spaced rep notes are typically **in-progress**, not all-or-nothing — use the comment field to track which lessons/days are done
- Manual flags section is for exam statuses, topics to revisit, or other loose ends
- **Exam Problem Bank** stores extracted problems with triage statuses:
  - `untriaged` — Not yet reviewed
  - `trivial` — He knows it cold, hidden by default in "All" view
  - `needs-review` — Can't solve or might forget, candidate for spaced rep
  - `needs-formula` — Needs a "write down this formula/algorithm" concept card created in spaced rep
  - `promoted` — Already added to fufu-spaced-rep as a card
- Problems are added via bulk paste (separated by blank lines) with a source tag (e.g., "Module 3 - Final Exam")
- Intended workflow: Extract via Claude in Chrome → paste into bank → triage → promote hard ones to spaced rep
- Problems can have an attached **image URL** — for geometry diagrams, figures, tables, charts, etc.
  - Prefer using the original image URL from the PSL platform (grab via right-click → Copy Image Address)
  - If PSL URLs expire, fall back to hosting in `images/` folder in the repo
  - Fallback URLs served via `https://raw.githubusercontent.com/grrarr/fufu-poshen-loh/master/images/FILENAME`
  - Naming convention: `mod{N}-mt{N}-q{N}.png` (mini test), `mod{N}-final-q{N}.png` (final), `w{X}-mt{N}-q{N}.png` / `w{X}-final-q{N}.png` (workouts)
  - Click "+ Image" on any problem card to attach a URL
  - Displayed inline with white background (for diagrams on white)

---

## GitHub deployment & API sync

- **GitHub Pages**: Hosted at https://grrarr.github.io/fufu-poshen-loh/
- **Repository**: `grrarr/fufu-poshen-loh` (branch: `master`)
- **Data sync file**: `christopher-psl-data.json` (auto-created on first sync)
- **Auto-deploys** on every push (~30 seconds)
- **GitHub CLI**: Already set up with `gh auth login` for autonomous repo operations (Claude Code uses this for commits/pushes)

---

## Extracting exam problems with Claude in Chrome

**Full reference:** `poshen-loh-extraction-guide.md` — covers all 11 sections in detail. Read it before any extraction session.

### Key things the guide covers that aren't in this file:
- **Brillium platform navigation** (§2-3): How to access exams via hidden form submission (`#exam__form`), landing page scenarios (Confirm Start, Confirm Login, Summary/0%), and exam timer warnings (60-75 min)
- **MathJax extraction** (§4): `innerHTML` is blocked by browser security — must use `querySelectorAll` on MathML elements (`msup`, `mfrac`, `msqrt`, `mroot`). `textContent` is lossy (strips exponents/fractions)
- **Image handling** (§5): NEVER screenshot images — only extract `<img>` src URLs. JS pattern for filtering out logos included
- **React form input workaround** (§7): Standard `.value =` doesn't trigger React state. Must use `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set` pattern
- **Christopher's Module 3 scores** (§6): W1=80%, W2=100%, W3=60%, W4=60%, Final=40%
- **Complete per-exam workflow** (§9): 12-step checklist from course page → Brillium → extraction → assembly
- **10 common gotchas** (§10): Gray overlay, innerHTML blocked, timed-out attempts, dark tracker app, MathJax lossy textContent, React inputs, exam timers, retake limits, scrollable containers, image size errors

### Quick reference — source naming convention
| PSL Exam Name | Tracker Source Name |
|---|---|
| Week N Challenge | Module X - Mini Test N |
| Final Challenge | Module X - Final Exam |

### Triage session (separate step, with Christopher)
Go through untriaged problems together:
- He solves it instantly → **Trivial**
- He's unsure or gets it wrong → **Needs Review**
- He doesn't know the formula/method → **Needs Formula** (note which formula)
- Already added to fufu-spaced-rep → **In Spaced Rep**

### PDF generation for exams
For every exam retake, generate **two PDFs**:
1. **Questions-only PDF** — save BEFORE filling in answers (clean exam)
2. **Review PDF (Q+A)** — save AFTER submitting with a passing score (shows correct answers)

Both are generated via playwright (headless Chromium, separate from Chrome MCP). Launch the questions PDF as a background agent immediately after landing on the questions page, before filling answers.

**Naming convention:**
```
Module 0 - W4 Challenge (Questions).pdf   # questions only
Module 0 - W4 Challenge (Review).pdf      # questions + answers
```

### Brillium retake workflow (proven process)
1. Navigate to course exam page → submit hidden `#exam__form` (target='_self')
2. Confirm Start page (a=L3) → click Continue. Or Confirm Login (a=S1) → click Start Answering Questions
3. Questions page (a=Q1) loads → launch Questions PDF agent in background (playwright, separate browser)
4. Extract questions via `get_page_text` + MathML queries (`msup`, `mfrac`, `msqrt`)
5. Solve questions, fill answers via JS:
   - **MC radio buttons**: `document.getElementById('TCTMC1-3').click()` — works without alt-tab
   - **FR text inputs**: Must use setter pattern + focus/blur:
     ```js
     const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
     setter.call(input, 'answer'); input.focus();
     input.dispatchEvent(new Event('input', {bubbles:true}));
     input.dispatchEvent(new Event('change', {bubbles:true}));
     input.blur();
     ```
   - **FR inputs require user to alt-tab to Chrome** before submission (Chrome throttles background tab input events)
6. User alt-tabs to Chrome, then clicks: Finished → Confirm → Finished (3-click submit)
7. Summary page shows score (may need alt-tab to trigger score animation)
8. If score >=60%: launch Review PDF agent via playwright

**Critical gotchas:**
- Questions are **randomized** per attempt — solve from page text, don't rely on bank ordering
- `.value = 'x'` does NOT work for Brillium FR inputs — must use the setter pattern above
- Score animation shows 0% until user alt-tabs to Chrome — the actual score is correct
- For <60% targets (e.g., matching 40%): no review PDF available, questions PDF only
- Input IDs: `TCTNF{N}` (numeric FR), `TCTFI{N}` (text FR), `TCTMF{N}1`/`TCTMF{N}2` (split fraction), `TCTMC{N}-{idx}` (MC radio)

### Exam tracking
`exams/exam-retake-tracker.csv` tracks all exams: scores, PDF status, review links, retakes remaining.

### If image URLs break later
PSL's image URLs may expire or require auth. If an image stops loading:
1. Screenshot it or re-grab from PSL
2. Save as e.g. `mod0-mt3-q5.png`
3. Tell Claude Code: "add this image to the images folder and push"
4. Update the image URL in the app to: `https://raw.githubusercontent.com/grrarr/fufu-poshen-loh/master/images/mod0-mt3-q5.png`

---

## Future enhancements

- Auto-sync across devices (CouchDB, Firebase, etc.)
- Scheduling integration for spaced rep reviews
- Export to PDF or Google Sheets
- One-click promote from problem bank → fufu-spaced-rep (auto-generate card with source tag)
- Problem bank: batch triage (select multiple → mark trivial)
- Problem bank: LaTeX rendering for math notation
