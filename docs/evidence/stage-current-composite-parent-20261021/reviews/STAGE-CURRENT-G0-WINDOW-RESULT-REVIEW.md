# Stage-current single-window result: read-only review

Conclusion: UNKNOWN / NOT_PROVEN. The first target commit returned; the target receipt interval and settlement preparation were subsequently traversed according to the exact frozen source order. The second commit function itself was not entered: construction of its prefix argument failed in the original Store.guard. Neither full original scope exit nor final deadline success is established. No retry or new window is proposed by this report.

Execution source: `a6192df3b5b00cf891792af27ab47890da979ff5`.

Evidence directory: `/tmp/sim2act-authorized-stage-current-g0-dee917c4d72a4503b66a1fcab86527c6/runs/stage-current-g0-dee917c4d72a4503b66a1fcab86527c6`.

Reviewer read JSON/JSONL, source and process listings only. No product import, test, DB open, Worker, Mock, G0, launcher, grant or repository write was performed. `diagnostic.json` contains two JSONL records, not one JSON document. A read attempted nonexistent `src/sim2act/store.py` and was corrected to the actual `db.py`; no product command was involved.

Direct original observations:

- Parent receipt and child final record classify UNKNOWN; the author reports exit 2, consistent with the launcher's unknown outcome. Work wall time is 341.85972994199983 seconds; G0 observation is 30.122223297003075 seconds.
- Six Mock exchange records are present; child records eight Mock method entries and two Source delegates. Prefix proof records zero real models. Selection is OWNED, phase `native:issuance`, with complete diagnostic metadata.
- Candidate commit observations contain exactly ordinal 1 with `returned=true` and copied authority deadlines. No ordinal 2 observation exists. `original_scope_returned=false`, `both_commits_returned=false`, `complete=false`, `final_deadlines=null`, `final_deadline_check=NOT_PROVEN`.
- The captured DomainError is VERSION_CONFLICT, message `Stale worker lease`. The captured stack is `advance_model:3720` → `pa_spec_apps._cold_commit_prefix:2055` → `_commit_guard_prefix:1985` → `app_jobs.lock_live:933` → `db.Store.guard:1134`.

Frozen-source reachability inference, distinguished from directly recorded phase counters:

`advance_model` first calls `cold.commit(spec._cold_commit_prefix(..., "first"))`. After that commit returned, the source calls `enabled`, the original target `_cold_receipts`, an original cold check, the current Attempt SELECT and guard/add, original RECEIVED/parameters/response assertions, `parse`, usage equality, output validation, `receipt_for`, another cold check, and `settlement-parsed` graph.add. It then evaluates `_cold_commit_prefix(..., "second")` as an argument before calling the second `cold.commit`. The actual stack is inside that argument evaluation. Thus the preceding calls returned; a second-commit function-entry claim would be incorrect.

The exact OWNED source passes `receipt_platform=self.platform` into candidate selection, constructs `_ReceiptClosure` before issuance, and retains that closure through the target receipt call. `_cold_receipts` then runs its exact begin, original binding pin, original `_receipts`, result checks, produced, record_receipts and finish sequence. Because the later second-prefix stack was reached, successful traversal of this native exact pair and original receipt proof is supported by source ordering plus the observed later stack. It is **not** a separately recorded receipt-phase event or an observation of actual root strings/index m. Do not report a measured m, guessed suffix zero, individual receipt phase time, or a complete runtime protocol trace.

Precise deadline limit:

The earlier captured RunCheck row records checked_at 1792581851.6805797, deadline/lease_until 1792581858.9357865, version 1 and fence 1. The first returned authority includes that deadline. These are existing earlier reads, not the current row or time at the failing Store.guard. There is no first-return timestamp, no failing guard's time/current row snapshot, and no admission end/stop diagnostic (`selected_context_diagnostic=NOT_REACHED`). Store.guard shares this same message across three OR conditions: fence mismatch, lease_until <= time.time(), or status outside RUNNING/PAUSE_REQUESTED/CANCEL_REQUESTED. The exact disjunct and excess are therefore not proven by these artifacts. In particular, do not subtract 30 from the G0 wall time, reuse the previous window's 0.5311813354492188-second overrun, or claim the first return occurred within its lease.

Observed local codec costs:

| Fixed stage | Codec calls | Successful returned bytes | Observed codec thread CPU ns |
| --- | ---: | ---: | ---: |
| _prepare | 3628 | 2440515433 | 9895037422 |
| _graph_run_context | 664 | 486579200 | 2017571713 |
| _graph_pb_accounting | 95 | 69653905 | 284757779 |
| _graph_resolve_trial_source | 993 | 746566755 | 2949818866 |
| _graph_pb_archive_chain | 9 | 6826563 | 25606663 |

Total: 5389 calls, 3750141856 cumulative returned bytes, 15172792443 observed thread CPU ns (15.172792443 seconds). The two affected containing stages changed from the preceding window's 892/1143 to 664/993, reductions 228/150, consistent with the previously proved local parent-call reductions. `_prepare`'s 3628 remains unchanged. These are partial instrumented stage costs with nonzero observer overhead, not allocation/RSS, whole-G0 CPU, total fresh-root size, a normalized speedup or proof of enough remaining deadline margin. Zero old input_key counters in native stages do not mean zero codec activity.

Cleanup and bounds:

Child reports THREADS_CLIENTS_CONNECTIONS_CLOSED; parent reports OWNED_GROUP_EMPTY and no finalization errors. Independent read-only process listing found neither parent PID 55992 nor child PID/PGID 56016. After-scope logical accounting is resident/live zero and active false, peak 478097556; issuance resident/live was 458430612. These are logical charges, not RSS or evidence that the retained fixture DB was deleted. Sampled disk accounting reports 6785 samples and peak allocated 2273280 bytes, explicitly SAMPLED_BUDGET_NOT_HARD_QUOTA. Authorizer denials are zero. W5 evidence is labeled STATIC_STOP_BEFORE_NEXT_STATEMENT_NOT_AN_OBSERVED_COUNTER, not an observed W5 invocation count.

Recorded child source digests before/after and parent-after-cleanup agree at `7cbf3a6a12fb6dcdbef1a80dd8e900028ffd78ae645f21b753b32e6e6ee4405c`; profile is `f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f`. The five relevant product files were independently hashed and matched the archived source map: admission 84195d0061f965b8f1cc2e1bc385941c2739e09dce02293596b3025f14b4433a; runtime eeab5367c95502f0ba57f194519f46a3cbe054ef0150051ba3c3126b9182ea57; pa_spec_apps 6197df6c98bf1eeff463c7fc7b99c9c48e9fe308969fde8243715091a31712d6; native b6ab0b09f6abb9d8ddcd72b54127af0517a1d0f67728d96582c90e0f4d2c7147; receipts 49f0c0ff3cb6583d02cee96f7125fe237f5fb4c2d52ea8b1e39d282f42e2fca2. This review did not rehash the entire 4154-entry source/dependency environment or open the DB.

Minimum still unproven: passing the original second-prefix live guard, constructing and entering the second original commit, its complete original verification, and normal original context exit/final deadline check. The new receipt continuation is no longer merely an issuance-only qualification in this window, but full G0 completion remains unproven. No additional observer, component, root migration or execution is requested here.
