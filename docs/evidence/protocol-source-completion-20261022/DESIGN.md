# Ordinary Source known-completion slice (V5 §8.2–8.3 / F2-T09)

The existing Source runner can receive all responses and verified resource.read
receipts, then lose its final completion transaction. Generic resume deliberately
refuses requests>0. This slice adds no sender to recovery and does not reconcile
UNKNOWN responses.

Before each actual offline Mock request, a Source-specific V2 origin binds the actual
Attempt, local request index, shared-pool reservation, exact wire and original
Run/provider deadlines. Existing extract V2 remains a separate namespace. Only
the existing test_only SQLite/mock/MockTransport boundary can issue these facts.
Historical/shared-ledger setups keep their original non-recoverable path.

After complete_task returns, before the original completion transaction, rebuild
its result from the ordered 2–3 RECEIVED responses and the complete VERIFIED
Operation set, rechecking current authorized reads and exact receipt bodies. A
READY event mirrored on Run/last Attempt binds full Attempt, slot, Operation and
provider-ledger seals plus the result. No response import or accept_candidate.

The owner-only three-field completion request opens the server-selected existing
sidecar read-only, locks project/Run/pool, revalidates every fact, and fences only
an expired uncancelled incomplete Run. The original complete_in_tx commits the
same result as WAITING_APPROVAL, semantic UNKNOWN. READY v/f anchors also admit
one proven existing metadata-only recovery transition, without rebinding send
fences or granting execution time. All writes and the final fresh
authorization/original deadline gate are one transaction. No reserve, send,
refund, halt clearing, semantic review or experiment advance occurs.

Idempotent replay returns the original receipt for its original key/version/fence.
A later legitimate review may change status/version, but cannot change its sealed
result or completion fence. Experiment history must remain valid; recovery cannot
revive a stopped/advanced incomplete stage. No widening to extract, Cold,
bounded-check, legacy V1, missing usage or unknown responses.

Validation: isolated real Store/Worker/Mock normal vs interrupted Source, fixed
synthetic business clock (not G0); at most seven Mock requests for two 2-response
and one 3-response control. Negative tests copy only committed sealed fixtures;
recovery must send/reserve zero. No CI/browser or real-time G0 window.
