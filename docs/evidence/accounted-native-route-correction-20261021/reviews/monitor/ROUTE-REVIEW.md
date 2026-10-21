# Historical G0 and current candidate: independent static route review

Decision: **ROUTE_CONFIRMED / CANDIDATE_NOT_CONNECTED / NO_PRODUCTION_OR_G0_FIX_CLAIM**.

Reviewed checkout HEAD: `824dfed3e9294727fd05aa88140d66b58b60ba3b`; `git status --short` was empty. Historical third-run code HEAD: `cdda2b2ed6bce1393b90a500c0377294e4d82e34`.

This reviewer read source, historical Git source, documentation and hashes only. No product code, tests, DB, Worker, model, Mock, G0, prepare/commit, profiling, process signals or new fixture/stub/window was executed. No repository file was changed. Only these `/tmp` review artifacts were written. This is a route review, not a new verification of every archived third-run artifact or a new performance measurement.

## Historical route and its exact synthetic authority boundary

`g0_bounded.child` calls `g0_prefix.run_prefix`. That function calls the existing `configured(..., prepare_case=prepare_pb)`. `prepare_pb` creates a synthetic PB contract/account, original approval and ordered extraction recipe; its account name explicitly says `synthetic-pb-production-shape`.

The historical design `docs/evidence/g0-fresh-mock-prefix-design-20261020/README.md` explicitly identifies three allowed fixture gate substitutions, all present in `configured`:

1. Replace `spec_production.environment` with an assertion limited to the isolated `test_only` SQLite Store/settings and `transport is None`. The prefix extends that assertion to its second cold Store on the same isolated database.
2. Replace `production_evidence.resolve_account` with a synthetic `SourceVerificationResult` producer bound to the exact user/approval/requirements. It is not a reviewed real account authority source.
3. Replace `production_trial_admission._qualified` with a test no-op. It is not a software qualification pass.

Separately, the fixture redirects `httpx.AsyncClient` to an exact `MockTransport`, records request/response bytes and uses the existing Worker factory; Worker/provider transport stays `None`. `fail_owned` is observed while the original function is still called. These transport/diagnostic hooks do not turn the three synthetic gate substitutions into real production evidence.

After Generate, Source, extraction, release, use review, enqueue and approval, `run_prefix` binds the exact cold Worker/run to `StopBoundary` and calls its original `worker.once()`. The original Cold settlement path enters:

`advance_model -> _cold_model_before -> _cold_graph_read(pre) -> _cold_first_binding -> _ColdTrialGraph(completed=...) -> first commit -> _prepare -> run context -> PB accounting -> Source resolver -> archive chain -> original finite/stop decision`.

The same enclosing Cold interval also contains the second original commit continuation if the first and intervening checks complete. `StopBoundary.wrap` invokes the captured original `_cold_model_before`; it does not replace `_prepare` or the semantic consumers. It converts an original DomainError into `G0Stop`, or stops after complete original context exit, before the following W5 writes. The third-run archive records the former: original deadline rejection, not a complete acceptance. No fourth window follows from this historical route.

The current `_cold_model_eligible` and `_cold_model_before` bodies were manually compared with the frozen third-run versions and retain this route. Git shows no changes from that historical SHA to the reviewed HEAD in `g0_prefix.py`, `configured`/`prepare_pb` source files, `production_evidence.py` or `spec_production.py`.

## Current candidate is a different, unselected branch within that route

`_ColdTrialGraph.__init__` now accepts `_accounted_candidate=None` and checks any explicit candidate is the exact private type, belongs to the same guard, is pre-phase/unselected and is not combined with `_accounted_prewrite`.

The native branch is present at the original `_prepare` producer positions: actual Source producer, candidate staging, original recipe check, actual backend-version read/check, actual Generate producer, candidate staging, then joint `choose(..., upstreams=(source_job, generation))`. Only an OWNED result installs the owned families. This establishes the intended code seam, not an executed whole-path result.

The actual `_cold_model_before` still constructs `_ColdTrialGraph(worker, c, guard, completed=completed)` without either private argument. No source caller invokes `_native_candidate`; its only external invocation found is in the native test harness. Thus the currently installed ordinary route keeps the default legacy behavior, and replaying the historical entry unchanged would not select the candidate.

The new native tests expressly say they never call `_prepare` or `trial.commit`. They exercise real SQLite lower producers/consumers and actual base/check methods against synthetic preloaded facts. The test's `object.__new__(_ColdTrialGraph)` plus assigned fields does not run the actual constructor, platform/trial preparation, original complete `_prepare`, or both commit continuations. Its loop over two lower helper rounds is not the two complete native commit boundaries. `test_missing_original_entitlement_still_blocks_pb_accounting` retains the account-source refusal for both routes. This review read these tests; it did not rerun them.

## Real admission and eligibility remain distinct

`production_evidence.resolve_account` first validates/projects requirements, then always raises `LIVE_BLOCKED / No reviewed production account evidence source is supported`; it has no authority override parameter or ALLOW return. Malformed requirements can fail earlier. A caller-supplied candidate diagnostic is not an authority source.

`Worker` validation reaches `_binding -> spec_production.environment` and `_account -> _journal_source -> spec_production.source`. `source` performs original approval, calls that fixed resolver and only then the source/software checks. `_graph_pb_accounting` also calls the same fresh `_journal_source`. Therefore a normal unpatched path can fail at the environment gate before the resolver; merely bypassing that environment gate still reaches the resolver refusal. Neither candidate representation nor arena qualification supplies account entitlement, software approval or dispatch authority.

The production environment requires `not store.test_only` and `not store.sqlite`. In contrast both the existing Cold selector and `_NativeCandidate` explicitly require `store.test_only and store.sqlite` (the Cold selector also requires the exact production-shape binding/PB contract, original resource identity and active transaction). This is an existing experimental/test-only optimization route with production-shaped logic, not eligibility for real PG/live production. Default account/software blocks and this domain distinction preclude a claim that the candidate fixes real production or has solved G0.

## Minimal reuse seam and remaining proof

The narrow future seam, if separately authorized, is inside the existing pre `_cold_graph_read` scope after successful `_cold_first_binding` and at the actual `_ColdTrialGraph` construction: explicitly create a same-guard `_native_candidate` with explicit bounds/limits, pass it as `_accounted_candidate`, and let the original constructor/first commit/whole `_prepare`/two continuations and final graph scope run unchanged. Candidate closure must preserve its OWNED resource lifetime through the original graph's final check/invalidation. The post/audit `_ColdTrialGraph` construction, default None route, original account/software gates, transactions, deadlines and W5 stop boundary stay outside that choice.

This is a static integration point, not an implementation, installation ACK, new configuration default, new authority stub or execution grant. A same-route acceptance claim still lacks the actual complete constructor-to-prepare-to-both-commits integration under that explicit selection, realistic eligibility/budget outcome and unmodified finite/stop checks. A G0 improvement additionally lacks a new authorized comparable measurement. Reusing only the lower helper fixture cannot close those gaps. No source change or new window is requested by this report.

Exact reviewed file hashes are recorded in `ROUTE-REVIEW.json`.
