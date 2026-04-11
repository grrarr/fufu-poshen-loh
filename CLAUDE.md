# Christopher's Po-Shen Loh Progress — Claude Code Context

## What this is

An interactive progress tracker for Christopher's Po-Shen Loh math curriculum. Single HTML file hosted on GitHub Pages. Tracks completion % across 6 modules and 6 workouts, plus spaced repetition note progress and manual exam flags.

**App URL**: https://grrarr.github.io/fufu-poshen-loh/
**Repo**: https://github.com/grrarr/fufu-poshen-loh
**Source**: `index.html` (single file — React + Babel standalone, localStorage for persistence)

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

### Setup
Open the exam/test page in the PSL platform. Make sure the full test is visible (scroll to load all problems if needed).

### The prompt
Adapt the source name each time (e.g., "Module 0 - Mini Test 3", "Module 3 - Final Exam", "Workout 1A - Final Exam").

```
I need to extract all problems from this page. For each problem:

1. If it's pure text/numbers — copy the problem text exactly
2. If it has math symbols (fractions, exponents, square roots, summations, etc.) — write them out in plain readable math. Use: ^ for exponents, sqrt() for roots, / for fractions, * for multiply. E.g., "What is 2^3 + sqrt(16) / 4?"
3. If it has any image — whether it's a geometric figure, diagram, table, chart, or graph — grab the image URL (right-click → Copy Image Address, or inspect the <img> src) and include it on a separate line right after the problem, formatted as: IMAGE: https://... Also briefly describe what it shows in brackets, e.g., [Figure: triangle with labeled sides] or [Table: values of f(x)]. Do NOT try to reproduce tables/charts as text if they're rendered as images.
4. If it has multiple choice answers — include them as (A) (B) (C) (D) (E) after the question

Format: output each problem separated by a blank line. Number them. Don't add commentary.

Source label for these problems: Module 0 - Mini Test 3
```

### After extraction
1. Copy Claude's entire output
2. Go to https://grrarr.github.io/fufu-poshen-loh/
3. Scroll to **Exam Problem Bank** → click **+ Add Problems**
4. Enter the source name (e.g., `Module 0 - Mini Test 3`)
5. Paste the problems
6. Click **Add N Problem(s)**
7. For any problem that had `IMAGE: https://...` in the output — expand the problem → click **+ Image** → paste that URL

### If image URLs break later
PSL's image URLs may expire or require auth. If an image stops loading:
1. Screenshot it or re-grab from PSL
2. Save as e.g. `mod0-mt3-q5.png`
3. Tell Claude Code: "add this image to the images folder and push"
4. Update the image URL in the app to: `https://raw.githubusercontent.com/grrarr/fufu-poshen-loh/master/images/mod0-mt3-q5.png`

### Triage session (separate step, with Christopher)
Go through untriaged problems together:
- He solves it instantly → **Trivial**
- He's unsure or gets it wrong → **Needs Review**
- He doesn't know the formula/method → **Needs Formula** (note which formula)
- Already added to fufu-spaced-rep → **In Spaced Rep**

### Gotchas
- **Multi-part problems**: Claude should keep parts together as one problem. If it splits them, delete the fragment and edit the main one
- **Answer keys**: Tell Claude: "Ignore the answer key, just extract the problems"
- **Long tests**: Scroll and ask Claude to "continue extracting from where you left off" — paste both batches with the same source name
- **Unreadable diagrams**: If Claude can't interpret a figure, it'll come through vague. The image URL is the backup — attach it via + Image

---

## Future enhancements

- Auto-sync across devices (CouchDB, Firebase, etc.)
- Scheduling integration for spaced rep reviews
- Export to PDF or Google Sheets
- One-click promote from problem bank → fufu-spaced-rep (auto-generate card with source tag)
- Problem bank: batch triage (select multiple → mark trivial)
- Problem bank: LaTeX rendering for math notation
