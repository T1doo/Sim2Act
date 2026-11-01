# Isolated PG verification: current executable core proposal, NOT EXECUTED

Current source: `be5f76d934791bb7375fbc9d108a131589c9a75b`. This supersedes the2c4fd44 candidate:
its1200-second product preparation option was withdrawn for lack of original
product authority. Original P-B preparation/API/UI are byte-identical to the
pre-extension baseline; current original300s scope, lease30, Run300 remain.
Runtime31 lock entries are aligned separately; the original runtime and four
native modules are preserved. The original production journal and bounded phase
controller are implemented; only Generate-only is currently executable through
the future specifically confirmed PG scope. No actual PG, role/credential,
container/bridge or real model operation was performed. CI487/900 unchanged.

## Read-only observations and blocking conditions

- Latest frozen read-only observations:2,394,136,576 /2,394,132,480 free disk
  bytes (core/Generate), >=2GiB;10,836,033,536 /10,835,771,392 available-or-inactive
  memory bytes, >=4GiB. This is not reserved capacity and must be rechecked before
  any effect. No new build/large test is needed to establish current plan facts.
- Existing managed Docker server28.4.0 is readable. Pinned image is not cached;
  no existing PG connection or postgres executable is assumed.
- Sole image remains
  `postgres@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3`.
  Public official Docker Hub tag17.11 metadata GET returned HTTP200 but its current
  index is `sha256:3b0cda93be7c8dba2ed484d19393d93845dc3dafb88973e248ba8e6d99d784e1`,
  which is different. The controller does NOT substitute it. Exact original
  manifest GET from registry-1.docker.io returned HTTP401. That query STOPPED:
  no auth/token request, retry, mirror, alternative content route or image pull.
  Exact original linux/amd64 descriptor, runtime UID/version and image licenses
  remain UNCONFIRMED. A successfully authorized original manifest is needed;
  a tag response, historical label or author-supplied PASS cannot satisfy it.
- Current and fresh-child imports bind reviewed src. Four existing native
  modules match complete build-input witnesses. Exact all31 installed lock
  versions now PASS in the isolated runtime below. Original .venv was not
  overwritten. Wheel name/version/hash/size, pip check, per-version old/new
  differences and bounded duplicate-copy cleanup are preserved in
  `../locked-runtime-live-controller-20261101/`; none of these resolves401.

Model-token presence is currently true for the opt-in read-only plan. This is a
boolean only. Existing token is never printed or written to PG/Docker/config.

## Implemented controller and exact binding

`scripts/diagnostics/isolated_pg_probe.py` is real code, not a placeholder. Default
operation is read-only (including a no-DB child Python import-origin check):

```text
/workspace/scratch/sim2act-pg-locked-runtime-20261101/venv/bin/python scripts/diagnostics/isolated_pg_probe.py --source-sha be5f76d934791bb7375fbc9d108a131589c9a75b
```

Observed machine plan hash:
`2774c9c9d4f01a0a1aa9283a67a5c886813666774b5844b954ae055f49f54f9a`.
It is a **NOT_READY observation**, not execution permission. Resource numbers are
excluded from the checksum, but thresholds/code/versions/import binding/native
recipe/image/source/phase/operations are bound; execution rechecks resources.
A resolved manifest/runtime changes the plan, requiring a fresh frozen checksum.

Only after prerequisites and one concrete execution confirmation, the supported
shape is `--source-sha <frozen-controller-sha> --manifest <verified-original-index>
--execute --confirmed-plan-sha256 <fresh-ready-plan-hash>`. This is not executed
here. Checks run before nonce/root/password/image/network/SQL effects: exact Git
source (including controller, package, native helper, lock and setup recipe),
original full software qualification, actual parent/child import files, installed
locked versions, complete native witnesses, exact index byte digest+one matching
linux/amd64 platform, current resources and matching concrete plan checksum.
A checksum is an accident-prevention gate, never a substitute for permission.

## Concrete effects of CORE_MODEL0 needing that confirmation

One new 0700 nonce directory under `/workspace/scratch/sim2act-pg-probe-<nonce>`;
0600 files. Reject collisions without adopting or overwriting existing state.
Bind dev/inode before state writes; changed root or public-state bytes stops.
One nonce-labelled dedicated ordinary bridge and one labelled container, with
exact recorded IDs. Docker-managed network effects are included in this scope;
no manual firewall/daemon/network-policy/ACL/owner changes or external service.
Only IPv4 `127.0.0.1:<assigned>:5432`; product HTTP only127.0.0.1. No host network,
privileged mode, host socket mount, named/shared volume or root fallback.

