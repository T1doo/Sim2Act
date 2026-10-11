# F2-T07/T08 project overlay → internal executable versions: independent architecture review

Read-only baseline: `a6dd6f401edb3aef997447fb41bd3f39cefd1f58`; branch `dev/project-column-revalidation-20261011`, working tree clean at inspection. Product files unchanged by reviewer. Full source hashes: `architecture-source-sha256.json`. This report describes required safeguards; it is not implementation acceptance. No tests rerun at this architecture stage.

## Concrete reuse mismatch

`project_column_patches.start:199–209` already creates exact fixed CSV read→sum→report worker jobs without composition. `csv_dag.canonical:165–214` freezes stable preview/aggregate/report IDs, complete typed ports and report outputs. The resulting `csv_dag.final_result:534–546` has complete `output` and steps, but no composition `output_by_step`/`output_status`.

The current internal family only understands composition: `csv_dag_instances.closed:46–77`; `source_snapshot:111–146` indexes composition; `apply_input:183–193` changes its aggregate node; `aggregate_result:96` reads output_by_step; `commit_result:425` requires output_status; `validate_binding:390` calls closed again. A safe minimal adapter must recognize the exact existing fixed family and verify all aggregate/report receipt data. Merely allowing closed without adapting the other contracts leaves new/cold instance runs broken. Do not generalize arbitrary or conditional plans.

The page also needs exact fixed-family seal support: `web/csv-dag.js:492` currently matches aggregate input using composition-specific `step_id + '_column'`. Source and derived plan checks in cold history must remain strict. At :613, select options default to the first numeric column; a generated patched version must display its proven patched source column as the selected default rather than accidentally running its original column.

## Atomic group contract

Reuse the lifecycle row/approval/receipt implementation with connection-taking helpers. `csv_dag_instances.prepare_release:197`, `lifecycle.commit_release:247` and `create_instance:352` each currently open their own transaction. Group creation must call transaction helpers inside one outer `store.tx()` and project lock; calling public wrappers independently risks partial group effects.

Freeze and validate the principal/project/target app, original patch key, exact FINISH receipt fingerprint, complete affected membership, the patched phase source run and plan fingerprint for every app, all source receipts/fences, changed/default column, execution family/limits, deterministic per-app intent keys, confirmation fingerprint and expiration. The client cannot choose different source runs or omit members. Baseline runs remain evidence and old-version sources, never substitutes for the required patched source.

Before writing, recompute the finalized project outcome using its existing actual workers and independent CSV checks. Build every release snapshot from the corresponding proven source. Create every approval/release/instance and the exact group receipt+seal within the same transaction; after all inserts, repeat frozen project/outcome/authority/lock/budget and fresh-expiry checks before commit. Any peer failure, capacity issue, cancellation, grant/source/version change or expired confirmation must leave zero partial group approvals/releases/instances/receipts. Rollback also preserves all prior canonical objects, unrelated IDs/content and locks.

A source already finalized under the prior worker deadline can be read later; new group creation should have a new exact confirmation expiry. Do not turn the original worker deadline into permanent release expiration. Original finalization's late worker rejection and cancelled/fenced source rejection remain intact.

## Durable provenance and original-key recovery

Existing release snapshots are reconstructed exactly on cold read (`csv_dag_instances.validate_snapshot:159–164`) and require an independent DAG origin pair (`validate_family:531–548`). Group origin can be a separate immutable pair anchored to the original exact FINISH; if included in snapshot it must be fully reconstructed from durable project/worker evidence. A client field or matching hash alone is insufficient. Both live and cold release/instance reads must reject changed/missing/downgraded group provenance.

Original group key + same exact confirmation must identify exactly one logical group. Changed body under that key conflicts. Unknown POST outcome is recovered through the original-key GET only, with no automatic POST or new request key. Recovery must return the original group IDs and attest each original identity/history while permitting legitimate subsequent instance switch history and appended data. Naively calling `create_instance_tx` again would reject a lawful instance now pointing to B because `create_instance:377–383` compares current release to initial release A; it must not reset the pointer or recreate anything.

## Old versions and A→B→A

New immutable versions and independent instances add rows; do not move an existing instance automatically. Explicit switch stays on `lifecycle.prepare_switch`/`commit_switch` and exact revision/release/data/grant preconditions. Same owner/project/source app/runtime and identical closed family/ports/columns/budget/schema remain mandatory (`csv_dag_instances.validate_switch:313–325`, `lifecycle.switch_target:555–577`). Active or paused/reconciling runs block switch.

A→B→A changes revision monotonically, retains all earlier typed records and real terminal worker proofs, and never reinstates an old approval or run's execution authority. Historical terminal reads may attest the approved old revision (`validate_binding:361–375`); active worker commit must match the current revision and release. Every history transition is checked against an actual consumed switch approval (`validate_instance_history:275–310`). Group recovery must survive this lawful history.

New input remains strictly a frozen numeric column selection (or any expressly designed bounded new-input schema), with no source/resource/workflow override. Showing B's title without running B's actual selected column fails the requirement. Internal namespace, semantic UNKNOWN, owner PENDING and `publishable=false`/formal publication false remain explicit.

## Necessary independent acceptance probes after source freeze

- Two shared-material affected apps plus another-material manually locked app: exact complete group, unchanged unrelated IDs/content/locks, immutable old releases. Actual new worker computation using differing column values; old-version instances still execute. Cold Store + fresh page recover and run new input.
- Same key replay and concurrency produce one group; wrong body/confirmation/source/plan/app/member/default-column/expiry or malformed seal fails. Third peer failure or final authority/source/lock/budget/expiry change rolls back every new group row.
- Unknown commit delivery followed by original-key GET performs zero additional writes/worker acceptance; context navigation ignores late replies. Client rejects malformed successful responses and incomplete group evidence.
- Cancelled or changed source receipt/fence never produces a version. New instance worker cancellation, late output and revocation produce no result data. Same terminal job read validates real receipt/oracle, not cached body.
- A→B→A: revisions and data/history retained; stale approval/live run cannot commit, active run switch rejected; cold read of old terminal proofs remains possible under current authority. Original group GET remains valid while lawful pointer is B.

Executed tests: 0 (intentionally pending implementation freeze). PG, Windows, native browser, original-source upgrade, real model/paid API, full P-A/P-B, deployment and remote CI: NOT RUN.
