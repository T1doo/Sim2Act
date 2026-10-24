# Fresh lookup SQL structure: local candidate

Base: `36e1e3b689cdd2ff04b059f0763ad8b7b79a0f65`. This is one local engineering candidate for the existing Cold lineage/read path, not a new Mock window or production account source. The older settlement costs belong to their historical execution SHA; none are attributed to this helper by this experiment.

Product change is only `delivery_graph_apps.lookup`: share a fixed full-table SELECT tree for four exact strings, create a fresh four-value binding dictionary and execute a real query on every call. Non-exact strings, subclasses and `None` keep the old construction path. All seven columns and RowMapping return type remain. `pair()` still makes two separate original reads in original order. No row/digest/PASS cache, merged query, authorization/pin/clock removal, cross-write proof or changed transaction/lease/Run occurs. This follows the existing data-free query-template pattern in `db.py`.

## Correctness and source freeze

Final pytest: **3 PASS, 0 fail/skip, 0.09 seconds**, one existing Starlette/httpx deprecation warning. The earlier 3 PASS/0.08-second development run is retained separately and is not added to make six tests. The first quality check flagged five test closure-binding B023 warnings; binding loop values explicitly resolved them before the frozen comparison. Ruff on all three changed Python source files passed.

The tests execute real isolated in-memory SQLite queries: complete rows and SQL/bound-value equality; 15 scope/qualification input combinations; exact execution-tree selection; update/delete/reinsert/rollback freshness and independent prior snapshots; six real `pair()` success/error cases including seal deletion between its two queries. A legacy SQL-construction oracle is used; this is not a whole-platform or real Grant/Cold test. No external database/Store/Worker/model/HTTP is started.

`plan.json` pins the three code hashes and thresholds before timing. The benchmark ran exactly once after limited readonly source review, without tuning or retry. All three hashes matched before and after execution and remain the candidate source hashes. Pure benchmark setup imports the test definitions but does not execute pytest again.

## One bounded local comparison

Original interpreter: CPython3.12.14, SQLAlchemy2.0.48. One eight-row memory SQLite table, serialized snapshot8261 bytes, twelve alternating-order rounds, 200 fresh reads per arm per round. Total4865 SELECT = setup1 + warmup64 + measured4800. Qualification, fresh parameters, complete JSON row decoding and the same checksum/select-counter overhead are included. No profiler or replacement function identity is used in product code.

Predeclared qualification: at least9/12 wall wins, paired median candidate/legacy wall and thread-CPU ratios both at most0.95; 30-second work bound, outer35-second owned-process timeout. Actual outcome: **QUALIFIED_LOCAL_CANDIDATE**, wall ratio0.26504452243388665, CPU ratio0.2650999053561567, 12/12 wall wins. Measured legacy totals169.361263ms wall/169.359787ms CPU; candidate44.839442ms wall/44.842881ms CPU. Ratios are paired medians, not ratios of these totals. Script interval to engine disposal0.344499284s; command wall0.548645816s, exit0. `comparison.json` and `comparison.log` are the original one-run records.

Final readonly reviewer `/root/confirmed_model_probe_review` recomputed counts, alternating order, checksums and median ratios from those originals, found the frozen hashes/three tests consistent and gave a **local candidate ACK**. It did not rerun tests or benchmark. This supports only this small SQLite lookup workload. It does not identify the largest current Cold cost, assign historical28230 SELECTs to lookup, predict whole-transaction savings or prove G0 passes.

No full Cold, new Mock, real model, browser, network/authentication, push/CI, installation or permission change. Engine/connection cleanup completed normally; the finite owned test/benchmark commands exited. Existing three unpushed commits remain preserved. PG runtime, full Cold semantics/performance and all original deadline gates remain unverified by this slice; current account producer remains independently missing.
