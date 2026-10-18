# Limited source review — current collection JSON export

Reviewer: non-author, read-only product/test review. No product, pytest, Worker, SQL, DB, network, credential or holdout access was executed by this reviewer.

No P1/P2 found in the reviewed implementation. `local-records.js:184` explicitly reads the selected instance afresh, then uses the existing complete projection validator. That validator checks app/principal/project/runtime/instance/Release bindings, exact event fields, per-event hashes and the folded current records. The exported top-level fields, records, history and artifact metadata are selected explicitly. The nested event is already constrained to the existing exact event schema. Pending Runs and controller/request/Grant/token state are excluded.

The existing identity, connection, project, workspace, app-generation, read and instance-selection fence remains checked after the HTTP read, after each asynchronous hash and before Blob creation/click. Busy state blocks duplicate export clicks. The link is removed and object URL revoked in `finally`. The selected historical Run is not replaced by the current collection reply. A current read failure clears protected cached content; the normal busy cleanup disables export without an instance. This does not change any API, executor, Grant, server write, durable intent or control contract.

The single new scenario has an A/B/A-DONE fixture and a fourth queued, unexecuted request; three fixture Worker IDs/time windows/claims are captured. It checks two Blob payloads including a cold page, old Run v1 alongside current collection v3, one GET on double click, a held read followed by another instance selection, and fresh READ denial. Page execution is read-only; the one known Grant revocation is an explicit fixture bridge action. This review does not count checks as pytest cases.

The capability inventory distinguishes bounded implemented functionality from semantic, production-source, formal-publication and platform requirements. Its T06 missing-export and no-new-qualification statements describe its stated `9b94` baseline; the final delivery should identify this new slice as completing that specific baseline gap. Generic chart composition and wider semantic patches remain unsupported code scope, while a token alone cannot install a trusted production source or LIVE controller.

Actual execution results are deliberately deferred to the sealed evidence review; no runtime PASS is awarded by this static note.
