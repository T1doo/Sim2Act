# Frontend real-use detail review

Baseline: `44dcab97a12904d603c308c6bc27aacbbde826ad`, clean and synchronized before this pass. Approved DOCX/main commit remains `be1b29724d34d6bb2a24a468357c9eb4741bfc35`; no new document or product merge to main. Source/evidence SHA256 values are in `source-manifest.json`.

## Concrete omissions fixed

1. Local lookup computed ArrowUp from the query's index -1 as result n-2. With three projects it focused the second instead of the last. The initial query now selects first/last explicitly; result navigation still wraps. IME composing arrow keys and arrows on the Close button are left to their original controls.
2. The inspection tabpanel contained static validation text but had no tab stop. It now has tabindex 0. Its selected-tab accessible label is also set before the empty-record early return, so empty and nonempty content remain labelled.
3. The coarse-pointer 44px minimum was less specific than the ID-based primary button's 36px and compact rules. The coarse rule now explicitly wins this conflict. It excludes checkbox/radio glyphs; their existing 18px size remains, while the directly enclosing label provides a 44px minimum hit region. Labels retain long-Chinese wrapping and may grow beyond the minimum.

This preserves the approved layout and existing controllers. It introduces no API operation, permission, model invocation, material mutation, persistence claim or dependency.

## Evidence and limits

| Evidence | Actual result |
|---|---|
| `before-lookup.log` | New targeted driver against baseline JS fails at ArrowUp-last behavior, as expected. |
| `before-touch.log` | New targeted driver using baseline CSS fails at primary button touch-rule priority, as expected. |
| `usability.json` | 18 checks PASS on delivered HTML/JS/CSSOM, including Chinese name preservation, arrow boundaries/wrapping, IME, close focus/draft preservation, empty results, focusable labelled panels, coarse-rule priority and checkbox label/glyph separation. Zero new API requests/errors. |
| `existing-interactions.json` | Existing 39 controlled interaction checks PASS. |
| `existing-review-fixes.json` | Existing 20 controlled DOM/geometry/WAAPI checks PASS, including reduced-motion behavior. |
| `existing-fragment.json` | Existing 57 checks/12 fragment scenarios PASS, including source versions, ABA, denial, unknown intent and old pending-read invalidation. |
| `contrast.json` | Existing 36 solid-token pairs PASS for both themes; colors were unchanged. |
| `api-regression.xml` / `.log` | 2 pytest cases PASS: delivered scope navigation/density and fragment source freezing/original-key recovery through real ASGI and TEST_ONLY synthetic SQLite. No worker/provider execution. |
| `independent-review.md` | Independent read-only final 18-check execution PASS, no remaining must-fix found. |

Keyboard/focus, coarse touch sizing, long Chinese, empty/error/loading/unknown cancellation, theme contrast, narrow-layout source rules, reduced motion and existing recovery boundaries were reviewed. No additional concrete source defect in the other reviewed areas was established in this pass. The full 29-case regression from the preceding delivery remains historical evidence; this small change did not rerun or claim it as a new 29-case result.

The CSSOM checks establish selector/priority intent and DOM text preservation, not actual dimensions, touch hit testing or text clipping. No product screenshot was produced. Real browser selection/viewport/zoom/keyboard/clipboard, screen-reader and Windows/WebView2 validation remain NOT_RUN. The earlier protected Chromium SUID-helper failure remains the blocker; no browser route was retried or bypassed.

CI ledger checked against the previous sealed delivery: **487/900 seconds**, **0 new CI execution**. No workflow was started, no dependency downloaded, no fees/permissions/security settings changed. Local installed dependencies were reused. Original 30-second lease and 300-second individual Run limit remain unchanged.

## Reproduce with already installed local dependencies

```sh
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_usability_ui.cjs
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_day_ui.cjs
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_review_fixes.cjs
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_fragment_ui.cjs
python scripts/check_frontend_design.py
NODE_PATH="$PWD/scripts/browser-ci/node_modules" python -m pytest tests/test_workspace_density.py tests/test_frontend_fragment_api.py -q
```
