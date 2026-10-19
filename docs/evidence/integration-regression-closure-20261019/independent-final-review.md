# Final bounded v11 runtime supplement

This adds the completed targeted Cold result to the sealed v11 source and two-test runtime reviews. All previous seals remain byte-identical. The reviewer read source, Git blobs and raw receipts/JSON/XML/observer logs only; no tests, product imports, DB, models, network or signals were run. The author-produced final audit was independently checked against the raw receipts and immutable input identities, not executed by this reviewer.

## Result by actual commit

| Commit | Executed check | Result | Outer wall time |
| --- | --- | --- | --- |
| aae3abd9c5c422b199f82e66570b4bd71be49621 | Actual controller seven-slot V2, MockTransport and synthetic clock | 1 PASS | 650.455743902 s |
| aae3abd9c5c422b199f82e66570b4bd71be49621 | Other selected 21 nodes | 20 PASS / 1 FAIL, ordinary Source | 273.960579931 s |
| 08a966cf5413295d49cdb942287e83d9f72ac6c7 | Exact ordinary Source failure after scoped proof reuse repair | 1 PASS | 111.796384303 s |
| 08a966cf5413295d49cdb942287e83d9f72ac6c7 | New complete-proof / copy / write invalidation / expiry guard | 1 PASS | 18.896901002 s |
| 08a966cf5413295d49cdb942287e83d9f72ac6c7 | Existing P-A Cold new Store/material/Goal case | 1 PASS | 171.218725350 s |
| 08a966cf5413295d49cdb942287e83d9f72ac6c7 | Full mypy src | 113 source files PASS | 121.660391348 s |

The new Cold case has completed JUnit 1 PASS (166.063 s testcase / 166.329 s suite), process exit 0, no failure/error/skip, 900-second outer bound not reached, and real network transport forbidden. Its 685 before/after input hashes exactly match the prior v11 Source and new guard executions. Independent Git blob verification again matched 679 committed blobs to 08a, plus six separately archived generated egg-info files; all 14 candidate files match. Local HEAD remained 08a with empty porcelain status. The author push/remote receipts are archived; this reviewer made no network call.

## What the Cold result demonstrates

The unchanged existing case performs actual finite mock generation, saves the generated P-A application, explicitly binds a different current Goal and new COLD material, creates a fresh Store, recovers the binding, executes the ordinary unbound Worker and asserts SUCCEEDED. It checks the resulting checklist references the new resource and exact COLD content, that two model requests were made, and that the original SOURCE bytes appear in neither request. This exercises the newly enabled ordinary read token through new-input model/local work and terminal saved-result readback, with the original lease/deadline/guards/assertions intact.

This case is P-A / GoalGeneration-derived Cold, not P-B task-source replay: ready() generates and saves an application rather than completing a Source Run and extracting spec_task. The earlier v11-runtime recommendation used “Source lineage” too broadly; this supplement explicitly narrows that wording. No additional P-B lineage runtime qualification is claimed. The unchanged P-B proof implementation already has the original bounded token; its broader lineage scenarios are outside this targeted runtime conclusion.

## Scope decision and remaining limits

No definite P1/P2 was found in the reviewed source delta or completed evidence. The exact ordinary Source failure and the one additional affected P-A Cold hookup now have actual passing checks at 08a. The new guard proves that scoped proof reuse still requires a full first proof, isolates caller mutation, rejects explicit-null binding eligibility, invalidates after a real write and detects Grant expiry without a write. No further covered recovery matrix or 650-second V2 rerun is required merely to unify hashes: the old bound versions short-circuit before the new ordinary helper, all non-None binding behavior is preserved, and the MD/heartbeat/owner/association/renewal modules remain byte-identical. Their executed runtime evidence stays attributed to aae3; source invariance is separate evidence.

The final author FINAL-AUDIT.json correctly preserves the old v10 21 PASS / 1 FAIL and reports exactly three new v11 passing nodes. AUDIT-BEFORE-COLD.json exactly equals the previously archived two-node audit. There is no complete-suite all-PASS claim on one SHA. Historical native crash, interrupts, failed attempts, the older full-disk missing report and the v10 Source failure remain preserved; native cause remains unknown. Whole Ruff still FAILs with 110 inherited diagnostics versus 117 baseline, no additions. Remote CI remains unverified after the recorded API access denial.

V2 was a synthetic-clock MockTransport controller test with explicit synthetic qualification stand-in and zero real model calls. Its 650-second real wall time is not a real 300-second model/semantic qualification. No Windows, PG, real model, fees/paid entitlement, live admission, real semantic acceptance or human acceptance is certified. The saved natural checklist still requires owner acceptance and semantic review.

This limited source/runtime review is complete with no further action requested for the reviewed affected paths. It is not an authorization to deploy or a product-wide acceptance certificate.
