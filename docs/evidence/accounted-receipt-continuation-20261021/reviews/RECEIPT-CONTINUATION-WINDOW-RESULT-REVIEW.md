# Receipt continuation candidate — actual once-only result review

2026-10-21. Result: **OWNED_FIRST_COMMIT_EXPIRED_RECEIPT_INTERVAL_NOT_REACHED_UNKNOWN**. Independent read-only source/evidence review; no product/code import, tests, database opening, Worker, Mock, G0, receipt/commit/launcher execution, repository edits or new grant/window by reviewer.

Run: `/tmp/sim2act-authorized-receipt-g0-1d84330347f74f3ba56ff88ee2195995/runs/receipt-g0-1d84330347f74f3ba56ff88ee2195995/`. Actual/current HEAD `5a012556196271c5b33137a1d0b9b4864c64784c`. Source digest `1c12ad8aaeaaaf41c635863275f6c154a5b2d5b4f826da65b91e522a2624de91`; frozen profile `f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f`. Consumed marker exists and absolute parent command is recorded. This attempt is complete and was not retried by reviewer.

## Direct result

Parent receipt/launcher output and child final classification are UNKNOWN. Author reports exit 2, consistent with the launcher's UNKNOWN return rule; receipt does not independently contain an exit-code field. The selected context records VERSION_CONFLICT, Production admission expired during verification, traced to `natural_spec_runtime.commit:2991` from original advance_model first commit. This is the original finite/stop admission predicate, not a continuation-name, provenance or Capacity error. Generic selected-path error_origin remains UNDETERMINED_ORIGINAL_OR_CANDIDATE; reviewer does not rewrite that classification.

Diagnostic.json contains **two JSONL records**, not one JSON document. The child_final record was selected and compared with receipt/control. G0 entered; 6 exchange records are SYNTHETIC_MOCK_TRANSPORT_NOT_REAL_HTTP; final counts are 6 Mock exchanges / 8 methods / 2 Source delegates. Prefix proof records real_models=0. OWNED was actually issued at native:issuance, diagnostic_incomplete=false and reason=null.

Target first commit has returned=false, deadlines=null, error_type=DomainError. Second target commit has no entry. Original context did not return, both_commits_returned=false, complete=false, final_deadlines=null, final_deadline_check=NOT_PROVEN. The target Cold post-first-commit _cold_receipts call, its begin/binding/result/proof pair, second guard and W5 were not reached. This statement concerns the new target interval, not the earlier Source receipt helpers used by the prefix. Qualification did reach and admit its preloaded raw/capacity domain; that is not runtime verification that the new proof roots were accepted or original target receipts passed.

## Actual deadline calculation

The rejection diagnostic contains eleven finite values, end=1792580405.388139 and stop=false. Minimum is run_check.deadline=1792580404.8569577, equal to actual Run lease_until; version=1/fence=1, checked_at=1792580398.1483963. The actual overrun is:

`1792580405.388139 - 1792580404.8569577 = 0.5311813354492188 seconds`

Source expires_at=1792581865.5007024 and the other recorded natural-spec/role/frozen/draft/call deadlines=1792580620.759508 are later. Generate role has no deadline entry. This is supported by actual named finite/Run values. It is not G0 wall minus 30, not a reconstructed old deadline and not a candidate capacity refusal.

G0 outcome interval is 30.576640528997814 seconds; parent work=341.7464095940013 seconds. The interval includes its own entry/unwind boundaries and must not replace the directly captured end-minus-minimum calculation. No first-commit successful return time exists because the commit did not return. No receipt pair or final closure deadline success can be inferred from a near miss.

## Recorded cost and budget limits

Five recorded stage walls: prepare 15.361985817, run context 3.425767411, accounting 0.381547731, source resolver 4.779158223, archive chain 0.033442487 seconds; sum 23.981901669 seconds. Check entries=3545/892/95/1142/9, old input_key entries=3537/0/0/0/0. Codec calls=3628/892/95/1143/9, total 5767; cumulative returned codec bytes=4030692610 and observed codec thread CPU=16.176437880 seconds. Observer overhead is nonzero and timing basis is only the recorded function spans, not full process/G0 CPU or RSS. These records do not establish a causal whole-run speedup/regression versus the prior window.

Actual selected logical ledger resident/live=458430612, peak=478097556, work=188404034025305936651508, below the frozen resident/peak/work limits. After unwind resident/live=0 and active=false. These are conservative logical units, not physical bytes/RSS. The budget successfully admitted OWNED; increasing it does not address this observed deadline rejection.

## Cleanup and frozen-source evidence

Child final reports THREADS_CLIENTS_CONNECTIONS_CLOSED; parent cleanup OWNED_GROUP_EMPTY and finalization_errors=[]. Read-only process listing found no parent PID51568, child PID51592 or PGID51592 member at review. Authorizer denials=0. W5 field explicitly uses STATIC_STOP_BEFORE_NEXT_STATEMENT_NOT_AN_OBSERVED_COUNTER, consistent with the first-commit failure source path. Evidence/database remains retained; reviewer did not open or decode it and makes no evidence-root deletion claim.

Disk observer: 6785 samples, peak logical=2262825 and allocated=2277376 bytes, sampled budget only. Source digest before/after child cleanup and after parent cleanup matches the description digest. Description equals run source-manifest JSON under canonical read-only comparison. Independent current SHA of four product files matches their frozen manifest values and the earlier final source ACK: native b6ab0b09..., receipt module 49f0c0ff..., runtime eeab5367..., pa_spec_apps 6197df6c.... Full dependency validation is parent/child verify_sources evidence; reviewer did not independently rehash every dependency.

## Minimum remaining acceptance conditions

The first original commit must finish successfully under its actual strict finite/stop conditions, **with time still sufficient** for the original target receipt consumer, second complete guard and full scope/final clock closure. The observed 0.531-second deficit is only the already-reached first-predicate deficit; it is not the total reduction sufficient for entire G0 completion. Original leases/checks must remain unchanged.

Then the actual target receipt interval must demonstrate its original validation and exact same-reader/dynamic-m pair, followed by the untouched second guard and scope/final deadline check. This window supplies no runtime evidence for those not-reached steps. No new component, observer, root migration, automatic retry or execution window follows from this review. The failed original check and safe cleanup are the bounded actual result.

Selected original SHA256: receipt.json `e1ed3926fc8f6ab65b148878f689e0c2da66f92045d316a3c86ca2a443a08a64`; diagnostic.json `a7c753f15e96800b7ef722da7c68ba6ce1695b78d9bb4de6dace8d5ff593efbc`; control.jsonl `cf05f28507baa1d611e6e8c63c67775a9a34c422528b4522a77f1f983ec38376`; prefix-proof.json `5973ee954043eb9798f83cf878e05e68c26c4237983a9d762a1997671ea61faa`; mock-exchanges.jsonl `2fd47be75658736744d95b518921c1350b5799be50c2fa256e3c56007b685f22`; run source-manifest.json `c6b641f97ccfc72faf8f27ab3d8415238d0df31a1c5240cfb47ed6affc480f0e`.
