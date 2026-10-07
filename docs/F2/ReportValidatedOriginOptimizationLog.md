# Report validated-origin reuse: bounded local result

Plan e265bf9 preceded implementation. Baseline33ee0f1; root documentation e9629d landed before implementation/test freeze, with no product delta. Product/test source frozen at1258e5bfa5a423c251ab133fb0775ad7a1bba544 in /workspace/Sim2Act-bounded-product-candidate. Only conditional_apps.py/report_manifest_apps.py and a dedicated negative test changed. Protocol core and conditional_runs bytes match baseline. Public named load/anchors signatures/returns and cold history per-Run validation remain unchanged.

The private companion carries the named validation's existing plan/job. Report still freshly validates extraction and source, requires SUCCEEDED, exact compiled-plan fingerprint/expected fingerprint, and performs fresh target authorization/hash checks. Cached promotion removes the second named read while independently validating its canonical marker/candidate/proof/caps. No client bundle, cross-request cache, provider activation or permission changes.

Final exact-source SQLite command:

`PYTHONPATH=src:tests /tmp/sim2act-delivery-adapter-venv/bin/python -m pytest -q tests/test_conditional_apps.py tests/test_report_manifest_apps.py tests/test_conditional_run_bindings.py tests/test_report_validated_origin.py /tmp/report-origin-1258e5b/test_profile.py`

Natural session20157 exit0:111 PASS,2 PostgreSQL-role SKIP,129.86s. New23 tests cover same-transaction post-companion source/extraction/seal/Grant/target mutation on new/cached/read; next-HTTP cached mutations; wrong named identity scope. Rejections preserve complete database fingerprints and existing receipts, with zero new provider calls. Existing related negative/real cold chains run unchanged. `/workspace/sim2act-pb-venv/bin/mypy src`:41 files PASS; Ruff src and four related test modules PASS.

| Actual SQLite operation | Before SELECT | After SELECT | Before extraction/source verification | After |
| --- | ---: | ---: | --- | --- |
| named load |228|228|2/6|2/6|
| first HTTP promotion |414|343|4/11|3/9|
| Report load |416|345|4/11|3/9|
| HTTP inspect, empty history |418|347|4/11|3/9|
| same-key cached HTTP promotion |646|347|6/17|3/9|

Report load SELECT decreases71 (17.1%); cached promotion decreases299 (46.3%). Source construction performs3 fixed OFFLINE MockTransport calls; profiling adds0 model/network requests. Read and cached operations preserve all-table and authority fingerprints; first promotion retains the original2 INSERTs and unchanged authority. Timings/counters are SQLite diagnostic samples and do not prove PG timeout resolution.

Development failures remain archived: first refactor NameError was corrected; negative test initially omitted existing VERIFICATION_FAILED400/GRANT_REVOKED codes, then used public metadata instead of internal parent in a mutation helper. These harness errors were fixed without removing rejection/zero-write assertions. Actual development logs and truthful initial NameError note are in evidence/development. The earlier full PG1278 PASS4 SKIP1 FAIL1407.99s and coalesce focused Report49 90s timeout after39 checks remain failures; see ReportUIPollCoalesceFocusedLog.md and its original evidence. This local result does not supersede them.

Evidence: docs/evidence/report-origin-validation-20261007/after-1258e5b contains actual result/counts, profile driver, focused/static logs, source/protocol hashes and development failures. No PG/full/native/CI/push was run. All owned TestClient fixtures were closed and test sessions ended. Pending independent review and separately authorized PG/browser verification remain acceptance boundaries.

The final executed command did not request JUnit output: JUnit NOT_RECORDED. A subsequent collection-only check (0.24s, no test execution) records113 unique nodes in unique-case-collection.json/collection.log. Two exact SQLite skips: tests/test_report_manifest_apps.py::test_existing_pg_crud_role_manifest_preview_without_ddl_or_authority_expansion, tests/test_conditional_run_bindings.py::test_application_role_actual_bound_chain_uses_existing_crud_only. Both have runtime_role fixture reason: Application-role subprocess regression requires explicit isolated PostgreSQL. Whole-table and authority before/after hashes were actually compared/asserted during execution, but digest values were not persisted (NOT_RECORDED); stored booleans report those comparisons. No reconstructed before hash is presented as actual evidence.

Independent exact-source review:19 unique actual SQLite/HTTP scenarios LIMITED_PASS, covering same-transaction source/extraction/anchor/type/target/expiry/scope mutation, next-request cached source Grant revocation/content/check-type/target expiry/wrong bearer, and two real queued cold Runs with cross-Run history replay rejection. All rejected operations asserted the complete database unchanged. The final five cases also retain actual before/after full-database and per-table fingerprints; the first14 retain Boolean assertions only, raw digests NOT_RECORDED. Two isolated fixtures used6 fixed Mock setup calls total,0 LIVE; cold enqueue used0 provider calls. Completed cold execution, independent timing and PG remain untested here. Evidence: independent-1258/final-1258-review.json (SHA256 7b5214ec7e510cbb4a968d178881b4ff6cae87a1df84700df73a7542ddfa7e78).
