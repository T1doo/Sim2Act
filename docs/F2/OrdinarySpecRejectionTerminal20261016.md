# Ordinary spec original-key terminal — finite verification

Baseline: `8268486f5f2c3df6968d7dd38f3bb50f797c53df`.
Development branch: `dev/ordinary-spec-rejection-terminal-20261016`.
This slice closes cross-page ordinary-spec rejection recovery. Root was the sole
product writer; cold_proof_review independently reviewed without executing tests.

## Result and finite contract

Previously A deleted its durable intent after a transient NOT_ACCEPTED proof.
B correctly retained its cached original key after storage deletion, but then
could only read OUTCOME_UNKNOWN. A transient proof does not prevent a late POST.

`spec_run_terminals.py` now provides authenticated owner-authorized closure of an
unused ordinary spec key. The client proof is a UI trigger, not a signed server
capability. Close independently checks owned instance/project, original release
application/family and absence of accepted identities inside the same project
lock and transaction as enqueue. The immutable journal permanently fences
`(principal, instance, key)` before executor dispatch, even for a changed DTO.
Accepted-first refuses closure and preserves the original accepted receipt;
close-first prevents late acceptance. Partial/conflicting accepted identities and
metadata scan exhaustion remain UNKNOWN. Scanning is bounded at 128 bindings.

An explicit `Store.initialize` migration creates `internal_spec_run_terminals`.
API/Worker startup does not migrate. Closure writes recovery metadata only: no
Run, model-budget reservation, business project data or artifact. Terminal GET
freshly authorizes owner/project metadata and verifies stored scope/integrity,
without reexecuting old materials. Accepted-result authorization remains intact.

The supported original wire DTO contains empty input, request key, integer revision
>= 0, release fingerprint and optional non-null owner-goal fingerprint; close also
receives the original release ID. Revision zero is a finite backend validation-error
case. Arbitrary malformed DTOs are unsupported and stay UNKNOWN. Browser durable
records still require revision >= 1: the synthetic page validation-phase case and
actual backend revision-zero case prove separate boundaries. Raw wire and accepted
execution request fingerprints are deliberately distinct.

A requests close only after strict proof/currentness checks, then authenticates
original-key GET before clearing. Terminal namespace/status/full scope/original
release/key/exact DTO/wire hash are verified. Clearing stays inside the nonqueued
Web Lock, identity/workspace/instance generation guards and exact record comparison.
B can recover its cached key without storage events. Failed/lost close retains
UNKNOWN; later actions only GET the original key. Deletion alone cannot unlock.

## Final executed evidence

Primary suite: **8 PASS, 0 FAIL, 0 SKIP, 0 ERROR**, 87.088 seconds in XML.
`tests/test_spec_run_terminals.py`, `tests/test_durable_recovery_protocol.py` and
`tests/test_internal_submission_rejection.py` ran with explicit SQLite, mock
transports, no inherited PG test URL and no real model/paid API calls.

- New actual-page JSDOM protocol: **24 checks**. Both proof phases; A/B recovery
  without storage events; failed and committed-but-lost close; fresh DOM GET-only
  recovery; scope-lock contention without queueing; eight receipt-field mismatches;
  forged deletion; identity-switch late reply; same-identity replacement-record CAS.
- Existing page protocol: **23 checks**, including successful receipt contention,
  identity boundaries, wrong scopes, corrupt/unavailable Storage and missing locks.
- Actual authenticated API and deterministic Worker: both proof phases, raw wire
  fingerprint, stable terminal/idempotency, changed-DTO permanent fence, genuine
  authenticated fixture-B denial, unsupported wire rejection, INSERT-after-execution
  rollback, forced two-thread SQLite lock orders, accepted-winner Worker success.
- New Store/app and **independent new OS-process TestClient/Store** reopen the
  committed SQLite database without initialization. Original-key terminal GET is
  identical; changed-DTO late POST is 409. Child stdout/stderr are preserved. This
  is not a network-server or Worker-process restart test.
- Final source closure: all **522 src/tests files** have identical before/after
  bytes. Manifest SHA256:
  `5708da4c45884b3570f42c6f85a511c12ec90b5ecde1a50b32eb9162e53f67f4`.
- Ruff passes for all five changed Python files; Node syntax checks and product /
  test / report whitespace checks pass. Verbatim historical logs and patches retain
  their original whitespace. Full-repository Ruff/Mypy were not rerun.

Final independent review accepted the finite source/evidence candidate, with no
product blocker. Its report and receipt are included with the evidence; publication
is verified separately after the normal development-branch push.

Checked-in evidence is under `docs/evidence/ordinary-spec-rejection-terminal-20261016`.
Original logs/XML, case archives, all intermediate passes/failures, preservation
snapshots and review history remain at
`/workspace/ordinary-rejection-evidence-20261016` and
`/workspace/ordinary-rejection-review-20261016`. Raw final cases remain at
`/tmp/ordinary-terminal-verified-20261016`. Before/after full source manifests are
`/tmp/ordinary-terminal-verified-source-{before,after}-20261016.json`.

## Failure history, cleanup and limits

Preserved baseline RED: strict rejection made no closure request. The first
implementation protocol run failed on an API-helper signature and was fixed.
Backend rounds 1/2 exposed test-oracle assumptions (confirm 200 vs 201;
OUTCOME_UNKNOWN 400 vs 409), corrected before passing. Independent review identified
a pre-insert fault injection and an ineffective late-GET assertion: the final
suite instead injects after INSERT execution and tests exact-key replacement/UI.
Initial 14 Ruff findings and the later single import-blank-line finding are retained,
fixed and covered by the final exact-source suite. Earlier PASS records never
substitute for the final revised tests. The original handoff text remains in the
preserved-untracked snapshot; old blocked review reports remain historical records.

ENOSPC was diagnosed as capacity, not inode exhaustion or an authorization refusal.
After explicit user approval, only `/tmp/run-private-2b-baseline/.mypy_cache` was
removed after checking cache signature, no symlinks and no detected process references.
It released **53,907,456 bytes**; the other 10,207 parent files retained their recorded
size/mtime. No other evidence/cache directory, unknown lock or process was removed.
Uncommitted source originals, tracked patch, exact untracked text and hashes were
preserved. The prior complete evidence bundle SHA remains
`6b96a866ce5ecdf058c7715f177a96124a988136c17a810c431be009f9109429`.

Main/core remote heads, original WIP files, anchors and qualification remain unchanged.
No deployment, force push, credentials or security permission changes occurred.
Native browser, Windows, PostgreSQL, old-source schema upgrade, network-server /
Worker-process restart, full P-A/P-B, real models and remote CI: **NOT RUN**.
No semantic qualification or complete production acceptance is claimed.
