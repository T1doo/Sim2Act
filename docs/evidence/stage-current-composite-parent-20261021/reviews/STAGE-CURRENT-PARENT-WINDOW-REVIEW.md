# Third parent candidate: single-window result review

**Confirmed result: UNKNOWN / final deadline NOT_PROVEN.** OWNED was selected and the first `_ColdTrialGraph.commit` returned. The original fence/lease/status guard refused while evaluating the second commit's prefix argument. The second commit function was never entered. No complete G0, final original-context return, second commit, Cold2 or W5 acceptance is established.

The reviewer read original JSON/JSONL/logs, relevant frozen source and hashes only. No tests, DB connection/query or DB-file inspection, product, Mock/model, G0, profile or signals were executed; no repository file was changed and no grant/window was created. Read-only process listing independently found no launcher PID 55992, child PID 56016 or member of owned PGID 56016. Child handle cleanup is supported by its recorded marker rather than retrospective inspection of each handle.

Root: `/tmp/sim2act-authorized-stage-current-g0-dee917c4d72a4503b66a1fcab86527c6/runs/stage-current-g0-dee917c4d72a4503b66a1fcab86527c6/`.

Execution/current checked HEAD is `a6192df3b5b00cf891792af27ab47890da979ff5`, with clean working tree at the source check. Recorded source digest is `7cbf3a6a12fb6dcdbef1a80dd8e900028ffd78ae645f21b753b32e6e6ee4405c`, identical in description/grant, child before/after and parent post-cleanup. Eight relevant source files were independently hashed against the saved manifest, including final stage-current source `84195d0061f965b8f1cc2e1bc385941c2739e09dce02293596b3025f14b4433a` and unchanged runtime/native/receipt/launcher/guard/prefix/apps files. This is not a whole-environment manifest recomputation. Profile remains `f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f`.

Invocation and separate observed parent argv use the absolute launcher path and this exact consumed grant. The consumption marker is present, and supplied evidence has one run directory and no retry. The unchanged limits remain six Mock exchanges/eight method entries, prefix 480s, G0 supervisor 120s, work 600s, cleanup 5+5s and directory 64 MiB sampled monitoring; these do not extend the original lease or replace its safety gates. Parent reports exit 2, consistent with the frozen UNKNOWN-to-2 launcher branch; the reviewer did not independently capture its original process exit status.

The child final record reports **6 exchanges / 8 method entries / 2 Source delegates**. The exchange archive independently contains six status-200 records identified as synthetic Mock transport, not real HTTP. This fixed isolated fixture supplies no real-account or production-model qualification. Control records contain one G0 entry after the expected synthetic prefix.

The candidate record has exactly one commit, ordinal 1, `returned=true`, with successful original authority deadlines. The earliest is `1792581858.9357865`. There is no first-commit return timestamp, no second commit record, no normal original-context return and no final deadline list. First commit return entails passage through its own internal finite check; it does not prove its later return was within lease or that the whole original context completed on time. Here commit is the validation helper, not evidence of an enclosing SQL transaction commit.

The error is `DomainError / VERSION_CONFLICT / Stale worker lease`, traced through `advance_model:3720 -> _cold_commit_prefix -> _commit_guard_prefix -> lock_live -> Store.guard`. Python evaluates `_cold_commit_prefix(..., 'second')` before calling `cold.commit`; the exception occurs in that argument evaluation. The original `Store.guard` condition is a disjunction of fence mismatch, `lease_until <= time.time()`, or disallowed Run status. No fresh `r`/`now` sample was saved at that guard, so this review does not isolate one disjunct, calculate a precise lease excess, or infer one from wall duration. Raw selected-path `UNKNOWN` and `UNDETERMINED_ORIGINAL_OR_CANDIDATE` remain unchanged; `selected_context_diagnostic` is `NOT_REACHED`.

The recorded failure position and frozen straight-line source imply that the earlier original `_cold_receipts` call returned through begin/binding pin/original receipt pass/produced/record/finish, and that reception-row checks, parse, usage/schema validation, settlement receipt creation and `settlement-parsed` pin completed before the second-prefix expression. This is **control-flow inference**, not separately observed receipt phase/root-name/index-m samples, payload equality, DB final-row inspection or a complete runtime acceptance. Do not invent an observed `m` or proof-root label. Cold2/W5 absence likewise follows the stopped source position and boundary design, not a dedicated W5 counter.

G0 wall duration is **30.122223297003075s**, total supervised work **341.85972994199983s**. Their bases differ from the lease clock; wall-minus-30 is not measured guard lateness, and total work is not G0 time.

Logical issuance resident/live **458430612**, peak **478097556** and work **188404034025305936651508** equal the prior receipt-candidate run's accounting values. They remain below the unchanged explicit logical caps, with no capacity refusal reported. After scope unwind resident/live are zero and active is false. This is conservative logical reservation/fuel accounting, not actual RSS, heap/GC release, CPU timing or all-input qualification. Documented original SQL decode/materialization and full guard/codec baseline exclusions continue to apply.

Directory monitoring records **6785 samples**, peak logical **2256916 bytes**, allocated **2273280 bytes**, below 67108864. Its mode is explicitly sampled budget, not native hard quota. The configured .1 interval is not scheduled; samples run each supervisor iteration/finalization with .05 selector cap, and maximum observed completion interval is about .138s. No between-sample peak or process RSS guarantee follows.

G0 authorizer denials are zero. Child final marker is `THREADS_CLIENTS_CONNECTIONS_CLOSED`; parent reports `OWNED_GROUP_EMPTY`, empty finalization errors and unchanged source digest. These records and the separate empty-group observation support cleanup, not business completion.

The complete five-stage observer records **5389 codec calls / 15.172792443 thread CPU seconds / 3750141856 returned bytes**. Run-context/resolver are 664/993 codec calls, consistent with the intended local reduction of 228/150, total 378, from the prior saved 892/1143 observations. This is an instrumented call-count comparison, not complete G0 improvement, an uninstrumented speedup guarantee or remaining lease margin. Other stage calls are prepare 3628, accounting 95 and archive 9. Observer overhead is nonzero; returned codec bytes are not measured SHA calls or bytes.

Original-file SHA-256 bindings:

| Artifact | SHA-256 |
| --- | --- |
| receipt.json | 21b987ec7107628f5addd7bfcb55248bff9a043c3ffae625897301a614b4671b |
| diagnostic.json (two records) | cd548a7f6cd33b29d9c0b0603de80b2232768e793776739f6e2a240eac476177 |
| control.jsonl | e963182a5e84f578a1d9a81150a1c35ac3428b4817e54f58c8aa67144e3cdc80 |
| mock-exchanges.jsonl | 0bf4a98859c905a28966c632e09f861cfab0512b5f9deb86320a3a44a52e88f3 |
| parent description.json | 626e2d5566fb396d71b8ee7d6f8ce827741a899d28272da4c8a37936290121eb |
| parent grant.json | 5c3bc3b276936147c37ef57a172afa9f992c43da0e0f2c875ec4929e47954f43 |
| parent invocation.json | 29d8437b6afab7834772cb64502c96d9f65a49025307714a951c5d4db8b2ceea |
| parent parent-argv-observed.json | 1c09fe746969c28a6f22dc3ad81bec6442869245950e95c280e5a2c7da68e3d5 |

The parent receipt's DB byte hash remains an author-recorded binding; no database semantic verification is supplied here. No budget/lease/gate change, wildcard, new implementation or further attempt is approved by this result review.
