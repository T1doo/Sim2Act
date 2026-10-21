# Absolute-path candidate retry — independent read-only result review

2026-10-21. Result: **ACTUAL_OWNED_FIRST_COMMIT_EXPIRED_PARENT_UNKNOWN_NO_NEW_WINDOW**. Source HEAD `102af120a66cda2c33ae2f7a48d5750e4e0fffa9`. Reviewer performed only source/evidence/JSON/hash/process reads and /tmp report writes: no product import, tests, database/SQLite opening, Worker, Mock, G0, prefix, launcher or commit execution, repository edits or new grant.

Evidence root: `/tmp/sim2act-authorized-native-g0-absolute-163d76cbc83647ae8f007dd917591761`; run below `runs/native-g0-absolute-163d76cbc83647ae8f007dd917591761`.

## Actual execution and stopping boundary

Unlike the earlier pre-prefix blocked attempt, invocation.json and parent-argv-observed.json both contain the exact absolute script `/workspace/Sim2Act/scripts/diagnostics/g0_bounded.py`, candidate flag and this run's grant/output-parent. The consumed marker exists. The observed process argv closes the earlier parent-argv evidence gap; this retry is a distinct actual attempt, not continuation of the consumed old grant.

Six raw Mock exchange records each carry SYNTHETIC_MOCK_TRANSPORT_NOT_REAL_HTTP. Final diagnostic records 6 exchanges, 8 method entries and 2 Source delegates; prefix-proof records real_models=0 and same-key replay. Control has original Generate/Source/extraction/Cold phases and G0_ENTER. Actual candidate route is OWNED, phase native:issuance, reason null, diagnostic_incomplete false. Therefore this was an actually reached and selected candidate, not a simulated route or a source-only unit result.

The single recorded target commit has ordinal 1, returned=false and DomainError; the second commit has no entry. Original scope_returned=false, both_commits_returned=false, complete=false, successful-authority final_deadlines=null and final deadline check NOT_PROVEN. The original second complete guard, W5, Cold2 and later PB qualification were not reached. The static StopBoundary/W5 boundary and zero authorizer denials support no settlement-write entry; w5_entries is explicitly a static stop-before-next-statement statement, not an observed counter. Reviewer did not open the final fixture database or infer its business rows.

The selected error chain locates `natural_spec_runtime.commit:2990`, VERSION_CONFLICT, “Production admission expired during verification”. This is the original final finite/stop predicate in the first commit, not Capacity fallback. Generic selected-path classification correctly remains UNKNOWN with UNDETERMINED_ORIGINAL_OR_CANDIDATE; this review does not rewrite the parent's conservative classification based on later inspection. Child final and parent are UNKNOWN, not candidate success.

## Actually captured deadline

Rejection diagnostic is complete and records stop=false and end=1792575671.5726795. Eleven named finite values were actually saved. Their minimum is run_check.deadline=1792575664.9779332, equal to the captured actual Run lease_until (version=1, fence=1). End exceeds that minimum by **6.594746351242065 seconds**. Source expires_at=1792577125.381348 and all recorded natural-spec/role/frozen/draft/call deadlines=1792575880.7124422 are later. Generate role is None and has no role deadline entry.

This lease statement is supported by actual finite values and Run snapshot, unlike earlier archives with missing finite/end/stop. `production_trial_policy.py:327–329` computes RunCheck.deadline as min(actual lease_until, original expires_at, created_at+original caps run_seconds). The named minimum equals the actual lease here; no duration was added twice, no old database time was modified, and no missing deadline was reconstructed. Checked_at=1792575660.0009522 still precedes the captured deadline, but later original verification finished after it. No lease extension is proposed.

## Recorded five-stage costs

| Original stage | Wall seconds | CGR check entries | old input_key entries | Codec calls | Returned codec bytes | Codec thread CPU seconds |
|---|---:|---:|---:|---:|---:|---:|
| _prepare | 14.953485608 | 3513 | 3499 | 3590 | 2405927206 | 9.388693579 |
| _graph_run_context | 5.509698047 | 1510 | 0 | 1510 | 1101866630 | 4.381916496 |
| _graph_pb_accounting | 0.451084922 | 95 | 0 | 95 | 69360640 | 0.336188378 |
| _graph_resolve_trial_source | 8.900123216 | 2324 | 0 | 2325 | 1736358180 | 7.056981730 |
| _graph_pb_archive_chain | 0.033014838 | 9 | 0 | 9 | 6798780 | 0.026559163 |
| Sum of these five stages | 29.847406631 | 7451 | 3499 | 7529 | 5320311436 | 21.190339346 |

The outcome wrapper's G0 wall interval is 36.6359487769987 seconds, while whole parent work is 348.2065204299979 seconds. The five-stage wall sum is not the complete G0 interval; original first binding and work between/outside named stages are not independently attributed here. The observer reports COMPLETE_OBSERVATION, timings_valid=true, thread_time_ns, maximum observed depth 1, and explicitly nonzero overhead. Its returned-byte sum is cumulative successful pickle output, not peak memory, stored file size, observed SHA byte count or unique input size. The codec CPU sum covers these instrumented function spans only, includes observation residual and is not full G0/process CPU. This single instrumented run has no same-context non-candidate counterfactual and proves no speedup or regression against historical G0 runs.

## Why OWNED still invokes codec: narrow source-grounded cause

