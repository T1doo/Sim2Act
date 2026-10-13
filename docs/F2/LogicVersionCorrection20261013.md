# Modified-version one-correction candidate: acceptance BLOCKED

This development branch extends the existing finite natural-spec correction chain to a rejected modified logic result. It is a candidate, not an accepted delivery. Tested product freeze: `9fb1104f0dac75ad265b91fc83cb0ac940e3c87d`; parent baseline `5dc3d54a1e2dfe32fb665480bb65dea3e10b9192`. No deployment or protected-branch change.

## Contract and implementation

`natural_spec_corrections.py` freezes the actual parent effective recipe, third-use Goal/material, explicit rejection/declaration, parent Worker proof, Release/origin and finite owned dependency trace. Existing paired receipts and exact approval fingerprint remain required. One accepted child permanently reserves its slot, including lost main/seal indexes; corrections of corrections remain forbidden. Old results, declarations and goals remain retained.

`app_jobs.py` and `pa_spec_apps.py` prioritize correction context over the default modified-version context. The source validation profile is sealed separately from the minimum new execution limits; it grants no extra execution budget. The source gate compares the owned contract budget projection without recursively entering `Store.frozen_contract`. Inspection/resume reuse the same already validated Release. The existing worker/executor is retained.

`web/owner-review.js` exposes the existing finite correction panel for a rejected modified version, displaying actual recipe/material/fingerprint, original Goal/all criteria/reasons, minimum execution budget and fresh acknowledgement. Original-key read-only recovery and selection fences remain. `tests/test_logic_version_corrections.py` creates fresh PA/PB modified-version per-use parents with synthetic models and simulated human declarations.

## Actual current-freeze results

Six terminal pytest groups, all with 464 source/fixture/config files unchanged before/after: **64 PASS, 9 FAIL, 1 SKIP; 1 deselected**. Counts include 61 qualification/lifecycle/switch regressions, 2 ordinary base correction regressions and 1 PA fresh modified parent. They do not include older runs or independent static observations.

The 9 failures are substantive and retained: PB fresh modified parent (1), PA actual modified correction (1), six late-injection cases (6), and PA full HTTP/JSDOM correction journey (1). The late callbacks did not fire, so these do not prove late-source/cancellation protection. The new correction did not reach an actual successful new artifact or independent new review. Full UI journey has zero passing cases; no result is inferred from successful preview or acceptance alone.

Ruff and JavaScript syntax pass. Mypy has the 5 existing status_report/tools errors; it is not clean. Ordinary independent source/qualification review found no new static blocker at the freeze; this does not override failed functional acceptance.

## Concrete current execution blocker

Accepted modified-correction Runs remain RUNNING. PA positive and PB parent show CLAIMED -> WORKER_LOST -> RECONCILED -> CLAIMED, reaching fence 5 without producing a terminal success. Late tests remain at fence 1 without reaching the synthetic model callback. Database copies, raw stdout/stderr, XML, source closures and full failure histories are retained in the evidence archive.

Static reading identifies a likely interaction: `Store.guard` calls complete source_scope_gate before checking the lease and again through frozen_contract; correction logic_gate freshly validates the complete Release/source proof. SQLite Store.tx uses BEGIN IMMEDIATE, so the heartbeat writer cannot extend the lease while a long validation transaction holds the writer lock. This is a source-based hypothesis; no timing profiler/private instrumentation has verified causal attribution. No lease/deadline/budget expansion, skipped authorization, cross-transaction proof cache, or unvalidated executor rewrite was used to hide the failure. The next required fix is bounded repeated-validation cost while preserving fresh authorization, source changes and transaction/lease correctness, followed by a fresh qualified source run. This candidate must not be reported as feature complete.

## Explicitly blocked and not run

The independent private-child UDF probe/diagnostic received a platform refusal: “This content was flagged for possible cybersecurity risk.” The complete original error and target are in `independent-private-probe-rejection.json`. That action is **BLOCKED** and was not rephrased or moved to another agent/tool/environment. The prior probe's 409 is not a private-read leak result. No private-body read-order dynamic guarantee is claimed.

PB correction/UI and startup matrix are NOT RUN; six actual late cases FAIL before callback, so successful late-injection behavior is not verified. PostgreSQL, Windows, native browser, real/paid models, real human semantics, complete P-A/P-B acceptance, remote CI and deployment are NOT RUN. SQLite synthetic tests cannot stand in for them.

## Evidence

[Machine-readable terminal results](../evidence/logic-version-correction-20261013/SUMMARY.json) and the archived raw histories have per-member hashes and archive readback verification. The evidence also preserves the older unsupported-preview, recursive-contract and source-profile failures; these are history, not added to the current result counts. Archive checksum and member counts are in the adjacent PACKAGE.json. [Final independent review](../evidence/logic-version-correction-20261013/INDEPENDENT_REVIEW.md) concludes BLOCKED, with four independent controller groups NOT RUN and capture process exit UNKNOWN after session loss; no exit success is inferred.
