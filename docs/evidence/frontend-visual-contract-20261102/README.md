# Approved visual specification: source differences and bounded closure

Baseline: clean `19b5a940d381c4163aeb11b9f71ee2c15f892ed0` on `dev/frontend-day-20261102`. The unmodified approved DOCX remains on main at `be1b29724d34d6bb2a24a468357c9eb4741bfc35`, SHA256 `1e6e34ec404c8e319e84b0c14c1d4f9293fce26e78c1c5d1f38fa439dceb6e74`; its locally consumed bytes were rehashed identically. No product merge to main.

This pass re-read the relevant approved text and actual image pixels: image3/4 (light/dark workspace), image21 (V06 menu/picker), image43 (selection/focus), image46 (empty/partial/unknown states), image47/48 (pressure/zoom layouts). They are document illustrations, not screenshots of implemented software. Precise chapter/figure/S-G identifiers below are used rather than inventing Word rendering page numbers; the DOCX has no stored rendered-page markers.

## Requirement → baseline implementation → actual difference

| Approved location | Existing implementation and difference | Action/status |
|---|---|---|
| §3I, figure V06, S19: ordinary menu 160–288px, longer explanation may reach 320px | Initial CSS had 288px, but the last rule and `frontendPositionMenu()` inline max width replaced it with viewport width. This menu has only the ordinary download command. | Restore min(288px, viewport−16px) in CSS and JS; the 160px minimum also yields to an exceptionally narrow viewport. No new action or asset. |
| §4 space priorities, §14A/14B, S01/S06/G02/G07: result needs ≥560px to remain alongside instruction | At a 900px viewport the old source allowed at most 900−64 navigation−40 main padding−280 instruction−8 divider = 508px result outer width; single-pane rules began only at 768px. | Reuse the existing task pane switch at ≤1100px. At 1101px the largest 420px instruction still leaves 569px result outer width. Task pane navigation and existing controls remain; shell/apps/resources retain their original breakpoints. No fixed 560px minimum forces page overflow. |
| §3C/3D, S13/S18: busy labels do not change button width | Ordinary Run cancel changed two characters to six and enabled a 100px busy minimum, without reserving width. | Only finite Run-state commands receive `width:calc(6em + 24px)` with a stable zero minimum overriding the generic busy minimum. Existing max-width and natural wrapping remain. Pause/resume/cancel protocol/version/unknown behavior is unchanged. |
| §3I/3Q, S19/G07: menu remains adjacent and inside the viewport on reopen | Independent controlled geometry found a reused old inline maxHeight affected the next measurement. After expanding the window the cap grew, but position used the old short height and could overflow. | Clear the previous inline maxHeight before measuring; then apply current available room. Same-menu short-window → larger-window reopening is covered. |
| §4, S25/G11: two Chinese typographic roles | Existing rows/tables use 15px/1.55; `.result-reading` uses 16px/1.6 with 20/18px headings and 78ch cap; literal Run answer retains 16px/1.65. Auxiliary copy is 13–14px. | No additional source omission established. Actual Chinese line length, optical hierarchy and mixed text/200% zoom remain unverified; the illustration does not justify guessing a new type system or tightening literal-text spacing. |
| §3C/3D/3E, S05/S18/S24: compact square hierarchy, thin boundaries | Controls have 0px radii, ordinary 32px/primary36px sizing, 1px necessary borders, flat main surfaces and weak popup-only shadow; standard/compact and light/dark tokens are separate. | No new source omission established. Actual density, clipping, compositing and forced-color perception remain unverified. The preceding coarse-pointer fix is retained. |
| §3J/3K/3L/13, S28/G05/G12/G14: limited legal idle backgrounds | Original local CSS warm/cool gradients, mutually exclusive preferences, 80px edge capped at 640px, default static, original system-font/SVG assets. No external image/font/script/runtime asset was copied. | No missing image download is required. Existing asset record remains authoritative. Background appearance, energy and scrolling performance still require real UI measurement. |
| §3P/3Q/12, S12/S14/S16/S19/S20/G03/G04/G14: local timing and reduced motion | Existing 140ms ≤4px menu reveal, measured 180ms disclosure, 200ms inspector entrance/180ms reading return, 90/120ms press/release, 1.6s successful-copy feedback, 1.4/1.2s Pulse/Dots, system/product/background motion controls. | No further parameter omission established. Existing controlled motion checks pass; real animation perception, clipping, frames and energy remain unverified. |

## Evidence actually run

| Artifact | Result and scope |
|---|---|
| `visual-contract.json` | **38 checks PASS**. Delivered controller, stylesheet media-rule projection through CSSOM, controlled geometry and command promises. Rules evaluated at 1100/1024/900/769/768/320 and boundary1101; these are **not rendered viewport tests**. Menu caps checked at1200/320/200/120 and short→tall reopening. One explicit controlled failed cancel; all other gestures issue zero new requests. |
| `before-layout.log` | Current driver with baseline CSS fails at the 1100px single-pane rule, as expected. |
| `before-menu-width.log` | Current driver with baseline JS fails at ordinary menu cap, as expected. |
| `before-menu-reopen.log` | Same final source with only the old-height-reset omitted fails reopening bounds, as expected. |
| `existing-interactions.json`, `existing-review-fixes.json`, `existing-fragment.json`, `existing-usability.json` | Existing 39/20/57/18 checks PASS respectively; controlled DOM/geometry/wire, not pixels. Includes unknown commands, motion reduction, draft/permission/version/recovery behavior. |
| `contrast.json` | 36 solid-token pairs PASS; palette unchanged. Not an actual compositing/accessibility audit. |
| `api-regression.xml` / `.log` | 2 pytest cases PASS: scope/density controls plus real ASGI/TEST_ONLY synthetic SQLite source freezing and original-key recovery. No worker or provider execution. |
| `independent-review.md` | Final read-only independent 38-check run PASS; no remaining must-fix within this pass. |

The two `harness-*` logs preserve early test-assertion mistakes: CSSOM correctly evaluated `min(...)` as104px and zero minimum as`0px`; initial assertions expected uncomputed text/`0`. Assertions were corrected to numeric comparisons. They were not product failures and no runtime guard was changed. The earlier 29-case regression belongs to the previous delivery and is not claimed as newly rerun here.

## Stopping point and remaining acceptance

The four evidence-backed source differences above are closed; no speculative aesthetic changes or new assets were added. The 42-row map was updated with this pass. Exact source/evidence hashes are in `source-manifest.json`, committed together with these results.

Real before/after screenshots, viewport/zoom/Chinese line breaks, pointer/clipboard/screen-reader/forced colors, actual animation and background performance, and native Windows/WebView2 remain **NOT_RUN**. Product screenshots produced this pass: **0**. The prior protected Chromium SUID-helper failure remains; no further launch, alternate route, SUID edit or sandbox disablement was attempted. Source arithmetic and CSS parameters do not establish visual acceptance.

CI ledger remains **487/900 seconds**, **0 new CI execution**. No download, dependency/lock change, new cost/permission, live provider, PG operation, deployment/release or user-PC access. Original30s lease/300s Run limit remain unchanged.

```sh
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_visual_contract.cjs
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_day_ui.cjs
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_review_fixes.cjs
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_fragment_ui.cjs
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_usability_ui.cjs
python scripts/check_frontend_design.py
NODE_PATH="$PWD/scripts/browser-ci/node_modules" python -m pytest tests/test_workspace_density.py tests/test_frontend_fragment_api.py -q
```
