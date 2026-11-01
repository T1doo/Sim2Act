# First-use production entry audit and narrow repairs

Audited against V5 product §3/§6 and staged plan F1–F3, plus Installation,
FirstUse, ProductionConnection and ConfiguredDesktop. R0 still requires both P-A
and P-B, normal authorization/recovery and native Windows evidence. Small CSV,
Mock, Linux or container success cannot substitute for those requirements.

| User operation | Existing implementation and real boundary | This change |
|---|---|---|
| DB/schema initialization | `cli.py migrate`, `Store.initialize`, optional explicit Setup.ps1; original admin/migration/app-role separation. No automatic service/DB/role provisioner or GUI installer | Installed CLI accepts explicitly selected existing `--config`, reuses original parser, only migrate/init-user; generic failure/cleanup preserve unknown effects and hide DSN |
| First application identity/login | Original `init-user` hashes bearer via Store.user; API authenticates hash, page token login. No self-service signup/reset/PG role creation GUI | Original identity creation retained, not executed for this audit; no credentials created |
| Projects/materials/authority | Normal authenticated project/resource API creates original project save and resource read/aggregate grants; grants list/revoke routes, saved Goal cards and bindings | Unchanged; no fake grant/source/approval inserted by new route |
| Model account/business selection | Fixed production_evidence source, existing Intern account/quota, original scoped approvals, five-field launcher selection; token is not a DB login or application identity | Existing P-A **or P-B** original approval can be recovered through a read-only authenticated worker-selection GET, no rebind or permission creation |
| Goal to app / completed task to app | Original P-A and P-B backend/routes, extraction/per-use/logic editor and explicit typed approval APIs exist | Not represented as missing wholesale; fresh server-authored seven-slot preparation GUI is still P-A only. Fresh P-B seven-slot GUI and special exact-stage scheduling remain gaps, not missing user fee consent |
| Desktop startup/close/reopen | Configured supervisor owns original API/Worker, READY/ACTIVATE/STOPPED protocol and persistent origin; explicit config/selection accepted by native host | New source is not in older frozen Windows package; no current PG/native-window acceptance added here |

The new existing-approval reader first authenticates original project/materials
before reading private scope JSON, then freshly verifies current exact approval,
revocation, scope/version/fingerprint and expiry inside the original project lock.
Only matching canonical account scope yields the original five metadata fields.
A legacy/unconfigured scope stays unconfigured. Export performs another GET and
compares approval/contract fingerprints; UI context/key/input generation protects
against late response navigation/login/connection changes. Export is not a permit;
original launcher/account/Worker execution gates still apply. No model request,
new Run, slot, approval, migration or credential is created by this reader.

Initial evidence: 25 backend regressions passed (synthetic SQLite and mocked CLI
plumbing, no real initialization); one actual HTML/JS JSDOM-to-real authenticated
HTTP scenario passed for old/new selection export and revoked recovery refusal.
These are operation checks, not a screenshot or Windows UI acceptance. Raw logs
and XML are retained separately with final frozen validation evidence.

PG setup is NOT RUN. [PG-PLAN.md](PG-PLAN.md) freezes exact requested setup,
privileges, dependency pin, resource preconditions, time/model ceilings, normal
production identity/approval path and cleanup. Current disk fails its minimum;
no container, image, role, new credential or model request was created here.
Old runtime packages remain unchanged and cannot be relabelled this new source.

## Frozen outcome

Source `7469b9997170a9a5e99bc88cf48435ad770a96d7` was normally pushed and read back
from the development branch. Final independent review corrected an explicit-empty
`--config` fallback: all five commands now reject it before Settings/Store/token
calls. It also corrected the proposed nonce network and one-final-teardown scope.

Final frozen regression: 39 passed, no failures/errors/skips. This deliberately
selected all 12 initialization tests, four original approval tests, all 22 actual
page/HTTP scenarios and the exact source qualification positive. The other 26
qualification negative variants were deselected on this final pass; all passed
in the immediately preceding broader 67-test run before the two CLI condition
changes. These overlapping runs are not added together as unique coverage.
`validation.json`, raw XML/logs and all 22 DOM result files identify those phases.
The DOM files contain only synthetic fixture identity/materials, not user tokens.
No pixel screenshot, PG, model request, production identity provisioning or Windows
execution occurred. Synthetic SQLite fixture identities are explicitly test-only.

The completed broader fixture, including all copied negative-test source bytes,
was archived locally after all-pass XML, no process cwd/fd users, and per-file
SHA256 plus symlink round-trip verification, before deleting only its expanded
own fixture. Archive: `/workspace/scratch/first-use-final-20261101-preserved.tar.gz`,
27,486,270 bytes, SHA256
`309f73643c5ef25e2436d267f8cdf87cc2a1c4d57d167b44ecde7fb601453e99`.
Original logs/XML and archive manifest remain. The current final resource snapshot
still fails the >=2GiB PG disk precondition; no provisioning has been attempted.

Unchanged internal Windows package remains source c8fba531, not this new source:
`Sim2Act-internal-win64-c8fba5316043-reviewed.zip`, 27,577,607 bytes, SHA256
`43b39df326f521601c3c5bdcc7e0303e9a0ff06ef320466d561945fa30640d85`.
It remains an internal assembled/static-checked input, not a newly accepted
Windows/PG/R0 final product. This source slice does not relabel or publish it.
