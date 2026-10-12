# P-A independent review — r5 finite qualification

**LIMITED PASS: 68 unique actual pytest nodes, 68 PASS / 0 FAIL / 0 ERROR / 0 SKIP.**
This qualifies only the frozen P-A/offline slice and the two exact regressions.
**The 82 old software-continuation/boundary cases remain an unresolved compatibility
blocker.** No whitelist or old object was resigned, widened, skipped or upgraded.

## Exact source and actual execution

Worktree `/workspace/Sim2Act-pa-provider`, branch `dev/pa-intern-provider-20261012`,
base HEAD `a4fd476127a477006dbdb29a9a1f6c2f09e6a001`; root is the only repository writer.

422-file frozen map SHA256:
`671955ea8cff8da3c84dde2cc3a7de8c3bdf373180cf58c1222284ffb2773ad7`.
All 422 source/tests bytes match before and after actual execution, zero difference.
pyproject SHA256 remains
`49f68cb7901e719cd014141c69e5fa9ea562f51e9b9c40acd122ace6f2085d81`.
The current 70 implementation Python files (config excluded) fingerprint is
`44dc40ab98fdafd8dc0928e17fa599a8df8e20e696bf1dbc570702f7e6ed05c7`.

The independent r4→r5 bridge compares all 422 qualified entries: only
`src/sim2act/api.py` and `src/sim2act/pa_material_bindings.py` changed; 420 entries
remain exact r4 bytes. This matches the author bridge, copied without alteration.
The r4 53-pass report, raw outputs, source map and manifest remain unchanged; these
r5 results were newly executed and are not borrowed through the bridge.

| Actual scope | Unique PASS nodes |
| --- | ---: |
| test_pa_generation_provider.py | 25 |
| test_pa_material_bindings.py | 12 |
| test_pa_provider_ui.py | 4 |
| test_goal_text_rejected_raw.py entire file | 14 |
| test_project_column_versions.py::test_approval_source_evidence_actual_run_read_only_and_authorized | 1 |
| Independent calibration/fault file | 12 |
| Total | 68 |

Extended specialist process 87576 exited **0** (terminal chunk 74f3b9):
56 passed in 228.94s. Independent process 36337 exited **0** (chunk 026ede):
12 passed in 27.85s. XML and logs retain exact names. There are no active reviewer
processes and no unexpected current failure or fixture correction.

The original 41 specialist cases are a separate repeat of the author's cases, not
41 additional distinct cases to add to author totals. The independent 12 comprise
one barrier calibration and eleven product fault nodes. The two direct known()
checks below are supporting read-only calls, not pytest nodes or old-DB execution.

The four real offline UI scenarios (valid/binding-lost/binding-late/scope-late)
completed 144 embedded check executions (34/34/38/38), with 20 frozen assets loaded
twice per case, 160 total asset loads. Every loaded asset hash matches this frozen
map. These checks/loads are not additional pytest nodes. The flow is in-process
HTTP TestClient + IPC + JSDOM, with actual SQLite Worker/new-material NoModel runs;
there is no socket/native browser or actual provider/model request. Production-
shaped gates are only a clearly synthetic SQLite façade with local AsyncClient
MockTransport injection. Synthetic clocks establish no real RPM timing or fees.

## The two finite fixes and source-marker review

The ordinary generation route now omits the optional `activation` keyword when
its value is None, keeping the established four-positional-argument policy call.
The explicit activated route still passes and validates its exact activation;
no approval/fingerprint/source/budget gate was lowered. The entire 14-node rejected-
raw suite passed, including the legacy-policy helper and actual response/raw
archive/strip/tamper cases. This is current legacy-shaped data evidence, not an
old-source/database upgrade claim.

P-A binding classification now uses only three metadata projections before choosing
its gate: candidate.namespace, candidate.pa_binding.kind and the independent
extraction snapshot.kind. It no longer probes full P-A META ledger rows merely to
classify an unrelated CSV draft. The exact project-version source-evidence test
now passed, including actual source evidence, read-only behavior and authorization-
before-protected-ledger checks. This validates the specific earlier regression;
it is not evidence of a complete PostgreSQL/private-read implementation.

Static marker boundary, based on exact source snapshots here:

- Removing namespace alone leaves the candidate binding or independent kind hint;
  the P-A gate still checks exact metadata/current material authorization, then
  `apps.validate_source_family` requires the original namespace and rejects.
- Removing pa_binding.kind alone leaves namespace/independent kind; the gate still
  runs and full exact reconstructed candidate fingerprint verification rejects.
- Removing independent snapshot.kind alone leaves the candidate hints; scope_gate
  requires that independent kind before proceeding and closes on corruption.
- Removing all three kind/namespace hints while retaining the source row makes
  scope_gate decline classification; it does not grant execution. The independent
  origin dispatcher rejects an unknown/missing extraction kind at `apps.py:311–314`.
  Removing the complete extraction row too still cannot make an origin-free literal
  candidate execute: residual pa_binding mismatches the independent source fields,
  and a stripped plain literal candidate is routed to text_apps.verify_origin,
  which requires the independent actual generation source. No new graph factory,
  generic fallback proof or automatic re-sign is introduced.

