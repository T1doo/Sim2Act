# CSV DAG cross-Release historical JSON downloads — 2026-10-17

Scope follows `docs/平台产品设计.md` F2-T05 and existing F2-T06/T08 boundaries, and `docs/F2/CsvDagVersionSwitch20261011.md`. This slice uses the existing compatible adoption UI and original per-use executor/approval/Grant contracts. It does not add backend version semantics or another family/matrix.

Frozen source: `a865971e73e4ce20cffec61e3bce5b71f5b0504c`, based on remote-confirmed `9acabaca0ccb3306122fb1d47af26b14e8f81533`. Only product change is one line in `csv-dag.js`: after complete current instance/Release validation, display that exact Release in the existing selector. No `change` event is fired, and the selected instance and durable intent remain intact.

## Actual red baseline

`f1c69f557b9f71bf3bf08b0791efe0fff17904e3` introduced only the two isolated test files; product `src` bytes matched 9ac. One actual ASGI/JSDOM execution failed (RC1, JUnit 14.657s) because the initial visible Release selector did not equal the opened instance Release. This happened before any directory Run or adoption: 28 product GETs, zero product POSTs. The failed predicate was recorded; the actual selected DOM ID was not separately snapshotted. Do not invent it. Original red log, JUnit, database and result are retained unchanged under author-originals/baseline.

## Limited acceptance

The new single report-family node executes the real served page with authenticated ASGI APIs, synthetic SQLite and rejecting NoModel providers. Source helpers perform two actual original source Worker Runs; two separately cold Store/Worker executions create the directory results. The visible UI prepares, reads, explicitly confirms and commits the existing compatible version adoption. No direct DB update impersonates adoption.

It checks initial/adopted/cold visible Release IDs, revision1 old result, revision2 new result, immutable own Release/source/plan bindings, exactly four product POSTs (two Run, one prepare, one commit), five actual Blob payloads, old pre/post-adoption byte identity, one held old-result response invalidated by a later new-result choice, and URL/key cleanup. All48 tables are checked at ten read-only checkpoints. Prepare changes only internal_approvals; commit changes only internal_approvals/internal_instances. Principals and Grants stay unchanged during adoption/execution.

Real existing resource.read revocation then produces old Run403 via the visible download control and clears protected results. A detached new-result callback sends no request. The new Run endpoint separately returns actual403 via a direct existing API probe after the view is cleared; that probe is explicitly not a second visible click. No new Blob is produced. The fixture revocation is recorded separately from the four product POSTs.

Author: one node PASS, RC0, JUnit122.495s,36 checks,137 product requests,2 page boots,2 source +2 cold Workers,5 actual JSON files, one held gate reached in2468ms (12s actual-reply/no-progress limit and60s total unchanged). Independent: one node PASS, RC0, JUnit99.221s,36 checks,137 API requests and5 actual Blob files; its one held history gate reached2942ms. The same node adds zero unique test nodes. Exact command, report, checksums and source-before/after are preserved with all independent originals.

## Evidence and limits

The two originals manifests map each new original path/size/SHA256 to its archived representation. Gzip uses deterministic mtime0. SHA256SUMS covers all repository evidence files except itself. Final verification checks stored bytes, decoded original bytes and these slice originals only; earlier historical evidence batches are not revalidated. Source-before/after hashes and full command/terminal/JUnit logs preserve execution provenance.

PG, native browser, Windows, real models, semantic/business scenarios, remote CI/Actions, deployment, other DAG families, rollback/fault matrices and the separate next project-creation fix are NOT_RUN here. The old full-disk independent-report gap is not recovered by these new reports. Historical classifications stay unchanged: 8f7 static defect;212 optional-script compatibility defect;880 late-error scheduling UNKNOWN; original84 legacy scenario not rerun, although the identical bounded wait helper is reused for this new single history gate.
