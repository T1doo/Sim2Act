# Configured PG runtime build and repaired P-B lease diagnostic

Frozen source: `c8fba5316043264bdfb7d761a49d3e96995f5aaa`, development branch
`dev/cloud-g0-live-20261028`. Runtime application bytes remain the reviewed
`1d4835a4c32e9ca68916eab9e99ac8d7afb8b895` supervisor implementation; this
revision completes packaging and repairs the diagnostic without changing a
production guard, callee, lease constant or absolute deadline.

## Actual functional and regression results

`configured-c8fba531-final-regression-20261101.xml`: **74 passed, zero
failure/error/skip, 72.75 seconds**. It covers the actual dual-process
TEST_ONLY SQLite desktop save/cancel/reopen flow, packaging closure, original
PB ownership/alias/code mutation refusals and the repaired lease contention
fixture. It is not native Windows or actual PostgreSQL acceptance.

The old P-B scheduler diagnostic had two independent invalid assumptions:

- It replaced six fixed production callees after contract issuance. The native
  PB entry correctly refused it. `sys.monitoring` now observes the original code
  without rebinding these functions, defaults, closures or classes. The tests
  that deliberately replace fixed generation callees still pass by refusing.
- A committed foreground renewal can coalesce the sender's first cadence.
  The first actual background write is then about the second cadence. The old
  22-second wait ended less than five seconds after actual writer acquisition,
  before its original bounded SQLite lock wait could raise BUSY. The diagnostic
  now waits for the actual writer handshake and observes BUSY within the
  original lease, leaving the original finite safety margin.

No BUSY assertion was deleted or replaced by a fabricated result. In the frozen
run: **one actual SQLITE_BUSY, one finite Mock exchange, one known request/attempt,
two reservation boundaries, committed renewal recovered, and the original guard
still passes after the previous committed lease interval ends**. The foreground
is deliberately held outside a transaction. The inspected intermediate state is
RUNNING; this diagnostic does **not** claim to finish P-B generation/source/Cold.
Two additional tests revoke actual synthetic Grants and preserve original
revocation latching and refusal before reservation.

`directed-lease-proof.json.gz` is the entire original 6,841,961-byte synthetic
scheduler trace, not a reconstructed success summary. Its uncompressed hash and
counts are in `directed-lease-summary.json`; failures from observer v1–v3 remain
alongside it. The JSON serializer now records callable metadata instead of
masking the original diagnostic assertion with a serialization exception.

## Actual same-version internal Windows input

Local file (not uploaded or published):
`/workspace/scratch/Sim2Act-internal-win64-c8fba5316043-reviewed.zip`

- Size: **27,577,607 bytes**.
- SHA256: **43b39df326f521601c3c5bdcc7e0303e9a0ff06ef320466d561945fa30640d85**.
- Current Git source resources: **197**, checked byte-for-byte.
- Exact package inventory: **1,897 members**, including the complete manifest;
  each size/hash and absence of duplicate members verified by rereading the ZIP.
- Installed metadata: **24 packages**, including original pinned psycopg 3.3.3
  and psycopg-binary 3.3.3; the old dependency image no longer supplies an
  incomplete PostgreSQL runtime in this explicit configured profile.
- Fresh current Python wheel: **1,564,104 bytes**, SHA256
  `08f1fa08902f7e7c8f9880342e48d67f70ee7c614a68e7ad9341baa7fa516828`.
- Current C# compiled from this exact Git commit using the existing pinned
  Microsoft tools/SDK: EXE **32,768 bytes**, SHA256
  `29ce9e931ba6365a09260d8ad06bd68843c7cb7a44f9fdb870c291e384230c13`.

The four Windows extension files are **REUSED_UNCHANGED_NATIVE**, not newly
compiled or newly executed Windows Python. Every complete C/header input group
(and the typed cohort's Python dependency), original setup recipe, SOURCE_SHA,
old actual Windows import record, PE/CP312 identity and binary digest match.
The new wheel is assembled from a verified source-only wheel plus these exact
PE files, regenerates every RECORD entry, and validates complete current source
and native inventory. No Linux binary is retagged as Windows.

Independent static review additionally checked all 24 installed RECORDs (1,833
records), actual packaged native hashes and PostgreSQL libpq/SSL/crypto import
path closure. This proves inventory, not an actual target DLL load or connection.
Original driver wheels/notices are retained. Project licensing remains unchanged
and dependency redistribution review is explicitly NOT_EVALUATED; no license or
publication qualification was invented.

The revised READ-ME-FIRST accurately states that an EXE is included, without
requiring users to compile C#. The root desktop manifest describes actual runtime
files; the full original host-component archive, including its referenced source
and compiler logs, is preserved under host-build-provenance. Earlier internal ZIP
b8395cd… remains local and was not relabelled as the reviewed input.

The offline assembly method, compiler output, wheel/source and stage identities,
and original assembly failures are saved here. The initial hosted-token substring
scan found a match inside a word in the unchanged original psutil `_pslinux.py`
string constant (file SHA256
`571c6cd7919971df4c1381cfd514808ff934f7f7fc79c312b52278fcd0c7dd10`). No match
value was printed. Standalone-token boundaries fixed that classification; bounded
private-key/token and private-config/database-name checks do not claim a universal
secret audit. No private configuration or database binary is published here.

## Actual environment and remaining external conditions

The original managed cloud task is connected. The existing alias
INTERN_API_TOKEN is observed ready/nonempty; dedicated SIM2ACT_INTERN_TOKEN and
explicit live mode flags are not injected. No value is printed/saved. Existing
fixed intern-s2 free-service authorization is unchanged. This revision makes
**zero real model calls**; the scheduler diagnostic's single Mock exchange is
labelled separately and never presented as real Intern.

No SIM2ACT_DATABASE_URL, SIM2ACT_TEST_DATABASE_URL or authorized isolated PG config
is injected. No local PG tools, cached PostgreSQL image or existing Sim PG
container is available. The managed Docker socket is available, but no database,
login, role, credential, auth setting or shared/training facility was provisioned
or touched. The old record-only PG fixture is guarded to its original authorized
Windows branch/scope; it was not bypassed or repurposed as formal P-A/P-B evidence.

Actual PG validation requires a selected existing initialized isolated PG
application-role connection, its permitted schema/CRUD scope and quota subject,
and the original principal/project/trial/approval/account selection plus existing
application login. Formal source/material approvals must match the selected
versions; they cannot be synthesized from the Mock fixtures. None is supplied in
this environment. Model fee permission is not the missing condition.

**Not run:** current complete-package Windows execution, actual PG dual-process
save/reopen/cancel/revocation/final commit, formal P-A/P-B full-chain live-model
acceptance, large Cold remeasurement or R0 AT01–27/F3. The package is ready as an
internal verification input, not an accepted installer or finished R0 Release.
No end-user candidate was uploaded. No new Windows CI was started: cumulative
ledger remains **487 / 900 runner seconds**. No main/force push/Release/deployment,
PC action, new persistent credential or security permission change.
