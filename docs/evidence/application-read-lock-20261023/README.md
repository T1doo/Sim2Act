# Current application read lock

Base: `79861f9acbda246f0ab275a34b0019a4734b4cae`. Original F2-T09 saved instance/run recovery and explicit same-key acceptance recovery remain the product scope; see [InternalEntry](../../F2/InternalEntry.md). This is an interaction repair, not a new application/recovery protocol.

An in-flight instance read previously disabled only refresh, column and submit. The original UNKNOWN recovery action remained available; a nested `applicationUseButtons` call could also release the three controls before the read finished. The repair binds the local control lock to the read generation. Submit/recover and refresh handlers also respect it. A completed request releases only its own object lock; only the original current-context check may update its controls. Original current authorization, accepted binding, readback validation and request key are unchanged.

Independent review found an intermediate lifetime defect: a workspace change invalidates the read but retains the same application view. If there is no selected Run, returning did not resume that read. The final implementation releases the invalidated request's own lock and extends the existing workspace-return read hook to an unfinished loading state. Return performs a fresh GET through the original controller, never a POST or reuse of the invalidated result. Both completion-before-return and completion-after-return are covered.

## Actual verification

- `final-red.log`: final test script against the two original product files fails on the available recovery control during the pending read. `red.log` preserves the first reproduction.
- `green.json`: actual `use.js` and `csv-owner.js` in JSDOM, 17 assertions over finite deferred synthetic responses, 11 adapter GETs, 0 actual HTTP, 0 POST and 0 model calls. Includes complete current success, current failure, nested reconciliation, overlapping reads, UNKNOWN body/key preservation, actor replacement and both workspace-return orders. These are assertions, not 17 independent user scenarios or native pixels.
- `compatibility.json`: the existing deferred read-feedback script passes its seven assertions, separately using two synthetic adapter calls. It is not added to the new script's request count.
- `harness-first.log`: retained first harness failure, caused by resolving a second cross-realm promise before its continuation registered. Final test yields a Node event-loop turn between the controlled successful responses. This was not a product or network failure.
- `node --check` for both edited product scripts and the new test, and `git diff --check`, passed. Local test process exits normally, closes JSDOM and clears its five-second watchdog; there is no API/browser/Worker child to clean up.

No new native rendering, CI, model, database, sidecar or source fixture execution. The separate desktop-column CSS patch remains **unapplied and visually unverified**. Prior screenshots sign their original runtime, not these new control-lifetime changes.

## Existing rendering route and exact missing condition

The successful renderer was the repository's existing GitHub Actions `source-review-ui-once` job on `windows-2025`, invoking `scripts/WindowsExtractCompletionUI.ps1 -WorkspaceVisual`, with installed protected Edge (`chromiumSandbox:true`, CSP unchanged). The previous [run/job](https://github.com/T1doo/Sim2Act/actions/runs/39946763547/job/120391205511#step:5:25) executed `8670b863c33732dec2d4552bb8061cebb680ce03` and its own processes/fixtures were cleaned up. That session is not available for reuse.

The current instruction prohibits another CI. No new CI request was attempted or denied. Local Chromium's previously established sandbox prerequisite remains unmet; this repair does not change its owner, flags or security configuration. Historical Library 401 and signed-storage refusal are not retried.

The smallest route requiring no new renderer/workflow infrastructure is one fresh exact-SHA invocation of the existing protected visual job: total work 180 seconds from setup, shared cleanup 10 seconds; at most 100 business GET, 120 static GET, 0 business POST, 10 PNG; unchanged sealed Source/Extract/CSV stores and drift/cleanup guards. Existing driver captures wide/narrow saved results and pending/error/recovery states. It returns original PNG/JSON via the normal authorized job-logs interface and the repository evidence folder. This is a proposal only; it has **not** been triggered. A four-frame-only window would first require a reviewed narrowing of the existing driver, rather than claiming such an entry already exists. No new account, credential, permission, model or user computer is needed for this route.
