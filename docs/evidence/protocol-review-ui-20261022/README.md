# Registered review entry — bounded synthetic engineering evidence

Product basis: `docs/F2/ProtocolStoreLoopPlan.md` (owner can request registered evaluation, never submit PASS), and the explicit missing UI action recorded in `ProtocolUiEntryLog.md`. The implementation uses the existing review endpoint. It adds no evaluator registration, authority, model request, publication or owner semantic signoff.

The candidate's five source/test hashes are in `source-hashes.json`; they were unchanged throughout the final run. `pytest-final.log` records **8 PASS in 1.76 seconds**: six new tests plus two targeted old completion/material-refresh controller compatibility tests. These are not the prior 39/37/20 backend suites. Ruff check, Python test formatting, both Node syntax checks and `git diff --check` passed. The existing Starlette/httpx TestClient deprecation warning is retained; no SDK/dependency was installed.

Command:

```sh
timeout --signal=TERM --kill-after=10s 120s .venv/bin/python -m pytest \
  tests/test_protocol_review_ui.py \
  tests/test_protocol_completion_ui.py::test_completion_controller_selection_receipts_and_original_key \
  tests/test_protocol_completion_ui.py::test_protocol_material_batch_freshness_and_late_catalog \
  -q --basetemp=/workspace/sim2act-review-ui-20261022-final
```

The real controller runs in a minimal element VM, **not a DOM/browser**. Its 63 review checks include Source/Cold routes, explicit confirmation, closed request fields, double clicks, frozen identity/project/Run/body/key, transport UNKNOWN replay, legitimate FAIL/business UNKNOWN GET-only recovery, stale/incorrect receipts and Run reads, context/workspace ABA, late receipt and GET isolation, and the two independently found read-state races. Compatibility checks cover the existing completion command (73) and fresh material batch (12); counts are assertion labels, not additional network/model runs.

The Source HTTP test copies the sealed `protocol-source-process-recovery-20261022/after.sqlite.gz` and original received sidecar, without initialization, claim, Worker execution or new acceptance. An explicit synthetic business clock replays original `resume_at`; product clocks, the 30-second lease and every original budget remain unchanged. A real loopback API accepts the page-generated review key. The test intentionally discards that POST response, closes/returns the workspace, replays the exact key, fails the next controller GET with a controlled 403, and recovers by GET only. Both real POST receipts are strictly identical. The authenticated inspection returns SUCCEEDED/PASS/APPROVED and only then reveals the existing explicit Source extraction button. It never clicks that button.

`accounting.json`, `http-receipts.json` and `cleanup.json` record the outcome. Exactly one review/event is persisted; only Run status/version change. All other tables, original result, sidecar, accounting and deadlines remain unchanged. New Mock exchanges, Worker claims, Source, extraction, model calls and native CI executions are all **zero**. Four additional isolated real backend cases reject wrong version, wrong frozen contract, wrong result fingerprint and revoked authorization with no command writes. The local test cap was 120 seconds, each Node driver 30 seconds, API cleanup 10 seconds. API and newly created threads ended normally with no remaining threads.

Independent read-only review found three concrete issues before final freeze: legal business UNKNOWN was initially treated as a malformed receipt, an old Run could confirm a later non-PASS receipt without a fresh GET, and an older failing GET could overwrite a newer accepted state. All were corrected and received a limited code ACK. `initial-before-review-fixes/` preserves the earlier passing local evidence; it does not validate the final changes. Final tests cover the corrected cases. The reviewer did not run tests/services.

Unverified: new-control native DOM/pixels, Cold HTTP fixture, cross-page key recovery, real providers, PostgreSQL, G0 or overall F2/R0. The earlier Windows Edge completion evidence remains tied to checkout `26ee1cf0120f5d7c3a4ef10fd911469cad951d99`; it does not validate these newer controls. No new CI was triggered for acceptance.