The additional individual/all-hint combinations above were STATIC, not four new
adversarial dynamic tests. The existing actual binding marker/namespace/graph
negative nodes were rerun and passed. A three-hint classification decline is not
misrepresented as authorizing private body reads or proving all hostile database
rewrites safe. This finite result establishes rejection before unsupported execution.

## Independent barrier/fault repeat

The prepared independent barrier and twelve test bodies are identical to the r4
probe bytes, copied to this new directory. The instrumentation was freshly
calibrated: exact nested/bound/alias ID projections return real IDs without full
private-cell UDF evaluation; deliberate full protected cells, wrong JSON paths,
explicit main access and reserved CTE are actually rejected. Permitted ID projection
necessarily evaluates its backing JSON internally; zero backing JSON evaluation is
not claimed. No parameter-only old-Run matching or SQL text-only inference was used.

The actual eleven product fault nodes again passed: revoked prepare; revoked cold
inspect/original-key recover/confirm; version-strip with withdrawal; actual claim
metadata rejection; finalizer withdrawal with global zero write; explicit approval
withdrawal before first confirmation; unknown usage without resend; post-STATE lease
and approval deadline edges with terminal-write rollback and immutable settlement.
HTTP denied requests/direct finalizer preserve global DB contents. Actual claim
rejection intentionally saves failure metadata and was never labeled global zero
write. The clock edges are local post-STATE faults, not the permanently excluded
cancelled installation window. All fixtures are new SQLite fixtures; no old rejected
probe/candidate or real model is imported.

Typed binding remains the same finite P-A contract: received model graph/step names
are preserved, only explicit typed identity/material/Goal paths vary, current target
Goal is human-bound, current target authorization is required, and new-material cold
NoModel outputs reflect that actual new resource. The original source remains an
authorized audit dependency. This is not a content-free P-B template, inferred
whole-Goal semantic acceptance, automatic owner approval or publication.

## Closed old-implementation gate and 82-case blocker

The approved anchor file SHA256 is unchanged:
`24f26f3621b8fc49a24fa3566484b568148d9317f2d279d79f264416b994193a`.
The exact CHANGED whitelist is recorded in compatibility-static-check.json and
was not altered. Two calls to current known(old_fp), with no old SQLite fixture,
returned VERSION_CONFLICT/CLOSED_REJECTION for both approved fingerprints:

- `08334fd20f4b3187ca2d5350bff50ec8d24cff881c2f1abaad821bd692bf1d2a`
- `7f464d1099210fe485bb08ef455267cadf9970d5d1a098b1d00253ee1ad0edee`

For each anchor, the current files outside the approved bridge are:

- Newly added: generation_approvals.py, pa_material_bindings.py.
- Changed non-whitelisted files: contracts.py, db.py, goal_applications.py,
  text_apps.py, worker.py.

The first rejection is reached at the new-file-set gate; the five changed-file
mismatches are independently byte-compared, not claimed as a second executed branch.
We did not extend whitelist/anchor data, auto-sign new releases, restore unsupported
legacy instances or downgrade signature checks. A known old anchor does not itself
prove current compatibility across these unapproved additions/dependencies.

Parent's completed r4 broad run was **675 unique: 587 PASS, 84 FAIL, 4 PG SKIP**,
exit 1, 2453.43s. Parent's precise classification: one legacy-policy keyword failure,
one unrelated CSV pre-authorization ledger failure, plus **46 continuation + 36
boundary = 82 compatibility rejection failures**. These are parent actual results,
not our independent 68. The two finite issues have the current tests above; the
82 are still actual historical FAIL and unresolved at r5. They were deliberately
NOT RERUN here, not converted to SKIP/PASS or summed into current r5 node totals.
Thus no full product or old continuation acceptance is asserted.

## Evidence retention and limits

Raw JUnit/log/exit, UI results/driver logs/SQLite fixtures, the tested barrier/probe
sources, exact map/bridge/implementation/source-before/source-after and supporting
known-check record are included by manifest. Original r4/prepared/static reports
and the infrastructure transport-disconnect error remain byte-preserved; r5 had
no transport or permission error. No denied read/browser/CI/install path was retried.

NOT RUN / NOT VERIFIED: real network/provider/model/paid usage or monetary cap;
PG roles/concurrency/real RPM, Windows, native browser/socket, remote CI/deployment;
old source/database upgrade, 82 old compatibility nodes on r5, permanently excluded
cancelled exact install race, arbitrary models/multi-source/semantic interpretation,
content-free P-B and whole-Goal human semantic acceptance. No credentials, security
permissions, repository product/tests/whitelist/main/core or remote refs were
changed by this reviewer. Parent remains responsible for the explicit compatibility
blocker and any separately authorized qualified continuation/commit/push.
