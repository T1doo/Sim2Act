# Same-transaction validated Report origin: read-only preparation

Source: 33ee0f14cc316d406489c5980e3c228b8d3f8784 in /workspace/Sim2Act-bounded-product-candidate. No product edits, PG, full suite, CI, real provider or network requests. This is a proposal, not an implemented performance fix.

## Actual bounded profile

Command: PYTHONPATH=src:tests /tmp/sim2act-delivery-adapter-venv/bin/python -m pytest -q /tmp/report-origin-profile-33ee/test_profile.py
Result: 1 PASS, 2.48s. Fixture performs real source/extraction through 3 fixed OFFLINE httpx.MockTransport requests, then actual named save and actual HTTP canonical promotion. Measurement calls add zero model requests. Whole-meta-table canonical fingerprints and authority rows are unchanged for all reads and cached promotion; new promotion legitimately inserts 2 rows, with authority unchanged. Instrumentation wraps every existing module alias and local-import entry for verified_pending/_plan/source_completion. Statement totals exclude before/after baseline reads. Table counters overlap and should not be summed.

| Measured operation | SELECT | Extraction verified_pending | Source verified_pending | source_completion | SQLite seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| named.load | 228 | 2 | 6 | 3 | 0.075 |
| first HTTP promotion | 414 (+2 INSERT) | 4 | 11 | 5 | 0.148 |
| same-key cached HTTP promotion | 646 | 6 | 17 | 8 | 0.267 |
| canonical Report load | 416 | 4 | 11 | 5 | 0.141 |
| scoped HTTP inspect, empty history | 418 | 4 | 11 | 5 | 0.177 |

The duplication is concrete: named.anchors validates extraction in _plan and explicitly again; each extraction validation invokes source_completion through _dependencies. named.anchors explicitly performs source_completion a third time. Each source_completion validates source both directly and through _current_check. Report then repeats _plan + extraction validation + source validation after full named.load. Cached promotion performs named.load before calling canonical load, whose own named.load repeats the entire parent validation.

## Proposed minimum implementation boundary

Do not modify protocol_jobs._plan, verified_pending, conditional_runs.source_completion, cold history validation or any public signature. Keep named public load returning the draft and public anchors returning the project with the original query/validation behavior.

Extract the existing anchors body into a private companion returning (project, plan, extraction_job), without deleting any validation. Capture the already fully verified extraction_job from the existing explicit verified_pending call. A private named._load_validated_origin, using the same closed parent/marker validation as load, returns the verified parent plus this private origin result. For Report only, it also calls verified_pending once for plan.source_run_id, exactly the direct source validation currently performed by Report, returning that source row for frozen-contract/goal/resource checks.

Report load and first promotion consume this result immediately in the same transaction, eliminating only their repeated _plan and extraction verification. Report must retain every canonical wrapper/marker/request/proof/origin/runtime/limits/goal check, target authorization/hash/format check, and source eligibility/check/result seals already executed by named validation. Cached promotion needs a private canonical validator that consumes the same lexically produced parent-origin result; its public load never accepts an optional caller bundle. Bind the trusted result to the exact c/user/pid/parent id/fingerprint/origin before use, and run the complete cached canonical marker/manifest/budget validation. No cross-request cache, caller supplied context, public bundle or universal memo mechanism.

Expected call structure, not yet measured: Report load/new promotion 2 extraction +7 source validations instead of4+11; cached promotion 2+7 instead of6+17 if its duplicate parent validation is removed by the private same-transaction path. Public named.load remains2+6. SQL/time reductions must be measured after implementation; this does not prove PG timeout resolution.

## Required negative oracles and risks

Current source completion, independent check seal, eligible status, result version/fence/attempt/operation seals, extraction namespace/plan fingerprint, current resource authorization/hash/format, frozen limits and frozen goal remain mandatory. Preserve project→Run→Grant lock ordering. Bundle creation and consumption must share the transaction without intervening domain mutations; no network/provider/tool work can be inserted between them. Every new HTTP request revalidates current authority and content. Revoke/source/hash/seal/version/budget attacks must still fail before writes; cached promotion must not become a marker-only shortcut. Source/target revocation and coherent proof/result tampering need fresh request negatives. No cold-history per-Run checks are removed.

The timing samples are SQLite diagnostics with Python instrumentation, not a PG benchmark. They identify repeated server work, not the exact cause of the retained PG failure. All earlier full/focused failures remain authoritative evidence; no timeout or check-count changes are proposed. No implementation or acceptance claim is made here.
