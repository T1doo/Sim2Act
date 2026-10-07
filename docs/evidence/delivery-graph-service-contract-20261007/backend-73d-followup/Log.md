# Frozen service follow-up

Ordinary merge of `3f07b751a45cab522e754ab3f31b22034dafc26c`; backend/db/core bytes match frozen `73d80f0eecb39272f0354bfc17d235614f81796e`. Only the owned two adapter/test files and new evidence are changed after merge. Original 17 FAIL /1 PASS files remain untouched.

Final exact focused command: `PYTHONPATH=src:tests /workspace/sim2act-pb-venv/bin/python -m pytest -q tests/test_delivery_graph_service_contract.py --tb=short`. **19 PASS, zero FAIL/SKIP, 13.20s**. Ruff for both added files PASS. All 17 frozen contract obligations now actually execute; no xfail, skipped case or MemoryDriver.

Native receipt fields are mapped rather than reconstructed. The adapter independently checks the actual server native seal and public outer seal, then exposes only server-provided core, expansion and outer_fingerprint. Cache transport metadata does not change the stored receipt. HTTP201→200, validation422→400 and revoked-permission error normalization remain explicit.

APP uses real CSV sources. Complete PROJECT uses the parent's explicitly authorized existing initial declarative bounded-agent service constructor, repository OFFLINE_REPLAY sample, and its already authorized CSV anchor peer. Both current graph anchors come from real HTTP derive. This is an initial declaration, not a claimed successful source Run, model generation or semantic P-B result. No new product Grant/permission semantics are introduced.

Locks use internal owner-validated `set_lock(LockInput)` plus actual HTTP derive. Membership mutation uses a spare normal HTTP-created/derived CSV app, authorized before baseline and quarantined by test-only membership parking. Restoring its original project and validating via HTTP derive changes membership only, with unchanged authority fingerprint. No accepted context, graph or receipt is forged.

First updated backend still had 7 FAIL because the real Report fixture preserves an unsupported source-parent application and therefore BLOCKED_PARTIAL; these are retained. The first complete agent fixture had one harness failure because creating another CSV app during add_related added normal API Grants, correctly tripping the baseline assertion. Preprovisioning before baseline fixes the fixture without removing the assertion. Final Report direct test independently retains actual partial server output and verifies the adapter rejects normalizing it as complete.

Pure-core source_versions bool/float remains a separate parent BLOCK, not closed by trusted service fixture results. No product edit, PG/full/CI/browser, real provider request, publication or platform acceptance is implied.