Pinned container: linux/amd64, UID/GID999:999, read-only root, cap-dropALL,
no-new-privileges, CPU1, memory512MiB, pids128. Writable tmpfs PGDATA512MiB,
socket16MiB and tmp32MiB, each owned999 mode0700. In that same container, a fixed
shell checks actual UID/GID and postgresUID then execs the original official
entrypoint; mismatch fails, no alternative image or root. max_connections16,
shared_buffers32MiB, WAL64/32MiB. Initdb local/host SCRAM, never trust. Readiness
uses actual mapped TCP SQL, PostgreSQL17.11/user/database identity, HBA rules and
a strictly identified wrong-password rejection. Timeout/refused connection is
not an authentication PASS. UID/version/HBA are future runtime checks, not
currently proved by public tag metadata. Historical socket-only readiness and
exit137 do not establish current readiness or OOM.

Exactly **four temporary secrets**, created only in this proposed isolated scope:
bootstrap PG password, migration-role password, app-role password, application
bearer from original `sim2act.cli init-user`. Nonces/session IDs are launch labels,
not credentials. No new model token/OAuth/account, no model token in Docker/envfile.
Bootstrap identity only configures this new cluster; API/Worker never receive it.
Migration/app roles are NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOREPLICATION/
NOBYPASSRLS, not members of each other. Nonce schema belongs to migration; app gets
CONNECT, schemaUSAGE, initialized tablesCRUD and required sequenceUSAGE/SELECT,
no owner/CREATE. Revoke PUBLIC connect/create only inside this temporary cluster.
Use driver-quoted identifiers/literals, explicit same endpoint/schema search_path,
and original CLI migrate with fixed canonical quota. Original CLI init-user
creates a clearly synthetic application identity, not the user's production user.

## Actual API workflow and deliberately limited assertions

Core uses real configured PG Store and original API/independent Worker supervisor;
model mode is explicitly mock/livefalse but it executes no model task and uses
no mock account/approval/SQL adapter. All identities and permissions flow through
original initialization, login and authenticated product APIs. No direct Grant,
Run, ledger, model-source, scope or PASS inserts to fake authority.

1. Normal project/material APIs, CSV sum30 preview, original release approval and
   commit, instance/Run; actual SUCCEEDED30 and same request key/same Run. Save JSON
   result through product response, not synthetic READY or an external write.
2. Normal pending CSV-report cancel -> CANCELLED/no result. Original API refuses
   terminal repeat with exact409 VERSION_CONFLICT; re-read must remain unchanged.
   It is not falsely required to return200 or replay another cancellation.
3. Real role/PID/session READY+ACTIVATE; STOP/EOF requires original STOPPED/clean,
   exact role identities, actual exit0 and both drained streams. New process with
   same origin re-reads material/result/terminal cancel and original Run key.
4. Two complete synthetic TXT/Goal cards; normal server P-A and P-B preparation,
   original exact consent/recover/withdraw APIs. P-B GUI now exists, and the probe
   uses its same typed endpoint with a finite recipe. Mock-mode scopes stay
   unconfigured for LIVE; the probe explicitly checks they cannot become a fixed
   account permit. This verifies production identity/approval code, not model
   entitlement. Revoke original resource grants via normal API and require403.

This implementation does NOT yet run PG fault injection for stolen owner,
heartbeat loss, pause-at-commit or crash recovery. Do not execute old pytest
PG fixtures that create extra roles/fabricated grants under this scope. Those
cases remain NOT_RUN rather than being included in the core result. Preparation
is not successful Source/extraction/Cold execution or full R0 acceptance.

## Budgets and optional live scope

Core: maximum660s from first effect, with90s reserved for cleanup. Pull<=300s;
setup/active operations share the570s active deadline; original service startup
30s and bounded original normal shutdown remain. SQL/connect waits stay bounded.
Read-only preflight is separate (bounded Git checks and a10s import child).
Timeout of a mutating CLI/Docker command does not kill or retry it: retain its
owned handle/PID and report UNKNOWN, keep private scope/evidence.

Optional stage implementation is in `scripts/diagnostics/natural_trial_live_phase.py`.
The supported future execution selection is `--with-live --live-stages generate`
(default Generate-only). It retains the original300-second P-B prepared and
exact-consented contract; no window field/API/UI extension remains. Existing
expiry/fingerprints/keys are never renewed or changed. Lease30 and Run300 stay.

