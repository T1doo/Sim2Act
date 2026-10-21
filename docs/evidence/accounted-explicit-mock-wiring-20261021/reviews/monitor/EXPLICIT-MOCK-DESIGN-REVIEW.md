# Explicit candidate seam: static exchange, time, resource and resolver review

Decision: **DESIGN_ACK_PRIVATE_DEFAULT_OFF_SEAM_ONLY**. The described same-guard seam is reviewable without changing the original admission or Mock allowances. This is not a frozen-code review, permission for a new execution window, or proof of complete prepare/commit integration or performance.

Scope: source/documentation/hash inspection only. No tests, DB, product, Worker, Mock/model, G0, prepare/commit, profile, signal, new stub or window was executed. No repository files were written. Current HEAD observed during this review: `a0fbd16e7d917ca00ab55aed81519d454bb35998`. This task reviews the proposed explicit hook; its later implementation needs a separate source review.

## Proposed seam

An internal keyword `_mock_accounted_config=None` on the original `_cold_model_before` can preserve the default route. Any non-None request must require the exact private `_NativeConfig`, the original eligibility predicate and test-only SQLite; an explicit ineligible request must reject rather than silently yield the default None branch. A same-guard candidate may be entered after successful original `_cold_first_binding`, passed to the actual constructor, and held through the original pre graph interval. All exception/exit paths must retain candidate closure and the original graph's final check/invalidation. Default and post/audit constructors must keep the old selection.

The existing `_prepare` already stages Source, performs the original recipe/backend checks, stages Generate and jointly chooses once. The hook must not add producers, replay receipt consumers as a substitute for original commits, suppress original authority/finite errors, or upgrade a capacity-induced LEGACY outcome into an OWNED result. If future execution claims candidate coverage, the recorded selected route must show OWNED; a valid LEGACY fallback would test the default route instead.

`test_only` SQLite and an exact private config are selection constraints, not a network sandbox or an account permit. Actual Mock-only execution still depends on the separately frozen original bounded harness: original three disclosed synthetic gate replacements, exact transport identity, real-network denials and stop boundary. The keyword name alone cannot establish that property. Adding this hook does not authorize any fourth window.

## Minimum exchanges for this exact fresh prefix

| Part | Actual exchanges | Mock method entries | Reason |
| --- | ---: | ---: | --- |
| Generate | 3 | 3 | Original ordered Generate path |
| Source | 2 | 4 | Two async exchanges plus two original synchronous `normal.handle_request` delegates |
| Cold first response | 1 | 1 | Response is received before the first G0 settlement interval |
| Both original G0 commit checks and W5-before stop | 0 additional | 0 additional | Both commits inspect the same received Cold attempt; the second continuation is not another model call |
| Total to G0 | **6** | **8** | Source delegate count **2** |

`MockBudget.enter` enforces the exact `generate,generate,generate,source,source,cold` exchange order and identities. `StopBoundary.wrap` calls `mocks.close()` before invoking the original G0 context; close requires exactly `(exchanges, methods, source_sync) == (6,8,2)` and then permanently disables further exchanges. Therefore unchanged prefix/handlers need no seventh exchange or ninth method entry even if both original commits complete. This is a sufficient *request-count ceiling for that static route*, not a guarantee the first commit, second commit or lease checks will succeed. Earlier original rejection may stop with fewer requests.

The original contract still allows stage maxima Generate3/Source2/Cold2, seven slots overall. That contract maximum is not a grant to execute Cold2: the diagnostic stops before W5 of Cold1 and must retain the six/eight ceiling. Changing Source's delegate implementation would require revisiting the method-entry accounting rather than silently relabeling it.

## Time contract and what can actually be derived

The policy's `reserve` and restored-ledger checks require adjacent reservation timestamps to differ by at least 60 seconds. The journal wait uses the same cursor's `last_reserved_at + 60`, checks stop/original Run deadline and waits in at most 0.25-second pieces with original heartbeat checks. Six fresh reservations consequently span at least **5 × 60 = 300 seconds**. This is a reservation-span lower bound; computation/verification can overlap those gaps. It is not an additional exact 300 seconds of sleep and it is not the original per-Run deadline.

Keep all original and outer limits separate:

