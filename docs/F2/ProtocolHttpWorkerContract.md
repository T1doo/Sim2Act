# Offline protocol HTTP and Worker contract

This is an engineering boundary, not owner semantic acceptance or LIVE approval.

POST `/api/projects/{pid}/protocol/source`, `/extract`, `/cold` accept a closed
phase payload plus `request_key`. Source fields are `goal`, `inputs`,
`resource_ids`, `contract_id`; extract fields are `source_run_id`, `expected_source_fingerprint`;
cold fields are `extraction_run_id`, `expected_plan_fingerprint`, `inputs`,
`resource_bindings`, `contract_id`. No client responses, Replay, candidates, gold, scope,
permission, review verdict or PASS is accepted. The contract ID resolves through the trusted server registry before submission;
its version/hash is frozen in the accepted snapshot. Missing registry entries
wait for configuration. Review uses that frozen contract, never a later choice. GET `/api/projects/{pid}/protocol/runs/{rid}`
checks both current owner and the requested project. Submission is asynchronous
202, semantic UNKNOWN; technical source/cold completion waits for review.

The Worker dispatches protocol jobs before app jobs. No default protocol runner
exists: absence yields WAITING_RESOURCE. LIVE workers and LIVE HTTP settings
reject protocol execution. Only an explicit test-only factory receives
`(worker, run, accepted_snapshot)` and returns a runner. The snapshot carries
scope and immutable phase input; no callback is client supplied.

`ProtocolAttemptRunner` wraps the offline BudgetedProvider (actual InternModel
with httpx.MockTransport). It reserves through existing Worker.reserve with the
actual tools, writes Attempt identity/usage/response and maps zero-based model
request indices to durable attempt IDs. STARTED attempts cannot be resent.
The backend supplies real tools.dispatch and stable call IDs bound to attempts;
cold compiled-plan steps are separately recorded. Heartbeat, lease and fence
remain mandatory around all calls and result writes. An injected test runner is
not a production provider selection or an authorization expansion.

Attempt responses retain parsed safe assistant/model/usage/finish reason. Private
reasoning and unknown message fields are excluded; only the raw response hash is
retained. There is no HTTP gold registry mutation.

## Local validation and remaining boundary

`/workspace/sim2act-pb-venv/bin/python -m pytest tests/test_protocol_http.py -q`
drives authenticated HTTP and durable Worker execution through actual InternModel
with httpx.MockTransport. Mock wire outputs read expected synthetic answers only
inside test code; registry gold/expected output is never provider request input.
The complete flow includes separate persisted source review, one model extraction,
a compiled plan, fresh cold material, actual read Operation, and separate cold
review. Negative cases cover strict and nested forbidden fields, identity/project,
LIVE refusal, missing provider, mismatched model/unknown usage, and STARTED crash
without automatic resend. Attempt responses exclude private reasoning and unknown
message fields, and tool request fingerprints use the actual sent schemas.

The injection is test-only. Each job's provider ledger is bound to its own scope;
this path has **not** demonstrated one shared 14-slot ledger across source,
extract and cold. Existing global ledger unit tests do not prove that integration.
Resolving scope inheritance plus an explicit separately approved provider boundary
is still required before any LIVE activation. No CI, push, external provider call,
role/Grant creation, UI or business-family compatibility was performed here.

Measured in this slice: HTTP focused suite 25 passed; protocol HTTP/jobs/reviews/
schema plus F1 closure/persistent app regression 133 passed, 6 environment skips
(SQLite); previous model-protocol/model-budget suite 60 passed. Ruff passed for
this slice's API/Worker/test files; mypy passed protocol_api and worker with
`--follow-imports=silent`. PostgreSQL/application-role evidence is not claimed by
this HTTP slice. The extraction-response tamper case rejects dependent HTTP
inspection, writes a failed cold Run and performs zero cold model requests and
zero cold Operations. Synthetic transport clock advancement is test-only and
does not change production no-wait/rate behavior.

Protocol scope gates now re-read the accepted snapshot and current authorization
under project-before-Run lock ordering. The explicit-tools reserve branch locks
the true Run owner's project before the Run; adapter writes use the same order.
The provider's current-authorization callback checks again before its request,
and real read dispatch rechecks permissions. This offline evidence does not claim
an atomic database permission lock across an external network request.

