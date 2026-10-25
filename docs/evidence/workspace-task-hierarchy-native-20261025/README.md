# Warm task hierarchy — actual protected Edge comparison

One new native window completed successfully, with 10 original PNGs inspected individually. This closes the screenshot gap for product `384e332cbdfaa12f0dc7b70c16f8db49710a67de`, not the entire frontend, G0 or owner semantics.

- Execution: `e9886a55ac23f753e420301d789adc372a284351`.
- [Original run](https://github.com/T1doo/Sim2Act/actions/runs/40166777639), [job and original logs](https://github.com/T1doo/Sim2Act/actions/runs/40166777639/job/121089342574), 2026-10-25 05:47:11–05:48:40 UTC / 13:47:11–13:48:40 Beijing.
- Windows Server 2025; installed Microsoft-signed Edge `155.0.4283.62`; sandbox and actual restricted renderer token checks passed. No browser installation or local sandbox retry.
- Before: four exact assets from `ef678365900f079971928f1a4631da0e6256cd82`. After: original server assets matching product384. Same sealed synthetic Source Run, output and four independent states compare exactly. Baseline assets retain original HTTP response/CSP headers. No controller or clock replacement in the browser.

## Actual visual findings

The previous concatenated task log is now a goal heading, separately labelled execution state, submitted mode, acceptance time and short identifier. UNKNOWN is not styled or described as success. The result panel has a clearer four-part status strip; semantic status, independent review, owner acceptance and publication remain separate.

Both 1366×900 and 390×844 main views retain their task/result content with no horizontal overflow or hidden-element leak. The two main-view pairs share scrollY=0. Task-area frames use native scroll-into-view; their scroll positions differ (wide 0→41, narrow 3017→3064), so they are not identical-scroll pixel diffs. No clipped control or overlapping text was observed in the ten frames.

| Actual screen | Before | After |
| --- | --- | --- |
| Wide main workspace | [PNG](native/before-projects-wide.png) | [PNG](native/after-projects-wide.png) |
| Narrow main workspace | [PNG](native/before-projects-narrow.png) | [PNG](native/after-projects-narrow.png) |
| Wide task area | [PNG](native/before-tasks-wide.png) | [PNG](native/after-tasks-wide.png) |
| Narrow task area | [PNG](native/before-tasks-narrow.png) | [PNG](native/after-tasks-narrow.png) |

Additional actual frames: [keyboard focus / unsent synthetic draft](native/task-focus-wide.png), [narrow reduced-motion form](native/task-reduced-narrow.png).

Native Enter opened the existing details; Tab entered the goal with visible focus. The original empty-CSV prepare gate remained disabled (DOM observation, not a dedicated disabled-control PNG). With real browser reduced-motion emulation, the disclosure transition changed from 0.16s to 0s and animation was none, while opening/closing remained functional. These are interaction/computed-style observations, not frame-rate or device smoothness measurements. The synthetic draft was never submitted.

## Execution and cleanup

- 25 recorded checks in one browser execution, not 25 separate scenarios.
- Browser and server each: 54 business GET, 54 static GET, 0 POST, 0 blocked; pageErrors empty. The recorded request span was 10.916s; whole GitHub job 89s, including setup and post steps.
- Original bounds retained: 180s work including setup, shared 10s cleanup / Node at most4s, GET≤100/static≤120/POST0, PNG≤10. No retry.
- 0 model, new Worker, new Source or new Extract actions. No CSV API child started. Only Source was browsed; the pre-existing paired Extract fixture was prepared and monitored, not exercised as a UI flow.
- Source and Extract each have all55 table vectors unchanged. Only SELECT7403 / BEGIN69 were observed, no DML/DDL. Original sidecar bytes and stored deadlines passed the unchanged coordinator checks. Synthetic historical business clock; not real-clock G0.
- API stopped, Node exit0, AnyIO/browser/installer residual lists and errors empty; fixture deleted within cleanup deadline. Outer supervisor: process exited0, no timeout/forced tree stop, owned dependency directory deleted.
- `receipts=[]`: this window did not replay completion/review commands or attest receipt recovery.

## Evidence and version binding

`archive.json` records 15 decoded files and exact lengths/hashes, reconstructed from the normal authorized GitHub job-log interface. Raw log: **1,145,432 bytes**, SHA256 `c5b80b10bf1fb7e5c21f40a66b5591b8cafa6ec4e7559d3004a944d4291ed64b`, preserved losslessly as `job-121089342574.log.gz` (includes UTF-8 BOM and CRLF). No denied signed-storage or Library endpoint was retried.

18/18 pre-run frozen file hashes and30/30 runtime normalized-LF source hashes match current files. Ten PNG hashes/dimensions match browser output. `plan.json` predates execution; `preflight.json` preserves the local scanner's initial false-positive incomplete f-string path and corrected static-only check. The earlier four Node suites belong to the product384 slice and were not rerun here.

No product file changed during or after this native execution. Loading/error flows outside this slice, other workspaces, touch devices, FPS, PostgreSQL, real provider, G0/Cold2/W5 and overall F2/R0 are not newly verified.
