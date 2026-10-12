# F2-T09 / AT-05 / AT-18 finite P-B cold recovery: read-only design review

Baseline: d5b3f47dbb14ce7d11e822b1ce37cac02e3eb408. This is a design review, not test execution or acceptance. Seventeen targeted committed source files were copied to the independent /tmp directory. The parent had already started unfrozen implementation when the working-byte snapshot was taken; eight relevant working paths differ from baseline and are explicitly listed. No shared files, old224 artifacts, Git state or application data were changed by this reviewer.

V5 §6.4 and §8.3 require durable identity before dispatch, status recovery after closing a page, and no blind replay when lack of a receipt does not prove failure. F2-T09 requires actual reliability chains; AT-05 says an accepted task has a durable record before page closure; AT-18 distinguishes same-key idempotence from a new explicit logical request. This slice remains local app-draft extraction with existing literal logic. It must not relabel source Run status, create fake Worker Operations or claim the full reliability/platform contract has passed.

Use a dedicated bounded intent journal rather than PENDING/CLOSED sentinels in task_extractions. Existing task_extractions requires non-null app_id and snapshot and already anchors committed effects. Reuse it as the authoritative COMMITTED receipt and retain the existing independent exact derivation, current-source authorization, target authorization, receipt and candidate installation checks. One journal table with immutable body, actor/project/source instance+Run scope, key, creation sequence, state/revision, body fingerprint and separate target metadata can support the finite slice. The existing project transaction lock serializes prepare, close and extract. A second execution engine, model, Grant or operator is unnecessary.

Prepare persists the complete finite extraction request and original key before extract is sent. The full request contains scope IDs, source proof fingerprint, selected existing target/fingerprint and name; it should not contain access tokens, provider credentials, model messages or copied material content. The server computes fingerprints and current authorization; strict input rejects control/private fields. Same key and same logical request is idempotent without advancing latest backwards. Same key and a different request conflicts. A new key requires an explicit user action and expected_latest_key CAS; unresolved PENDING blocks it even if a GET currently finds no accepted task row.

Never clear the latest high-water pointer to null when closing. CLOSED remains a tombstone and keys are never reused or reactivated. Otherwise an old expected_latest_key=null can become valid again after another request is created and closed. Same-key prepare of an older record may return its record state, but must not replace a newer latest pointer or make an old request active.

Extraction must check the journal in its own same-project-lock transaction, including direct API calls. A CLOSED key cannot create a draft. Two draft/marker inserts and journal COMMITTED must commit atomically. A late original extract and explicit CLOSE share the lock: whichever commits first decides; if an accepted task row already exists, CLOSE returns COMMITTED and does not write a false CLOSED/no-effect receipt. Journal PENDING plus missing task row is not proof of failure because a request may still arrive later. Legacy committed task rows may remain read-compatible without automatic backfill; unjournaled new text POST must not bypass the new pending/CLOSED/latest gate. Original CSV behavior stays separate.

Cold discovery and reconciliation are GET-only. Discovery returns only the minimum owner-scoped metadata: key/state/sequence/revision and source/project/principal IDs. Full name/request, source proof, candidate and source content are returned only after current source and target authorization. Store target_app_id separately as metadata so authorizing target does not first require reading the protected request JSON. A metadata-only scope helper can join Run project/principal, binding app_run_id and AppRun instance/principal without selecting full Run, binding snapshot, input, output or receipt. CLOSE after resource revocation uses only that metadata and accepted task app_id/request-fingerprint pointers; it must not call protected source verification or read journal body.

A COMMITTED server effect does not prove a browser installed it. Retain current showApp pre-install candidate/request/key/hash checks. Do not invent a server installed state; a fresh explicit request can instead require a verified committed effect plus a new explicit user action, with UI installation separately qualified. An acknowledged browser result is not human semantic acceptance. New owner stays PENDING/unsupported task-owner entry, semantic UNKNOWN, LIVE0 and formal publication false.

Do not persist request bodies or secrets in localStorage, sessionStorage, IndexedDB, cookie, URL, window.name, service-worker caches or other browser recovery stores. Existing token is memory-only. New protected recovery responses should be Cache-Control:no-store and sensitive client fetches use no-store. Actual HTTP headers and storage-call refusal probes are inspectable; JSDOM cannot prove native browser cache behavior.

Every discover/key/body/receipt/digest/install await, success, inner error and outer catch needs frozen scope plus a monotonic read generation. Context includes workspace/app/goal/identity, source instance/Run and material/name edit generation. Old PENDING and old errors must not overwrite a newer COMMITTED/CLOSED view. Same creation sequence with a current legitimate state change is possible; read order cannot rely solely on sequence or a severity lock. Programmatic reconstruction must not overwrite a user's edited form or steal focus after navigation/edit/undo ABA.

Cold revocation needs a visible metadata path. The current source app opening path reads protected app/releases/instances and can fail after revocation; the current control-status fallback helps only an already-open view. If cold CLOSE is claimed, use an owner/project minimal intent index reachable without protected app details, then explicit selection and authorized body recovery. A bare close API alone does not prove cold-page reachability. If scope is deliberately narrower, document that boundary.

Minimum refusal and crash matrix for later frozen-source execution:

| Scenario | Required result |
| --- | --- |
| Prepare committed, response dropped, page destroyed | Fresh page discovers original key by GET; no auto prepare/extract POST |
| Intent PENDING, extract never reaches server | Fresh GET keeps PENDING/blocked; no failure inference or replay |
| Extract transaction committed, response dropped | Fresh original-key GET returns exact existing app; candidate validated before installation; no duplicate |
| Extract rolls back/crashes before transaction commit | Durable PENDING remains; neither draft nor accepted marker exists; explicit close is required before new intent |
| Concurrent same key/same body | One logical app effect and one durable identity |
| Same key/different body or CLOSED-key reuse | Conflict, no journal/body/draft mutation |
| Two tabs prepare new keys from same latest | Exactly one accepted CAS; stale tab conflicts |
| Close then late extract; extract then close | CLOSED blocks effect in first order; second order returns COMMITTED, never false cancellation |
| Source/target grants revoked after prepare | Body/receipt/candidate restoration denied; owner metadata CLOSE remains reachable and reads no old body |
| Foreign owner/project/instance/Run/key | Reject before protected Run/journal cells; no writes or existence/content leakage |
| Missing/tampered journal/body/accepted marker | Do not self-resign or downgrade proof; preserve explicit failure and no new effect |
| Stale same-key read/error after new COMMITTED/CLOSED | No render, state reset, focus or draft mutation; all outer catches qualified |
| Edit/undo, target select ABA, navigation/identity ABA | Monotonic context invalidates old response; current unsaved form intact |
| Poison minimal index, key receipt, reconstructed body, actual candidate | Exact scope/key/fingerprint/request binding rejects wrong adoption/installation |
| Browser storage or response cache checks | No protected body/secret recovery storage; actual no-store HTTP headers; native browser still NOT_RUN |
| Explicit close/reconcile then fresh request | New key/sequence/app ID; original key/history retained, normal cold literal Worker reuses existing execution path |

No tests or real provider calls were started. Future evidence must distinguish actual SQLite/API/Worker/fresh HTTP/JSDOM chains from controlled persisted-data faults, local scheduling probes and unavailable native browser/PG/Windows/real-model/real-owner/full F2-T09/AT-05/AT-18 coverage. Original source audit dependency remains; this slice does not retire original content or change operators.
