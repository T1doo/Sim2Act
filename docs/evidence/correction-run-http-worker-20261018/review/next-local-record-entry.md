# Next concrete user entry gap

The existing typed local-record capability is implemented. The missing link is project task history → that record Run's typed result, not another record executor or a new business contract.

`api.py:317` metadata task listing returns only owned/project-scoped `id/status/created_at`, fixed `goal_summary`, and `mode=UNKNOWN`; it includes local-record Runs without a family discriminator. `web/app.js:172` opens these through `showRun(id)` (`:404`), whose `readRunDetail` (`:412`) calls ordinary `/api/runs/{rid}`. `db.py:1405` correctly invokes `reject_record_legacy` before protected ordinary data. `local_record_apps.py:209` explicitly rejects that family with UNSUPPORTED_CAPABILITY. Consequently the project list exposes a real record task that its selected detail route cannot open.

Keep that rejection. The typed path already exists:

- `local_record_apps.scope_job(store,c,user,rid,iid=None)` (`:481`) resolves owner-bound scalar Run/AppRun/instance metadata, calls `instance_header` for current authorization, and validates the exact RUN_SCOPE double seal. Only this helper permits omitted iid.
- `inspect_job(store,user,iid,rid,limits)` (`:876`) requires iid and delegates to the above scope, current projection and accepted binding. Its exact route is GET `/api/internal/record-instances/{iid}/runs/{rid}` (`:991`). A minimal family locator must explicitly delegate through owned typed scope, rather than relax `Store.inspect` or invent an INTERNAL_APPRUN namespace.
- `openLocalRecordsApp(app,generation,selectionCurrent=()=>true)` (`web/local-records.js:314`) validates the app and reads fresh delivery.
- `localRecordsSelectInstance(v,iid)` (`:220`) clears old private selection and reads the current projection.
- Set the known Run selection, then `localRecordsReadRun(v)` (`:247`). It invokes the existing fresh instance+Run read and `localRecordsRunValue` checks exact instance/Release/AppRun, immutable event, event hash and VERIFIED receipt against the projected history.

Use `showApp`'s existing LOCAL_RECORDS branch (`app.js:688`), not `engineering/showInternalInstance`. For an explicit project-history button, capture account/connection/project/origin Run selection/workspace/app-generation; preserve them across each await and release any temporary cross-workspace fence after handoff. The record controller already fences its own view, connection, workspace, app, edits, instance selection and read generation. An interrupted or late handoff must not change a newer app/instance/Run, nor submit a write.

Minimal actual qualification fixture: `tests/test_local_record_apps.py:128` `ready`, `:155` `create_body`, `:186` `execute` creates one real CREATE through the existing NoModel Worker (`:44`). Reuse `test_local_record_apps_ui.py`'s TestClient IPC and `local_record_apps_ui.cjs` page boot. After the fixture, project history → exact typed Run/current record/history should use GET only, preserve all table rows, and create no additional Worker/model/Grant. Do not repeat the old two CREATE + DONE flow or weaken legacy routes.

## Separate deferred control-entry defect

The accepted correction's new button first reads the full instance. Material revocation makes `showInternalInstance` catch → `invalidateInternalContent` (`internal.js:574`), which clears private instance/Run and advances generations. The button stops before `showInternalRun`. The latter's existing resource-denial fallback to `control-status` (`:332`) requires a current nonempty instance at entry and is therefore unreachable on this path.

The backend owner-only metadata API is already present. `internal_api.scope_run:100` verifies owner/project and scalar instance association before any accepted body, then uses the existing natural control scope; `:511` returns only id/instance/status/version/cancel intent with `content_access=false`. No separate visible correction-child metadata stop entry was found. A future fix needs an explicit metadata-only control entry using known iid/rid and current identity/project fences. It must not reinstate a cached private instance, restore content authorization or widen the one-layer correction contract. This is recorded separately and is not mixed into the record-history slice.