| Limit | Meaning retained |
| --- | --- |
| TTL 1800 seconds | Original contract expiry |
| Run at most 300 seconds | Each original Run's own created-at/contract/frozen deadline, not the total multi-Run prefix allowance |
| Lease 30 seconds | Original live ownership deadline; no candidate allowance or outer timer renews it |
| One reservation per 60 seconds | Actual journal quota pacing, equivalent here to one RPM; do not describe it as 60 requests/minute |
| Prefix 480 seconds | From the parent's work start until valid first G0 event; includes preparation, waits and original checks |
| G0 120 seconds | Outer diagnostic ceiling from first G0 event, not permission to exceed a finite product deadline |
| Work 600 seconds | Parent deadline is `min(start+600, start+480 before G0 or g0_at+120 afterward)` |
| Cleanup 5+5 seconds | TERM then KILL, only for verified owned group; total outer work/cleanup ceiling 610 seconds |

The archived third run is a single historical observation: total work `342.467021839` seconds; G0 `30.985113144` seconds, ending `0.955520630` seconds past the original finite lease deadline. Milestone timestamps show the prefix progressing from fixture start `103.633697717` to G0 enter `413.424203630`; they do not separately measure journal waiting vs CPU or prove the new candidate finishes both commits. Retain 480/120/600+10; there is no evidence-based smaller guaranteed bound here. The original finite deadline still wins even when outer budget remains.

## Resource claim and missing numeric allowance

Retain the original sole fresh DB/run directory, finite writers, exact six/eight counter, request/response wire checks (32768 bytes), G0 SQLite same-connection read-only authorizer, parent supervisor and owned-group cleanup. The directory limit remains **67108864 bytes / 64 MiB sampled budget**, counting logical and allocated bytes including unknown files and writable unlinked regular fds. It is not a filesystem hard quota. Configured 0.1 seconds is unscheduled metadata; sampling is each supervisor iteration and finalization with selector timeout at most 0.05 seconds, and actual intervals must be reported. The old hard-quota design text is superseded by the monitored contract and must not be revived as an achieved protection.

The native `_Bounds(nodes, edges, depth, leaf_bytes, encoded_bytes)` and `_Limits(resident, peak, work, integer_bits)` are explicit positive exact integer domain controls. Their ledger uses conservative logical managed-allocation/work units. A legitimate separately chosen finite allowance must state these units and accepted subdomain, preserve pre-issuance LEGACY routing and fail-closed post-issuance behavior, and not pretend all valid business inputs fit. No production default or useful numeric native allowance can be derived from `resident=10**30, peak=10**32, work=10**40` in the synthetic test. Those values let finite tests reach branches; they are not resource qualification.

Neither native logical units nor the 64 MiB disk monitor bound whole-process RSS, GC/allocator overhead, CPU time or baseline SQL/decoding/full checks. The archived small directory peak likewise says nothing about memory. The existing evidence does not establish a whole-process RSS ceiling or derive a safe complete-input native allowance; this review supplies neither an invented constant nor a claim that wall monitoring alone proves one. This is an explicit remaining resource/eligibility limitation, not permission to enlarge the old disk/time/request contract.

## Minimal account resolver input/output/trust contract

Input remains `resolve_account(user, original_contract, approval_key)` at a fixed server boundary, after the caller's original `_approved` check. `requirements_for` parses the exact original contract, matches its principal and binds principal/project/runtime/trial/approval, full contract fingerprint, software/authorization fingerprints, fixed provider/model/endpoint, quota subject, expiry and zero paid cap. It is a projection, not an authorization check by itself.

The intended internal output is an exact strict `SourceVerificationResult`: requirements fingerprint; opaque account ID and canonical quota subject; original provider/model/endpoint; evidence fingerprint; ALLOW/DENY/UNKNOWN; explicit entitlement/non-chargeability/revocation facts; observation time and expiry. `policy.check_source` requires exact binding, canonical account quota, ALLOW, revoked false, both entitlement facts true and `observed_at <= now < expires_at <= contract.expires_at`. The enclosing controller additionally matches the binding's account ID, repeats current checks and preserves original software qualification. **This policy does not impose a universal 30-second observation-age limit**; the 30-second rule in `validate_candidate` applies to untrusted candidate diagnostics and must not be silently imported as this output's rule.

Trust must come from a separately reviewed fixed server-owned producer with current provenance, revocation and enforceable non-chargeability. Constructing the DTO, accepting caller booleans/opaque IDs/digests, private config selection, a successful structural diagnostic, or the historical synthetic producer proves none of those facts. The current resolver has no override/registration parameter: it projects requirements then raises `LIVE_BLOCKED / No reviewed production account evidence source is supported`. It issues no FeeProof, Permit, credential or reusable dispatch authority. Source absence must remain a refusal before reservation/send; UNKNOWN or a received response must not trigger automatic resend or presumed zero usage/fees. Installing a real resolver is outside this seam and this review.

The companion JSON binds the inspected source and historical grant/receipt/control bytes. This report does not reopen or independently query the historical DB.