Each Attempt additionally stores `safe_response_fingerprint`, computed from its
complete persisted safe envelope. Completion seals can re-compute this value;
the original raw response hash remains unchanged and cannot substitute for a
re-computable persisted response fingerprint after private fields are removed.
After the lock-order strengthening, HTTP/jobs integration measured 53 passed.


## 2026-10-06 bounded shared-pool and recovery follow-up

The earlier missing shared total and recovery gate is historical for that slice.
The local follow-up now binds source/extract/cold across protocol owners/projects/
Runs/processes to a fixed mode pool. Controller initialization defaults to zero;
14 is explicit synthetic test-only offline allowance, LIVE remains zero and
rejected. Attempt STARTED and pool slot reserve in one transaction; received
outcomes settle both ledgers together. Pending/unknown and inconsistent records
retain consumption and block sends. The conservative one-inflight policy may
halt concurrent work even when the originating caller later records a response.
No reset/refill/retry interface is supplied.

POST `/api/projects/{pid}/protocol/runs/{rid}/recover` accepts only strict
`expected_version`, `expected_fence`, `request_key`. It rechecks owner/project,
current resources and frozen dependencies, returning metadata, never a provider
request. Sealed results await their existing review; unknown stays stopped; known
responses without atomic protocol completion report continuation unimplemented.
Each expired protocol Run is recovered in a separate project→Run→pool transaction;
ordinary F1 claim holds no pool lock. This follows an actual PostgreSQL 40P01
reproduction and same-schedule fix verification. See
[scope](ProtocolSharedBudgetRecoveryPlan.md) and
[evidence](../evidence/protocol-shared-budget-recovery-20261006/README.md).
There is no LIVE/semantic, automatic continuation, native-browser or whole-P-B
acceptance claim. Prior failures and coverage correction remain recorded.

## Offline preparation and project canvas follow-up

The project-owned `/protocol/contracts` GET now exposes only fixed public goals,
inputs, schemas and material hashes. Project task history/result canvas offers
source, reviewed-source extraction, fresh-input cold submission and metadata-only
recovery with original-key retry. It never submits a checker verdict or grants
permissions. `owner_semantic_acceptance=PENDING` remains separate from the finite
registered review state. UI responses recheck identity/project and user selection.

Controller `prepare_handoff`/`require_handoff` use existing events to freeze the
offline accepted snapshot, scope, material projection and budget policy. The
zero-network demo rechecks this before each actual request reservation; legacy
offline fixtures are not silently relabeled as approved experiments. A cold
handoff accepts only one exact public read/interpret template, including all
schema/argument/instruction fields. Source dependencies are checked before the
pool lock. Provider stages are bound to frozen family/phase; extraction scope is
one request and source history uses its original frozen allowance.

This handoff is not an actual outgoing-envelope validator or LIVE provider switch.
The DB total is shared, but six-stage/time policy remains per sidecar. The uniform
experiment identity, exact sender projection and owner approval are still missing.
See [scope and checks](ProtocolExecutionReadinessPlan.md) and
[evidence](../evidence/protocol-egress-readiness-20261006/README.md).

## Bounded experiment controller integration (2026-10-06)

Controller-only initialize/bind/advance on the fixed DB pool adds sealed events without new tables. Initialization defaults0; offline controller demonstration may tighten the existing shared14/64000 allowance. Run→stage→Attempt→slot→completewire witnesses are checked bidirectionally; any retained experiment trace prevents downgrade to a legacy sender. Source/cold require separate persisted registered checker acceptance before advance, while owner acceptance remains PENDING. Unknown stops globally; no refill or resend.

Worker reserve commits experiment SEND and completewire SHA256/byte/character witnesses with the actual Attempt/slot. Current result settlement commits in the existing adapter transaction. Reserve and actual transport both enforce last known settlement+6 and300second stage bound. The actual sender uses frozen checkedbytes, performs a strict metadata and current-state guard directly before client.send, and validates type-sensitive durablewire seals. Cold has only newmaterials; fixed extract public projection excludes the previous answer and evaluator metadata.

These hooks are offline/test-only. Production LIVE remains forbidden in HTTP/worker, with pool0; a separately authorized production controller binding an owner-approved exactspec is still required to execute real requests. See the bounded package evidence for exact code boundary rather than interpreting a synthetic checker PASS as permission to send.
