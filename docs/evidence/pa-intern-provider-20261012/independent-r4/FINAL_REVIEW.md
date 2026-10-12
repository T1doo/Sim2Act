# P-A provider + explicit new-material binding independent review (r4)

**LIMITED PASS for this frozen candidate and the stated SQLite/offline scope.**
53 unique pytest nodes completed: **53 PASS, 0 FAIL, 0 ERROR, 0 SKIP**. No current
core failure was found within this independent scope. This is not full-product,
whole-Goal semantic, real-provider, PostgreSQL or platform acceptance.

## Exact candidate and runtime

- Base HEAD: `a4fd476127a477006dbdb29a9a1f6c2f09e6a001`.
- Worktree: `/workspace/Sim2Act-pa-provider`.
- Branch: `dev/pa-intern-provider-20261012`; root is the sole repository writer.
- Frozen 422 src/tests file map SHA256:
  `6732ed8db8b7040fbd2c5c103547486881c4e75fd4e4ec79e0d638fc111a43d9`.
- pyproject SHA256:
  `49f68cb7901e719cd014141c69e5fa9ea562f51e9b9c40acd122ace6f2085d81`.
- 70 implementation Python files, excluding config; exact canonical implementation
  fingerprint independently derived using the production algorithm:
  `3b144ac41e019d76f7c05b305ae1a7e66027cb507c3edbbd3d91143d01a37b92`.
- All 422 files and pyproject match before/after actual execution, with zero
  differences. Both known pytest processes have explicit exit 0; no independent
  test remains running. All writes were to this `/tmp` evidence directory.
- The parent explicitly authorized the original `/workspace/Sim2Act/.venv/bin/python`
  runtime. PYTHONPATH and cwd select only the new provider worktree source/tests;
  no old owner product source or cancelled probe was executed. Bytecode writes
  were disabled and pytest caches/fixtures/JUnit/logs were placed here.

## Actual counts (do not add author counts)

| Scope | Unique nodes | PASS | FAIL | ERROR | SKIP | Wall time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Provider file | 25 | 25 | 0 | 0 | 0 | included in specialist |
| New-material binding file | 12 | 12 | 0 | 0 | 0 | included in specialist |
| Actual HTTP/JSDOM file | 4 | 4 | 0 | 0 | 0 | included in specialist |
| Independent calibration/fault file | 12 | 12 | 0 | 0 | 0 | 24.13s |
| Total | 53 | 53 | 0 | 0 | 0 | parallel scopes |

The specialist run (25+12+4=41) completed in 271.98s. Those 41 execute the same
cases as the author's 41; they are independent execution, not 82 distinct nodes.
The extra 12 comprise one instrumentation calibration and eleven product fault
nodes. The calibration's internal SQL cases are not additional pytest PASS nodes.
`specialist.xml`, `fault-first.xml`, `final-result.json`, `execution.json`, raw logs
and per-process exit JSON contain the exact node names and terminal results.

The four actual offline UI scenarios were valid, binding-lost, binding-late and
scope-late. They ran IPC + in-process HTTP TestClient + JSDOM, with real SQLite
Worker processing, not native browser/socket HTTP. They completed 144 embedded
checks (34/34/38/38), loaded 20 qualified assets twice per case (160 total loads),
and their loaded source hashes match the frozen assets exactly. Embedded checks
and asset loads are supporting evidence, not extra pytest nodes.

## Independent private-cell barrier and fault evidence

The barrier was calibrated against a new, actually completed SQLite/MockTransport
P-A fixture. Exact bound/nested identifier projections and an alias/join/IN
identifier query returned their actual identifier/list shapes with zero complete
private-cell UDF evaluations. Twelve deliberately prohibited SQL probes then
failed: bare snapshot, alias/join snapshot, IN context, no-WHERE result, full Goal
snapshot, resource content, Attempt parameters and response, two non-ID JSON paths,
explicit main-table read and a reserved CTE. The first ten invoke the protected
cell UDF; the direct-main and reserved-CTE paths are denied by the instrumentation.
Each deliberate failure required an actual recorded barrier hit, not a regex or
old-Run query-parameter match. Attempt full-cell UDF evaluation was separately
asserted. Calibration exceptions are intentionally caught expected failures;
they are not failed product tests.

This allows only an exact enumerated set of ID/ref/discriminator paths. Dedicated
view projection UDFs evaluate their backing JSON to produce only those IDs. We do
**not** claim zero backing JSON evaluation for that permitted projection. Complete
private cells use a separate error UDF and telemetry. The barrier is fault
instrumentation, not a production authorization implementation. Its exact tested
source and whitelist are preserved in `probes/identifier_private_barrier.py`.

Actual fault nodes established:

- Revoked material before prepare: only identifier projections, denial before full
  Goal/material cells and global DB content unchanged.
- Revoked material before cold inspect/original-key recovery/confirmation: denial
  before any full protected Run/Goal/contract/resource/Attempt cell, global DB
  unchanged across each HTTP request.
- Fault-injected removal of P-A contract version plus current withdrawal: independent
  ACCEPTED source marker still closes the read before bodies, global DB unchanged.
  This is a labeled corruption probe, not valid old Worker or real attack evidence.
- Revoked queued source at actual Store.claim: no private payload load/model Attempt;
  only permitted failure metadata is written. Claim rejection is not mislabeled as
  global DB zero write.
- Revoked source before direct finalizer: denial before the first complete contract
  read and global DB content unchanged.
- Explicit provider approval revoke before first candidate confirmation: refusal
  and global DB content unchanged; no partial application is minted.
