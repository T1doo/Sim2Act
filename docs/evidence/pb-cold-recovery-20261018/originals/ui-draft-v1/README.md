# P-B cold-page recovery CJS author draft

Only this isolated directory was written. The parent owns repository integration, production freeze, independent review and actual execution.

`tests/pb_cold_recovery_ui.cjs` loads the actual index, CSS and every production script via bridge HTTP on every boot. It acts through visible/enabled controls. It never stages the production pending Map, calls a Worker, or creates a target Release/instance/Run. The Python bridge owns the genuine source fixture and all database assertions.

The five bounded bridge cases use `flow`, `navigation`, `boundary` with source/target revoke kinds, and `platform`. They cover:

- Actual accepted201 lost after commit, double-click suppression, closing the whole old JSDOM, a new boot sharing browser persistence, original readonly key, zero automatic recovery GET/POST/UUID, explicit original-key GET then fresh app validation and explicit open.
- Independent canonical SHA256 and exact17 scalar ticket fields, tied to the complete actual POST, complete reviewed candidate, fresh source proof and seed anchors. No key-only self-echo qualifies recovery.
- Late actual receipt responses across workspace/project/account/reconnect/app/instance/Run navigation, plus a late fresh-app response across workspace ABA. Tickets stay byte-identical and stale controllers cannot set saved.
- Controlled nested-request/candidate delivery tampering while keeping original keys/fingerprints, and actual source or target grant revocation via the bridge. The raw server response and controlled delivered JSON are separate evidence.
- Controlled missing Web Locks, recovery storage access failure and malformed JSON with zero POST; two real pages sharing the original browser adapter, an actual accepted201 held under the lock, explicit second-page recovery receiving ifAvailable BUSY without queueing or another request, then explicit valid recovery after lock release.

Every HTTP/asset response comes from the bridge. Shared localStorage/Web Locks, response loss/delay/tampering and JSDOM are explicitly controlled test platform behavior; native-browser, Windows, real model/semantic, PG and remote CI qualification are not claimed. The existing source fixture uses MockTransport; this page calls no model or Worker.

The final accepted checkpoint permits only GET afterward, except the bridge's one fixed grant revocation; the final readonly checkpoint checks all rows. Static asset digests, all real HTTP requests/responses, delivered poisoned objects, visible gestures, closes, per-boot UUID observations and browser lock events are retained.

Validation performed here: Node v24.19.0 `--check` PASS only. No product test or running DB access was performed. See `source-provenance.json` for exact input and draft hashes. The production JS was parent WIP when read; the parent must freeze the actual execution inputs before running.
