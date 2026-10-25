# Goal-card editing and version navigation first

Base: `e02d4a1b12463b02480b100cc42e422ecc9faf09`. Product changes are limited to `src/sim2act/web/index.html` and `app.css`.

Original V5 §2 places the user's goal and outcome before engineering detail; F2-T01 distinguishes facts, assumptions, unresolved questions, hard constraints and acceptance checks. The existing goal-card page instead began with the eight-button seven-slot trial panel; saved cards and version history followed the CSV candidate panel.

The editor now leads with its current draft/read state and four readable sections: goal, background/unresolved questions, boundaries/acceptance, and materials. Saved cards and version history precede CSV candidate creation in the adjacent library. The complete trial subtree follows the main editor/library and remains expanded and available, including UNKNOWN, LIVE-closed text, exact scope, original key and read-only recovery. No permission, confirmation or execution action is added or removed.

All eight field LABELs, save and status remain direct form children. This preserves the original app.js shared-form borrowing contract; new direct headings are hidden during preparation and restored with the original nodes. All new CSS is scoped to `#goal-cards-panel`; it does not follow the borrowed form into the Apps preparation host. Declared responsive rules make fields single-column at1000px and the whole goal workspace single-column at750px. No visual order override, overlay or animation is added.

## Before state and verification

`before-index.html.gz`, `before-app.css.gz` preserve exact pre-edit source bytes; `before.json` records base/hash/time. These are source snapshots, not screenshots. The previous native workbench capture did not cover this goal-card page.

Four local Node processes ran once, using already installed JSDOM/css-tree through the existing NODE_PATH. `test-plan.json` predates execution; `test-execution.json` records argv, time, duration, exit and unchanged32-file hashes. Original stdout is under `tests/`.

| Node program | Actual result | Scope |
| --- | --- | --- |
| goal_card_hierarchy.cjs | exit0;11 checks;0.955676s | Original controls/IDs, unchanged outside DOM, complete trial subtree, direct labels, actual form borrow/return, UNKNOWN original gates, CSS declarations/cascade |
| natural_input_preparation_navigation.cjs | exit0;39 checks;0.804556s | Existing same-node restoration, generic saving, identity/project ABA, UNKNOWN original-intent recovery; synthetic API only |
| goal_card_run_ui.cjs (default branch) | exit0;27 checks;0.738071s | Saved-version execution, original request key, read failure and late responses; controlled adapter, not HTTP branch |
| workspace_density.cjs | exit0;6 named checks;0.439244s | Existing project focus/navigation and unchanged form-parent assumptions |

These are four Node executions, not83 independent tests. Test-only writes target in-memory adapters. No HTTP, Worker, model, Mock execution, G0, browser or native CI window ran. Original controllers, payloads, permissions, CAS, keys and callback guards are unchanged.

Initial plain Node dependency lookup omitted NODE_PATH and reported MODULE_NOT_FOUND before any test; the already installed dependency path then resolved successfully. No packages were installed. Local sandbox helper remains owner65534:65534/mode4755; no browser launch, sandbox downgrade or permission change was attempted.

Independent read-only review confirmed the two-file product scope and32/32 execution-before/after/current hashes; all four logs agree. Syntax and git diff checks passed. **Native pixels, actual breakpoint rendering and device smoothness remain unverified.** No previous screenshot is used as acceptance for this new page.
