# Sim2Act frontend follow-up: independent review and full coverage map

This follows the first delivered frontend source/evidence at `91d272f6f342e2e921209bba5730052e47b41a7e`. The original unmodified DOCX is already on main at `be1b29724d34d6bb2a24a468357c9eb4741bfc35`, SHA256 `1e6e34ec404c8e319e84b0c14c1d4f9293fce26e78c1c5d1f38fa439dceb6e74`. It was not pushed again. Development remains on `dev/frontend-day-20261102`; the source manifest binds the final implementation commit and exact bytes.

## Changes after independent review

The read-only reviewer found seven correctness issues in the first batch. Historical application source no longer borrows the current draft's manifest; only the selected Run's frozen contract may supply provenance, with missing fields explicitly unknown. Historical draft recovery rechecks current material membership/disabled state, semantic catalog version, identity connection and object version. Unknown cancellation stays unknown on validation/version tabs. Application history return focuses the visible application history. Lookup of the current project preserves the existing draft. Material picker confirmation checks the complete option snapshot and real directory changes without invalidating on identical polling. Retained outcomes now include previously hash-verified Markdown, tool receipt content and structured sums, with original Run/version attribution and no copied mutation controls.

The remaining feasible local controls are implemented: measured 180ms supplementary disclosure height, 200ms inspector entrance/180ms reading-zone return with reduced-motion behavior, body-level resource command menus with ArrowUp/Down/Home/End/Escape/Tab and viewport clamping, Markdown artifact reading separate from literal original text, and adjacent current CSV-column context. Identical directory polling retains resource row/menu ownership and focus; actual changes dispose stale menus.

Text-fragment instructions now use the existing immutable TXT/MD resource and ordinary Run contract. Selection is limited to the complete original text node, with ID, SHA256, UTF-16 half-open range and exact original text recorded in page-memory draft context. Surrogate halves and cross-node selections are refused. Selection creates no Run. Explicit submission performs one readonly resource reauthorization/hash/range check, checks input/material/context ABA, and freezes the reference in ordinary goal text alongside the same selected resource ID. Combined goals over 4000 Unicode code points are refused without truncation. The existing atomic backend submission then authorizes and freezes that resource hash again. This is a new ordinary-task result, not original-document mutation, cell writeback, a structured fragment API or proof of semantic goal acceptance.

Unknown submission keeps the exact body and original key. Definite same-source denial clears the corresponding private fragment/raw/reading projection even if the user edited during the read, while preserving instruction text and other sources. Removing the fragment or changing identity/project invalidates a pending readonly check and releases its draft lock; a late reply cannot submit or replace a newer intent. Preview/download denial and explicit permission withdrawal also clear the affected fragment binding. No retry loop or new permission was introduced.

## Actual evidence

| Artifact | Result | Scope |
|---|---|---|
| `final-regression.xml` / `.log` | 29 passed, no failures/skips | Existing 28 delivered-UI regressions plus the new actual API fragment case. TEST_ONLY synthetic SQLite and controlled wire, Mock/NoProvider where applicable. No live provider, PG or native browser. |
| `frontend-interactions.json` | 39 checks PASS | Delivered HTML/JS in controlled DOM: retained input, themes/density, lookup, inspector, copy promises, command double-click/unknown behavior. |
| `review-fixes.json` | 20 checks PASS | Delivered DOM with controlled geometry/WAAPI: stale guards, provenance, history return, verified artifact retention, menu keyboard/position logic, measured disclosure and inspector animation frames, reduced motion. Zero requests after initialization. |
| `fragment-interactions.json` | 57 checks / 12 scenarios PASS | Original range/hash, cross-node and surrogate refusal, goal/material ABA, changed version, denial including edit race, pending-check removal, preview/download denial and 4000-character refusal. Controlled wire, not browser selection pixels. |
| `fragment-api-final.json`; standalone `fragment-api.json` / `.xml` / `.log` | 6 assertions / 1 pytest PASS | Delivered controller and real ASGI authorization/persistence. Genuine durable receipt deliberately lost in transport; original-key recovery returns the same single QUEUED Run. Frozen resource/hash/range/original text independently checked in synthetic SQLite; zero attempts/worker executions and semantic acceptance NOT_RUN. |
| `contrast.json` | 36 solid-token pairs PASS | Token contrast only, not actual compositing, forced colors or complete accessibility. |
| `independent-review.md` | No remaining must-fix found | Independent read-only source/controlled-DOM review, separate from the original author self-review. |
| `source-manifest.json` | Source hashes and commit | Exact byte binding, not runtime evidence. |

The earlier 29-pass run is preserved as `regression-before-final-denial-cleanup.*`; the final run includes the additional same-source preview/download/authorization cleanup. The standalone API case is retained separately so its zero-worker proof can be inspected directly. The pytest warning is the installed Starlette/httpx deprecation, not a failure. Existing lock files/dependencies were not changed.

## Coverage and unfinished acceptance

All 42 source mappings remain in [frontend-day-coverage.md](../../design/frontend-day-coverage.md), now with explicit implementation and acceptance status. The reviewer identified no remaining independently implementable local-control gap in the reviewed diff. This does not mean all 42 acceptance gates passed.

- **Implemented, browser/native NOT_RUN:** product before/after screenshots, real viewport/zoom matrix, browser text selection, pointer splitter/menu positioning, real clipboard, screen reader/forced colors, animation perception/focus clipping, main-thread/scroll/background energy, Windows WinForms/WebView2 close/reopen and DPI behavior.
- **Inherited source, full scenario NOT_RUN:** complete manual-lock and every anomaly combination, semantic two-material/model outcome, full P-B/R0 and formal PG. Bounded mock/SQLite evidence cannot establish these.
- **Not a document-required capability:** per-cell database writeback or direct in-place resource editing. Historical restore brings authorized content into an explicitly unsaved editor draft; the existing Save/version contract persists it. No new restore mutation endpoint was added.

The sole protected Chromium launch previously aborted on its misconfigured SUID sandbox helper, before any screenshot. The original blocker record is [browser-blocker.json](../frontend-day-20261102/browser-blocker.json). This follow-up made **zero further browser launch attempts and produced zero product screenshots**; no sandbox disablement, SUID edit, alternate executor or denied-route bypass occurred. The existing defunct Chromium process is not an active validation session.

No product merge to main, deployment, release, live-model call, PG operation or user-PC access. CI remains **487/900 seconds**, **0** new CI execution; development branch pushes are outside the two existing workflow branch filters and use `[skip ci]`. Original lease 30 seconds and individual Run limit 300 seconds are unchanged.

## Bounded reproduction

```sh
NODE_PATH="$PWD/scripts/browser-ci/node_modules" python -m pytest \
  tests/test_natural_trial_stage_ui.py tests/test_resource_file_ui.py \
  tests/test_workspace_density.py tests/test_exact_read_ui.py tests/test_internal_stop_ui.py \
  tests/test_report_manifest_apps_ui.py tests/test_application_use.py tests/test_table_chart.py \
  tests/test_frontend_fragment_api.py -q
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_day_ui.cjs
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_review_fixes.cjs
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_fragment_ui.cjs
python scripts/check_frontend_design.py
```

Use the locked Python 3.12 environment and unchanged packaged native extensions described in the prior evidence. These commands are local checks, not additional authorization for live, PG or native execution.
