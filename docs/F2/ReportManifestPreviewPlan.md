# Canonical bounded Report Manifest private-preview bridge

Published baseline e828c066ec63689fe5de5d66f650eda33c0086e8, new isolated tree
/workspace/Sim2Act-report-manifest-preview, branch bounded-report-manifest-preview.
Named source 6d42966103f072f16b6234e9948b8fc614ac2767 was normally merged without conflicts;
combined before-development source b38185e88cf643906b0736bd7d9bcca232a3b1a3. Old tree remains intact.

## Existing result and concrete next gap

Named PREVIEW persists an immutable sealed finite extraction wrapper and executes new typed
Scenarios from a fresh page. It is deliberately excluded from AppManifest/compile_preview/generic
App catalog. V5 product §4 P-B (119/125), §5.3/5.4 and AT10 call for the same ActionSpec/AppManifest
contract and actual new-input execution. This slice bridges that concrete compiler/use gap only;
it does not establish full P-B, arbitrary language generation, AppRelease or AppInstance support.

## Closed minimum implementation

POST /api/projects/{pid}/conditional-apps/{aid}/manifest-preview accepts only
expected_app_fingerprint and request_key. Server rechecks source/check/extraction dual seals,
current named wrapper and target hash/authorization, then constructs a canonical ActionSpec and
AppManifest from that fixed program. Persist in existing app_drafts/task_extractions only, with
an independent closed family marker. No client manifest, candidate, report, gold or model wire.

Common compile_preview/preflight recognizes exactly bounded_report / intern.conditional_report,
resource.read only, fixed typed Scenario wiring, registered Report output schema and source checker.
Only nullable boolean/integer is added to the explicit schema subset because UNKNOWN Scenario
facts require null; other negative schema/coercion tests stay intact. New runtime identity mode is
user_and_project_intersection, explicitly shared existing project runtime. Declare source and target
read ceilings; current caller/runtime/resource rights are rechecked. No Principal/Grant or table/DDL.

Generic App catalog/inspect returns actual canonical candidate and compiler receipt. Scoped
GET /api/projects/{pid}/apps/{aid}, POST .../previews (typed input + expected_candidate_fingerprint
+ request_key) and history produce/retrieve real asynchronous protocol cold Runs using the same
trusted worker/Attempt/tool permission gateway. Fresh app page opens this generic catalog item,
uses only typed Scenario and sees new Report/history. Internal release/instance routes remain
unsupported for this family; no publication or provider is enabled by compiling/saving it.

## Independent acceptance oracle and boundary

Freeze complete canonical candidate including IDs, schemas, wiring, dependency/check locks,
origin references, original limits and authority declaration; rehashing does not establish validity.
Read/create/run/history must retain source/check result-null/Attempt-seal protections. Cold inputs
must not contain source Report or old facts. History binds actual project/principal/runtime/phase,
request key, App fingerprint, sealed program and Scenario. Before/after authority rows unchanged.
Two typed Scenarios in cold fresh pages produce independent ALLOW/BLOCK via actual Intern
MockTransport/Worker receipts; UNKNOWN remains a legal new result. No client answers can enter.

Negative oracle: client extras; wiring/executor/dependency/schema/version/bool rehash; missing or
null source result/check/Attempt seals; source/target revoke or hash drift; cross-owner/project;
late project/selection/identity responses; accepted lost/malformed receipt with subsequent422 keeps
original body/key locked, whereas first authoritative422 allows correction. Old CSV/agent behavior
and internal release refusal are separately checked. Tests are actual HTTP and explicitly jsdom,
not native. No LIVE, push, CI, full/PG unless separately requested. PREVIEW_ONLY;
source overall NOT_ACCEPTED, semantic UNKNOWN, owner PENDING. Private canonical compiler
support does not imply unified published runtime or independent AppPrincipal completion.
