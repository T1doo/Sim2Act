# Third-window original-result independent review

Decision: **ACCEPT_ACCURATE_THIRD_WINDOW_ORIGINAL_REJECTION_AND_HOTSPOT_EVIDENCE_NO_FOURTH_WINDOW_NO_PRODUCTION_CANDIDATE_ACK**.

Executed HEAD: `cdda2b2ed6bce1393b90a500c0377294e4d82e34`. Reviewed original evidence directory: `/tmp/sim2act-g0-monitored-third-20261021/authorized-monitored-g0-third-20261021`. This was the already-consumed third window; I did not execute or authorize another one.

The original G0 DomainError is VERSION_CONFLICT / “Production admission expired during verification”. G0 wall is **30.985113144 seconds**, compared with **342.467021839 seconds for the whole window**. Original end 1792548718.8062055 exceeded the captured minimum finite/run_check.deadline/actual lease 1792548717.850685 by **0.955520630 seconds**; stop=false, original diagnostic incomplete=false and authorizer denials=0. Other finite deadlines were later. This is an original business deadline rejection, not observer or disk-budget rejection. W5 is stopped at the original static next-statement boundary, not measured by a separate runtime counter; G1/finalguard were not reached.

I independently read six persisted synthetic MockTransport request/response records, all status 200, and seven control events. Final diagnostic says six exchanges, eight methods and two Source delegates. Pre-cleanup and child-final original error, finite/stage evidence and observer aggregates match exactly. The classification remains INTERRUPTED, not PB success. As in the approved StopBoundary design, BaseException retains the rejected scene rather than entering ordinary production rejection writes; retained RUNNING/RECEIVED scene data would not by itself imply production cleanup failure. No DB payload was opened by this reviewer.

The five stage wall intervals total **24.919289479 seconds**, not all G0 wall. The stage observer reports all five reached, COMPLETE_OBSERVATION, valid timing, maximum depth 1 and no observed helper exceptions. Recomputed totals:

| Metric | Calls | Thread CPU seconds | Accumulated codec output bytes |
| --- | ---: | ---: | ---: |
| codec | 5697 | 16.319125064 | 4,408,544,578 |
| typed storage | 20783 | 1.485238333 | unmeasured |
| raw copy | 18996 | 2.004102806 | unmeasured |
| typed comparison | 32672 | 0.732434221 | unmeasured |

Codec is **79.447% of the four observed, nonnested metric CPU totals**, not a measured percentage of total G0 CPU. Its cumulative output volume is neither unique source size, peak memory nor observed SHA input calls. With maximum depth 1 these metric intervals did not nest each other, but codec still includes its native Pickler, fresh custom reducers, metadata reads and other uninstrumented work. Observer cost remains nonzero, and neither old heavy-observer totals nor the smaller synthetic profile establishes a directly comparable performance baseline.

Cleanup: parent reports OWNED_GROUP_EMPTY and finalization_errors=[]; child records THREADS_CLIENTS_CONNECTIONS_CLOSED. I independently scanned /proc stat files and found no member of recorded PGID 708; no signal was sent. The disk monitor recorded 6796 samples / 6795 intervals, mean completion gap 0.050399277s, min 0.000188104s and max 0.143231934s. Allocated peak 2273280 bytes stayed below 64MiB. This remains a sampled budget, not a hard quota or realtime interval.

Provenance: all seven non-DB receipt evidence hashes and lengths match the original files. Description and run source-manifest objects are identical; their 4137-entry digest matches grant, child-before, child-after and parent-cleanup values. Six key current diagnostic/product sources match their execution-manifest hashes. This authorization parent contains one grant consumption marker and one run directory, with no fourth-run evidence. Current HEAD equals execution HEAD and tracked src/historical evidence had no diff. The original DB size/hash are receipt-reported only; I did not open, hash its payload or decompress it. Earlier tmp roots being absent/old archives not restored are parent precheck statements, not independent recovery work.

**No production optimization candidate is ACKed.** The real stage evidence establishes the codec as the largest of these four observed costs, but does not distinguish its native full serialization/buffering from RowMapping/Limits reducer, metadata-validation and marker/import cost on the actual stage inputs. The existing 61657-byte stored-contract/synthetic-row pstats cannot supply that missing same-input decomposition. A large aggregate is not proof that any part can safely be removed.

The current codec already uses a fresh C Pickler/memo for complete current inputs. Reusing bytes/memos/row metadata would weaken mutable-state scanning; replacing the rejecting reducer with an unproven dispatch table can change unknown-type rejection and callback order. Validator/SHA/type-dispatch/prefix changes, streamed SHA, fewer pins, cross-transaction caches and lease changes are excluded. No source change is justified merely to produce an optimization commit. A candidate needs a concrete cost mechanism and equivalence evidence retaining complete fields/hidden metadata/aliases, every fresh read and original callbacks/error order; those are not present in this result.

Reviewer activity was read-only non-DB source/log/hash/JSON and /proc inspection plus writing this /tmp report. No tests, profiles, business fixtures, Mock, G0, launcher or signals were run. G0 expiry remains unresolved and no fourth window is authorized.

