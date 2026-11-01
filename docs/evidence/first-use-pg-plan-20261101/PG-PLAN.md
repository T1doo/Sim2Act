# Isolated PG verification: current executable core proposal, NOT EXECUTED

This revision follows space cleanup and the P-B preparation UI. Product source
is `2ea0ba0fa8e8cc9ea1b4a75e7f0b966bc0fcd291`; executable controller/helper source
is `d1f9b2b531acf039b092a9e5ee11541eb77299fa` (same application bytes). The former
160MiB observation and “PB GUI absent” description are historical, no longer the
current prerequisites. No PG/network/container/image pull/role/credential/model
operation was performed. No execution approval is being requested while the two
current dependency conditions below are false. CI remains 487/900 seconds.

## Read-only observations and blocking conditions

- Current disk: 2,248,253,440 bytes available; >=2GiB PASS. Cgroup memory available
  or inactive/reclaimable: 11,041,394,688 bytes; >=4GiB PASS. No limits, ownership,
  cache settings or unknown processes were changed. Recheck immediately before
  any future effect; these observations are not reserved resources.
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
- Current and child Python imports bind the current src (PASS). Four native
  SOURCE_SHA256 witnesses match the complete original build input groups (PASS).
  Full installed requirements.lock comparison FAILS: certifi2026.10.23 vs2026.7.22;
  Starlette1.10.0 vs1.7.0; iniconfig2.3.1 vs2.3.0; pluggy1.7.0 vs1.6.0;
  pytest9.2.0 vs9.0.2; ruff0.17.3 vs0.15.6; librt/mypy/mypy_extensions/pathspec
  absent. This is not hidden by checking only six direct packages. No dependency
  installation/downgrade/TLS edit was done. Use a separately aligned original
  locked runtime, then re-freeze/check; do not weaken the dependency gate.

Raw official responses, local inventory and all booleans are in
`../pg-execution-preflight-20261101/`. Existing model token is only observed as an
injected boolean, never copied into core env/config/Docker or printed.

## Implemented controller and exact binding

`scripts/diagnostics/isolated_pg_probe.py` is real code, not a placeholder. Default
operation is read-only (including a no-DB child Python import-origin check):

```text
.venv/bin/python scripts/diagnostics/isolated_pg_probe.py --source-sha d1f9b2b531acf039b092a9e5ee11541eb77299fa
```

Observed machine plan hash:
`5752c6967b008e34e03da0fbfcae3568c4cbc3e9602bf69375753cae348a9688`.
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

Optional existing-free-Intern phase is **not implemented/executable by this
controller**, therefore not part of a current confirmation request. Its upper
bounds remain: Generate<=3 requests/<=300s per Run, Source<=2/<=300s, Cold<=2/<=300s,
total<=7 actual calls, <=1024 output/request/<=7168 total, no retries/fallback;
probe ceiling1080s including handoff90 and final cleanup90. Every stage is also
bounded by the original approved absolute expiry (new P-B V1 is one300s window);
the1080s outer ceiling cannot extend it. Seven slots are a maximum, not a promise
to consume all under one-minute spacing or complete every stage in300s. Exact
source/extraction/stage dispatch automation remains a genuine implementation gap.
Existing intern-s2 free-use authorization is valid; no new fee consent is needed.

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
manifest and locked-runtime prerequisites are actually resolved.
