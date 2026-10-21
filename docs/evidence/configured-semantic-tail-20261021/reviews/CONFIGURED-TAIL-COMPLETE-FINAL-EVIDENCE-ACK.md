# Configured synthetic complete tail — final evidence ACK

**ACK within the configured synthetic virtual-business-clock scope. No remaining identified P1/P2 in this reviewed slice.** The terminal author log reports **1 pytest test passed in 257.53s**, containing six explicit cases. This reviewer read the frozen source and existing artifacts only; no tests, product imports, database opening, Mock calls, signals or repository writes were performed. This is not a new execution authorization.

The seven SHA256 values remain exactly those in `freeze-complete.json` and in the accompanying `CONFIGURED-TAIL-COMPLETE-IN-PROGRESS-REVIEW.md/json`: five test files and the unchanged two product files. The product source/script diff is empty. The partial review remains an earlier observation; this addendum closes its pending suite-result questions.

Both normal arms execute the actual configured `_cold_model_before` path through original `_prepare`, two actual commit returns, the precisely recognized actual Cold receipt, and normal original context return. TailStop then stops before W5/Cold2; Cold Attempt remains RECEIVED. This demonstrates the complete C1 admission-tail semantics under this fixture, rather than a synthetic commit stand-in. It does not demonstrate complete business settlement/W5, production qualification or real-clock G0/lease performance. The old arm restores only the two original guarded policy calls; both arms share the other current implementations and existing configured three qualification replacements.

Both complete serialized authority-output files are independently byte-identical under `cmp` (SHA256 `01cb964d2d5ae30239ae15b5cd56705cf435e16eb326f6bb9106cdfc79bc76e1`), with equal original context/source business fingerprints. The passing test compares the complete in-memory ordered SQL/parameter sequences, complete outputs and Run-predicate call counts; its final summary records all three assertions passed. SQL statement counts are 7735 per arm and Run predicates two each. The reviewer did not replay SQL or independently materialize a database comparison. The tagged quoted-name fix affects diagnostic serialization only.

All four negative oracles are reached with `fault_applied=true` and original scope not returned normally:

- Final expiry: both commits and receipt complete, then original exact post-scope expiry DomainError rejects.
- Mutation after first commit: exact VERSION_CONFLICT / Native mutable frontier changed; no second return.
- Source revocation: configured source checker raises LIVE_BLOCKED; the test requires `check_source` in the original traceback, not any generic failure. It is a configured qualification-boundary revocation witness, not a real account revocation.
- Same-transaction SQL write fault: first probe insert returns, second actual SQLite insert violates CHECK; the test requires SQLite code 275 and a new-transaction count of zero persisted probe rows. The final summary's generic SQLAlchemy code `gkpj` is not itself SQLite's 275; that precise code and rollback are passing source assertions.

Final summary is emitted only after those six cases, both output/SQL comparisons, unchanged template SHA, cumulative **13 exchanges / 15 method entries / 2 delegates**, and absence of new live threads all pass. Each case also checks inactive graph/accounted mode and runs union-thread cleanup in `finally`; the successful arm tests closed-guard reuse rejection. This supports the stated fixture cleanup/cross-scope assertions. A read-only filename listing found no `fixture.db-*` sidecar. The owner's separate no-pytest/timeout-process observation was not independently sampled here.

The cumulative 13/15 explicitly includes two earlier failed harness Cold calls in addition to the original 5/7 prefix and six final cases; it must not be presented as one uninterrupted 13-call successful run. The same untouched pre-Cold template is hash-checked; failed Cold databases are not restored. Metadata reconstruction and local test allowance remain disclosed.

Observed codec calls **8373 → 8337**, returned bytes **4920607268 → 4894540040** establish only this instrumented local difference. They establish neither total helper CPU/RSS cost nor real-time speedup. The business clock is deliberately virtual and held during admission verification; existing real-clock failures remain separate evidence.

Evidence bindings:

| Artifact | SHA256 |
| --- | --- |
| freeze-complete.json | 93083304a68d37474377d43cd92ec037f76e96ce6016f8a3106294bae082c860 |
| complete.log | bdcf06a545b990133a5009b902c37ecb8b25118be644c0e0a87638a182f9cc81 |
| complete-semantic-difference.json | 51ba34eabf6c03fc9425493cc7f247cfddfaf5ddfce557a40d8e8b858cf2020b |
| revocation/tail-result.json | 4492cf1baf30de02701406fd191fec24fa4538312849f3854520b77310eb2168 |
| write-fault/tail-result.json | d54b8a4f81fe52ccb1c82a7949b0d40ad39ebc7a94966c61daf31cc3dd3a124f |

Files are under `/tmp/sim2act-configured-semantic-tail-20261021/`; case artifacts are under `pytest-complete/test_complete_configured_old_c0/`. No `complete.xml` was present at the attempted path, so this ACK cites the actual text log and JSON rather than claiming a JUnit review.
