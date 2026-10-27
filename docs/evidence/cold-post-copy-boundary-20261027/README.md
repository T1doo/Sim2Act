# Remaining post cost: diagnostic attribution and snapshot counterexample

Base product: `4d1475500484d2e50e1eece23c0682c7e184cb24`. **No product optimization is admitted in this slice.** The previous candidates remain default off and unchanged. This is not a G0 run, performance acceptance, provider validation or seven-family migration.

## One diagnostic run, with an important budget failure

Existing final root-key-set reports cannot supply caller/exclusive attribution; the older stdlib profile covered only pre-settlement. One new isolated configured synthetic chain therefore used the existing CPython3.12 owner-thread stdlib profiler over post-settlement entry through foreground CLOSED. Product/core/schema/serializer identities were not wrapped. Explicit flags: FINAL_ONLY=1, POST_PAIR=0, PROFILE_POST=1. The existing configured environment/account/software substitutions, actual SQLite Store/Worker/approvals/accounting and HTTP MockTransport were used. Limits remained6 Mock/8 entries, external600 seconds plus10 cleanup, and the unchanged SemanticClock300-second cooperative budget check. No real model, G0, Cold2, native/browser window or user computer ran.

**Actual result: pytest1 passed, 2 warnings /443.95s; supervisor exit0 /444.811784969s, no timeout/forced kill.** One warning is the existing Starlette deprecation; the other is material: `Thread-32 (beat)` raised `AssertionError: Semantic regression exceeded real 300-second test budget` from `cold_semantic_clock.event_wait → healthy` and exited. See original `pytest.log`. This is NOT a healthy budget-compliant success and does NOT demonstrate normal heartbeat throughout. Foreground nevertheless completed five writes, normal pre/post and CLOSED, scopes became inactive/detached, and the final test-owned-thread-empty assertion passed. This is only final cleanup evidence, not retroactive health acceptance. The external600-second supervisor did not make the300-second failure acceptable. No guard/clock/lease was changed, no warning suppressed, and no retry occurred.

587 recorded Python files match before/after. The actual executed test and five dependencies are frozen byte-for-byte in `frozen-sources/`, sealed by `executed-sources.json`. After collection, the optional profiling modification was removed from the repository test entry; the archive preserves precisely what executed. Product files are unchanged. The later snapshot counterexample is a new test and is not claimed as part of that587-file execution set. `supervisor.py.txt` is the actual retained script; before.json records argv/flags/start/source hashes.

## Attribution, with nesting and observer limits

The original `.prof` and JSON are retained. Sum of function **exclusive** CPU is373.266103979 seconds under heavy profiling disturbance and the background budget exception. This cannot be scaled to the earlier uninstrumented58.278835-second post CPU, compared as a slowdown, or treated as production wall time / a30-second impossibility proof. Post owner measurement also includes profiler export. Application and test observer calls are present in the raw profile; inclusive values overlap and must not be summed across ancestors.

| Actual profile node | Calls | Exclusive CPU s | Inclusive CPU s |
| --- | ---: | ---: | ---: |
| `_trial_pure_data` | 66366 | 0.1147 | 127.7858 |
| its recursive `visit` | 13156404 | 42.6000 | 127.5634 |
| `_trial_typed_equal` | 41077 | 10.5633 | 29.9102 |
| C Pickler.dump | 10363 | 28.9332 | 38.1117 |
| `_schema_matches` | 4384706 | 17.5594 | 29.7137 |
| `_model_value` | 5906692 | 14.5082 | 34.9554 |
| SQLite Cursor.execute | 8173 | 0.1437 | 0.1437 |

SQLAlchemy-file exclusive total is2.043762418 seconds, separate from SQLite execute. This observation supports investigating pure repeated copying rather than initially blaming a database lock; it does not establish uninstrumented percentages.

Caller evidence for `_trial_pure_data`: `_graph_trial_accounted_models_from_raw`50988 calls /62.7178 inclusive seconds, `_graph_trial_stage_raw_from_raw`5220 /45.8265, `_graph_trial_extraction_models_from_raw`2820 /15.8063. These three sibling caller edges are distinct, but their enclosing stage-model/collector/check methods include them and cannot be added again. `_typed_parameter_models`788 /143.5853 inclusive; post composite539 /203.7510 inclusive. In comparison, `_ColdRunRawSeed.check`538 /10.3178 inclusive is smaller; its nested source-audit path includes default dumps and equality callbacks requiring substantial qualification, so that route was not implemented. Full targets/callers and top exclusive nodes are in `attribution.json`, reproducible from the raw JSON/prof.

Actual candidate selection remained539 post composites, pre293/post249 base selections and371 stage selections. Full-chain codec count18043 matches the prior candidate. Foreground result uses virtual business time, not real G0 qualification; summary exact equality is null because this was one diagnostic arm, not AB.

## Why the proposed borrowed streaming comparison is rejected

The identified helpers repeatedly evaluate `typed_equal(pure_data(left), pure_data(right))`. Their two recursively copied values preserve observation snapshots. Replacing them with complete left/right validation followed by comparing borrowed live containers changes those semantics even if every final graph pin remains.

`tests/test_cold_copy_snapshot_boundary.py` executes one controlled real-thread counterexample in the existing isolated SQLite/CGR fixture, with Worker/transport execution forbidden:

1. Both full graph roots start with value1. Original actual snapshot captures1.
2. The owned test thread changes both live roots to2. Original saved snapshot captures2.
3. Original strict snapshot comparison rejects1 versus2; borrowed live comparison accepts2 versus2.
4. The test thread restores both roots to1. The original complete late `graph.check` passes.

Actual **1 PASS /1.43s**, no physical Mock/model exchanges. Thread is joined and no test residual remains. This proves that complete side gates and a late full pin do not by themselves preserve snapshot behavior or detect transient change/restore. It is a rejection witness for the proposed algorithm, not a new product implementation or blanket claim that streaming is impossible. Left/right mapping normalization, batch-left-before-batch-right order, and-short-circuit errors, exact bool/int/list/tuple/NaN/cycle/DAG and depth semantics would also need preservation; no unproven comparator was added. Previously rejected type-dispatch/buffer experiments were not reopened.

## Contract boundary and next minimal technical choice

Retain the existing two observation snapshots under the current semantics. A safe optimization must either (a) capture equivalent values at the same original observation points in a demonstrably cheaper owned representation, with full schema/mapping/depth/error/concurrency and net-cost evidence, or (b) explicitly define a different local owned-capture observation point and prove the affected consumers under the already approved isolated ownership direction. General ownership approval is not itself a proof that this borrowed comparator is equivalent. Neither option needs relaxing SQL/auth/revocation/lease30/fence/clock/epoch/receipt, and neither is implemented here. This slice does not infer30 seconds is unattainable and does not request another G0 window to gamble on timing.

Independent read-only review confirmed the attribution and counterexample, **withdrew any healthy-profile interpretation after checking the thread warning**, and ACKed rejecting borrowed replacement and retaining originals. The profiling entry was frozen then restored; only the focused regression and evidence are added. No further full execution, performance promise, UI/package work or deployment followed. Original G0 UNKNOWN, provider provenance and overall F2/R0 gates remain open; October31 delivery risk remains high.

`manifest.json` seals every archive file except itself. Current product source remains the base source; this commit does not claim an additional runtime speedup.
