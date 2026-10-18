P-A saved unseen input: one synthetic current-page case
======================================================

Draft `test_pa_unseen_input_ui.py` is intended beside the UI author's
`pa_unseen_input_ui.cjs` under repository `tests/`. The CJS contract read was
SHA-256 `d220ad72ff1a0d73cf72a7de40c99ccbb7e50eb699693fa83d39d8af72f807b2`.
Initial actual checkout read was `304bff97584ac157d56597f5ab52ea7f5ecb1d9f`.
Only this new external directory was written; prior drafts/sealed evidence,
repository source and Git were not edited.

Current qualification is Python compilation and Ruff only. No pytest collection,
product HTTP, database/Worker execution or model call was performed while
authoring. Counts below are expectations asserted by the draft for a later
frozen actual run, not results already observed.

The self-built fixture uses Store, mock Settings with `intern-s2`, a synthetic
identity and normal project/material/Goal APIs. The unchanged existing
`ready(data,'single')` generation oracle produces the saved P-A app, Release and
instance (3 MockTransport requests). One normal Worker call produces SOURCE v1
(1 mock). THIRD and `A` repeated 2049 times are saved as real TXT resources, each
with its own matching Goal. There is no P-B extraction, close fixture or fixture
owner PREPARE/DECIDE.

Only pure `trace_http`, `header`, `once` and SHA helpers are imported from the
existing result-navigation test module. Its fixed P-B manifest/seed/test is not
used. This file defines its own source/test-input manifest including this file,
its CJS and the helper source. The two business phase names are `pa-v1` and
`pa-v2`, so helper evidence cannot overwrite `source-before.json`.

The actual page discovers the P-A app and instance through the unified directory
and selects v1. It explicitly PREPAREs the fresh returned contract, chooses
ACCEPT and fills a fixed `SIMULATED_TEST_ONLY` reason for each item, acknowledges
and explicitly DECIDEs. The bridge independently checks ordered item IDs,
current contract fingerprint, sequence, original review ID/fingerprint, full
request hashes, immutable row payloads and both seals. This creates exactly two
owner records and two seals, with every other table unchanged. These automated
fixture gestures are not a real human semantic judgment or signoff.

The accepted snapshot is the next baseline. The page selects the normally
available 2049-byte TXT resource and its matching saved Goal. Exactly one real
`pa-use-reviews` request must return `400 INVALID_INPUT` with the actual source
bound error. All database tables, Run/Grant counts and model request counts
remain unchanged. No mismatched Goal, poisoned response, fault injection,
recovery window, download or adjacent failure matrix is used.

The page then selects saved THIRD and its Goal, explicitly reviews and consents
to one new per-use Run. The exact original-key GET verifies that accepted Run.
One cold Store and one normal Worker call produce v2 (1 mock); no clock, lease,
deadline or success row is altered by the test. The expected full case therefore
has 5 actual mock requests (3 generation + 1 v1 + 1 v2), two business Worker
calls, one generation Worker call and one page-requested Worker call. It does not
have two model nodes or six business steps.

The queued database delta is exactly one Run, AppRun, immutable contract and
binding, six existing metadata rows (`spec.RUN_META`, `PA.meta`, `PA.use` and
their seals), and one runtime READ Grant for THIRD. Completion adds a single
typed version 2 and JSON artifact, four verified operations/intents, one local
effect, attempt, reservation and owned Worker heartbeat. The existing offline
request/response archives add four rows, making ten new journal rows in total.
Both pairs' original base64 body bytes, byte counts, SHA-256, canonical response
hash, attempt wire seal and actual captured model payload are checked exactly.
The normal saved artifact adds two derived READ Grants for owner and runtime;
the page has three new READ Grants overall and zero new SAVE Grants.

Original app/runtime/Release/instance identity, Goal rows, v1 typed data, saved
artifact and both old owner records/seals stay unchanged. The instance advances
only its data version from 1 to 2. Old accepted v1 becomes metadata-only STALE;
v2 has a fresh sequence-zero PENDING owner ledger and does not inherit the old
synthetic declaration. A whole second JSDOM boot explicitly rereads both machine
Runs, owner states and saved artifacts through GET only. Both versions' exact
Run/version/source/resource/output hashes and artifact response bytes are
independently checked. Every one of the 27 served assets is hashed on each boot.

The fixed IPC is one `worker {run_id}` plus `checkpoint {phase}` with phases
`seed-readonly`, `v1-simulated-owner-accepted`, `oversized-preview-rejected`,
`v2-queued-before-worker`, `v2-complete-after-manual-refresh`,
`cold-two-versions-readonly` and `final-readonly`. All page POSTs use the original
UTF-8 `body_text` through TestClient `content=` with exact byte comparison and
the page's own Authorization header, without an authenticated bridge default.

The observer flushes actual HTTP request/response bytes and hashes from normal
fixture setup onward, generation/runtime wire by phase, original owner requests
and contracts, checkpoints, complete snapshots, claims/accepted clocks, raw
Node stdout/stderr, page progress/actions and production/test hashes before and
after. `finally` preserves partial rows/wire/claims and closes only owned
clients/engines/Node. Node has an owned 900-second watchdog; the parent supplies
the separate outer 900-second execution bound.

The parent must adopt and freeze source plus tests before actual execution.
This one synthetic page path is not complete P-A coverage. Native browser,
Windows, live models, real human/semantic acceptance, PostgreSQL, deployment and
remote CI remain unexecuted and are not claimed.
