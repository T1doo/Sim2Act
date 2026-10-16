# Recovered ordinary-spec Run: explicit cancellation and stale-page rejection

Baseline: `f29f5a3305567edc44ae54d95c899c6af65129e9`.
Branch: `dev/ordinary-spec-recovered-cancel-20261016`.
The existing control API, executor and page already support this finite path.
Only the three existing process/page test drivers, this report and evidence change.
There is no product `src` or `pyproject.toml` change, and no full F2-T09 acceptance.

## Executed contract

The saved six-step sequential natural-spec fixture uses three explicit mock
generation responses. Document 1 submits exactly once. Its actual HTTP 202 is
received by a delivery-loss test adapter and withheld from the page, retaining
the real minimal durable original-key record. No Run, product Map, lease, clock
or durable recovery record is injected.

The actual old Worker executes its first model step. The existing observer waits
only after the original `pa_spec_apps.advance` and its transaction have returned,
with zero active senders, two VERIFIED operations, one VERIFIED Attempt, no
UNKNOWN, data or artifact effect. A real authenticated versioned pause command is
accepted; the observer is immediately released. The original executor settles
Run and AppRun PAUSED with lease zero, and the old Worker exits normally.

Old Worker PID **1217556 / starttime 44633131** is replaced by PID **1217566 /
starttime 44634226**, with a different worker_id and the same SQLite URL. Every
child forbids `Store.initialize` and reports zero calls. The new Worker performs
two original `Worker.once` probes around Document 2 recovery: both return False,
with zero model calls and an unchanged selected execution snapshot.

Document 2 loads the full real page assets and authenticates normally. Its
original-key GET returns the same key, Run and AppRun at PAUSED. It consumes the
original durable intent without another execution POST. Its actual visible,
enabled resume button and original event handler remain in that document.
Document 3 authenticates normally, opens the same instance and reads the same
PAUSED Run through normal history GET. It does **not** claim a second durable-key
recovery. Its explicit visible cancel click sends the current frozen version 3
and receives HTTP 200/CANCELLED. Run and AppRun settle CANCELLED immediately;
cancel_intent is preserved and version becomes 4. Only Run status/version/intent
and AppRun status change in the selected snapshot.

Returning to the retained Document 2, the test clicks its original visible,
enabled resume button. The actual authenticated version-3 POST for the same Run
receives HTTP 409/VERSION_CONFLICT, and the page visibly renders that error.
Separately, a parent-authenticated resume using the latest terminal version 4
also receives HTTP 409. This second HTTP probe is distinct from the old-page
gesture. After the visible conflict, normal refresh, instance selection and Run
selection show the same CANCELLED terminal on the old page.

The new Worker performs two more original `Worker.once` probes, after cancel and
after stale resume: both return False, with zero model calls. The selected final
snapshot remains identical across those probes, both rejected resumes and repeated
authorized readback. The complete project Run-ID set, binding/frozen clock,
verified operations, Attempt and reservation prefix remain identical to PAUSED.
There is one AppRun, zero result versions and zero artifact effects. The observed
Run deadline remains original created_at+300 seconds; configured lease is 30
seconds. These are bounded probes after graceful safe-step exit, not arbitrary
in-flight crash, UNKNOWN reconciliation or indefinite scheduler fault coverage.

Identity throughout the cancellation case:

- request_key: `90c64a9b-67f5-42bf-91d3-b09be794e1c8`
- Run: `run_1326983f04e54a65902a3d91c8157c0d`
- AppRun: `iapprun_07719acacb20406ea4c33669374609b7`

## Actual validation and failure history

Final suite: **10 PASS, 0 FAIL, 0 SKIP, 0 ERROR**, XML **237.829 seconds**;
one existing Starlette/TestClient deprecation warning. This includes both resume
and cancellation process cases and the previous eight related recovery cases.
The prior resume path still produces exactly one result version and one effect.

```
env -u SIM2ACT_TEST_DATABASE_URL PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
 /workspace/Sim2Act/.venv/bin/python -m pytest -p no:cacheprovider \
 tests/test_safe_step_process_recovery.py tests/test_spec_run_terminals.py \
 tests/test_durable_recovery_protocol.py tests/test_internal_submission_rejection.py \
 --basetemp=/tmp/ordinary-cancel-final-20261016 \
 --junitxml=/tmp/ordinary-cancel-recovery-20261016/final.xml -q
```

The cancellation case records **26 actual-HTTP JSDOM checks**, **141 HTTP
responses**, **3 document objects** and the exact **63 HTML/CSS/script assets**,
all hashes checked against executed source. JSDOM, file-backed Storage/Web Locks
and disabled automatic polling are explicit test adapters, not a native browser.
Mock model counts for this case are fixture **3**, old runtime Worker **1**, new
runtime Worker **0**; these are not aggregate counts for all ten tests.
Four owned children use exact PID/starttime/argv/nonce records. Workers and page
exit 0; the owned API is terminated during cleanup (exit -15). Cleanup passes;
unknown processes are never signalled and existing files/caches/locks are retained.

All **526 src/tests + pyproject.toml files** match before/after both process cases,
the complete final suite, and the archived source snapshot. Manifest SHA256:
`27cc152678f9e9073a33829af270c918295a1ef6ea0aa14c900a2233b31212b3`.
Both Python drivers pass Ruff; the CJS driver passes syntax checking.

The first run is preserved as **1 FAIL, 1 DESELECTED** in **67.89 seconds**. Its
24 successful page checks already include cancellation and visible stale-resume
rejection. It then failed in the driver: VERSION_CONFLICT correctly invalidated
the page's instance selection, but the driver refreshed and tried selecting a
Run without selecting the existing instance again. Adding that ordinary page
selection fixes the test navigation. This was not a product failure. The original
three driver files, first raw case, source closure, error/log/XML and final
rerun remain available; no failed history is overwritten.

## Evidence and preserved limits

Committed evidence: `docs/evidence/ordinary-spec-recovered-cancel-20261016`.
It contains exact compressed snapshots/receipts, XML/logs, source closure and a
compact **derived** page proof: every HTTP body has its UTF-8 byte length and
SHA256, while keyed-receipt/control responses retain their full text. The full
original page response bodies and additional HTTP trace are not duplicated in
the compact committed view. `RAW_MANIFEST.json.gz` hashes every first/final raw
file. Disk limits required this distinction; no prior evidence was removed.

Full original SQLite, page/HTTP proofs and process files remain under
`/tmp/ordinary-cancel-first-20261016` and `/tmp/ordinary-cancel-final-20261016`.
The complete source/originals/failure/publication bundle is produced at
`/tmp/ordinary-cancel-complete-20261016.tar.xz`, with its external index, after
publication. Original files remain in place. Independent read-only review checks
the final executed closure and the distinction between original and derived data.

The **128-binding** terminal absence scan cap is unchanged. Strict observation
of database row-lock waits is still NOT RUN. The historical `2b7068d` child was
TestClient/Store, not Worker; this evidence does not retroactively expand it.
Only the identified old/new Worker pairs establish their stated finite paths.

PostgreSQL, Windows, native browser, arbitrary in-flight crash/UNKNOWN recovery,
API/network restart, old-source schema upgrade, broad cancellation/revocation/
version-race matrix, real provider/paid API, full P-A/P-B, semantic/owner acceptance
and remote CI remain **NOT RUN**. No main/core changes, force push, deployment,
new fees/credentials/security permissions/model access or unknown-file cleanup
are part of this slice.
