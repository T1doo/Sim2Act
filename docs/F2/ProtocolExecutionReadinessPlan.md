# Protocol execution readiness, 2026-10-06

Baseline: `3cbd112be29549009f330b0235f3a9288b26e398`. This slice is local engineering only: no LIVE, approval request, push or CI.

## Scope and gates

1. Independently reconcile the 14-request proposal with the actual shared DB pool and per-scope provider sidecars. Check the disabled real-provider boundary, complete wire limits (1024 output tokens, 8000 characters, 10000 UTF-8 bytes), public data provenance and independent gold exclusion. Any missing enforceable policy remains an explicit execution blocker, rather than an implied approval.
2. Reuse the project task/result entry for protocol source/extract/cold inspection and state-only recovery. Keep technical completion, synthetic checker review and pending owner semantic acceptance distinct. No automatic review or continuation, no client gold/candidate injection, no new configuration console or permission grant.
3. Exercise both synthetic families through authenticated HTTP, durable worker, independent registered review, extraction and fresh-material cold execution using only MockTransport. Share the existing 14-slot DB pool. Demonstrate failed review stops extraction, unknown recovery never resends, and gold stays outside provider inputs.
4. Run focused regression and real HTTP-backed DOM checks, preserve failures and limitations, independently review changes, then make a local commit only.

## Acceptance

- Default production configuration remains unable to send protocol model requests. No test silently reads credentials or uses network transports.
- Public UI shows frozen source/plan fingerprints, versions and current recovery disposition; stale/cross-project responses cannot change the current selection. Lost recovery replies reuse the exact request key and version/fence.
- No button equates a mock checker result with owner acceptance or publishes an application.
- Zero-network evidence records actual Attempts, Operations and pool consumption across both families, complete request geometry and failure stops. Independent evaluation assets are used only for mock responses and separate checker review.
- Budget/data prerequisites are described from final source, including any unimplemented activation or approval gate. Historical failed CI/DOM results and untested native protocol UI are retained.

## Stage log

- Planning: existing protocol HTTP/worker supports offline execution only; source/cold await explicit review, recovery is metadata-only. Four-package manifest and six-stage proposal predate the shared DB pool and require reconciliation. Existing workspace is clean on the baseline branch.
- Independent review: DB enforces the cross-Run 14/64000 total; sidecars do not yet implement one six-stage/clock experiment. Exact outgoing-envelope and independently approved cold/source-feedback projections remain activation blockers. No current LIVE bypass found.
- Implementation: immutable offline controller handoff and exact public cold-template oracle; stage/phase matching; extraction max one request with separate frozen source-history allowance; owned public catalog and project canvas protocol controls. No new tables, API DDL, roles or grants. Synthetic checker approval remains distinct from owner semantic acceptance.
- Zero-network validation: both shapes execute authenticated source→separate registered review→extract→fresh cold→separate review; eight MockTransport calls share one DB pool, six VERIFIED Operations. Failure B stops before extraction after six calls. Frozen controller/budget/demo focused suite 59 PASS; stage/source/backend suite 171 PASS.
- Preserved failures: extraction allowance initially narrowed source history incorrectly (61/6), two new test-fixture assumptions failed (114/2), an oversized negative candidate failed before the intended oracle (whole suite 788/34/1). Corresponding corrections and final focused results are recorded without overwriting failure logs.
- Native UI boundary: installed Chromium aborts with a misconfigured SUID sandbox helper; no system-mode change or security-disabling flag. Record precise BLOCKED coverage, retain the actual FAIL. Actual local HTTP/jsdom exercises UI and asynchronous receipt guards; it cannot stand in for native browser acceptance.
- Continuity: after a reported executor disconnection, actual shell, branch/HEAD and persisted normal zero-network report were rechecked successfully; no task, CI or LIVE was restarted.

- Final role closure: genuine public goal/hash alone previously allowed a cold package as a source. Freeze, provider-stage and handoff now bind the registered source/cold material role. Four opposite-role freeze cases plus an authenticated HTTP cold-as-source case reject before any Job/Attempt; independent review retained the baseline reproduction. Existing all-contract positive fixture now supplies each registered role correctly.
- Final frozen validation: **799 PASS /35 SKIP /0 FAIL**, 834 collected, 365.72 seconds; 157 source/test/script files unchanged across the run. Role-focused **152 PASS**; Ruff PASS, mypy32 PASS, Node syntax and diff checks PASS. HTTP DOM21 checks PASS with valid owned-other-project Run and strict fixture-ID oracle; native remains BLOCKED_SANDBOX and PostgreSQL-only regressions remain skipped in this local run.
- Delivery: local commit only. Exact results and before/after SHA lists are in `docs/evidence/protocol-egress-readiness-20261006/final-validation.json`; no push, CI or LIVE request. LIVE activation/experiment-wide timing and envelope/approved projection prerequisites remain open.
