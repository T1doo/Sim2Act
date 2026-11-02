# Sim2Act frontend day — actual delivery and boundaries

The approved Library DOCX version 1 was materialized in this consumer environment using the current Library helper and verified as SHA256 `1e6e34ec404c8e319e84b0c14c1d4f9293fce26e78c1c5d1f38fa439dceb6e74`. All 995 body paragraphs and 49 embedded reference/original images were consumed; key original layouts and control figures were inspected at readable pixel size. These are reference pixels, not product screenshots.

The unmodified DOCX alone was committed to main at **be1b29724d34d6bb2a24a468357c9eb4741bfc35**. Its GitHub remote main blob was read back and hashed identically. The commit changed one DOCX only. The privacy inspection found no embedded executable/object payload, secret-like token, private user filesystem path or private screenshot; author metadata was empty. External reference/asset limits remain in the original document and `docs/design/frontend-assets.md`.

Implementation starts from the confirmed prior writer HEAD **b6b2e32884fad0252ad739105fdd0ea7430807f7**, whose last product source was **462f08dad18e6d174df263e86ba75b8176f4f9e3**. The original writer stopped writing. Initial local main-only checkout was not mistaken for that handoff. The developer branch is `dev/frontend-day-20261102`; no product history was put into main.

## What changed

The static HTML/CSS/module-JavaScript stack is retained. Unified light/warm-gray tokens, independent density, square compact controls, typography, focus/touch targets and content-driven reflow replace the old layered palettes/card surfaces. Original form/control nodes move without cloning. The instruction/result divider supports keyboard, pointer, reset and result-priority controls.

Project and application Runs share one optional four-tab inspector. It uses the current actual receipt and identity/instance/version scope, shows unknown rather than inventing evidence, restores focus, and clears stale application content. Already-read directories support local lookup, material query/list/grid, an adjacent command menu and a distinct material selection dialog. These presentation/draft gestures issue no new API requests.

Text/CSV projections preserve literal source, empty vs zero and complete original text; HTML is never interpreted. Existing trusted manifest tables/charts retain their original Run/Release authorization checks. Copy feedback follows a settled clipboard promise and ignores stale callbacks. Historical goal viewing is read-only; a separate unchecked confirmation brings known authorized historical content into an explicitly **unsaved editor draft**, then the original Save/version check is required. It does not claim server restoration or rollback of real effects.

The old Run may retain already-read text while a new Run or a transient same-Run read fails; permission denial clears retained content. Explicit task commands suppress duplicate clicks, keep unknown cancellation separate from stopped, retain the version body and offer a readonly state query instead of automatic mutation retry. Original Source/Cold review, original-key recovery, permission checks, checkbox consent, instance controls, owner review and manual locks remain in the original controllers.

## Evidence actually produced

| File | Actual result | Limits |
|---|---|---|
| `final-regression.xml` / `.log` | **28 passed**, no failures/skips; 131.18 s | Actual delivered pages loaded by jsdom through real test API/HTTP, TEST_ONLY synthetic SQLite, typed controlled stage wire and Mock/NoProvider as appropriate. No actual live provider, PG or native pixels. Includes 9 Source/Cold cases, 9 file cases, scope navigation, exact read, independent stop controls, report/app use and table-chart cases. |
| `frontend-interactions.json` | **39 checks PASS** | Real delivered HTML/app.js with controlled DOM receipts and clipboard promises. Appearance/draft/lookup/inspection/copy gestures 0 requests; 2 explicit controlled failed GETs, 1 explicit controlled command POST for double-click/unknown tests. Not an actual browser/clipboard. |
| `contrast.json` | **36 solid-token pairs PASS** | Normal/muted/semantic/primary/disabled/selection text at 4.5:1, necessary control/focus at 3:1. Does not verify transparency, actual pixels, forced colors or complete accessibility. |
| `browser-blocker.json` | Browser launch aborted before capture | Chromium sandbox helper misconfigured; **0 product screenshots**. Isolation was not disabled, no alternate executor/rejected route was tried. |
| `source-manifest.json` | Source/evidence hashes | Binds the frozen source bytes and document identity; does not substitute for runtime evidence. |
| `author-review.md` | Author source review | Not an independent review. |

The initial test collection lacked optional packaged native modules; the local environment’s default `clang` was absent. Building the unchanged locked source with available GCC supplied the required extensions. Fresh local npm dependencies use a workspace cache (the initial default user cache was unwritable). The expected older test dependency pathname is a local symlink to the newly installed dependencies, not recovered old environment state. No backend/runtime guard was disabled or patched.

Three old test drivers needed current UI navigation: Source/Cold now enters the Goal section explicitly; accepted AppRun cancellation uses the existing independent metadata/read/cancel controls; table-chart workspace ABA explicitly refreshes the fenced history before selecting an instance. Their security/Run/version/state assertions remain; failures before correction are preserved in `regression-before-*.log/.xml` and `chart-before-history-refresh.*`. `resource-regression.xml` preserves the initial missing-extension setup failure. Product fencing was not relaxed. Returning to an app now marks stale instance/version rows unavailable until the existing readonly Refresh action.

## Still not accepted

The 42-row implementation/evidence map is [frontend-day-coverage.md](../../design/frontend-day-coverage.md). It is not a declaration that all 42 acceptance gates passed.

- Before/after product pixels, real keyboard/clipboard, viewport/125–400% zoom matrix, screen-reader and forced-color checks are **NOT_RUN** because protected Chromium could not start.
- Current Windows/WinForms/WebView2 resize/focus/close/reopen, animation direction/exact expansion height, pointer hit testing, background/main-thread performance and energy behavior are **NOT_RUN**.
- Arbitrary text-fragment instructions and per-cell writeback remain outside the current material/column selection phase; direct server historical-restore and its unknown/conflict flow were not added or validated. The editor explicitly says unsaved.
- Full manual-lock/semantic/two-material arbitrary-output scenario and all error combinations were not rerun. Independent review still needs another readonly reviewer; this task did not spawn another writer.
- No product merge to main, deployment, release, paid job, live model call, PG operation, security permission change or user-PC access occurred. CI remains **487/900 seconds**, with **0** new runner execution. Original lease 30 seconds and single-Run 300 seconds remain unchanged. The separately approved future P-B overall contract work was not executed here.

## Reproduce the bounded checks

Use a lock-matching Python 3.12 environment with the unchanged optional extensions built, and the current local jsdom dependencies:

```sh
NODE_PATH="$PWD/scripts/browser-ci/node_modules" python -m pytest \
  tests/test_natural_trial_stage_ui.py tests/test_resource_file_ui.py \
  tests/test_workspace_density.py tests/test_exact_read_ui.py tests/test_internal_stop_ui.py \
  tests/test_report_manifest_apps_ui.py tests/test_application_use.py tests/test_table_chart.py -q
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_day_ui.cjs
python scripts/check_frontend_design.py
node --check src/sim2act/web/app.js
node --check src/sim2act/web/internal.js
```

The older stage driver resolves its existing `/workspace/scratch/sim2act-ui-deps-20261029/node_modules` path; it points to the newly installed ignored test dependencies in this environment. These reproduction paths are not product dependencies or Library paths.