`natural_spec` Generate **requires3 calls without repair**: bound resource.read,
actual spec.check_candidate, then final candidate. The ordinary non-spec two-call
path is not applicable. Fixed original source: goal_applications.py1445,
1752–1769. Strict same-trial P-B Source needs2 model nodes and the finite selected
Cold recipe needs1. Six causal reservations require at least300 seconds between
first and last at1RPM, before any model/compute/preparation time. The original
scope expires strictly300 seconds after preparation. Therefore current complete
P-B path cannot fit; worker heartbeat cannot extend the separate trial expiry,
and a second trial cannot inherit the first trial's exact source/journal identity.
The prior two-call interpretation was caught by independent review and never
executed; MAX_REQUESTS3 now preserves the real checker. Repair remains0.

`--live-stages all` is read-only-inspectable but **refused before any nonce,
container, role, credential or model effect**, even with an otherwise valid plan.
The module also refuses an original300s full pipeline before its first model Run.
Full Source/extraction/Cold routines retain original per-stage authority/journal,
strict extraction and cancellation/expiry guards for protocol coverage, but are
not enabled as an end-to-end product under this preparation contract. No hash,
fixture time, synthetic metadata or longer outer probe clock makes it executable.

Generate-only ceiling480s includes90 handoff/90 cleanup; combined core+Generate
maximum1140s from first effect, not a renewed clock. The contract's original300
seconds is stricter and checked before every request; original Run300 includes
queue/model/tools, max3 calls, <=1024 output/call. Original production caps remain
3/2/2, total7, output7168, envelope64000 per stage/192000 total. The narrower probe
observes Generate<=3/Source<=2/Cold<=1; it never borrows slots, repairs or retries.
Only existing fixed free Intern/model/account is usable, no paid fallback.

Preparer follows original project/material/Goal/preparation/consent API and clean
STOP, then starts original selected Worker. Every accepted Run is matched through
original-key recovery before it is observed/cancellable; Source/Cold additionally
bind full exact request/principal/project/app/instance/release. Cancellation first
withdraws original trial, then rechecks established original identity/current
version, never guessing a lost2xx Run or replaying its POST. Generated candidate is
saved/confirmed through original API, then withdrawal **and original terminal
observation must be confirmed** before successful teardown. Withdrawal unknown:
retain saved candidate/known usage/private PG state/UNKNOWN, no automatic second
withdrawal. Technical candidate saved is not natural goal complete.

Production-journal metadata GET uses original paired namespace, authorization and
approval recovery. Missing or unknown journal does not create/fall back to a
synthetic ledger; false execution/source authority flags remain false. Private
strict extraction (not invoked in Generate-only) uses original extract_pb,
reauthentication, same PG role/schema/endpoint, tighter session SQL waits only,
owned bounded observer thread and SQL/precommit stop guards. Unknown owned effects
are retained, never force-killed/cleaned. Public output is a redacted copy.

Frozen core plan2774c9c9d4f01a0a1aa9283a67a5c886813666774b5844b954ae055f49f54f9a;
Generate-only plan1ce91a4e7a79d136a0643b4f3fff294dc965a09ea3130b90fef39c60d93e5eb8.
Both execution_performed=false; all runtime/native/import/resource checks true,
original manifest false. Actual token is only observed as present, never printed.
Current evidence is `../original-pb-window-controller-20261101/`.

The full-P-B blocker requires an explicit product contract decision, such as a
separate versioned review/execution deadline design (P-A V2 is an existing distinct
precedent, not automatic permission to apply it to P-B). No such product change is
implemented/enabled here. This is separate from original pinned-image401 and the
future concrete isolated-PG-role/credential execution confirmation. No fee consent
is missing, and no unready execution request is made.

## Cleanup and unknown effects

Only after known original API/Worker STOP/exit/dualEOF: verify exact owned image,
container ID and nonce labels; pg_ctl fast/wait30, confirm stopped, docker rm
without force; verify exact labelled bridge has no endpoints then remove it.
Remove only known private credential files after those proofs. Keep redacted
receipts and synthetic result data; image cache is retained unless separately
confirmed unused/new-image cleanup. No docker rm-f, kill, service adoption,
shared-volume deletion or old claim reset. If any step is UNKNOWN, preserve exact
private owner state, known handles/IDs/claims and bounded known-secret-redacted
startup tail; do not replay or infer rollback. Unknown directory never gets a
public-state overwrite. Unconfirmed shutdown never becomes a successful report.

Current controller is source-reviewed and tested against real TEST_ONLY SQLite
API/Worker HTTP, plus pure gate/ownership/auth-diagnostic negatives. It has not
provisioned or connected to PG, and does not claim Windows, live or Release
acceptance. Await only a concrete ready-scope execution confirmation after the
manifest prerequisite is resolved and a fresh exact ready plan is confirmed.
