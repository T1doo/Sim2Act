# Independent limited review — PROJECT deterministic revalidation

LIMITED_PASS for exact product freeze `429a62a418748822d51d9e930ec05f8b560c5ef2`. Baseline `5fedb359eff076798782b99a5fd5748d76da5148`. This review uses independent tests and does not adopt author results.

## Actual independent final results

- SQLite/API: **35 passed, 0 failed, 0 errors, 0 skipped**, 160.43s.
- Private loopback HTTP with actual product page/scripts in JSDOM: **2 passed**, 47.21s; GET422 recovery **11 checks**, lost/late recovery **19 checks**, total **30**. Each scenario loaded 13 web files whose SHA-256 matched the frozen source. No native browser claim.
- All **68 tracked product source files** matched Git blob bytes before and after both runs. Only project_revalidation.py input guard and project-revalidation.js POST-stage gate differ from eafea; other66 files unchanged.
- Independently archived old5fed **66 source files** all match baseline. Actual old ASGI/TestClient options, POST confirmation, and history routes are all404, no writes; 1 negative test passed. Old API SHA-256 `7223c25689b1590f008f8f32d094a6c11c39576272207a521b17797aa2af0bdf`. This is an old-route sensitivity test, not an old-database upgrade test.

Original CSV remains amount-only: exact numeric total4/count2 (returned decimal text4.00). Actual Report rules are recomputed from current source/facts, and a schema-valid archive with a deliberately wrong decision records FAIL. Faulty registered CSV count records FAIL; extreme precision1e-1001 records NOT_RUN. Every current CHECK has exact identity/revision/ref bookkeeping, and authorized underived canonical declarations have explicit NOT_RUN entries. Only scope_check+scope_check_seal insert two rows; every other table and existing plan/jobs/presentation remains byte-for-byte unchanged.

Strict extra/shape/selection/confirmation and exact Run version/fence/result gates reject without writing. Current owner/Grant/source byte/hash, semantically unchanged valid source rehash, unknown member family, member addition, peer lock ABA, plan seal, independent seal and jointly rehashed accepted receipts are rejected without writing. Cold independent Store/current readback and same-key recovery pass; changed same-key body rejects. Real page consent, exact choices, unknown original body/key, stale callback context/busy release, exact history recovery and malformed HTTP200 proof clearing pass.

## Blocks discovered and resolved

- cbdc: wildcard field-before validator on discriminator caused Pydantic import failure; `blocked-cbdc-collection.log/xml` and frozen module retained. Final root model-before guard imports and completes all35cases.
- eafea: four escaped Unicode inputs in discriminator/extra value/extra key/nested extra key reached the server and failed UTF8 error rendering; `unicode-eafea.log/xml` retained. All four final negative cases now safely reject and preserve all tables.
- eafea: actual POST201 then controlled GET422 deleted the original unknown intent; `ui-eafea-readback422.json/log` retained. Final actual page11checks preserve that original body/key and resolve accepted history without a new POST.

Earlier eafea31 unique backend cases and19 lost/late page checks belong to eafea. Initial independent harness failures (sum text4 vs4.00, HTTPX surrogate encoding before API, original fixture requiring exactly one CSV resource) were corrected only in the private harness; all raw logs retained. Final executed harness snapshots are `executed-final-429-*`.

## Limits and evidence

No independent PG/CRUD-role/two-connection race/upgrade/native or overall acceptance signature. PROJECT remains PENDING/BLOCKED_PARTIAL, dependency_completeness BLOCKED_UNKNOWN, explanation NOT_CHECKED, semantic UNKNOWN, owner PENDING, overall NOT_ACCEPTED and formal publication disabled. LIVE0; no real model requests or business writes from scope checks. PG resources-history/full timeout OPEN, damaged HTTP200 hint limitation, Windows900/Edge240/Node150 unaccepted remain unchanged.

Final raw files: `backend-final-429.log/xml`, `ui-final-429.log/xml`, `ui-final-429-readback422.json/log`, `ui-final-429-lost-and-late.json/log`, `source-final-before.json`, `source-final-after.json`. Baseline: `old-negative.log/xml`, `source-old-5fed.json`, `test_old_negative.py`. All live in `/tmp/sim2act-project-revalidation-independent-20261009`; FINAL_REVIEW.json contains precise scope and SHA-256 artifact manifest. Private DB case directories are preserved for forensic review but are not required for the compact archive.

No product, author test, Git ref, author process or PostgreSQL changes by this reviewer. Current shared worktree changes are parent-owned Plan documentation and evidence, recorded in the source manifest. No reviewer blockers remain within this limited scope.
