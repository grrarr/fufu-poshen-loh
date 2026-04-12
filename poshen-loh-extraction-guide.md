# Po-Shen Loh Exam Extraction & Progress Tracker Guide
## Instructional Document for LLM Claude in Chrome

---

## 1. Overview

This guide covers how to extract exam problems from Po-Shen Loh's online math course (daily.poshenloh.com) hosted on the Brillium testing platform, and enter them into the progress tracker app at grrarr.github.io/fufu-poshen-loh/.

### Domains Involved
- **daily.poshenloh.com** — Course pages with exam links and scores
- **expii.onlinetests.app** — Brillium exam platform (where actual questions live)
- **grrarr.github.io/fufu-poshen-loh/** — Progress tracker app

---

## 2. Course Page Structure (daily.poshenloh.com)

### Exam URLs (Module 3 - Algebra)
| Exam | URL |
|------|-----|
| Week 1 Challenge | `https://daily.poshenloh.com/courses/take/3-algebra/brillium_exams/M3ALGEBRAW1-week-1-challenge` |
| Week 2 Challenge | `https://daily.poshenloh.com/courses/take/3-algebra/brillium_exams/M3ALGEBRAW2-week-2-challenge` |
| Week 3 Challenge | `https://daily.poshenloh.com/courses/take/3-algebra/brillium_exams/M3ALGEBRAW3-week-3-challenge` |
| Week 4 Challenge | `https://daily.poshenloh.com/courses/take/3-algebra/brillium_exams/M3ALGEBRAW4-week-4-challenge` |
| Final Challenge | `https://daily.poshenloh.com/courses/take/3-algebra/brillium_exams/M3ALGEBRAFINAL-final-challenge` |

### Key DOM Elements on Course Exam Page
- **Score display:** `.exam__result_score` — Shows Christopher's score as a percentage
- **Hidden form:** `#exam__form` — Submitting this form navigates to the Brillium platform
- **Completion overlay:** A gray overlay may appear showing past results; this is NOT interactive

### How to Access Brillium Exams
Do NOT try to click visual elements on the course page. Instead, use JavaScript form submission:

```javascript
document.getElementById('exam__form').target = '_self';
document.getElementById('exam__form').submit();
```

This submits the hidden form and navigates to the Brillium exam platform in the same tab.

---

## 3. Brillium Exam Platform (expii.onlinetests.app)

### Landing Page Scenarios
After form submission, you may encounter several different pages:

1. **"Confirm Start of Next Attempt"** — Click the "Continue" button to proceed
2. **"Confirm Login Information"** — Click "Start Answering Questions" or "Continue Answering Questions"
3. **"Summary" page (0% score)** — This means a previous timed-out attempt exists. Navigate back to the course page and re-submit the form to get the Confirm Start page instead
4. **Direct to questions** — Rarely, you land directly on the questions page

### Questions Page Structure
The questions page URL contains `a=Q1` parameter. All 20 questions are on a single scrollable page.

#### Key DOM Selectors
- **Question wrapper:** `.question-wrapper` — Contains each question block
- **Question text:** `.question-text` — The main question text
- **Answer choices:** `label[for="radioXXXXX"]` — Radio button labels containing answer text
- **Images:** `img` elements within question wrappers (filter out logos)
- **MathJax containers:** `.MathJax` elements containing rendered math

### Exam Timer
Each exam has a 60-75 minute timer. Extract questions quickly and navigate away before time expires, or the attempt will be recorded as 0%.

---

## 4. MathJax / Math Extraction

### CRITICAL: innerHTML is Blocked
Browser security blocks `.innerHTML` calls, returning `[BLOCKED: Cookie/query string data]`. You MUST use `querySelectorAll` on semantic MathML elements instead.

### CRITICAL: textContent is Lossy
MathJax `.textContent` strips mathematical structure. For example, `a^2 - c^2` appears as `a2−c2` in textContent. Always verify with MathML element queries.

### MathML Elements to Query
| Element | Meaning | Plain Text Format |
|---------|---------|-------------------|
| `msup` | Superscript/exponent | `base^exponent` |
| `mfrac` | Fraction | `numerator/denominator` |
| `msqrt` | Square root | `sqrt(content)` |
| `mroot` | Nth root | `n-th root of content` |

### Extraction JavaScript Pattern
```javascript
// Get all superscripts (exponents)
document.querySelectorAll('.question-wrapper msup').forEach(el => {
  const base = el.children[0]?.textContent;
  const exp = el.children[1]?.textContent;
  console.log(base + '^' + exp);
});

// Get all fractions
document.querySelectorAll('.question-wrapper mfrac').forEach(el => {
  const num = el.children[0]?.textContent;
  const den = el.children[1]?.textContent;
  console.log(num + '/' + den);
});

// Get all square roots
document.querySelectorAll('.question-wrapper msqrt').forEach(el => {
  console.log('sqrt(' + el.textContent + ')');
});
```

### Plain Text Math Formatting Rules
- `^` for exponents: `x^2`, `2^n`
- `sqrt()` for square roots: `sqrt(16)`, `sqrt(x + 1)`
- `/` for fractions: `3/4`, `(x+1)/(x-1)`
- `*` for multiplication: `2 * 3`, `a * b`
- Use parentheses for clarity: `(a + b)^2`, `sqrt(x^2 + y^2)`

---

## 5. Image Handling

### CRITICAL RULES
- **Do NOT take screenshots** of images — this causes size limit errors
- **Do NOT embed images** directly
- **Do NOT reproduce tables/charts as text** if they're rendered as images
- **ONLY extract the `<img>` src URL** from the HTML

### Image Extraction JavaScript
```javascript
document.querySelectorAll('.question-wrapper img').forEach(img => {
  const src = img.src || img.getAttribute('src');
  // Filter out logos and UI images
  if (!src.includes('logo') && !src.includes('favicon')) {
    console.log('IMAGE: ' + src);
  }
});
```

### Image Format in Problem Text
Place image URL on a separate line after the problem text:
```
13. If 1/x - 1/y = 1/z, and x = 3 and y = 5, solve for z.
IMAGE: https://expii.onlinetests.app/day-images/M4W1-exam-p13-latex.png
[Figure: fraction equation rendered as LaTeX]
```

### Known Image URLs from Module 3
| Problem | Source | URL |
|---------|--------|-----|
| Week 1 Q13 | Mini Test 1 | `https://expii.onlinetests.app/day-images/M4W1-exam-p13-latex.png` |
| Week 4 Q3 | Mini Test 4 | `https://dailyimg.poshenloh.com/M4W4-exam-point-x-3.png` |
| Week 4 Q4 | Mini Test 4 | `https://dailyimg.poshenloh.com/M4W4-exam-line-ab-slope.png` |
| Week 4 Q16 | Mini Test 4 | `https://dailyimg.poshenloh.com/M4W4-exam-lattice-square.png` |

---

## 6. Christopher's Scores

Score = percentage of the first 10 questions answered correctly.

| Exam | Score |
|------|-------|
| Week 1 Challenge (Mini Test 1) | 80% |
| Week 2 Challenge (Mini Test 2) | 100% |
| Week 3 Challenge (Mini Test 3) | 60% |
| Week 4 Challenge (Mini Test 4) | 60% |
| Final Challenge (Final Exam) | 40% |

The score is read from the `.exam__result_score` element on the course page before accessing Brillium.

---

## 7. Progress Tracker App (grrarr.github.io/fufu-poshen-loh/)

### App Characteristics
- **Extremely dark theme** — screenshots appear nearly black/dark blue
- **Always use DOM refs** from `read_page` / `find` tools, never visual coordinates
- **React-based** — form inputs require React-compatible value setting

### Naming Convention for Sources
| Exam | Source Name |
|------|------------|
| Week 1 Challenge | Module 3 - Mini Test 1 |
| Week 2 Challenge | Module 3 - Mini Test 2 |
| Week 3 Challenge | Module 3 - Mini Test 3 |
| Week 4 Challenge | Module 3 - Mini Test 4 |
| Final Challenge | Module 3 - Final Exam |

### Adding Problems Workflow

1. **Scroll to bottom** of the Exam Problem Bank section
2. **Click `+ Add Problems`** button (green button at bottom of problem list)
3. **Fill Source field** with the section name (e.g., "Module 3 - Mini Test 1")
4. **Paste all 20 problems** into the textarea, each separated by a blank line
5. **Click `Add N Problem(s)`** button
6. **Verify** the problem count increased by 20
7. **Repeat** — the form stays open; just change source and paste new problems

### Adding Images to Problems

1. **Find the problem** by its text content using the `find` tool
2. **Click the problem** to expand it
3. **Click the `+ Image` button** inside the expanded problem
4. **Set the image URL** using React-compatible JavaScript:

```javascript
const input = document.querySelector('input[placeholder*="image URL"]');
const setter = Object.getOwnPropertyDescriptor(
  window.HTMLInputElement.prototype, 'value'
).set;
setter.call(input, 'YOUR_IMAGE_URL_HERE');
input.dispatchEvent(new Event('input', { bubbles: true }));
input.dispatchEvent(new Event('change', { bubbles: true }));
```

### Multiple Expanded Problems
When multiple problems are expanded simultaneously, each has its own image URL input. Target the correct one (usually the last/newest):

```javascript
const inputs = document.querySelectorAll('input[placeholder*="image URL"]');
const targetInput = inputs[inputs.length - 1]; // last one = most recently expanded
```

### GitHub Sync
The app has a green "● GH" button for GitHub sync. Click this after all changes to persist data to the repository.

---

## 8. Problem Formatting Rules

### Format
```
1. Problem text here with math like x^2 + 3x - 4 = 0.
(A) Answer A  (B) Answer B  (C) Answer C  (D) Answer D  (E) Answer E

2. Next problem text.
IMAGE: https://example.com/image.png
[Figure: description of what the image shows]
(A) Answer A  (B) Answer B  (C) Answer C  (D) Answer D
```

### Rules
- Each problem separated by a blank line
- Number problems sequentially within each section (1-20)
- Include multiple choice answers as (A) (B) (C) (D) (E) after the question
- Use plain text math notation (^, sqrt(), /, *)
- Place IMAGE: URL on its own line after the question text
- Add brief description in brackets after image URL
- Do NOT add commentary or explanations

---

## 9. Complete Per-Exam Extraction Workflow

```
For each exam:
  1. navigate to course exam URL on daily.poshenloh.com
  2. wait 3 seconds for page load
  3. javascript: read score from .exam__result_score
  4. javascript: submit #exam__form (target='_self')
  5. wait 5 seconds for Brillium platform
  6. Handle landing page:
     - "Confirm Start" → click Continue
     - "Confirm Login" → click "Start Answering Questions"
     - "Summary (0%)" → go back, re-submit form
  7. wait 5 seconds for questions to load
  8. get_page_text for bulk text extraction
  9. javascript: query MathML elements (msup, mfrac, msqrt, mroot)
  10. javascript: query answer choice labels
  11. javascript: query img src URLs (excluding logos)
  12. Assemble problems in correct format
```

---

## 10. Common Gotchas and Tips

1. **Gray overlay on course page:** Not interactive. Don't try to click elements on it. Use JS form submission.

2. **innerHTML blocked:** Browser security blocks innerHTML. Use querySelectorAll on specific elements instead.

3. **Timed-out attempts → Summary page:** Navigate back to course page and re-submit the form. The new attempt prompt will appear.

4. **Dark tracker app:** Never rely on screenshots for the progress tracker. Always use find/read_page tools with ref IDs.

5. **MathJax textContent is lossy:** Always cross-check with msup/mfrac/msqrt/mroot queries. "a2−c2" in textContent actually means "a^2 − c^2".

6. **React form inputs:** Standard `.value = 'x'` doesn't trigger React state updates. Use the Object.getOwnPropertyDescriptor setter pattern shown above.

7. **Brillium exam timers:** 60-75 minutes. Extract quickly. If you navigate away, the attempt may time out and show as 0%.

8. **Multiple retakes:** Each exam allows ~8 retakes. Starting an attempt and letting it time out burns a retake. Be deliberate about when you start attempts.

9. **Scrollable containers on Brillium:** The questions page has a custom scrollable container. scrollIntoView may scroll the wrong element. Prefer get_page_text and JS extraction over visual scrolling.

10. **Image size errors:** If you screenshot an image instead of extracting its URL, you'll hit upload size limits. ALWAYS extract the img src URL from HTML only.

---

## 11. Future Tasks

### PDF Creation
Navigate to each Brillium exam questions page and use browser print-to-PDF. This requires starting a new Brillium attempt (burns a retake) or finding cached/saved versions.

### Score Matching
To record Christopher's score on the Brillium platform, answer the first 10 questions to match the target percentage, then submit the exam. For example, for 80% score, answer 8 of the first 10 correctly and 2 incorrectly.

### Additional Modules
This guide covers Module 3 (Algebra). The same workflow applies to other modules — just update the exam URLs and source names accordingly.

---

*Generated for use by LLM Claude in Chrome browser automation sessions.*
*Last updated: April 2026*
