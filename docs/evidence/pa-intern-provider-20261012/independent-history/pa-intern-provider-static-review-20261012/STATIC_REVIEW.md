# P-A provider independent static review — first fixed snapshot

Static review only; dynamic acceptance is NOT RUN. Repository reads were confined to `/workspace/Sim2Act-pa-provider`; root remains the sole product writer. No tests, provider transport, real network, credentials, CI, browser, sockets, PostgreSQL, installation, or old owner workspace were used.

Base HEAD: `a4fd476127a477006dbdb29a9a1f6c2f09e6a001`.
Branch: `dev/pa-intern-provider-20261012`.
The reviewed source is an uncommitted, not-finally-frozen author candidate. Exact bytes are preserved in `fixed-snapshot/`; hashes are in its two source maps. `read-completion-source-map.json` also records all 71 Python files (including config) and pyproject at read completion. The initial pre-fix review did not record byte hashes; no claim is made that the preserved snapshot is the original red implementation.

## Previously reported findings, current static disposition

1. Actual-send configuration recheck — FIX PRESENT in inspected bytes. `goal_applications.py:464–486` factors provider eligibility without reading completed history, permitting the explicitly named current STARTED Attempt transition. `check_active` calls it at line 842. The wire guard at lines 576–598 locks and checks the current Run, current mode/LIVE flag/token/LIVE approval ID and compares Authorization with the current selected token. The error string does not include token contents. Historical `validate_run(active=False)` remains independent of live configuration; historical evidence is not fresh send permission.
2. Finalization error after immutable settlement — FIX PRESENT in inspected bytes. `goal_applications.py:743–755` leaves the already-settled Attempt status/error/usage unchanged and records `GA_POST_SETTLEMENT_REJECTION`. It does not run another settlement over a changed error. The author added five send-gate tests and one final-error test at `tests/test_pa_generation_provider.py:272–321`; I reviewed them but did not execute them. Parent-reported six red results and currently active author r3 suite are not independent counts.
3. New PARTIAL final guard — present at `worker.py:275–276` and `worker.py:326–327`. Both checks execute inside the same Store transaction as candidate verification, terminal result/state and event writes. Any exception from the final active gate rolls back that transaction. Candidate readiness retains `PARTIAL`, semantic UNKNOWN, Goal acceptance NOT_RUN and app_created=false; this is not whole-Goal or semantic acceptance.

## New static boundary findings

S3 — Authorization must precede protected Goal/material cell reads (requires finite repair or explicit contract decision before dynamic sign-off).

- `generation_approvals.py:200` calls `validate_card_version` before it has obtained and authorized the selected resource. `goals.py:93–98` reads the complete historical Goal snapshot before `snapshot` authorizes its resource refs. Project ownership is checked first, but a same-project owner whose resource grants are revoked reaches the private snapshot read before denial.
- `goal_applications.py:109` and `generation_approvals.py:334` call `Store.frozen_contract` before their material authorization gate. `db.py:921–925` reads the complete frozen contract, then `db.py:950–965` reads and hashes complete resource content before source verification. `Store.guard` also invokes the same loader at `db.py:915`, so adding a gate only inside the later source function does not protect the preceding guard call.
- `worker.py:260` reads a complete saved contract before any target gate. The current GET original-key recovery at `api.py:527–531` reads a full Run and calls the same complete loader before material authorization.

This is a static private-cell evaluation ordering finding. It is NOT a response plaintext disclosure claim, an actual attack, a dynamic barrier FAIL, or a tool authorization rejection. The relevant scope is current project owner + selected material authorization revoked, and foreign identity should separately be rejected before full private cells. A minimal targeted hook can project the selected Run/Goal identifiers/resource refs, authorize the current principal/runtime/project before full loaders, and preserve legacy generic behavior outside this new activation path. No broad executor rewrite is suggested.

S4 — The write-after active check does not recheck elapsed worker lease (narrow static late-result boundary).

`Store.guard` checks fence/lease/status at `db.py:907–915`. The final check at `worker.py:327` uses the original locked pre-write Run dictionary intentionally: the persisted row has just become PARTIAL with lease_until=0. `check_active` checks Run/approval deadlines, current flags, Goal, permission, cancel and stop, but not the original lease_until. If lease expires while the same final transaction verifies the candidate, and the approval/Run deadlines remain valid, the post-write gate does not reject that elapsed lease. A same-transaction final comparison against the original guarded lease is sufficient; calling ordinary guard after the terminal write would reject valid completion. This remains STATIC, not a reproduced product FAIL; parent has been informed to assess against its precise late-result contract.

## Other inspected invariants

- Scope/metadata/approval/revoke/charge/send/settlement each use separate paired records and exact canonical fingerprints (`generation_approvals.py:130–148`). Scope includes full native Goal version/snapshot, material identity/hash, principal/project/runtime, distinct generation and approval keys, exact software fingerprint and grant snapshot.
- `prepare` caps requests/tools/repairs/tokens/output/run duration to 3/1/1/64000/1024/300. Config defaults activation off, empty LIVE ID and provider disabled. Policy live_request_allowance remains literal zero; only the separate exact activation enables the finite route.
- Cached approve reuses the original absolute deadline and exact consent/body. Revoke is irreversible, including after material read authorization loss, and uses metadata/hash projection rather than Scope Goal body.
- Submission now rejects a mismatched route project using metadata before full Scope/Approval reads (`generation_approvals.py:382–388`). Foreign principal lookup is scoped before Scope loading. Prepare/current-source software and current Goal heads are compared; no automatic re-sign or budget renewal occurs.
- Charge count, immutable actual Attempt metadata and independent reservation events are reconciled. Next stage requires all previous settlements, actual RECEIVED status, known usage and only the specific first-candidate repair diagnostic; unknown sends are not resent. A sent or rejected reservation is not refunded.
- Quota row and current reservation are checked under transaction/row lock before send; send increments blocked_until by 60 seconds. PostgreSQL concurrency behavior and real clock/transport behavior are NOT RUN.
- The same absolute request deadline covers headers and body in `model.py:211–250`; byte-bounded, cancellation-cooperative transport is the supported assumption. Returned names only accept the explicit intern-s2/Intern-S2 aliases; arbitrary model names, refusal, truncation and unknown usage reject. No model claim is derived from a synthetic fixture.
- Archived protected response evidence remains private Attempt data, with bounded metadata events. Final candidate result is not an automatically created/executable application.

## Evidence and remaining qualification

Independent dynamic count: 0 PASS, 0 FAIL, 0 SKIP, all dynamic checks NOT RUN by instruction. Author suite outcomes were not adopted as my independent results. Production-shaped mocked HTTP is also NOT RUN by me; no real provider request was made. Typed cold new-material bindings are an untested draft and are excluded from this static provider conclusion. New terms on the original material cannot stand in for a new material binding.

PG, Windows, native browser, real model, credentials, monetary cap proof, deployment, remote CI, old-source upgrade and the permanently excluded exact cancelled installation window are NOT RUN / NOT VERIFIED.

Only `/tmp` evidence was written. One initial snapshot command used `.venv/bin/python` inside the new workspace and returned missing executable (no repository code executed); the corrected snapshot used system `python3` with stdlib only. This is a bookkeeping environment path error, not a test or permission/transport rejection. No retry of a denied browser/CI/install path occurred.
