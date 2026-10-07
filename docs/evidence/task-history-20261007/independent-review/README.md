# Independent task-history review, 2026-10-07

Read-only review of pending task-history patch in /workspace/Sim2Act-task-recovery, atop 442e90b0. No product edits, credentials or provider requests, push, browser sandbox changes.

API list_runs authenticates via user dependency, calls own_project, and filters both project_id and principal_id. It returns bounded collapsed goal_summary (160 codepoints plus ellipsis), accepted time, persisted submission mode. Protocol request-key prefix deliberately downgrades mode to UNKNOWN rather than label its placeholder MOCK. DOM row uses textContent, not HTML. Snapshot is server-created; normal client API cannot supply it. Mode is submission configuration, not evidence of actual calls or semantic acceptance.

Refresh history guards identity, selected project and refresh generation, including both successful and failed late history replies. showRun guards identity, project, selected ID and selection generation. Recovery map is separated by bearer identity and project; accepted-read retry is GET-only, uncertain retry uses frozen old request body/key.

Found reproducible gap before developer fix: connect only clears history. A displayed selected Run/result/raw-result/events/refs survives switching to B when B authentication fails; activeRun still A. Actual app.js/index in JSDOM with denied HTTP adapter yields reproduction.json showing retained synthetic A values after PERMISSION_DENIED. No API permission bypass occurs, but UI retains prior identity's private content and poll can continue using old selected ID. Also token-value checks alone do not invalidate A->B->A pending selected reads unless selection generation advances. Recommended: clear all identity-bound selected/result/form state and increment selection generations before connecting, even if new authentication fails; stale connect failures must not overwrite current identity's feedback.

Current existing offline tests passed 5 tests, 1 browser deselected,1 deprecation warning,2.55s. These tests did not detect the connect retention case. Reproduction script is a UI state check, not real network/browser evidence. Final fix re-review pending.

## Developer fix re-review

Developer added clearIdentityView before connect: invalidates run history/selection/user intent generations, clears activeRun/refs/reconcile/results/commands/project/list state and goal/app/protocol views. App/goal-list responses now check identity and selection generation. Original reproduction re-run: denied B connection leaves selected Run null, refs empty and result/raw/events empty (reproduction-after.json).

A second actual-handler counterexample found: an older A connect rejection arrived after B connect succeeded and generic safe() overwrote B error. Preserved reproduce-late-connect.cjs and late-connect-before.json. Developer added identityConnectionGeneration and current-guarded connect catch/capabilities. Re-run late-connect-after.json: before and after both empty. Both independent counterexamples are closed.

Intermediate tests-after.log and tests-final.log each retain4 PASS/1 DOM FAIL from syntax errors in injected driver code at168/174; developer corrected injected helper regex escaping with startsWith/endsWith. This was not a passing final regression nor a demonstrated product security defect. Latest stable independent suite:5 PASS/1 browser deselected/1 deprecation warning/3.23s (tests-stable.log). Protected real browser/native validation was not run by this reviewer.
