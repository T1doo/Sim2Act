# Explicit Mock candidate wiring: independent static code review

Decision: **ACK_DEFAULT_OFF_WIRING_ONLY; SELECTED_EXECUTION_CLASSIFICATION_GAP**.

This report binds the four-file freeze in `/tmp/sim2act-explicit-mock-wiring-20261021/frozen-hashes.json`, on base HEAD `a0fbd16e7d917ca00ab55aed81519d454bb35998`. The reviewer read the actual four files, diff, source dependencies and writer-produced first-test log/XML. No code, tests, DB, Worker, Mock/model, G0, prepare/commit, profiling or signals were executed by this reviewer. No repository files were changed. Only `/tmp` review files were written.

## Confirmed narrow wiring

- `g0_prefix._mock_accounted_context` returns the original function for None; otherwise it checks the exact private `_NativeConfig` and creates a `partial` of the captured original `_cold_model_before`, supplying only the private keyword. Constructing the partial does not execute it. `run_prefix` defaults to None and does not synthesize bounds/limits.
- `StopBoundary.wrap` ignores the selected context for unbound and non-target Workers. For its exact bound Worker it retains the original one-entry/run/current-call/version/attempt checks, exact six/eight/two counter closure, g0-enter event and SQLite arm before invoking the selected context. All original stop behavior remains around that interval.
- `_cold_model_before` explicitly refuses wrong config, non-test-only/non-SQLite Store, and wrong original PB Cold route. None retains the original eligible/ineligible selection. Both the selector documentation and constructor explicitly describe test-only SQLite, not genuine production qualification.
- Candidate entry is inside the same original pre `_cold_graph_read`, after original `_cold_first_binding`; the actual `_ColdTrialGraph` receives the same-guard candidate. There is no replacement of `_prepare` or the real semantic producers/consumers in the implementation.
- The original complete second-authority-record identity and finite-deadline checks remain. Candidate context exit occurs before the original graph's final check/invalidation, and the original final stop/clock read remains after graph closure. ExitStack plus the original graph `finally` preserves closure on failure. Native OWNED lifetime still belongs to the graph scope rather than prematurely to the lexical helper.
- The actual default `advance_model` call does not pass the option, and the post/audit constructor still passes only `audit_seed`. The launcher calls `run_prefix` without keywords. Git diff confirms launcher, configured/prepare_pb fixture files, production account resolver/controller and software-admission source unchanged. The three historical synthetic fixture gate replacements are neither expanded nor concealed.
- All `LIMITS`, writer limits, exact Mock counters, timing supervision and disk monitor code are unchanged. This patch creates no grant, config CLI, network authority or actual execution window.

## One concrete gap before any selected diagnostic execution

`StopBoundary.wrap` still catches **every** DomainError from the selected context and labels it `G0_ORIGINAL_REJECTION_NO_W5`. The newly selected candidate can itself raise `_Capacity`/`_Unsupported` (DomainError subclasses), `_Rejected`, or native eligibility/protocol `require` failures. Such errors are not evidence that an original business deadline/authorization guard rejected. The target selection is correctly bounded, but exception provenance is no longer necessarily original.

Therefore this freeze is acceptable only as default-off wiring with no selected execution. Before any future reviewed grant uses it, classification must distinguish or conservatively leave unproven selected-path failures as UNKNOWN/selected-context rejection. Merely retaining the original exception as cause does not make it an original guard rejection. A local regression should cover a candidate-specific rejection as well as an ordinary body rejection, without running G0. No new execution window is needed to close this diagnostic gap.

## Exact tests and resource limits

The frozen test file defines 11 parametrized cases. Its stand-ins are disclosed: local tests exercise original CGR/native context wiring with first-binding and TrialGraph substitutes; a record-shaped second-boundary stand-in tests exit/clock order, not a completed authority proof. They never run full prefix, actual `_prepare`/commit, Mock/G0, Worker/model/transport construction. The first writer log and JUnit contain **9 passed**, one existing warning, 1.75 seconds; they precede the added two exit-order cases. This reviewer did not run any case and does not claim final 11 passed.

The prior static resource conclusion remains unchanged: exactly 6 actual exchanges/8 method entries for this fixed fresh prefix, with 2 Source delegates; no extra exchange for the second commit. Six reservations span at least 300 seconds because of the original one-per-60-second journal policy. Preserve TTL1800/per-Run300/lease30 and 480-prefix/120-G0/600-work+10-cleanup, plus 64 MiB **sampled** directory budget. Neither existing huge fixture allowances nor this private keyword establish a legitimate full-input native allowance, whole-process RSS ceiling, performance improvement or successful G0 deadline. No such numeric budget or promise is added by this patch.

The resolver remains fail-closed and no real account/software/production source is installed. Default-off static ACK does not approve installation, remove any guard, or authorize a fourth Mock window. A later complete prepare/commit/G0 claim still requires separately authorized actual evidence with explicit finite config and an honest OWNED/LEGACY selection record.

## Frozen SHA256

| File | SHA256 |
| --- | --- |
| src/sim2act/natural_spec_runtime.py | eb6010151979b5c6e085559f45e4a4fb430db3790393d44162a8e3e4d924c459 |
| scripts/diagnostics/g0_guard.py | 07d001a11c3d3300c2873bacfaaf40ec67c4ae3194801371dc3d6e34129651ab |
| scripts/diagnostics/g0_prefix.py | c67132016a0c782d148aeae8ca6ab2c164ba78182d984d46dde99682e116596b |
| tests/test_cold_accounted_mock_wiring.py | fd1071ba378104a6083a912492f424f2fddd1ec7adc64b69e418051cc8411a38 |
