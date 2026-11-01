# Isolated PostgreSQL probe: frozen proposal, NOT EXECUTED

This file requests no implicit permission. No database, role, password, token,
container or image was created/pulled for this proposal. Parent coordination must
confirm the concrete setup below before execution. Existing free Intern consent
is already valid; it is not the outstanding condition. CI remains 487/900 seconds;
this plan grants no additional CI allocation. It uses the existing managed cloud
machine, never the user's computer or a training/shared production database.

## Prerequisites and pinned inputs

- Freeze a clean source SHA plus this plan's SHA256 and exact dependency inventory.
  Use the existing locked Python dependencies, psycopg/psycopg-binary 3.3.3, four
  existing native modules. No new package versions or mutable dependency fallback.
- Sole historical image input:
  `postgres@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3`.
  Repository startup evidence labels it `postgres:17.11`, not version 16. No
  current registry/platform validation or pull has been performed. At approved
  setup verify registry digest, linux/amd64 manifest, image identity, postgres
  UID/GID 999, server SQL version and supplied licenses; mismatch stops without
  changing image/tag, running as root or obtaining an alternative image.
- Require at least 2 GiB free writable disk before vfs image extraction and 4 GiB
  available/reclaimable cgroup memory after accounting for kernel/file cache.
  Do not kill unknown processes, delete unknown evidence, drop global caches or
  change cgroup limits to meet these conditions. Current disk is only ~160 MiB;
  this prerequisite FAILS. There is no cached postgres image or existing PG URL.
- Use only the currently allocated managed Docker daemon. No new VM, hosted DB,
  paid runner, purchased storage or paid model fallback is requested. This avoids
  new paid provisioning calls; it is not a claim about provider-internal billing.

## Concrete setup needing confirmation

One new nonce-labelled container and one private directory under
`/workspace/scratch/sim2act-pg-probe-<nonce>` (0700, files0600). Reject existing
paths/names/volumes. Create one dedicated ordinary Docker bridge labelled with the same nonce, and
pass `--network sim2act-pg-probe-$nonce` explicitly. This network creation/removal
is part of the concrete confirmation scope. No privileged mode,
host networking, host socket mount, system service/firewall/ACL changes or public
listener. Publish only `127.0.0.1:<assigned-port>:5432`; API is also loopback-only.

After confirming the pinned image UID, the intended container shape is:

```sh
docker --host=unix:///var/run/docker.sock network create --driver bridge \
  --label "sim2act.probe=$nonce" "sim2act-pg-probe-$nonce"
docker --host=unix:///var/run/docker.sock run --detach \
  --name "sim2act-pg-probe-$nonce" --label "sim2act.probe=$nonce" \
  --network "sim2act-pg-probe-$nonce" \
  --user 999:999 --read-only --cap-drop ALL --security-opt no-new-privileges \
  --memory 512m --cpus 1 --pids-limit 128 \
  --tmpfs /var/lib/postgresql/data:rw,uid=999,gid=999,mode=0700,size=512m \
  --tmpfs /var/run/postgresql:rw,uid=999,gid=999,mode=0700,size=16m \
  --tmpfs /tmp:rw,uid=999,gid=999,mode=0700,size=32m \
  --publish 127.0.0.1::5432 --env-file "$private_dir/bootstrap.env" \
  postgres@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3 \
  -c max_connections=16 -c shared_buffers=32MB -c max_wal_size=64MB \
  -c min_wal_size=32MB -c password_encryption=scram-sha-256
```

This is a proposed command, NOT an executed one. `nonce/private_dir` must be
validated by a bounded controller; no command is run from user strings. Private
env contains only new ephemeral PG bootstrap settings: PGDATA, POSTGRES_DB,
POSTGRES_USER, POSTGRES_PASSWORD and INITDB args enabling SCRAM for local/host
connections. Never copy the existing Intern token into Docker, this file or logs.
Do not use trust authentication. Bootstrap password is visible in the container's
private configuration until removal: this is part of the requested narrow scope.

Create, only inside that new cluster:

1. Bootstrap superuser solely for cluster/schema/role preparation. Never give its
   URL to API or Worker. Two temporary SQL login roles, migration and application,
   both NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; passwords
   supplied through driver-quoted literals/private files, never shell args/logs.
2. Database connect and a nonce schema: migration owns only that schema; revoke
   PUBLIC schema CREATE/database CONNECT, explicitly grant role CONNECT. Set
   explicit URL `options=-csearch_path=<nonce-schema>` consistently for migration,
   app and supervisor identity. Do not change a shared/public schema.
3. Run original explicit `python -m sim2act.cli migrate --config migration.env`
   with the canonical fixed Intern quota subject. Then grant app schema USAGE
   and SELECT/INSERT/UPDATE/DELETE on the actual initialized tables only; grant
   sequence usage only for verified required sequences. App is not owner, member
   of migration, or granted CREATE. Verify role/catalog privileges using app login.
4. Original explicit `python -m sim2act.cli init-user --config app.env --name
   'Isolated synthetic PG probe'` creates one synthetic application identity and
   its bearer, privately captured once. This is the fourth temporary secret
   (bootstrap, migration, app DB passwords, application bearer). It is NOT a
   model account or the user's production identity. Never commit/output them.

