# Cold original-key recovery independent of the Goal catalog

Base4ae6b1e2a26223c552d2f47cc386eb68d4db5107. This is a normal local source fix, not another G0/native/model window. The original scoped visual window remains consumed.

## Existing contract and reproduced defect

V5 product §8.2–8.3 requires recovery to retain original operations and recheck authority without blind resend. More specifically, [the existing trial-consent contract](../../F2/PATrialConsentEntry20261015.md#恢复与授权边界) requires cold-page same-project original-key UNKNOWN placeholders, GET-only recovery, no new key/consent while unknown, and independent metadata-only recovery when material READ is unavailable.

In natural-goal.js refreshTrialCards, the existing URL/entry restoration happened only after await goal-cards. A controlled403 from that catalog therefore left the cold original-key field empty, despite an existing separate preparation/consent-status readback path. The unchanged original controller/template reproduced this exact failure: red.log/JSON exit1, 0.408805s. before-natural-goal.js.gz preserves the original product bytes; this is a DOM failure, not evidence of backend unauthorized access.

## Minimal change

Move the original same-project/valid-key and existing-entry logic before the catalog GET, render the UNKNOWN state immediately, retain the original directory GET and current-generation check. No new URL parsing rule, accepted receipt or execution capability is introduced. clearTrialConsent already invalidates private scope/checkboxes at entry; remove the redundant post-GET scope/checkbox clearing so a late catalog response cannot erase a newer explicitly read original-key metadata receipt. Retain final render after successful directory population for ordinary new preparations.

Only natural-goal.js production code changes. No backend, immutable snapshot, Run status, lease, fence, authorization, deadline, key generation, request body, POST or model path changes. The existing preparation/consent-status fallback and validation are reused; a real authorization failure is not bypassed or reclassified. Failed metadata reads stay UNKNOWN. An existing unresolved key wins over a different address key; foreign-project or malformed keys are not adopted.

## Actual validation and limits

One final pytest node passed (JUnit0.652s, outer1.431583s). Its actual-template/app+natural-goal JSDOM child performs13 assertions and12 finite in-memory GETs, not13 independent tests or HTTP requests. It covers catalog failure with cold original key, explicit original-key metadata fallback, failed fallback remaining closed, existing-key precedence, foreign/malformed addresses, recovery while catalog is pending, late catalog not erasing recovered scope/receipt, and ordinary two-card selection still enabling new preparation. Five source/test digests are identical before/after execution in final.json. Node syntax and git diff whitespace also passed.

Initial10-assertion green is separately preserved; it predates the added pending-catalog/normal-success witnesses and is not evidence for final-source equivalence. red/initial/final runs are separate executions, not an all-history-green claim. The final pytest warning is an existing Starlette/httpx deprecation; no dependency was installed or changed.

No HTTP server, database, Worker, model, G0, Cold2, W5, browser or native CI was launched. JSDOM windows close in finally; final subprocess returned normally and its own temporary pytest directory was deleted. This does not repair or attest the real-clock G0 second-commit lease failure, actual persisted UNKNOWN settlement, process restart, provider identity, PostgreSQL, pixels or overall F2/R0. The immediately preceding four-image visual archive binds the older natural-goal.js and does not sign this new source. No additional visual window was requested or consumed.
