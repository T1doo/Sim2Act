# Native fixture session diagnostic and independent pool transition

Final source: `5acfd6cc8bc70abe79814dee1e3360737db708fe` (base failed Windows source `e6c03cf15b7473ebce4cd3d5b8c4dcc06405a676`). Local only; no push, CI rerun, LIVE/model request, budget/runner/workflow/PowerShell/PNG-slot change.

The Windows attempt 37613698141 failed with `Owned conditional fixture exited before reply`; raw child exception remains UNKNOWN because that source discarded stderr. Engineering finished 1017 PASS / 18 SKIP; old protocol26 passed, new bound19/manual22 and report PNGs did not complete. The referenced browser-results hash and root error are preserved. Linux reproduction is evidence for the actual experiment gate prerequisite, not recovery of the original Windows stderr.

Actual old preparation uses the existing gated source/review/extract/cold chain (4 Mock requests), default 16-drain worker, and metadata recovery, leaving five jobs and sealed experiment pool. A new bounded Run in either existing project is correctly rejected with RESOURCE_UNAVAILABLE and no new Attempt/pool consumption, including -O. Counterfactual extra-QUEUED cleanup and same-DB other-project approaches were withdrawn; final source includes neither cancellation nor experiment bypass.

After old26 and its sandbox audit, the same protected Page navigates about:blank to destroy old polling. An owned manager joins the old API before starting the normally seeded independent test fixture on the same port; it verifies current new source ID/hash and health before a READY acknowledgment. Old full-table/pool fingerprints are preserved. Each seeded synthetic DB independently has 4 Principals and 12 Grants, verified with read-only SQL. This is two separately seeded authority baselines, not a zero-authority assertion across their creation. Bound19 plus manual22 use the new domain; manual report screenshots remain the original two output slots. No product authority changes are introduced.

The transition request and response publish completed same-directory temporary files via atomic rename/replace. An owned watchdog kills the Node child at its absolute original 150-second deadline even while snapshot/old-API join blocks. Final cleanup cancels/joins the watchdog and collects all owned children under original 10+5-second cleanup bounds. A timeout cannot acknowledge READY or proceed to a new API after the blocked operation returns. Short-deadline actual-process snapshot and stop tests verify child termination and no replacement/READY.

Evidence history:

- `target.log`: initial actual old experiment -> original-project bounded failure, 2 FAIL / 8 PASS.
- `fixed-target.log`: withdrawn same-DB other-project attempt, 2 FAIL / 18 PASS.
- `rotation-target.log`: first independent-pool implementation, 11 PASS.
- `final-target.log`: WIP pre-freeze validation, 18 PASS / 60.08s; not an exact final-source claim.
- `frozen-regression.log`: exact dedd source, 15 PASS / 70.84s, superseded by the atomic/deadline source.
- `atomic-deadline-frozen-regression.log`: exact 5ac source, 18 PASS / 0 SKIP / 73.23s; actual same-port HTTP/JSDOM normal/-O bound19/manual22, manager faults, deadline faults and existing guards/manual oracle.
- `receipt-regression.log`: incorrect test selector collection exit4; retained.
- `receipt-regression-v2.log`: bounded rerun to preserve actual same-DB gate and safe closed-child receipts. Earlier pytest temporary directories were evicted automatically; their initial logs remain, so no missing old receipt is claimed.
- `5ac-*-bound-native-results.json`: exact source real transition, old before/after fingerprints, fresh baseline, current source and 19/22 check receipts.
- `authority-sql-receipt.json`: separately measured synthetic authority counts.

Real protected Edge execution, final PNG pixels, Windows budget and original raw child exception remain NOT_RUN/UNKNOWN locally. JSDOM does not sign off native sandbox or the 900-second job. New Windows verification is the parent's responsibility after independent review and impact regression.