Readiness requires mapped-loopback TCP **actual SQL** (`SELECT version(),
current_user,current_database()`) after final server startup, not socket
pg_isready. Preserve redacted startup logs. Historical socket-only readiness was
misleading; historical exact failure root cause remains unknown. Exit137 followed
explicit removal and is not proof of OOM. Failure stops this attempt; no blind
restart/root/security fallback. Validate actual SCRAM by refusing wrong password.

## Normal product execution and assertions

Core phase has **zero model calls**. Use the real configured production PG Store
and independent API/Worker supervisor, production settings and real transactions;
no TEST_ONLY_SQLITE, mock authority, resolver injection or direct Grant inserts.
The data and account are synthetic, but they use production identity/approval
code. Register no alternate provider/account. All HTTP uses the real bearer.

- Login; create project via normal POST /api/projects (its original code grants
  project save authority); save CSV `amount\n10\n20\n` via normal material route
  (original code grants resource read/aggregate). Use ordinary zero-model CSV preview draft
  (`POST /api/projects/{pid}/apps/csv-preview`, name/resource_id/goal), internal
  release approval (expected_draft_fingerprint/sample_input), approval commit,
  release instance and instance Run APIs, sum30 result, original-key repeat and JSON
  export; verify authorization and version boundaries. Do not insert fabricated
  Grant, approval, usage ledger, Run, model source or PASS rows into the database.
- Real API/Worker READY plus role/PID/session and ACTIVATE; no /health-only proof.
  STOP/EOF must yield both actual role receipts, exit0, drained streams and sender
  handles. Restart from the same config/origin; authenticate and re-read original
  result, Run, material and original-key identity without replay.
- User cancellation through normal API reaches a valid terminal outcome with
  committed result absent on cancellation, complete rollback, repeated cancel
  idempotent. Revoke original grants via authenticated revoke API; assert current
  read/new work refusal. Exercise lease heartbeat loss/old owner/absolute deadline
  and final-commit fence against this isolated PG schema, no patched PASS.
  Existing `tests/conftest.py env/runtime_role` provisions extra test roles and
  direct synthetic fixture rows: do NOT run it under this narrower scope or
  claim its fixture authority as normal production approval. The core controller
  must use only the above pre-created app identity, roles and normal API routes;
  fault checks requiring additional fixture authority stay NOT_RUN until a
  reviewed, scope-matching harness is available. Record exact subset, not all R0 passed.

Optional following phase, only after core succeeds and parent confirms this
bounded phase: **at most seven actual requests TOTAL**, no retry or paid fallback,
existing fixed intern-s2 endpoint/token precedence, explicit live flags. Original
seven-slot PB contract (Generate <=3, Source <=2, Cold <=2), TrialCaps lease30 and
Run300; never SQLiteSettlementCaps120. Output <=1024/request, <=7168 total; input
and remaining budget no larger than the original approved contract. Abort on
first unknown usage/result or exhausted request quota without changing key.
Use two synthetic short English TXT files (`The river is blue.` / `The tree is
green.`), complete Goals and edited Recipe frozen before approval. Prepare facts
from normal authorized product routes/current SQL; submit original typed PB
approval through its real HTTP endpoint and recheck exact software/content/auth
fingerprints. No direct scope/Grant rows. This PB pipeline includes Generate and
Source, not a separate full P-A Cold acceptance. Fresh PB seven-slot preparation
GUI is absent: identify this as production-API synthetic acceptance, **not full
ordinary GUI, Win11 or R0 acceptance**. Any unsatisfied source/recipe/current
identity condition stops that phase; fee consent does not waive these checks.

## Bounded time, shutdown and residue

Local core <=660s: pull/verify300, setup60, assertions210, reserved cleanup90.
Decide optional PB scope before setup: core-only tears down after core; when PB
is separately confirmed, retain this same container/schema between phases, run
core STOP/reopen without database destruction, then PB, then one final teardown.
Never destroy tmpfs between core and PB or reuse an unreviewed replacement DB.
Optional PB
<=1080s including three Runs at most300 each, handoffs90 and cleanup90. Overall
wall deadline <=1800s including cleanup, no repeat attempt. Model timeouts and
absolute deadlines retain original values. These are probe budgets, not changes
to worker leases or permission to consume CI.

Normal cleanup: STOP owned supervisor; verify real STOPPED/exit/EOF, close its PG
connections. In the exact labelled container run postgres `pg_ctl -m fast -w -t30
stop`; verify exact container ID/digest/nonce and stopped state, then `docker rm`
without force. Verify the exact nonce network has no remaining endpoints, then
remove only that owned network without force. tmpfs destroys database/roles/password
hashes. Remove private
credential/config files only after known shutdown; keep redacted log/evidence and
manifest. No docker rm-f, forced kill, shared-volume deletion or unknown PID lock
reset. If live result/shutdown remains UNKNOWN, preserve exact private owner
state/container identity and report it for explicit cleanup rather than deleting
evidence or replaying an uncertain request. Image cache retention/removal must be
reported; remove only this newly pulled image if unused and separately confirmed.

Acceptance report must distinguish Linux PG / model0 or actual calls / API path /
Windows not run, core vs optional PB, and every failed/not-run case. This plan is
not a test result, a production migration, an image license approval or a Release.
