# Protected Edge catalog comparison — limited actual PASS

Actual execution commit: `c24ec4cf199d3b75af34d16156a55c7d5b048e60`.
Prepared runner: `2e00d679884f195f02dc32cef9e75d95acb3de4a`.
Before product: `cc4e609539e20d4e3d24a0186650e8f6fe2ce32e`.
After product: `521a47bcb1d6e60e3a11b4fa02552932043f7031`.

- Run: https://github.com/T1doo/Sim2Act/actions/runs/40432483616
- Job: https://github.com/T1doo/Sim2Act/actions/runs/40432483616/job/121953253469
- Job completed success, 2026-10-27T01:25:35Z–01:26:30Z (55s). Existing windows-2025 / Microsoft-signed installed Edge155.0.4283.62; no browser install or added SDK. Actual renderer AppContainer/restricted-token and sandbox switch audits passed before/after reload.

## One actual window, no retry

User confirmation covered one new four-image synthetic read-only window: 180s work including setup, one shared10s cleanup (Node≤4s within it), job≤4min, GET≤100/static≤120/POST0, no model/user-computer/business-write/auto-retry. No G0/Cold2/W5 or production-source changes.

The first empty activation commit `38ec063eb7e834d6a6b4719a9e5b87e4308c4367` created no run: the workflow has a push paths filter. Two readonly run queries returned empty, and the workflow source explained the missing trigger. A non-executable technical window record under scripts was then added; no frozen product/runner file changed. That corrected invocation created this **one** run. The empty commit and window record remain in Git; no consumed run was retried.

## Original evidence and source binding

`job.log` is the UTF-8 byte representation returned by the existing authorized GitHub job-logs interface, retaining BOM/CRLF: **402528B**, SHA256 `ae1c8ea09746fad31829b9d38e249d2d5fd911eac41ff7f17678b76c5d39fcf9`. No refused signed-storage/Library endpoint was retried.

Ten FILE records /108 CHUNK records were independently reassembled with exact contiguous indices, byte lengths and SHA256; each matches the archived original. Includes four PNGs, launch contract, native inventory, result, browser, complete-store hashes and original prepared catalog contract. `emitted-files.json` is the original per-file metadata. `run.json` is the actual completed GitHub run response. `supervisor.json` preserves the exact original log line plus its parsed receipt. Other verification summaries are derived and do not replace these originals.

The prepared198-file manifest matches the current files and Git objects at both prepared and execution commits (independent review). Native inventory emits **28**, not198, file hashes; all28 LF hashes match execution Git, with27 native raw hashes explained exactly by Windows CRLF and1 exact raw match. Native `source_after_matches=true` records the runner's repeated full frozen-contract check. The prepared catalog contract is returned unchanged (`SOURCE_PREPARED_NOT_RUN/execution_authorized=false`); it is historical preparation input, not the actual execution result. Actual execution is established by this run/result/browser/supervisor chain.

## Actual requests, unchanged facts and cleanup

Browser: **18 business GET,54 static GET,0POST,0blocked,0pageErrors**,72 requests completed with200. Sixteen business GETs are explicitly labelled synthetic presentation-directory responses; only two are original authenticated `/api/capabilities` responses. Thus server counts are **2 business GET,54 static GET,0POST/blocked**. Do not merge these as additional requests or call synthetic directories actual backend reads. Browser records no `/health` request.

All four frames have the same original metadata: intern-s2 / MOCK / MOCK_ENGINEERING; resource.read, data.aggregate_csv, artifact.save_text; code execution DISABLED. Model/new Worker/new Source/new Extract counters are0. Source and Extract snapshots each cover55 tables and are unchanged before/after. SQL observed only SELECT5999 and BEGIN12; no DML/DDL. Original sidecars, cases and deadlines are checked by the existing sealed-fixture path. Fixtures use an explicit synthetic business clock; this is not real-model/G0 timing evidence.

Cleanup: API stopped=true, AnyIO/browser descendants/installer-supervisor survivors and errors all empty, Node exit0, fixture_deleted/within_deadline=true. The separate exact-handle PowerShell supervisor records process_exited=true, exit0, timed_out/forced_tree_stop=false, owned_directory_deleted=true. Its finished_ms1793064386380 is before shared deadline1793064393170. This confirms deletion of this new root, including private npm dependencies/temp/profile tree, for this successful run; it is not a whole-host residual-files audit. No unknown process/lock was touched.

## Actual pixels and limits

Root and independent catalog_native_review each opened all four original PNGs. Sizes: before/after1366×900 and390×844. The connection area is readable, no horizontal overflow/overlap/text clipping. The new view separates model name, mode and server status, retains explicit engineering-simulation/non-acceptance wording, shows the read-only refresh action and a closed original-metadata disclosure. No fake successful model connection.

Important comparison boundary: before scrollY=0/0; after wide54/narrow266 because the adapter scrolls the connection section into view. The after connection panel is shown, but the global header and narrow-screen resources title have scrolled out. These are same-state section comparisons, **not identical-position/full-page pixel acceptance**. Before header still says “正在检查后台”; global health readiness is unproved. Disclosure contents are compared via DOM metadata, not expanded-pixel coverage. No claim of native retry/error/empty/LIVE/keyboard/FPS acceptance, other resource tabs, overall frontend completion, real provider/PG/production data, or G0 resolution.

Independent review: limited actual-evidence/pixel ACK, no blocker in this narrow scope. Reviewer performed readonly hash/Git-object checks and actual image viewing only; no browser launch, test rerun, network or CI. See review.md. This single window is consumed; no further execution is implied.
