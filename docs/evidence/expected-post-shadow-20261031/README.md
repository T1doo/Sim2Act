# Expected-post data shadow: implemented, not enabled for reuse

Frozen tool commit: **8c794051f2be2fee9ec07b99f58f7f2959f3247e**. Accepted application: **c6a42c783fd92818654b02e5fb469675877c632a**. There is no `src/tests` difference between these commits. [The isolated tools](../../../tools/expected_post_prototype/README.md) are not imported by the runtime.

**A real SQL endpoint differential is implemented and exercised. The complete semantic/authorization dependency bridge is not implemented. No production writer optimization is enabled.** Original G1 remains authoritative; `eligible_for_reuse` is fixed false.

## Actual one-Cold result

One bounded probe completed at **2026-10-31 08:24:08 UTC**, exit 0, elapsed **147.851912 s**. All five tool-file hashes matched before/after and frozen Git blobs. Core callees were not replaced by the observer; existing synthetic account/environment/software/heartbeat fixtures and **virtual business time** were explicit. Six fixed Mock exchanges, zero real model calls, no Cold2.

1. At original G0 `promote` entry, capture complete ordinary-main logical data and an independent SQLite backup, before any mutation. No original journal mode or page header edits.
2. Record five actual native DML statements, final primitive bound parameters, rowcounts and change deltas. Preserve the original intermediate Attempt SELECT.
3. Wait for original G1 **READY** before collecting uncommitted actual post data from the same connection. Replay captured statements only on the isolated G0 backup; compare complete logical endpoints.
4. Result: **DATA_MATCH**, **eligible_for_reuse=false**. Original G1 continues through settlement/tail to **CLOSED**. The frozen test also asserts original transaction COMMITTED and one actual Cold Attempt VERIFIED; exit 0 supports these assertions, which are not additional raw JSON fields.

| Observed W5 operation | Actual affected rows | Actual change delta |
| --- | ---: | ---: |
| UPDATE attempts | 1 | 1 |
| INSERT NS_SETTLED event | 1 | 1 |
| UPDATE operations | 1 | 1 |
| UPDATE internal_app_runs | 1 | 1 |
| INSERT SPEC_STEP_VERIFIED event | 1 | 1 |

SQL shapes and parameter **hashes/types** are published, not parameter values. Timed collector regions: **0.282047 s** G0 capture; **0.342858 s** post comparison. These are added diagnostic costs, not full observer overhead or time saved. This is not real-clock lease, PostgreSQL, Windows, live-model, first-fresh-reopen or two-Cold performance acceptance.

## Data coverage and refusal boundaries

Images include complete captured main schema and ordinary table rows, typed values, duplicates, rowid or WITHOUT ROWID keys, internal sequence/stat tables when present, and index definitions/metadata. Authoritative `table_list.wr` and SQLite ASCII case rules determine row identity. Capture all rows, not just observed IDs, so missing/range membership changes participate in endpoint comparison.

This does not prove every query result sequence or identical intermediate effects. Without ORDER BY, logical rows/index metadata alone are not a query-order certificate. An earlier different write overwritten later can have the same endpoint; a dedicated test preserves that limitation. The plan owns data bytes; the clone connection belongs only to the observer lifetime and its complete before data is rechecked before replay.

Limits are page/byte preflight, schema/row collection caps and cooperative time checks, not hard SQL interruption or peak-memory guarantees. Existing driver callbacks can still run on diagnostic reads; their provenance is unproven. No authorizer, progress/trace callback or function is cleared to manufacture qualification.

Final **45 tool cases** pass: insert/delete/update and duplicate/missing/range changes; endpoint mismatch despite five writes; integer/real distinctions and rowid-only changes; selected Python content and split/merged aliases; supplied owner/version/fence/epoch/cancel/revocation/deadline changes; actual SQLAlchemy transaction replacement; rebound driver/shadow state; unknown schema/trigger/view/temp/attached/function configurations; unsupported SQL, rowcount, extra/multiple writes and bounds.

Unit flags test supplied boundary data, not new application grant-revocation or owner-cancel acceptance. Unobservable raw-driver transaction boundaries remain unproven. Original failures are preserved by private XML/log hashes: native SQLite extension functions also have `builtin=0`; WAL serialization did not directly reopen through deserialize; an overwritten-write fixture incorrectly expected a final endpoint difference. Fixes retained complete comparisons, untouched original connection configuration and production guards. Overlapping runs are not summed.

## Six unclosed dependencies

| Gap | Why the SQL endpoint match is insufficient |
| --- | --- |
| Complete Python/file closure | Only selected raw/wire/meta/response data is captured, not every G1 input/alias or external byte. |
| Callback/UDF provenance | Inventory/output equality does not prove implementation purity or absence of external/intermediate effects. |
| SQL execution-environment qualification | Actual and clone environments are retained separately; semantic equivalence is unproven. |
| Raw-driver transaction boundaries | SQLAlchemy identity checks cannot establish that unobserved raw COMMIT/BEGIN never happened. |
| Unordered query sequences | Logical rows cannot substitute for each original query's result contract. |
| Dynamic authorization | No grant, approval, owner, epoch, expiry or PASS is transferred; original read and tail checks remain. |

These are engineering gaps, not missing free-model permission. No runtime producer/consumer skip is connected and no new two-Cold real-clock test was run on an unqualified candidate. The implemented alternative is this collector/replay/full-data differential alongside original G1.

Next close actual input/query/effect/callback dependencies with complete differentials and refusals, then introduce fresh G1 Graph/Binding data for a complete Source/Generate family. Only afterwards run two real-clock large saves, immediate first reopen and actual locked cancellation. Never transfer old graph/seed/reader, mutable alias, authority or PASS as a substitute.

Application source, deadlines, atomicity and the original 30-second admission/first-DML versus 120-second settlement policy are unchanged. No fifth Windows CI, PC, main/Release/deployment, new fee/credential/security permission, training or real provider request occurred. Raw synthetic databases/model bodies remain private; public summaries and source are independently reviewed and secret-scanned.
