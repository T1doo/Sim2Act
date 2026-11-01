# Configured desktop lifecycle

The installed `sim2act.desktop_service --supervise --control-stdin` entry now owns
separate original API and Worker processes. The native host selects it with
`Sim2Act.exe --config <existing-private.env>` and an optional
`--spec-selection <existing-five-field-selection.json>`. It retains the original
synthetic entry when no configuration is selected. These switches do not create
an account, approval, credential, schema, migration, grant or model entitlement.

This source integration is **not a new accepted Windows package**. The frozen
042ab21c portable preview omits psycopg and predates this supervisor; it cannot
be made into a configured PostgreSQL desktop by passing these switches. A new
same-version build with the original PostgreSQL dependencies and redistribution
materials, actual PostgreSQL configuration/approved selection, and native
Windows acceptance remain required. No Release qualification changes here.

The source maintainer equivalent is `scripts/manage.py desktop --control-stdin`
with its existing explicit `--config` / `--spec-selection` arguments. Its stdin
must be the owning parent's private pipe; a terminal is rejected. The installed
module and source script share the original configuration/selection checks.
They do not load a discovered dotenv file. Actual loopback access still needs
the existing application principal's normal login; no public synthetic token is
issued by the configured path.

The supervisor listens for parent EOF/STOP before database preflight, and checks
one startup deadline before role creation/activation. PostgreSQL diagnostics
retain bounded driver/statement waits and check stop/deadline before subsequent
SQL. A preflight thread that does not actually finish is reported unconfirmed,
with the claim preserved. Preflight catalog readiness alone is never R0, model
or current Worker readiness.

Each role receipt binds the protocol, launch session, backend, role and actual
PID. API READY follows the actual Uvicorn socket/start; Worker READY follows its
own initialization and heartbeat. Worker dispatch remains paused until both
roles are ready and it receives ACTIVATE. Global READY requires that exact
Worker's activation receipt. Public `/health` cannot supply this identity.

Persistent origin identity includes the explicit connection endpoint/user/database
and complete query options, including search_path; URL passwords are excluded.
Indirect service/credential query defaults and nonempty inherited PG variables
are rejected rather than resolved differently by parent and children. The
configured WebView profile is separate from the synthetic profile and binds its
first navigation to the validated database binding, data directory and origin.
A changed or unknown binding preserves prior requests/profile and stops instead
of silently reusing or clearing localStorage.

Window close or parent EOF requests ordinary owned-service shutdown. It is not
user Run cancellation. User cancellation remains the original authenticated API
command and version/fence path. The Worker retains the original rolling lease,
absolute deadline, dynamic authorization/revocation and final commit protection.
Every business heartbeat branch registers the actual thread handle; its old
join budget is unchanged, and a still-running sender prevents clean shutdown.
API shutdown must return after requests/connections drain. Clean STOPPED also
requires both matching role receipts, actual exit 0, stdout and stderr EOF and
finished readers. No process terminate/kill, PID-only inference, forced request
cancellation, automatic claim reset or database deletion is added.

Cloud integration uses an explicitly TEST_ONLY_SQLITE fixture with real separate
API/Worker processes and loopback HTTP. It covers sum/save, original-key reuse,
user cancellation, normal STOP/EOF, same-origin new-process readback, a competing
controller, a wrong Worker PID, a blocked actual app heartbeat and an undrained
preflight. Existing real-store cancellation/commit/lease negative tests are
separate. None of these substitute for configured PostgreSQL, Windows native,
P-A/P-B model execution or full R0 acceptance.

## Same-version build inputs

`package_windows_portable.py --configured-runtime` now mechanically includes both
original pinned psycopg 3.3.3 archives, all their supplied license files, original
wheel copies for provenance/replacement, and the configured launcher. It no longer
relies on the old SQLite dependency image for PostgreSQL. PG-RUNTIME-INPUTS.json
keeps redistribution review explicitly unevaluated and the project license
unchanged; this is build integration, not a publication/compliance decision.

The local source builder can use `--reuse-windows-native-wheel` only with the
exact previously imported 042ab21c wheel and its frozen actual-import report.
It verifies the unchanged setup recipe and every complete native input group,
original bytes, source witness and CP312 Windows PE identity, then assembles the
current pure Python inventory with those unchanged PE files and regenerates the
wheel RECORD. The manifest explicitly records REUSED_UNCHANGED_NATIVE and does
not claim that current Python executed on Windows. Any changed native dependency
requires recompilation; a Linux binary cannot be relabelled as Windows.

The existing Windows full-package script is prepared to include these original
PG drivers and to check actual private-runtime binary imports on its next
explicitly authorized run. No workflow trigger or budget was expanded here.

## Explicit first-use initialization and existing approvals

The installed CLI now accepts an explicitly selected existing private config for
its original initialization commands only:

```text
python -m sim2act.cli migrate --config <existing-migration.env>
python -m sim2act.cli init-user --config <existing-app.env> --name <local-user-name>
```

Use the separate original migration/app roles. These are deliberate mutating
commands, not Doctor or automatic desktop startup. They do not create a database
or SQL role. `init-user` prints its new application bearer once: run it only for
a genuinely new identity and privately retain the result; do not run again for
an existing login or include its output in shared logs. On failed initialization,
retain private configuration and database state; effects may be unknown.

For an already approved P-A or P-B scope, enter its original trial and approval
keys in “正式连接与启动选择”, read the existing approval, then recheck/export.
The original five-field selection contains no credentials or authority. An old
unconfigured-account scope cannot be silently rebound by this reader. Fresh
seven-slot preparation in this panel remains P-A only; P-B still needs its
original typed contract, recipe, source chain and explicit approval procedure.
