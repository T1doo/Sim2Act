# Local record UI: independent limited review

Production commit: `d5eadc708ee2968bb574ec66e335c05451f66cf7`. UI bytes are identical to `a38c33f7496dca3da079d59bab16f13b5c283d1e`; tests were frozen at `81ad223bf72fb6e15af03ef6aca87af70e9bf4f8`. Baseline: `5322dfd7f8c6686be29c9989d2f02fb6f54cfc28`.

**Limited conclusion:** no remaining definite P1/P2 issue was found in the reviewed UI/controller and actual HTTP-receipt integration scope. The earlier P2 was fixed and is covered by the final real revocation scenario. This reviewer performed non-author source review, proposed the additional bounded revocation test, and independently read the root-executed raw results. It did **not** independently execute the full UI suite or any Worker.

## Finding and correction

P2: prior full original-key recovery replies contain record title/details in the recovery proof. Previously Refresh failure cleared only collection/history/Run proof while leaving that recovery body, and Recover failure only changed status. A current 403 could therefore leave revoked private record text visible.

The frozen fix is `localRecordsClearPrivate` (lines177-180), called by current Post, Delivery, Refresh and Recover error branches (lines133,157,244,311). It invalidates read/edit generations, clears current collection/history/Run/preview/recovery bodies and record form fields, and retains the exact original request key plus intent map. It does not mark a background Run failed. No repository file was changed by this reviewer.

The added third test scenario starts from exactly one genuine synthetic seed. The page first reads its successful Run and uses original-key GET to restore the body, then a closed fixture-only RPC revokes exactly its known artifact owner resource.read Grant. The real Refresh GET and original-key GET each return403. Both clear all old text/form fields, preserve key/stage, perform zero page POST and zero page Worker. Whole-database assertions allow only that known Grant's revoked/revision change; original Run rows and all other rows remain unchanged. The RPC cannot select arbitrary Grant/principal/project or resource, and is callable once only in this scenario.

## Final raw results independently read

Root final batch `ui-d5eadc70`: **3 PASS, 0 FAIL, 0 ERROR, 0 SKIP**, JUnit 50.029 seconds; all three Node processes exit0. This review did not launch that pytest process. Its three scenarios record132 check labels:

- flow-recovery:62 checks,56 page HTTP actions,10 explicit POSTs,3 page NoModel Worker calls. It creates the app, separately prepares/commits Release and creates/selects the instance, then performs CREATE A, CREATE B and SET_STATE A→DONE. One accepted receipt is deliberately lost after actual HTTP, and only explicit original-key GET recovers it. A cold page preserves old OPEN event beside current A DONE@2 and unchanged B OPEN@1.
- navigation:36 checks,60 page HTTP actions,zero page POST/Worker and one fixture seed. Controlled late actual HTTP responses are isolated across instance selection, Run deselection, original-key recovery, workspace ABA, new-app navigation, project ABA and same-account reconnect.
- revocation:34 checks,18 page HTTP actions,zero page POST/Worker and one fixture seed; the two actual GET403 paths cover the resolved P2.

All served asset hashes (54/27/27 across2/1/1 boots) match the frozen files. Every final per-case source-before/source-after manifest is unchanged and matches exact d5 Git bytes. Read-only SQLite inspection found5 distinct successful Runs across the three fixtures, each with one claim/fence1, zero attempts/reservations, and unchanged database file hashes during this review. These are synthetic NoModel engineering results, not real semantic acceptance.

The preceding root batch `ui-final` also has3PASS, JUnit49.484s on the same UI bytes. It is kept as a separate earlier phase; it is not six unique cases or an independent rerun. The d5 change from a38 is limited to Python type narrowing and an assertion after an existing rejecting guard.

## Bounded source review

`localRecordsCurrent/Fence` capture identity, connection, project, workspace/app epochs, view identity, instance selection, read and edit generations. Each POST sets its scope intent and sending/busy lock before its first hash await; every hash/HTTP await checks the captured current predicate before adoption. UNKNOWN requests retain their original key and cannot automatically POST or change key. Explicit recovery usesGET; acceptance never claims a successful business record before the same Run is read. The scene runner's double clicks demonstrate one accepted write per explicit phase.

Creation, Release approval/commit, instance creation/selection and typed preview/commit are separately reachable. New family metadata routes to its dedicated controller and does not automatically create a version or Run. Canonical event hashes and linked previous collection/record hashes are folded into the collection; the same Run's event/output/verified receipt must match that history. Original artifact.save_text output remains the real resource_id/hash, while current records are explicitly separate adapter projections. The new UI uses textContent and fixed DOM elements for names, record bodies, reasons, proof and error text; no user content is inserted as HTML.

## Remaining scope limits

The actual navigation test controls HTTP response delivery. Hash-await current checks were inspected statically; no separate held-crypto runtime probe was executed. This was not a full independent backend/lease/recovery-matrix audit. Native browser, Windows, PG, real model, real semantic acceptance and remote CI were not run. Prior API tests and earlier pre-fix UI tests retain their own execution evidence and are not counted as this final three-case result.

Raw source/result paths, hashes, per-scenario counts and read-only DB observations are recorded in `final-ui-review-proof.json`. Original author outputs remain at `/workspace/local-record-state-evidence-20261018/ui-d5eadc70{.log,.xml,/}` and the preceding `ui-final` paths.