- Actual unknown-usage response: one immutable original Attempt/reservation, no
  candidate result and no repeat send after original-key recovery/another Worker.
- Synthetic lease and approval clock edges after tentative final STATE: final
  PARTIAL/result/state-event transaction rolls back, original two charge/send/
  settlement records and immutable Attempt errors remain, with separate post-
  settlement rejection evidence. This is a local post-STATE fault, not the
  permanently excluded cancelled installation race.

## Static and dynamic contract assessment

The factored current provider eligibility gate is used at actual wire and active
finalization. Wire identity/content/method and current Authorization token are
checked before send. LIVE configuration, exact selected LIVE ID, native Goal head,
permission, software and absolute deadlines remain current active gates. Historical
received proofs are read without requiring a new live configuration. Completed
Attempt settlements remain immutable and final failure is a separate event.

ID projections now gate full-body loaders, finalizer, claim, cold inspect and
original-key recovery; independent ACCEPTED kind/approval/application IDs prevent
single-marker stripping. Exception fallback projects only fence. The final active
check and original lease deadline check share the terminal-write transaction.
The before-fix observations were static; the preserved original static reports
were not overwritten or relabeled as dynamic reds.

Precise Scope/Approval double seals bind principal/project/runtime, native Goal
version/snapshot, original generation key, material identity/hash, grant state and
software. Budget caps are 3 requests, 1 read, 1 repair, 64000 reserved tokens, 1024
output, 300 seconds and effective RPM 1. Default activation/provider/LIVE ID grant
zero real sends. Reservations/charges are not refunded; unknown settlements stop
further requests. The two explicit returned model aliases and total request
header/body deadline apply. The tests include synthetic production-shaped gates,
repair, wrong names, extra tools, truncation, unknown usage, oversize, current wire
configuration changes and immutable final failure. Production-shaped LIVE rows
come only from the explicit SQLite façade plus locally injected AsyncClient
MockTransport; they are **not real Intern requests or production PG evidence**.
Synthetic 61-second clock advances do not establish real-world rate timing.

The new-material path was reviewed separately. `pa_material_bindings.slots` only
substitutes named app/action/resource/hash/Goal/card paths; the normalized graph
fingerprint is equal to the actual received model candidate. It preserves the
model-selected workflow/step labels, executor, schema and other graph fields, and
uses no canonical graph factory to supply a candidate. Exact metadata+binding
paired seals and the independent KIND marker bind the selected original PARTIAL
Run, target native Goal/current version/hash, target source hash, received candidate
and graph, original binding key and new runtime. Missing namespace/marker or
coherent graph rewrite is rejected. It creates a new runtime with exactly the
authorized target read grant and rolls back all new objects on seal-write failure.

The backend and all four UI cases saved and cold-ran the separately authorized
new material with NoModel, with actual new-material complete-line citations and
new source hash, while the old-source term gives no old result. This is more than
new input on the original material. Old provider proof/results remain provenance;
**the original source remains a current authorized audit dependency**. This is not
a content-free P-B template or completed-task extraction, despite using the shared
`task_extractions` table for its distinct P-A binding marker. The explicit target
Goal is human-bound; whole-Goal semantic acceptance remains NOT_RUN/UNKNOWN, owner
acceptance PENDING and formal publication false. No artificial P-B success was
inferred from the received candidate or from the new NoModel computation.

## History, limitations and remaining work

Current independent pytest runs had no unexpected failure or fixture correction.
The earlier first-final attempt failed to create an exec process:
`exec_command failed: CreateProcess { message: "Rejected(\"Failed to create unified exec process: exec-server transport disconnected\")" }`.
No test had started then. It was kept as transport infrastructure history, not an
automatic approval/security review rejection. The failed read action remained
stopped. Parent explicitly authorized a new lightweight same-tool/same-worktree
pwd + saved-source check, which succeeded (chunk 3de570), then these authorized
frozen tests. No new environment/tool/permission escalation or prohibited retry
occurred. `transport-history.json` preserves the exact error and recovery record.
Minor pre-test file-name lookup errors did not execute product code or tests and
are not counted as pytest failures.

Prior author's red/fixture/UI histories remain the parent's original byte evidence;
this report does not overwrite, sum or reclassify their earlier 6 red, combined-r1
fixture errors, app-open UI failures or disabled-recovery UI failure. Our previous
static/prepared reports and source maps also remain unchanged.

At reporting time the parent's broader adjacent regression was not yet complete.
Parent reported one separately reproduced legacy monkeypatch compatibility error:
the old four-positional-argument `legacy_policy(*args)` test helper does not accept
new `activation=None` keyword. This is outside the 53 nodes here and is neither
claimed resolved nor misdescribed as a private read/model/authorization failure.
The parent plans a separate qualified None-keyword omission after active tests
exit. These 53 are assigned solely to this r4 frozen map; no future source change
inherits them automatically, and no broader/full CI green is claimed.

NOT RUN / NOT VERIFIED: real model/network/paid API and actual provider money cap;
production PostgreSQL roles/concurrency/real RPM/Windows; native browser/socket;
remote CI/deployment; old-source/database upgrade and cancelled exact installation
window; arbitrary model graphs/multi-source or semantic generation; content-free
P-B template/whole-Goal human semantic acceptance. No credentials, security
permissions, main/core branch or remote push were changed by this reviewer.

The result is the finite independent r4 acceptance above. Root remains responsible
for the broader regression repair/qualification and any authorized commit/push.
