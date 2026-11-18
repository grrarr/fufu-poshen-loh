// Tests for the GitHub-overwrite guard in index.html (audit FP1, 2026-11-18).
// Run: node test_gh_guard.js   (no browser: pulls the pure function out of index.html and evals it)
//
// The risk: a page load whose GitHub fetch failed falls back to localStorage or DEFAULT_DATA; the next
// edit (or pasting a token on a new device) then fetched the remote sha and PUT the stale copy over
// christopher-psl-data.json - the 378-problem bank replaced by an empty one. The guard refuses a write
// that would drop problems or flags GitHub has and this copy lacks, when this session did not load
// from GitHub. Each check below fails on the old index.html (no guard at all).
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const m = html.match(/\/\/ ---- pure: ghOverwriteRisk ----([\s\S]*?)\/\/ ---- end pure ----/);
assert.ok(m, 'ghOverwriteRisk block missing from index.html');
const ghOverwriteRisk = new Function(m[1] + '\nreturn ghOverwriteRisk;')();

const bank = n => Array.from({ length: n }, (_, i) => ({ id: 1000 + i, source: 'M1 W1', text: 'p' + i }));

// nothing on GitHub (first sync, or a 404): writing is fine
assert.strictEqual(ghOverwriteRisk({ examProblems: [] }, null), null);
// defaults / empty local over the real bank: refused
assert.ok(/378 problem/.test(ghOverwriteRisk({ examProblems: [], flags: [] }, { examProblems: bank(378), flags: [] })));
// a stale local copy missing a few remote problems: refused
assert.ok(ghOverwriteRisk({ examProblems: bank(370) }, { examProblems: bank(378) }));
// local holds everything remote has, plus new ones: allowed
assert.strictEqual(ghOverwriteRisk({ examProblems: bank(380), flags: [] }, { examProblems: bank(378), flags: [] }), null);
// a flag on GitHub that this copy lacks: refused
assert.ok(/flag/.test(ghOverwriteRisk({ examProblems: bank(3), flags: [] }, { examProblems: bank(3), flags: [{ id: 7, text: 'x' }] })));
// missing arrays on either side do not throw
assert.strictEqual(ghOverwriteRisk({}, {}), null);

// both write paths that run without a GitHub-loaded sha consult the guard
const save = html.slice(html.indexOf('const save = useCallback'), html.indexOf('const updateItem'));
assert.ok(/ghOverwriteRisk\(/.test(save), 'save() does not check the guard');
const tok = html.slice(html.indexOf('const doSaveToken'), html.indexOf('const doClearToken'));
assert.ok(/ghOverwriteRisk\(/.test(tok), 'doSaveToken() does not check the guard');

console.log('ok - gh guard tests passed');
