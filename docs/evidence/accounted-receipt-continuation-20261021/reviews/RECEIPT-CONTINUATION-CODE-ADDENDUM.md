# Receipt candidate draft — incremental read-only review

2026-10-21. Author is running a temporarily frozen local batch; no final source hashes/results are attested here. Reviewer performed source reads only, no product/test/database/Mock/G0 execution or repository edits.

The previously reported pending/ordinal/status/run gates, intent-key prepayment, exact protocol dispatch, candidate/graph owner checks at dispatch, default no-frontier/no-private-import path, prepaid extent traversal/Unicode/shared-DAG sizing and explicit two-root administration were read as corrected in the latest draft. The author reports an earlier 69-case batch changed source during execution and produced 68P/1F software-fingerprint refusal; this is not treated as a passing final batch. Current 22-case results remain pending in this addendum.

A new P2 remains in native cleanup: `_NativeCandidate.release` currently invokes receipt.release whenever its type is exact _ReceiptClosure, without confirming the candidate/graph ownership that the new entry helper requires. A G1 candidate whose receipt reference has been replaced with a G2 exact closure will correctly fail the entry owner gate, but G1 cleanup then sets the G2 closure's result=None and phase=CLOSED. Rejection cleanup must not mutate a foreign active scope.

Minimal correction: release only an exact closure whose candidate is self and graph is self.graph; otherwise discard the local reference without calling foreign cleanup. Keep normal owned release and logical ledger closure. This mirrors existing graph invalidation's refusal to dispatch cleanup to a foreign mode. Do not edit source during the currently running frozen batch; preserve original outcomes and review final hashes after any correction. A local cross-graph cleanup test can assert G1 invalidation leaves G2 protocol unchanged, without a Worker or G0.

No final code, numeric-budget, execution-window or grant ACK is given by this draft addendum.
