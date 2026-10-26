# API receipt read failure: actionable, conservative feedback

Base: 3ce962dadea5b4999cfe44c6501843641422df6c. UI API helper only, no backend change, business request mutation or automatic retry. The warm-orange layout/CSS is unchanged.

## Before / after (actual DOM/controller evidence, not pixels)

Before: api() leaked the raw JSON parser exception when a received HTTP body could not be parsed. The new real-template driver fails against the original helper: GET malformed response is explicitly unconfirmed. Its controlled PRIVATE_HTML_BODY marker is never an acceptable UI message.

After: GET/HEAD say the response cannot be confirmed and suggest a read-only retry; command responses tell the user to preserve the original request key and read status. The wrapper sets code=API_RESPONSE_UNCONFIRMED and transportStatus only. It deliberately DOES NOT set httpStatus or submissionRejection, which existing controllers interpret as a confirmed rejection and may use to drop a submission key. Existing valid JSON, server-clock metadata and structured rejection semantics are unchanged. The original fetch URL/method/body/header/cache behavior is unchanged. No response body or parser exception text is reflected.

The existing Goal execution DOM driver now includes an optional API_FAULT branch: a successful HTTP status whose json() rejects. Actual executeGoalCard retains UNKNOWN and the original body/key, ordinary clicking does not resubmit, and explicit recovery uses the same request. This is synthetic transport, NOT a model/service execution. Existing default 27-check driver behavior remains available; no product controller was changed to satisfy the test.

## Actual runs, preserve overlapping scope

- api-response-red.log: Node exit1 against old api(), expected new assertion failure.
- api-response-green.log: real template/app controller + synthetic response objects, 10 checks PASS. This specifically injects SyntaxError; separate stream-abort/fault variants were not executed.
- api-response-http.log/xml: initial local HTTP pytest FAIL, 1.13s: fixture expected401 but this backend correctly emits403 PERMISSION_DENIED. Original retained; only the expected test status changed. Normal owned API cleanup assertion ran. This is a deliberately unauthorized request against an isolated synthetic fixture, not a denied external connector retry.
- api-response-final.log/xml: 2 pytest PASS, 1.70s: local health + unauthorized GET, and existing default 27-check Goal DOM compatibility test. This earlier backend branch had 2 actual HTTP GETs.
- api-response-goal.log/xml: 1 pytest PASS, 0.92s: API_FAULT Goal driver, 32 synthetic checks including same-key/read recovery and existing late-response/selection isolation. No real HTTP or Worker/model in that driver.
- api-response-authenticated.log/xml: final local HTTP branch, 1 pytest PASS, 0.97s; final driver14 checks includes health, authenticated project list exactly matching a seeded local project, then deliberate unauthorized403. Exactly3 real loopback GETs, no HTTP POST. Worker/InternModel constructors are forbidden by test. The test seeds a synthetic principal/project directly in its own SQLite store before server startup; therefore this is not a zero-DML fixture. After final test, only its module docstring was updated from two to three GETs; executable definitions unchanged.

The HTTP runs overlap; they are not four independent end-to-end feature passes. Across the three local HTTP attempts there were 2+2+3=7 real loopback GETs, zero HTTP POSTs and zero model/Worker execution. Each used a separate temporary SQLite store and owned uvicorn server, stopped and joined normally with assertions, with Node exit0 for green runs. These results are not native-browser, PostgreSQL or real-provider validation. No all-table/sidecar comparison was performed. Earlier G0/owned-candidate limitations remain unchanged.

Commands: NODE_PATH=/workspace/sim2act-research-desk-node-tools-20261023/node_modules node tests/api_response_feedback.cjs; pytest tests/test_api_response_feedback.py for the local HTTP node; pytest tests/test_goal_card_run_ui.py::test_saved_goal_execution_ui for default compatibility; pytest tests/test_api_response_feedback.py::test_goal_execution_unreadable_receipt_keeps_original_key for the optional fault mode. Full raw stdout/JUnit and available driver reports are retained. Final sources.json is a current frozen-source manifest, not invented historical pre/post timing metadata.

Independent readonly next_ui_slice_review gave limited source ACK: no definite P1/P2, key/body and conservative submission classification preserved, no sensitive payload reflection. It did not run tests or inspect pixels. It explicitly excluded independent protocolRequest() in protocol.js. No native screenshot, cancelled read, separately injected stream error, timeout, or full API/product acceptance is claimed. Existing protected-browser constraints were not retried or relaxed.
