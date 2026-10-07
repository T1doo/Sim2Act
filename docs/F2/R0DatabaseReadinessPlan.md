# R0 database readiness: isolated draft plan

Base cb3d600a58bb6cba9cb97b6c64ebad4772251451, branch dev/r0-db-readiness-local, /workspace/Sim2Act-r0-db-readiness. This draft is excluded from the root final/full candidate. No merge/push/PG provisioning or execution is authorized here.

Replace Doctor's connection-only claim with a narrow read-only PostgreSQL structural check. A private module takes the already selected application engine and current server metadata (never caller-supplied table/context lists). Only SELECT/catalog queries: connection, effective schema/search-path resolution, metadata relations/columns/declared primary and unique keys, schema USAGE, each SELECT/INSERT/UPDATE/DELETE privilege, current/session role and reachable owner/admin roles, schema CREATE. Unknown dialect/schema/type/role/catalog shape fails closed. No data rows or secrets are read or printed. No DDL/DML, migration, repair, Grant/Principal, initialization, Start or provider work.

Output is closed safe JSON: namespace/version, STRUCTURAL_READY or BLOCKED, fixed reason codes, missing known metadata names/privileges only. Structural PASS never proves RLS/writes, identity, worker, browser, Windows or R0. SQLite cannot establish PostgreSQL qualification. Doctor must suppress DSN/token/raw exception text and exit nonzero on BLOCKED. Existing Start/Status/Stop semantics remain untouched.

Synthetic catalog oracles: healthy least-privilege metadata; unreachable/empty/old/malformed/schema shadow/column/key damage; separately missing CRUD; current/inherited/session admin and owner/schema CREATE; role/catalog unavailable; unknown dialect; credential sentinel never emitted. Enforce SELECT-only statements and unchanged fixture records. SQLite unsupported check uses no connection/DDL. Dedicated local unit/static checks only, no long CPU/full. Real owned PostgreSQL roles/privilege behavior, inherited-owner catalog function semantics and Win11 remain NOT_RUN pending root's separate GO after final full.

Before implementation commit this plan; freeze draft source before final dedicated checks; retain failures. Installation explains existing manual software/config/migration/role/identity steps and that Doctor cannot automatically satisfy them. Product roles remain unchanged.

## Independent draft correction before further execution

Independent static review of b701 found two blockers: Doctor finally.dispose can bypass safe JSON with raw exception; schema CREATE checked only current effective role while login/MEMBER-reachable roles may regain CREATE through RESET/SET ROLE. Preserve b701 evidence. Authorized minimum: catch cleanup failure and append fixed cleanup BLOCKED (never READY); aggregate reachable schema CREATE in existing ROLES set and enforce strict bool. Add sentinel CLI cleanup failure and reachable-CREATE unit negative, retain original41 cases; freeze new source for actual PG preparation. No PG/container or mainline write is authorized yet.

## Ordinary relation scope correction before PG execution

Parent review limits readiness to the physical shape created by the existing explicit Store.initialize: ordinary relation kind r. Partition parent p and view v are unsupported metadata and must return BLOCKED/SCHEMA_MISMATCH. Add the partition synthetic negative while retaining all44 prior unit cases; update the prepared23-case PG oracle so only healthy ordinary40-table least-role schema qualifies. No actual PG startup or execution before root confirms the newly frozen checker source.
