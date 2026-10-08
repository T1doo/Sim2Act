# Owned fresh-schema optimization evidence

Frozen source693fd3ca6f01e8d0930b0fbd3c5a538f424ea907. [Result log](../../F2/FreshSchemaInitializationLog.md) and [minimal remaining checklist](../../F2/DeliveryRemainingChecklist.md).

Actual finalPG38PASS0SKIP, SQLite68PASS9SKIP, database/lifecycle39PASS1SKIP are separate runs; firstPG37PASS1FAIL remains preserved. test-summary.json lists exact skips and durations. Raw log/XML wrappers reproduce original UTF-8 bytes using `text.encode()` and record SHA256; exported-original-hashes binds originals. No DSN/password or database export is saved. controller.py documents owned PG startup, actual tests, alternating benchmark, catalog census and container removal.

benchmark/measurement-summary retain six local initialization groups, probes164→0 per four schemas with unchanged164DDL. Linux sample medians369ms→302ms cannot establish Windows/whole-suite savings. source-git-closure binds279 current frozen execution files; before/after runtime snapshots were NOT_RECORDED. Final owned PG schemas/roles/public tables0 and container removed; first attempt recorded container removal only. Own local fixture directories were removed after verified export.

No new native/CI/LIVE/provider;900/240/150 remain unchanged NO_GO. Win11/provider/owner/completeP-B acceptance remains open.
