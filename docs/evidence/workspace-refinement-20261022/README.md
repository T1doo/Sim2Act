# Workspace refinement — 2026-10-22

Base `51bcbcde3d9188420081802aa9aa35aebe5d009a`. One writer in the specified Sim environment. Product scope is `src/sim2act/web/index.html` and `app.css`; controllers, API, authorization, deadlines, protocol bytes and runtime code are unchanged. No G0, new CI, provider, Worker or business request was run. No dependency manifest/lock changed; the existing engineering-ci lock was installed with lifecycle scripts disabled for the static audit.

The three workspaces now have distinct titles, quieter supporting copy and consistent visual hierarchy. Project anchors lead to tasks, protocol work, goals and maintenance. Four low-frequency project fieldsets remain intact inside an explicitly expandable native “项目维护与复用” disclosure; it starts closed. Primary task/result cards are reachable without scrolling through those tools. All existing controls, confirmations, dynamic gates and source order within those tools remain. Application and resource headings, spacing, task-history cards, file preparation, fields and narrow layouts share the refined forest-green/neutral shell. No external font/image request was introduced.

Default status panels are neutral, avoiding a green success impression for UNKNOWN or unavailable results. Header output styling is scoped to the header, fixing the pale trial-status text on white. The two full receipt views scroll at 240px; both are keyboard-focusable with descriptive labels and the standard visible focus outline, including forced colors. Evidence is retained in full; CSS does not infer a business status.

## Actual checks and independent review

`static-audit.json`: JSDOM parses both exact templates; all **623** original IDs, **487** controls (attributes, values, labels and order), **96** hidden gates and script order remain. Six new IDs are unique. Original goal-form parent and result-panel selectors still resolve correctly. CSS Tree validates **206 rules / 614 declarations**, zero syntax/property errors after resolving declared CSS variables. Nine specified solid foreground/background pairs exceed 4.5:1. These are static invariants and color calculations, not a rendered accessibility audit.

The audit initially failed because CSS Tree's property matcher cannot directly match `var()`. Only the verifier was corrected to resolve the declared root variables; no product CSS was changed to silence that failure. `initial-audit-failure-summary.json` labels the summary accurately; raw output remains in the task transcript.

Two existing completion controller VM tests: **2 PASS in 0.13s**, one existing Starlette/httpx deprecation warning. They cover original-key selection/recovery and the optional locator NOT_FOUND followed by completion composition. No HTTP or actual DOM layout is claimed for these VM tests. Raw pytest and JUnit outputs are stored losslessly. No old backend, process or model suite was repeated.

The independent read-only reviewer found no definite P1/P2 in the final presentation slice and verified critical controller parent selectors, hidden/disabled attributes and the receipt keyboard correction. This is a static ACK, not visual acceptance. See `independent-review.md` for the exact reviewed source hashes.

## Real pixels still open

Existing actual baseline pixels: [Source restored frame](../protocol-completion-readback-native-ui-20261022/native/source-refreshed.png) and the other three PNGs in that archive. They came from protected Windows Edge on the older checkout and show a scrolled protocol section, not a complete page or a narrow viewport. They informed the diagnosis; they do **not** validate this candidate.

No new screenshot was taken. The local Chromium helper is still uid 65534 / mode 4755; its already recorded protected-launch prerequisite remains unmet. This turn only inspected that prerequisite, with zero browser launches, no sandbox relaxation or ownership/mode change. The active G0-stage handoff withheld a new CI window; this turn did not trigger one. Native before/after pixels, actual disclosure keyboard interaction, focus, 320/390/768/1366px overflow and all-workspace visual quality remain NOT_RUN. A subsequent explicitly scoped protected installed-Edge window must use this final tree, preserve zero business POST/model/Worker/Source/extract, and record cleanup. It must not reuse an old green run as current acceptance.

## G0 audit safely closed for this turn

The old full profile's 2271 `checked` calls are not 2271 interchangeable full-cohort validations. There are 191 direct `_base` parents, while most other parents perform independent graph/stage checks. Source inspection found two independent raw snapshots for the same actual model (`_graph_trial_produced` registration versus admission-prefix `_dump`), and nested SQL/model/serializer/new-root boundaries. Mutating one raw snapshot is not witnessed by checking only the other. `_saved` and produced-result paths contain SQL/model_dump/parsed-result interleavings. These are source-constructed counterexamples, not newly executed mutation tests.

No safe fixed segment with the complete same alias/raw read set was proven, so no pin was deleted or PASS cached and no window was reopened. This conclusion does not establish that a 30-second G0 is impossible. Prior account-source and overall F2/R0/provider/PG/G0/owner-semantic gates remain open as already documented.

Follow-up: the subsequently authorized [one native visual window](../workspace-refinement-native-20261022/README.md) executed this exact b538ce79 product tree and archived real project before/after plus all three workspace wide/narrow frames, keyboard/receipt/failure evidence and cleanup. Its bounded PASS supersedes the preparation-stage NOT_RUN above for that explicitly tested tree and scope. A two-declaration button-spacing correction was made after capture and is separately labelled static-only; old frames do not certify its native pixels.
