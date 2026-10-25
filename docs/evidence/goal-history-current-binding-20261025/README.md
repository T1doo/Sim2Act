# Multi-version history keeps current editing and execution binding

Base16e53b3416ce6928ed2f097e582b9bf71ee95572. No product files changed. Reuses tests/goal_card_run_ui.cjs setup, controlled fetch adapter and real template/app.js, with an explicit HISTORY mode. Existing default27-check and HTTP branches remain unchanged.

One selected saved GoalCard has three distinct versions and a <=200-character long title containing HTML-looking text. The page first loads v3, then the user leaves unsaved goal and hard-condition edits. Actual DOM clicks on each history button must show that version's exact complete text while keeping all editor fields/material selections, active saved card/version/fingerprint/snapshot, original execution key context, execute label/disabled state and current status unchanged. Text remains text in list/history, with no injected image element.

Final unique pytest node: test_goal_history_keeps_current_saved_binding,1PASS/0.41s JUnit (7internal checks, not7tests). Recorded adapter calls are3setupGET; history clicks add0requests/0POST. No task submission, actual HTTP/API, Worker, Mock/model execution, browser, native window or G0. Selection remains saved v3; execution was not invoked.

Initial direct-onclick evidence passed0.48s but did not cover native default button behavior. It is preserved under initial-direct-handler/. The final patch uses actual button.click plus event settlement; only this new node was rerun once to strengthen that boundary. Thus1unique node,2executions, bothPASS; no product defect or product patch was found. Raw pytest/driver/results/JUnit and before/after five-file SHA snapshots are preserved. Existing FastAPI/Starlette deprecation warning is retained; no dependency change.

The final fixture remains in-memory and no database is created by the node. Self-owned pytest temporary files were copied to the evidence root and removed after completion. This closes the local history interaction gap, not populated-history native pixels, UNKNOWN intent screenshots, typography/FPS or real execution/authorization evidence. UNKNOWN remains the separately recorded visual gap. Old DOM suites/native10PNG/G0 were not repeated.
