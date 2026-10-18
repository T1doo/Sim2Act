P-B original-key close: actual page bridge draft
================================================

Adopt `test_pb_extraction_close_ui.py` beside the new backend module
`test_pb_extraction_close.py` and the UI author's `pb_extraction_close_ui.cjs`.
The bridge was written against CJS SHA-256
`8ebd6284c8f9ebd78e42e91723b3e2c566879e82d8483155cea6da6868027b2c`.
Only this external directory was edited. No collection, product HTTP, Worker or
model execution occurred while authoring the bridge. Compilation and static
Ruff are the only checks performed here.

There are two page cases: `preaccept-close` and `accepted-refuse`. They import
the completed backend fixture `pb_extraction_close_seed` and `CloseCase`; no
generation oracle, seed builder or old cold-page fixture is copied or invoked.
Only the older module's pure `assert_one_extraction` and `assert_assets` helpers
are imported. The new fixture makes one fresh SOURCE seed per pytest process:
three generation mock requests and one source Worker inference request. Running
backend and UI in separate processes means two independent fresh seeds, hence
eight mock requests when both seeds actually complete. Each page case invokes
zero Workers/models and begins with an exact physical clone of its shared seed.

In `preaccept-close`, the CJS fixture captures the original extraction envelope
before API dispatch and throws a controlled client error. The normal page
callback releases its own Web Lock, then the old entire JSDOM closes. The fresh
page makes an explicit original-key GET (actual `OUTCOME_UNKNOWN`), an explicit
close POST, then a separate terminal GET before forgetting the original raw
ticket. The transport fixture dispatches the captured original envelope once;
the real API must reject it with 409. Only a new explicit review and confirmation
may create a distinct key and one accepted application. This controlled delivery
fixture is not presented as actual network or database concurrency; the backend
suite separately exercises real overlapping SQLite transactions.

In `accepted-refuse`, the original extraction really returns 201 before the
fixture loses its response. The cold page's close POST must return 409 and add no
rows. The page then obtains the original accepted receipt and fresh application
through GET, preserving the existing app rather than replacing or resubmitting it.

Every body-bearing CJS HTTP envelope must supply `body_text`. The bridge encodes
that exact string to UTF-8 and uses TestClient `content=raw_bytes`; it never
re-serializes through `json=`. It compares the resulting actual request bytes
with the captured bytes, saves their hashes and forwards the page's real headers.
A separate bridge client has its default Authorization removed so that fixture
credentials cannot mask a missing page header. Requests and response bytes are
flushed by the existing shared observer and new backend trace helper.

The four IPC checkpoints are strictly checked against independent database state:

- `zero-effects-checkpoint`: every row equals the current baseline before API
  receipt or after the late closed-key rejection.
- `closure-checkpoint`: independently reconstruct full ExtractInput and all 17
  identity fields from the actual earlier review, check the exact terminal
  receipt, and permit only its two sealed journal rows.
- `extraction-accepted-checkpoint`: permit one app, one runtime, two existing
  derived Grants and exactly four existing extractor journal rows. For a new key
  after closure, both old terminal rows remain byte-for-byte unchanged.
- `readonly-checkpoint`: compare every table/row with the latest baseline.

No resources, business artifacts, Release, instance, Run, attempt or typed result
may be created by these page flows. Original source app/result/history rows are
preserved by the full-table comparisons. Each complete page boot loads and
SHA-256 verifies all 27 production-served assets. The bridge records raw stdout,
stderr, IPC, every HTTP request/response, review receipts, checkpoints, seed
provenance, final rows, original source claims/clock, page checks/actions,
Storage/Web Lock events, transport controls, and source/test hashes before/after.
Failure evidence is saved in `finally`; only the owned Node process has the
observer's 900-second watchdog. The parent supplies the outer pytest bound.

Before treating these drafts as acceptance evidence, the parent must adopt and
freeze the actual production source plus both test files and execute them. Native
browser, Windows, PostgreSQL, live models, real semantic acceptance, deployment
and remote CI remain outside this bridge's qualification.
