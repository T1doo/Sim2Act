# input_bytes reuse decision and return to the original recovery gap

Reviewed HEAD: `04ef9f2a5e112b67689e142d7d2629fa5d7383e3`.
Decision: **no qualified production reuse slice in the current representation**.
No product code, guard, transaction, deadline or default selection changed.
This is a static feasibility review, not another performance experiment or a
claim that all safe optimization or a 30s result is impossible.

## Exact repeated work and why its current value source cannot be reused

`_ColdGraphRead.input_bytes` constructs a fresh complete PB contract projection,
combines it with the current inputs, role Limits, phase and binding metadata,
then invokes one fresh C Pickler with one fresh memo. The previously observed
8,062 codecs / 4,682,215,371 returned bytes per complete synthetic arm establish
volume, not a reusable subset or its recoverable CPU. Contract typed storage
runs before `_cold_graph_bytes`; these are sequential siblings under
`input_bytes`, not typed storage nested inside Pickler. C Pickler inclusive
time includes its reducer/row-storage/Limit-leaf work and must not be added to
those nested inclusive times. Profile time is not a measure of safely
recoverable CPU. No new profile or microbenchmark was run.

| Source in the actual method | Ownership / alias fact | Reuse decision |
| --- | --- | --- |
| `self.inputs` or explicit frontier | The constructor retains the caller's dict. `add` validates each new edge and re-pins; current/call/complete and later receipt roots grow in the scope. | No old dict, bytes or PASS reuse. |
| `b.contract` | Frozen outer ProductionTrialBinding retains the original mutable PB model. Its bindings list, Recipe/Step, caps and model storage remain readable by existing consumers. | Frozen dataclass is not recursive value ownership. |
| `_trial_typed_storage` result | Containers are fresh for this call; its per-call seen map preserves DAGs. Scalar and actual key objects remain original references, including aliases into independent graph roots. | A previous result is neither current storage nor an isolated pickle fragment. |
| `self.role_limits` | The dict and exact Limits instances are original references. The reducer freshly checks complete raw fields/extra/private state and reads each value. | Neither the dict nor its models is an immutable closed subtree. |
| RowMapping reachable through inputs | `keys` is the original list, `data` the original tuple; hidden positions may contain mutable JSON or share values with other roots. Only the safe string lookup is rebuilt. | Visible-column snapshots omit protected state; tuple alone is not recursive immutability. |
| Existing owned Source/Generate | `_Frontier` already substitutes exact accounted paths, nested complete paths and the Generate Run reference with private immutable continuity values. Other independent aliases are deliberately still serialized fresh. | Not a new unexploited full-graph ownership proof. |
| phase / None / fixed envelope / leaf scalars | Some are immutable. References can still participate in the same memo, and the envelope is already written outside pickle. | No evidenced material reusable closed subgraph or additional repeated-content elimination. |

The four **existing** configured-contract counterexamples in
`tests/test_cold_typed_storage_alias_contract.py` distinguish equal values from
equal graph bytes: directly reusing caps changes sharing; retaining equal old
keys changes memo aliases; early copies miss a fresh scalar; patching values
does not repair key identity/order. They were read, not rerun or counted as
new results. The RowMapping original keys/data and hidden positions are part
of this same graph. Independently pickling a supposedly static root and
concatenating its bytes loses the shared memo/frames; a visible-field hash
does not preserve this contract either.

`_check_dynamic`, `check`, `add`, the pre/post scopes, original SQL/authorization
returns, full read sets, current Run/fence/stop and final clock remain intact.
A transaction does not freeze the Python graph. A one-time disjointness scan
would itself go stale when later roots/aliases are added. No new exclusion,
cross-call memo, reentrant flag or cached validation result was introduced.

The smallest architectural alternative would require an explicit value
ownership/protocol migration: all consumers of the selected fact family read
one server-owned recursively immutable representation; no mutable or
cross-domain alias escapes; future root admission preserves that partition;
dynamic frontiers stay fresh. Private manifests must remain separate from old
raw/pre/post/origin/business signatures. This does not currently follow from
the two accounted families or the old design ACK and is not implemented here.
Under the present exact byte/alias contract, freezing or cutting a new subtree
without that migration is not a safe implementation shortcut.

## Original product gap selected after this audit

The concrete independent gap is **protocol-specific trusted continuation and
unknown-request reconciliation**, from V5 §8.2–8.3 and F2-T09. It does not
depend on Cold G0 or a real model. The current safe refusal is real code:

- `Store.reconcile_attempt` verifies the protocol job and then raises
  `UNSUPPORTED_CAPABILITY: Protocol continuation is not implemented; no F1 fallback`.
- `protocol_jobs.process_job` rejects an already-requested context;
  `command_job(resume)` rejects unknown requests, any prior request count or
  an existing result. Unsent/zero-request resume already exists and is not a gap.
- `ProtocolAttemptRunner`/the provider sidecar, immutable shared request slots
  and optional experiment ledger also participate. Merely replacing the
  refusal with generic F1 response import would bypass those contracts.

This is a next implementation target, **not a claim that a supplied response
proves a send or that a timeout means no effect**. Before changing its route,
the narrow contract must bind the exact accepted phase/plan and request
ordinal, original key/wire/response/trace, Attempt, Operation receipts,
normalized usage and nonrefundable pool/experiment reservation. A resumed
pure step can consume only verified prior results; a new request requires an
explicit remaining budget, fresh authority and its own original slot. Missing
usage stays unknown; reservations and halt conditions cannot be reset.
Ownership/version/fence, cancellation, current material/source dependencies,
original finite deadline and same-key idempotency must be rechecked, with no
automatic resend. Deterministic replay and network dispatch need distinct
interfaces so recovery cannot quietly invoke a sender. This contract and its
counterexamples need review before a runtime implementation; the current
refusal remains, rather than shipping a partial bypass as recovery.
Historical requests lacking the necessary immutable receive/trace evidence
cannot be backfilled from user claims or silently migrated into this contract.

Other tempting items were checked and **not** selected as new work: CSV App
material authorization exists; four-step text owner review exists; controlled
composition already accepts per-node wiring/columns, checks new plans and
creates internal Releases/instances; compatible version switch/rollback
exists. A multi-node derived DAG is not a canonical `app_drafts` single-sum
candidate. Removing the finite PROJECT `len==1` gate would change that accepted
contract, not repair a proven omission. Formal publication and a real account
resolver still require their original evidence/authority boundaries; neither
is fabricated to unblock this audit. General project memory was not selected
without a specific missing consumer contract.

## Actual checks and evidence limits

`source-facts.json` records exact input hashes and AST locations. The writer
performed file/Git reads and standard-library AST/hash checks only; the
existing independent reviewer performed read-only source review. No product
imports, DB opening, pytest, Worker/Mock/model call, new grant, HTTP business
request, profile, benchmark, G0/Cold2/W5 window or retry occurred in this slice.
There is no new speedup, lease margin, real-source qualification or recovery
success to report. The preceding A/B and historical failures remain unchanged.
The row candidate remains default closed. Git/remote receipt is verified
separately after this evidence-only commit.
