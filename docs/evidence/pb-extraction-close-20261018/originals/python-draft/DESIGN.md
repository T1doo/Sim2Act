P-B unaccepted-key closure: bounded backend acceptance draft
===========================================================

Scope and qualification
-----------------------

Parent alone writes `/workspace/Sim2Act` and Git. This directory contains only a
draft test module and this design. Current read checkout was
`3d1a3160fda6e9bfead96fae8a40935617270da4`, with approximately 25 GiB free.
No product/model execution or pytest collection was performed in this authoring
turn. Compilation and static lint are the only local checks. Existing cancelled
P-B installation windows and old recovery matrices are excluded.

The parent froze `CloseInput={identity,consent}` with the existing strict 17
scalar recovery fields. Consent is
`CLOSE_ONLY_THIS_UNACCEPTED_PB_EXTRACTION_KEY`. Only the original by-key URL gains
POST `/close`; its GET gains a terminal receipt alternative. No executor,
principal, Grant, application, Release, instance, Run or business artifact is
created by closure. The only permitted effect is two existing journal rows on
the source Run ID, kinds `pb_natural_spec_terminal` and its `_seal` companion.

Seven actual cases after parent adoption/freeze
----------------------------------------------

1. Unknown original-key GET is read-only. Close yields the exact independent
   terminal receipt; same-close replay and a fresh Store/engine GET agree.
   Original and changed late extraction bodies are both rejected. Changed
   metadata on the same closed key is rejected, with all rows preserved.
2. After an explicit normal target Goal update and real target owner-read Grant
   revocation, the original unaccepted intent can still close and recover its
   terminal receipt. A private-cell SQL barrier proves neither operation depends
   on target material bytes. A late extraction must return the terminal conflict
   before any target-body access; only the two terminal rows are appended.
3. A normal extraction accepted first remains accepted. Close returns
   `409 VERSION_CONFLICT`; accepted by-key GET and same-body idempotent extraction
   still recover the unchanged original app. No terminal rows appear.
4–5. Two independent Stores/engines, clients, request threads and DBAPI
   connections race close versus extraction in both forced orders. The first
   transaction is held after the actual project lock. SQLAlchemy observers prove
   the second independent connection reached `BEGIN IMMEDIATE` while the first
   remains held and the second BEGIN has not completed. A bounded test event
   releases the first; the second BEGIN then completes. Request order, physical
   connection IDs, handler thread IDs, SQL entry/completion and all responses are
   saved. There is no sleep-based ordering, model call, old digest hold or second
   actor prepare window. Every gate/listener is released/removed in `finally`.
6. One bounded scope/authority case covers foreign identity, wrong owned project,
   source-instance/proof/version anchors, strict-schema extra-field rejection,
   and actual source-read revocation. Private-cell barriers cover foreign and
   revoked calls before original protected Run/material/artifact bodies. A
   separate exact seed copy applies a real source Goal update and proves the old
   source identity cannot close. Refused calls add no rows.
7. Each synthetic corruption starts from a genuine API-accepted extraction or
   genuine API-closed terminal. Remove only named known fixture rows: one
   extraction seal remains after marker/body removal; or derived app/runtime and
   grants remain after marker/four extractor journals disappear. Both must stay
   `OUTCOME_UNKNOWN`, including one spoofed prospective app/runtime identity.
   A single surviving terminal seal gives `VERSION_CONFLICT` on GET/close and
   permanently blocks extraction. Finally, raise after the first actual terminal
   INSERT through a test-owned SQL observer: HTTP fails, every row rolls back,
   original GET remains unknown, and a later explicit same close can succeed.

Fixture and shared UI bridge contract
------------------------------------

`pb_extraction_close_seed` is module scoped. It uses existing SOURCE generation
oracle unchanged via a fixture-module-only `SimpleNamespace` transport observer:
three mock requests. The ordinary source Run has one normal `Worker.once()` and
one mock inference; actual CLAIMED events and the unchanged accepted clock and
created-at timestamp are recorded. COLD is saved and reviewed through normal
HTTP. The seed adds no unrelated project, instance or cancelled Run. All owned
connections close before `shutil.copy2`; any unexpected WAL aborts sealing.

Every `CloseCase(seed, folder, observer)` starts with a physical copy whose bytes
match the sealed seed SHA-256, then verifies all database rows before any case
request. It exposes `store`, `settings`, `client`, `info`, `identity`, `commit`,
`path`, `by_key()`, `close_body()`, `close()`, `read()`, `submit()`, `cold()` and
the fixed-resource real `revoke_read()` helper. It never initializes a clone,
changes its clock/lease, edits success rows or mints extra success evidence.

`seed['info']` provides project/principal and source app/name/instance/Run/AppRun/
Release/fingerprint/result-version/resource/artifact plus target card/resource/
hash and synthetic source/target content. `seed['identity']`, `['review']`,
`['commit']`, `['sealed']`, `['seed_sha256']`, `['settings']` and `['rows']` are
also available. A separate UI pytest process creates its own fresh seed; actual
mock counts must report 4 per process (8 for two independent backend/UI seeds),
not imply cross-process seed sharing.

Evidence and limits
--------------------

`_PageObserver` flushes progress and errors. HTTP response and request bytes are
stored separately with SHA-256, status and exact parsed request metadata; a
shared trace lock prevents concurrent response-file collisions. Seed proof,
generation/inference wires, Worker claims and clock, copy provenance, full
before/after rows, original/terminal receipts, named fixture damage, transaction
overlap events, rollback observations, revocation receipts and SQL barriers are
saved. Each case records source and relevant fixture/test hashes before/after,
including on failure. All threads/gates/listeners/clients/engines are owned by
the test and bounded; the parent must supply an outer timeout for actual pytest.

These are SQLite/TestClient backend cases. They do not prove native browser,
Windows, real semantic/human acceptance, PostgreSQL, live models, paid services,
deployment or remote CI. Cap 64 is part of the frozen production contract and
independent review; this bounded suite does not loop through 64 expensive source
proofs or fabricate a capacity-filled table.
