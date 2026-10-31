# Bounded pure-slice result: do not enable the old contract projector

Observed clean HEAD was **e9c08b4bc765277cdd71203336923bca5ee33ddb**; application source remains **c6a42c783fd92818654b02e5fb469675877c632a**. This round changes no `src`, application test, qualification or workflow file. The SQLite endpoint shadow remains disabled for reuse. No large Cold rerun or production speedup is claimed.

## Actual real-clock paired experiment

The existing native contract projector was rebuilt from unchanged source using the recorded command and loaded through its existing exact-build loader. Binary SHA256: **a9c32db0f64ab4a8f901a5c7c5dc3cf32cc72c67573437f38b7ec306459510f2**. This is this cloud's CPython 3.12.14 Linux build, not Windows qualification.

`benchmark.py` reads one existing **synthetic** PB contract from the previous probe's private SQLite prefix database, in read-only/query-only mode. The database hash is unchanged. It creates only a data shell of `_ColdGraphRead` using the original `ProductionTrialBinding` class, the existing synthetic account, a diagnostic synthetic approval-key string, and external aliases to actual contract keys/caps storage. This is not a saved approval or a real authority binding. It has no Worker, connection, Graph lifecycle, guard, authorization or G1. The unchanged `input_bytes` method is called; measured loops use `_snapshot_values=True`, so **the timed region does not encode graph bytes**. Original C Pickle byte equality, including surrounding key/caps aliases, is checked before and after each pair, outside timing.

Six alternating pairs, 1,000 calls per arm/pair, produced:

| Measurement | Result |
| --- | ---: |
| Median candidate/original wall ratio | 0.806218026 |
| Median thread CPU ratio | 0.806224618 |
| Median wall saving per projection call | 37.097943 microseconds |
| Native selections, including byte-equality checks | 6,007 |
| Python fallbacks | 0 |
| Synthetic contract JSON model-dump size | 6,049 bytes |
| Mock / real model requests | 0 / 0 |

This is fresh contract projection plus selection qualification on one actual synthetic contract. It is neither a 19% encoding/G1 improvement nor a whole-cohort benchmark. No extrapolated end-to-end saving is reported. The complete data/methods are in `paired-results.json` and `benchmark.py`.

## Two decisive refusal reasons

1. `_cold_graph_structure_guard._qualified` explicitly requires `graph._typed_native_candidate is None`. Directly selecting the existing backend would make the current structural fast path decline and invoke original full SHA/encoding. The microbenchmark contains no structural selector and cannot measure that net cost. The eligibility gate was not removed or bypassed; no claim of net component or G1 improvement is made.
2. The dormant adapter pins helper object identities, but not their current code/defaults/global roles. `helper_counterexample.py` runs in a new interpreter and warms both paths' lazy imports before changing only `gate.require.__code__`. It preserves the original require semantics and records its successful calls. The old candidate still selects native, produces equal values, and calls that hook **0** times versus **168** for the original projection. Thus complete output value equality is insufficient behavior equivalence. Code is restored in `finally`; no Worker/model/authority is created, and the private input DB remains unchanged.

The helper counterexample is an **offline candidate refusal**, not an exploit of an enabled production path or a product authorization result. It intentionally changes local Python code only inside that short-lived diagnostic interpreter. Existing source and running product configuration are untouched. A future qualifier also needs entry-signal changes, actual global role binding and native-export identities; this counterexample does not establish closure for those other cases.

The first scratch counterexample attempt assumed no successful require callbacks before resolving lazy imports. It failed that assertion. A diagnostic run measured 9,629 candidate-side import/projection callbacks versus 168 original projection callbacks. The final version explicitly warms both original and candidate paths, then records only the changed-helper call (0 versus 168). This preparation mistake is not a production test failure. Likewise the initial benchmark scratch used the wrong synthetic quota-subject account and was rejected by the original `ProductionTrialBinding` constructor; it was corrected to the existing fixture's synthetic account, without changing the constructor or any authorization.

## Concrete next implementation boundary

The existing whole `_trial_typed_values(models)` call is the smallest material pure seam identified by the independent review. Its prior observed 3,307 calls cost 5.346373 exclusive seconds. A new **single-call whole-cohort backend** can preserve all current fresh mutable-value checks while reducing Python traversal overhead. It does not require proving all external G1 environment dependencies or moving old Graph/authority across transactions. It does not exist yet; the old projector cannot stand in for it.

See [the precise implementation boundary](next-minimal-pure-kernel.md). No safe, materially faster runtime substitution was demonstrated this round, so no runtime route was enabled and the unchanged large sample was not rerun. The already accepted save/reopen/locked-cancel evidence and remaining 42–46 second writer interval remain [separate](../g0-effective-single-publication-20261031/README.md).

No fifth Windows CI, user-computer operation, main/Release/deployment, new credential, fee, permission, model request or lease extension occurred. The token value and model/database contents are not included in these evidence files. Private fixture paths and hashes identify project-generated synthetic inputs only.
