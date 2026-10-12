# Exact P-A-era literal software qualification — independent static review

Design result: the bounded whole-target qualification is an acceptable route to
finite review, pending actual frozen legacy/deep/shared execution. It adds no file-
name exemption to CHANGED and supplies no instance execution permission by itself.
No dynamic test was executed in this static phase. Root is the sole repo writer.

## Root cause and scope

At clean HEAD 6088dcfc93ecf9de48f10ab6a72b89ec4759fd91 the original known() gate
correctly rejects both previously approved 233/a747 software anchors. The new files
`generation_approvals.py` and `pa_material_bindings.py` are outside the closed old
set; five non-CHANGED files differ: contracts.py, db.py, goal_applications.py,
text_apps.py and worker.py. The first set difference rejects before the five hash
comparisons are reached. This is a software-qualification precondition failure,
not evidence that old saved history has already passed or failed its deeper checks.
Parent's r4 82 failures (70 preflight failures + 12 not reaching deep history) must
remain actual historical failures; changing their expected assertions/skipping or
adopting the P-A 68-pass report would not repair them.

The operator/check/compiler/oracle and persisted-schema checks cannot be inferred
unchanged merely from filenames or P-A success. Parent separately ran immutable
a4fd old suites (100PASS) and 6088 two representatives (2FAIL); these are parent
baseline/red evidence, not this reviewer's runs.

## Seven-file audit (a4fd → 6088)

| File | Actual change | Risk requiring actual proof |
| --- | --- | --- |
| contracts.py | New exact activation type and optional activation on ApplicationGenerationPolicy; existing frozen/Goal/data types otherwise unchanged. | Old snapshots missing new optional field must remain parseable without rewriting their raw sealed bytes; model_dump defaults may alter historical serialized comparisons; ordinary literal sources must remain application_generation=None. |
| db.py | New P-A identifier-only source gate before guard/frozen loader/claim/inspect; denied claim saves metadata failure and returns None. | Shared Store paths can accidentally classify an old AppRun as P-A, read private old/foreign cells or affect queue/lease/recovery; target/current identity gates must precede bodies. Gate FALSE is expected for genuine legacy literal contexts, with old matching-status/frozen checks still intact. |
| worker.py | Activated P-A quota/charge branch, source gate before finish, activation-only final active/lease checks, exception fence-only projection. | New grant/rejection path can affect shared NoModel history/finalization; old model=0 job must never reserve/send/refund an Attempt. Lease/stop/late receipt fencing must remain valid; exception metadata must not load revoked bodies. |
| goal_applications.py | Independent P-A run discriminator/seal, activation-aware provider gates/history/model identity/deadline/settlement and confirmation. | The new gate is imported by shared db/worker. True legacy literal runs must not enter its P-A body/provider branch, while stripped genuine P-A records must still be identified and denied. Historical frozen contracts and accepted headers cannot be automatically resigned. |
| text_apps.py | New exact namespace dispatch to pa_material_bindings.verify before unchanged task_proof/literal branches. | Old authorized_data_free_text_logic path must still call the original archived logic verifier. No model-origin namespace may impersonate it; old kernel compute/oracle bodies must remain exact. |
| generation_approvals.py | New isolated namespace of exact Goal/source/key approvals and nonrefundable charge/send/settlement records. | No old authority/logic/instance is promoted to a model scope; absent old activation never imports a fresh LIVE permission. Defaults zero, current role before bodies, unknown no resend, current flags/deadlines and immutable late evidence must remain enforced. |
| pa_material_bindings.py | New typed model-graph reuse; independent three-hint classification and paired provenance. | Must return FALSE for unrelated old literal/CSV families without full P-A ledger reads; individual or group hint stripping must not permit source-free execution. A new human-bound material remains P-A with authorized original audit dependency, not old P-B canonical logic/template. |

The seven full file snapshots and exact a4fd→6088 diff are retained here. No
claim is made that dynamic validation of only the branch predictor is enough.

## Existing CHANGED files and downstream gates

CHANGED is unchanged: api/app_jobs/internal_api/owner_acceptance/app_owner_goals/
apps/lifecycle/text_logic_reuse/text_continuations/text_run_checks/text_workflows.
Between a4fd and 6088, api adds the explicit provider/binding routes and exact native
Goal run input; normal None activation retains the four-positional API policy call.
apps adds only exact P-A compile/independent family dispatch. text_continuations
adds P-A metadata classification ahead of the existing independent literal gate.
Other CHANGED files remain a4fd bytes. The new qualification locks their complete
current bytes too; it does not declare that future changes to CHANGED are safe.

