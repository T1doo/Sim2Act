# Exact e6 combined full regression

Frozen source: `e6c03cf15b7473ebce4cd3d5b8c4dcc06405a676`. All 204 tracked files under src/tests/scripts/.github match that Git object; no product edits were made by this regression branch. The six current-controller/clean-child import probes use the three isolated venvs and this worktree. Collection contains **1035 tests**. This is a complete combined-source run, not a sum of earlier native/core suites.

Final authorized **serial** complete runs, with unchanged source, deadlines and coverage:

| Database | Passed | Skipped | Failed / errors | Duration | Exit |
|---|---:|---:|---:|---:|---:|
| SQLite | 995 | 40 | 0 / 0 | 392.15s | 0 |
| PostgreSQL 17 | 1031 | 4 | 0 / 0 | 892.57s | 0 |

Each includes all 1035 collected tests with `-q -ra --durations=30 --junitxml=... --basetemp=...`. SQLite ended before PG started. Exact commands, timestamps, complete skip reasons, prior failed-node final PASS timings and result counts are in [final-summary.json](final-summary.json). Full logs retain all `-ra` reasons and the slowest 30 tests; JUnit and controller records are under [serial-full-final](serial-full-final). Each database uses its existing separate local venv, distinct fixture files/schema and read-only shared dependencies. NODE_PATH is `/workspace/browser-tools/node_modules:/opt/codex/runtimes/cua/lib/node_modules`; jsdom30.1.2. The final PG run does not claim PG coverage for the two explicitly SQLite-only protocol UI subprocess tests. Windows-native launch and protected Chromium sandbox limits remain explicit skips; sandbox/security settings were not changed.

History is retained, not relabeled:

- fcea was rejected **before full started** after an actual native fixture namespace defect; its collection, source/import hashes and independent failure are the `fcea-*` files. `fcea-pre-full-defect.json` states full_started=false.
- First exact-e6 concurrent complete runs ended FAILED: SQLite994PASS/40SKIP/1FAIL in676.36s (API readiness10s before capture callback); PG1030PASS/4SKIP/1FAIL in1102.62s (optimized no-queued child startup10s before guard assertion). [parallel-full-first-attempt](parallel-full-first-attempt) preserves complete logs/JUnit/commands and failure messages. No source, guard, timeout or coverage was changed for the authorized subsequent serial complete validation. The resource observation has no pre-run baseline and establishes no cause. The serial PASS results do not erase these failures.

Owned cleanup is complete: [cleanup.json](cleanup.json) records schema0/role0/public-table0/controller-and-child0, deletion of only the `sim2act.final-combined-regression=20261007` container, remaining label-container0, removal of private URLs/raw PG logs/XML and the four exact owned fixture basetemps. Public PG artifacts were sanitized and checked against the actual private password/URL before those records were deleted. Other trees, shared venv, containers and system policy were not modified.

This evidence supports local offline engineering verification. Mock provider fixtures and finite technical candidate checks do not constitute overall source/cold semantic acceptance, live provider activation, formal App publication, native pixel acceptance or complete P-B delivery. LIVE calls, push and CI by this agent remain0. The controller Plan predates the final freeze; the Log and final summary supply the completed outcome. The independent namespace repair evidence is separately preserved at `docs/evidence/bounded-native-namespace-fix-20261007` on the frozen candidate.
