# Typed local-record project-history entry: initial source review

Source-only review; no Git/auth/network, product/test/Worker/model execution, DB read/hash or private holdout access. Parent identifies baseline `2ca34f24`; no Git query was performed. Initial file hashes are preserved separately. No current test outcome is inferred before author closure.

The backend dispatch is narrow: `require_run_owner` precedes family discovery; a recognized local-record family routes to a dedicated full typed read. `inspect_project_run` and `_inspect_job` share the caller transaction, rechecking typed instance scope, projection and accepted binding and comparing rid/iid/Release/AppRun before adding owner/project/app navigation metadata. Ordinary Store.inspect and command legacy rejection remain intact. No new executor, Grant, business table, write endpoint or caller-selected permission is introduced.

The UI returns from the typed namespace branch before unresolved-attempt/ordinary-command logic. Explicit navigation uses the typed app controller, fresh instance projection, exact Run membership and existing receipt/event readback. Its temporary scope tracks connection/project/workspace/user Run selection/app generation and typed view identity; newer instance or read selection stops follow-up without clearing the newer view. The finally clause releases only its own temporary fence. Background reads of the same Run do not own the human navigation scope.

## Initial P2: delayed error misses the typed success fence

`readRunDetail` captures `readWorkspace` and `readConnection`, but its common `current()` does not check either. The new typed successful response adds them only in `typedCurrent()`. A delayed 403 or transport failure instead enters the common catch, where the old predicate can still be true after a workspace exit/return with the same selected Run. It then clears the current result, sets activeRun=null and paints the stale error. The existing held typed detail scenario releases an actual 200, so it does not exercise this asymmetry.

Minimal correction: require the captured workspace and connection in the catch before any DOM/activeRun change, or strengthen the common current predicate. Keep the navigation's distinct user-selection scope, so same-Run background generations do not poison an already-started handoff. This is a source finding, not a dynamically reproduced failure; it remains open until the final source is re-reviewed.

The proposed two targeted nodes are relevant: owner typed GET + foreign/revoked READ barriers + preserved legacy rejection, and actual full-page project-history navigation from one NoModel CREATE fixture with no page POST/Worker and full-table equality. Additional coverage should stay within that entry; no old model or recovery matrix is needed.
