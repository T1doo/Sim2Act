# Sim2Act UI polish candidate

Independent worktree `/workspace/Sim2Act-ui`, branch `dev/ui-polish`. Final base is remote development tip `ca4b29f5d67a35e08ddf170ea863484944c5092f` (2026-10-22 08:08 UTC), with required `9e09532ccbb563bc1ed0b0ed718b4d8bc51de834` verified as ancestor. Initial checkout was `work` at `6f688e4`; no product was recreated from initial main. Exact commits and remote development ref were fetched normally. No main update, merge of another workstream, deployment or remote workflow change.

## Presentation scope

Only product change: `src/sim2act/web/app.css`. Source inventory in `scope.json` verifies all other tracked `src/` files against the final base, including `index.html`, `protocol.js`, API and business state controllers. No shared template edit, state/permission/budget/recovery change, framework, external font/image, fake product data or progress indicator. Existing content, controls and DOM order are retained. Repo tree contains no `AGENTS.md`, `SKILL.md` or `.agents/skills`; project instructions read: `docs/Plan.md`, `docs/F2/Plan.md`, `docs/F2/NextSteps.md`.

The existing forest green palette now has a consistent shell, active navigation, typography, spacing, cards, fieldsets, primary/secondary controls, tables and evidence views. Inputs/buttons are at least 44px high; long identifiers wrap; grids become one column below 750px. Focus outlines, native hidden/disabled behavior, reduced motion and forced colors are included. Existing empty/loading/error copy is retained; empty raw-result containers lose their blank box. This is a CSS candidate, not a completed information-architecture redesign or visual acceptance.

## Actual checks

- `git diff --check`: PASS.
- CSS Tree 3.2.1: 139 rules / 424 declarations, zero parse/property grammar errors. Declared text pairs measure 5.64–10.95:1; primary button 7.04:1, focus outline on white 5.10:1. This is a solid-color calculation, not a rendered contrast audit. See `css-audit.json`.
- Existing targeted pytest: **8 PASS / 1 FAIL**, 63.19s. Seven resource FileReader/save/recovery guard cases passed. Manifest text/table test passed, with 46 page checks, 2 cold page boots, 54 loaded-asset hash records and unchanged 55-table page state. Evidence is real ASGI/HTTP plus JSDOM; native layout/keyboard/viewport behavior is not measured. Fixture setup used 2 offline MockTransport generation requests and 3 NoModel runs; zero real models. See `pytest.log`, `junit.xml`, `resource-results.json`, `page-proof.json`, `measurement.json`.
- The failed business case is `tests/test_resource_file_ui.py::test_local_csv_file_actual_http[business]`, `Error: Timeout cold results` at `tests/resource_file_ui.cjs:85`. It also fails at the identical location on a separate untouched `9e09532c` worktree (11.23s). See `pytest-baseline.log` / `junit-baseline.xml`. No controller or test was patched to make it pass. Final base has identical `src/` and `tests/` bytes to that baseline.
- Initial test collection failed because sparse checkout omitted `docs/evidence/bounded-agent-offline-20261006/independent-gold.json`; original log retained. Adding the existing fixture directory resolved collection. npm's first attempt used an unwritable default cache; installation succeeded with a workspace-owned cache and the existing lockfile. No dependency manifest/lock change.

## Visual blocker and handoff

Actual installed Chromium launch with `chromium_sandbox=True` aborted because the SUID helper is not correctly configured. The browser did not reach page creation: **0 real page screenshots, visual review NOT_RUN**. `browser-blocker.json` records the exact action, target and observed error excerpt. No `--no-sandbox`, sandbox downgrade, ownership/mode/security change or escalation was used. Desktop, narrow screen, actual focus/overflow and pixel quality need parent review in an already authorized protected browser environment. Compilation/DOM checks are not visual acceptance.

No new remote CI was started; this branch is outside the existing workflow's push filters. No workflow was edited. Local evidence and the CSS are ready for parent integration; the existing cold-result failure remains for the functionality line. Ordinary development-branch push only; no self-merge.
