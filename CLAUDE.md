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

### Tracking three things:
1. **Progress %** — Completion level (0–100%). Note: percentages can be deceptive (e.g., 98% might not mean final exam is done)
2. **Spaced rep notes** — Checkbox + comment field to track note-taking progress (e.g., "days 2-3 done, 5 and 9 needed")
3. **Manual flags** — Free-form notes for exams not done, topics needing review, etc.

---

## Using the app

### In the browser:
- **Update progress %**: Drag the slider for any module/workout
- **Toggle spaced rep notes**: Check the checkbox, then add a comment (e.g., "lessons 1-10 noted, 14-15 missing")
- **Add manual flags**: Write flags like "Module 0 - Exam 2 not done" and click "Add Flag"
- **Export backup**: Click "Export Backup (JSON)" to save a local copy
- All changes auto-save to localStorage and backup

### From Claude Code:
Most updates are done in the browser. If you need to manually edit data:
- Edit `index.html` → find `DEFAULT_DATA` object → update module/workout values
- Commit and push
- Refresh the browser (data reloads from GitHub)

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

---

## GitHub deployment

- Hosted on GitHub Pages: `grrarr/fufu-poshen-loh`
- Source: `main` (or `master` if that's what's deployed)
- Deploys automatically on push (~30 seconds)
- To set up GitHub CLI for future autonomous repo operations: `gh auth login`

---

## Future enhancements

- Auto-sync across devices (CouchDB, Firebase, etc.)
- Scheduling integration for spaced rep reviews
- Export to PDF or Google Sheets