Archive and execution stay separate. Original AUTH/BIND/candidate/logic/Goal/Release,
data rows/history/signatures are not rewritten. `no_context` blocks generic preview/
prepare/new-instance paths for old software; `execution` binds exact instance,
current revision, release ID/fingerprint and full implementation to the actual
sealed commit. enqueue/dispatch/final commit/resume/owner paths still use those
contextual gates. App-wide archival permission cannot revive another unapproved
instance or old queued Run. All terminal history jobs retain exact owner/project/
runtime/ReleaseIndex/binding/frozen contract/Goal checks; potential-result statuses
and residues use the original complete verifier, typed rows match bidirectionally.
New Release/revision makes old owner acceptance stale; a fresh Worker is required.

## Exact fallback contract

The original ANCHOR_HASH/anchor JSON/fingerprint validity and unknown-source denial
happen first. The original successful bridge is preserved. Only failure of the
source-file set/hash comparison consults the new qualification; no catch-all
DomainError fallback is used and no identity, TTL, Grant, source or schema error
is overridden. Its result remains the original approved old anchor.

The qualification raw SHA is pinned in one module-level simple assignment. It
contains the exact two old source fingerprints, original anchor hash, hard-pinned
a4fd review baseline and 6088 reviewed candidate, exact schema and complete 70-file
implementation set. JSON duplicates reject, including nested duplicates. Current
names and byte hashes must equal all map entries; new/missing/changed files reject.
Only the unique canonical QUALIFICATION_HASH literal's 64 characters are replaced
with zero to avoid the digest cycle. AST verifies one Store, one module-level simple
Assign and one literal value with exact source spelling. The normalization does
not ignore comments, formatting, AST bodies, other literals or file content.
Syntax/OSError/type errors fail closed. A source-map comparison statically matches
all 70 normalized hashes and the pin to the actual JSON file SHA.

Actual implementation() is UNCHANGED and still hashes the full current Python
bytes, including the real qualification pin. Prepare, commit CAS and every current
execution permission use that full fingerprint; the normalized map is never an
approval/permission fingerprint. Existing old/current permits do not gain a new
target automatically when the actual software bytes change. Current target owner+
runtime authorization, old AUTH TTL/revocation, exact instance consent, all history
and final stop/lease/expiry rules remain mandatory.

This is a reviewed software artifact anchor under the existing trusted filesystem
code/pin model, not a cryptographic defense against an actor who can arbitrarily
replace the program and its anchors. The only digest hole is explicitly documented.
Runtime config.py is intentionally excluded by the existing implementation contract;
config changes still require current flag/budget/Grant checks and are not described
as an exact source-code qualification. No unsupported broad old-software inference.

## Packaging and required proof

pyproject adds only text_software_qualification.json to package-data beside the
existing anchors/web. Installed wheel code must possess exactly the same raw JSON
and Python set as the reviewed source. Package-data declaration is static evidence,
not a built/installed-wheel result. Parent's build attempt failed due missing
setuptools; no reviewer dependency install/network is authorized. Real wheel
construction/installation is NOT RUN, and that original failure is retained.

Required actual frozen matrix: original two legacy files (100, preserving original
assertions) including each formerly failing 82 node; target qualification positives
for both source anchors and negatives for seven added/changed files plus existing
CHANGED file edits, extra/missing source, manifest/pin/anchor mutation, duplicate
JSON, nonliteral pin and unknown old source; current P-A 41/legacy archive14/specific
CSV1 (56), plus the independently calibrated 12 private-cell/deadline/no-resend
probes. Old boundary spies must prove the successful/failed residue jobs actually
reach the original full verifier and that wrong-scope private cells remain zero.
Positive cold NoModel must preserve all old bytes and data versions, fresh owner
staleness, exact scope and unrelated instances. Mutation/cancel/expiry/late results
must preserve zero partial writes. Shared lifecycle/app_jobs/worker/Goal/owner/
resource identity/history/scheduling suites are separate parent regression evidence.
No author counts will be added to this reviewer's actual unique node total.

Current inspected qualification SHA:
f247ef81b9ed40725cab07b89e0fe1f2b22caee88454bae663c13a9978f186c2.
pyproject SHA:
9524bab8092864bb329a7a6797ece01340a1a51c99a9406d030b80d1e0270a7d.
Exact static source hashes: static-source-map.json. No open static design blocker
was found after the sole-pin/duplicate-key/review-commit fixes; actual acceptance
remains pending the separately recorded frozen runs. No tests/DB/probes were run
in preparing this static document. Only /tmp was written; root remains sole writer.
