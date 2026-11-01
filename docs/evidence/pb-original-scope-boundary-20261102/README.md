# Exact original P-B boundary; no claim of expiry/G0/PG acceptance

Application/controller source remains `be5f76d934791bb7375fbc9d108a131589c9a75b`.
`git diff --exit-code` confirms **no changes** in src, existing stage controllers,
requirements.lock or setup.py. Diagnostic source:
`5a2d0258adbbefd5eaa502bc3483c8c7c99622bc`.

Actual single command:

```text
/workspace/scratch/sim2act-pg-locked-runtime-20261101/venv/bin/python scripts/diagnostics/pb_original_scope_boundary.py --root /workspace/scratch/pb-original300-boundary-20261102-once
```

Exit0. Receipt SHA256
`d06e98b0a0eacb3107d11b35966da977edcd46f1d8265906e518ae3939004e9b`.
Explicit literal SQLite/test_only, fixed public synthetic fixture identity,
MockTransport that raises if invoked. No conftest ambient URL selection, PG,
network service, production role/credential, clock/expiry/method patch, claim,
provider call, G0 or G1. The real application API/Worker validators run unchanged.
The new diagnostic records actual rejection and safe convergence; it does not
repair or accept a complete P-B path.

## What actually happened, in order

| Actual phase | Seconds | Result |
|---|---:|---|
| Normal P-B preparation and exact consent | 0.196721 | PASS, original300 seconds |
| Original Generate request accepted | 0.020397 | QUEUED, no claim |
| Worker using canonical offline runtime quota | 0.000843 | LIVE_BLOCKED in pa_trial_dispatch._binding |
| Worker runtime matching original unconfigured quota | 0.023463 | LIVE_BLOCKED in production_trial_admission._resolve |
| Original production environment validator | 0.000093 | LIVE_BLOCKED for deliberate SQLite/mock configuration |
| Original cancel/repeat/withdraw | 0.088262 | CANCELLED/no result; repeat409; REVOKED |

The observed1.023663 seconds is elapsed **before** closing/reopening Store/API,
including bootstrap/reads outside this non-exhaustive phase table. It is not a
300-second expiry result or complete end-to-end performance measurement. Fresh
Store/API afterwards re-read the same CANCELLED/no-result and revoked trial;
that read passed but was not separately timed and is not a separate process.
Original database stays in its own scratch directory, not published in this packet.

Source and Cold were **NOT_RUN**. Attempts0, model dispatch0, slot/journal rows0.
Neither validator invoked once/claim. Original300/lease30/Run300 remain unchanged.
Exact captured exception frame/function/line lists are in actual-receipt.json.

## Classification: three different boundaries

1. **Observed local Mock trust boundary, not a performance defect.** Normal
   natural_trial_preparation.py234 assigns `unconfigured:<principal>` in mock.
   Canonical account binding therefore mismatches the runtime/scope before claim.
   Matching runtime quota to the original contract merely reaches `_resolve`,
   where canonical account ownership still cannot match `unconfigured:`. Original
   preparation/consent is not an account or production entitlement. No source,
   contract fingerprint, approval or success gate was edited to bypass this.

2. **Original standard300-second preparation has a structural whole-trial
   scheduling contradiction at1RPM, independent of PG/CPU speed.** This is source
   analysis/lower-bound proof, not a newly run300-second failure. natural_spec
   requires3 provider responses: read request, real checker request, final
   candidate (goal_applications.py1434–1446 and1750–1769). Strict same-trial Source
   requires2 (natural_source_archives.py247/431; pa_trial_dispatch.py522/1793).
   Even the finite single-model Cold needs1. The actual original account cursor
   requires >=60s between reservations (production_trial_policy.reserve and
   pa_trial_dispatch.wait_unreserved). Six reservations occur no earlier than
   offsets0,60,120,180,240,300 from the first one, itself after preparation. But
   natural_trial_preparation.py256 fixes normal P-B expiry at prepared_at+300,
   and _run_context/admission enforce strict `now < expiry`. Thus no amount of
   G0/G1 CPU optimization or valid worker heartbeat can make this **specific
   standard prepared scope** complete. A two-node Cold needs a seventh call and
   an even larger lower bound. No checker/field/input is removed for speed.

   Important scope distinction: underlying V1 model admits a separately frozen
   finite absolute expires_at; historical1200/1800s synthetic contracts exist.
   That does not authorize silently changing the standard preparation policy,
   any existing approved contract or this task's original300-second condition.
   This report does not call all possible P-B contracts impossible.

3. **Formal PG/production/large-lock acceptance is still absent.** The explicit
   production validator requires a non-test PG Store, original live configuration,
   exact configured account and real source. Its issues in this probe describe
   deliberately chosen mock settings with empty token; they are **not evidence
   that cloud token injection is missing**. Current injected-token presence is
   true (boolean only), free Intern authorization is unchanged. Registry original
   fixed manifest query previously returned401 and remained stopped: no auth,
   retry, mirror, new image, database, bridge, role or credential operation here.
   PG readiness alone also cannot solve the scheduling contradiction in item2.

## Why no five-minute fixture run was started

A proposed wallclock prototype was independently reviewed but NOT EXECUTED.
It would already fail for item1. Its 250ms synthetic-account refresher also
replaced the entire worker.pa_trial object, which current complete Cold graph
identity checks reject; such a VERSION_CONFLICT could not honestly be labelled
an expiry failure. The static OfflineRegistry has no reviewed refresh interface
that preserves that issued binding and its complete graph ownership. Original
production source observations do preserve binding identity, but that production
backend cannot be installed over this SQLite fixture by relaxing environment
checks. Ambient PG selection/optimizable assertion and weak expiry attribution
were also rejected before effects. No300s run or altered clock followed.
This does not rewrite or reclassify historical successful/failed test artifacts.

## Remaining smallest decisions/dependencies

- To complete a **normal prepared full P-B** at original1RPM without deleting
  required calls, the product must explicitly define a distinct newly approved
  execution window/protocol. Existing P-A V2 separates finite300s review and
  finite execution expiry; it is a design precedent, not automatic P-B consent.
  Current standard P-B stays300. No new contract/UI option was added this round.
  Alternatively changing the required generation/source protocol would need its
  own complete producer/history/proof migration; it cannot be a dispatch shortcut.
- To measure formal PB G0/G1/locks/cancel/old-owner/fence over the actual production
  backend, original pinned-image/platform metadata must be verified, followed by
  the exact isolated PG scope in current PG-PLAN and its concrete execution
  confirmation. Four proposed temporary secrets remain uncreated. No generic
  model fee/token request is needed.
- In current permitted scope, no independent performance change can turn item2
  positive while preserving all stated invariants. No speculative cache, larger
  timeout, account fake, changed PASS or new test backend was layered in. Prior
  small working flows, original lease-control fix and unresolved long-lock risks
  remain version-bound and are not expanded by this diagnostic.

Cancellation convergence was really observed here; UNKNOWN provider/withdrawal
handling remains only the earlier version-bound controlled negatives, not a newly
executed model failure. No new suite was run to pad counts. This round provider0,
PG0, nativeWindows0, explicit CI execution0, PC0; prior runner ledger487/900 remains.
Normal dev push only, no main/Release/deployment/permissions change.