1. OWNED installation occurs near the end of `_prepare`, only after the original Source producer, recipe/version gates, Generate producer, full-copy/equality/oracle admission and native qualification. The early part of prepare still performs original full raw continuity. Its 3499 old input_key entries are therefore compatible with actual later OWNED; the observation does not separately timestamp issuance inside prepare.
2. `_Frontier.values` (`_cold_accounted_native.py:350–374`) replaces only the two exact accounted roots and complete.source, complete.generated and complete.generation.run paths. All other independent roots and mutable aliases remain fresh. It does not erase general generation/source/audit/job, stage/raw/metadata/extraction, binding or role-limit state.
3. Every native `_ColdGraphRead.check` still invokes `_Frontier.check`→key→`_ColdGraphRead._frontier_input_key`→`input_bytes(_frontier_inputs=...)` (`natural_spec_runtime.py:1783–1853`). `input_bytes` re-reads typed PB contract storage, constructs the remaining complete envelope and calls original `_cold_graph_bytes`. That codec (`:1733`) creates a fresh BytesIO and protocol-5 private pickler. Native hashing uses a separate namespace, but still encodes the remaining mutable envelope afresh on each check.
4. The new frontier key path bypasses the old `input_key()` method, whose entry counter is the reported input_key_calls. Thus zero input_key_calls after prepare means that counter's old entry point was bypassed, **not** zero codec/serialization. The observed run-context 1510 checks/1510 codec calls and accounting 95/95 agree with that call chain; resolver has 2324 checks and 2325 codec returns, so not every extra codec can be assigned solely from these coarse counts.
5. Original repeated parent boundaries remain: `_ColdTrialGraph._base` (`:2488`) checks CGR, validates typed parameters and checks CGR again; `_trial_typed_guard` (`natural_live_admission.py:1349`) calls its full parent plus typed values; `_AccountedScope._full_check` (`cold_accounted.py:216`) still calls CGR. OWNED removes the selected accounted oracle layer after the final pre-issue original checks; it does not memoize current permissions/SQL/transaction/clock or the remaining frontier.

The narrow remaining bottleneck supported by these artifacts is therefore repeated fresh encoding/checking of the **remaining** mutable frontier, plus the original pre-issuance prepare work. The largest measured wall stages are prepare, source resolution and run context; their measured codec CPU is correspondingly large. This is a local causal explanation from actual counters and source, not proof of each root's byte contribution or the safety of deleting any retained scan. No per-root trace, alternative implementation, hardware/contention attribution, full-RSS/CPU bound or new component is inferred. The current slice demonstrably reaches OWNED but has not completed even the first original admission within its actual strict deadline; existing semantics must remain intact before any future qualification can be claimed. No optimization or new window is authorized here.

## Budget, source identity and cleanup

Selection records logical resident/live=85803380, peak=105470324 and work=50098473668149788430366, within the selected logical limits. After scope unwind resident/live=0 and active=false. These are allocation-ledger units, not RSS. Child cleanup reports THREADS_CLIENTS_CONNECTIONS_CLOSED; parent cleanup OWNED_GROUP_EMPTY with finalization_errors=[]. Read-only current process listing found neither parent PID40364 nor child PID/PGID40388. This supports the recorded cleanup, without claiming deletion of the retained evidence/database.

Disk observer reports 6911 samples, peak logical=2270397 and allocated=2289664 bytes. It remains a sampled budget, not a hard filesystem guarantee. G0 authorizer denials=0.

Read-only canonical JSON comparison shows this description's complete source_manifest map equals the earlier b4bac26 description map, and description equals the run source-manifest JSON. Source/dependency digest before, after child cleanup and after parent cleanup is `39190dfc45d353346bf41c1c12786e02e94d652c603331bf8bc9569c348efedd`; candidate profile digest is `f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f`. Reviewer independently hashed bounded/prefix/guard/stage-observer/native/cold_accounted/runtime source and found the expected frozen bytes. The entire dependency tree was not independently rehashed by reviewer; equality and parent/child verify_sources receipts are the full-tree evidence.

## Selected original-file SHA256

invocation.json `e05af3a46e906e87681ac9dfbcb9e22f87f4f26ab3cbe0fc3f6d76f514a2b33f`; parent-argv-observed.json `b0a3e0429adc50b85e181de6206c06176002870e9c8332e9ef6943e1a941c02b`; description.json `3437ca6dd92cdc6f38e48413a584a108c1039fedd03389f7dde7db1cdf66613e`; grant.json `254df40fe44fa6e636be96ae19539a04c71e02f291cae7e47f70ced1bf4121c4`; receipt.json `ffee1a745feb75a6a325a2498f85f922e3a3f7aedc8b9602c19c3030b8af9800`; diagnostic.json `f92e733288edffa0428d37fdcdd6b568c7b03de680c17a148768e65ff8f55632`; control.jsonl `ddb335563d34d05058f200befd311d09dc00c597da8f0d74be1e67bbeb2e3ecd`; mock-exchanges.jsonl `96fa7a702389b52b4b99f405434f9668949b333c51545d0d42c191acc037a109`; prefix-proof.json `8e78c74cb96ccdd655e21a48b28b548f4b7ca79579c9ed2afd3bb9a8c04effdd`; run source-manifest.json `b6f6bba67cfccb89e3b298c18fc9162c5bddbe77347ffe9d18c9e3ba07cf3705`.

This review seals a failed, safely closed actual attempt. It permits no new grant, retry, code optimization, database reopening or further execution.
