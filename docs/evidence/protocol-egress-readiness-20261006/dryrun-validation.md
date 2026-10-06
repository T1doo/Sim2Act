# Local protocol Store demonstration

Baseline 3cbd112. Scope: new script and focused tests only; no LIVE, push or CI.

The initial actual source/read+answer -> review -> extract run exposed an extract scope regression: source's two received attempts were compared with the new extraction single-request cap. It failed before any extract send with VERIFICATION_FAILED / Complete bounded source trace required. Parent repaired independent frozen source_request_limit; the script did not bypass it.

Before controller handoff integration: six focused tests passed (20.67s). They run a real authenticated TestClient/Store/Worker/ProtocolAttemptRunner/InternModel/httpx.MockTransport pipeline, block socket connect/connect_ex/create_connection, inspect actual Operation VERIFIED receipts and Attempt/slot bijection, and show source exact-checker FAIL stops candidate extraction. JSON-string decoding audit tests catch nested source answers and escaped material, rather than only scanning field names.

Standalone normal run: 8 actual Mock requests, 8 Attempts/shared pool slots, 6 VERIFIED Operations, two source/extract/cold Runs, shared fixed offline pool cap14 with known synthetic usage160. Six scope approval IDs share that pool. Max actual complete body5952 characters/5952 UTF8 bytes; output reservation1024. Standalone b-source failure run:6 requests/slots,4 Operations; b extract/cold never created; known usage120 retained, no unknown-cost halt.

Response-only pinned oracle fixtures are synthetic fake model outputs. HTTP submissions never carry candidate/gold/decision/expected_output. Private full evaluation contracts and their asset/gold/rubric fingerprints never appear in any request. Actual public source outputs can enter extraction. Cold requests are decoded recursively and checked for absence of source answer and full source materials; source/extraction cannot see the future cold materials.

Technical source/cold results stay UNKNOWN until explicit registered synthetic checker review. Those checks do not establish owner acceptance or real model semantics. This demo uses temporary SQLite and does not claim PG, native UI, LIVE, publication or recovery coverage.

Evidence: /tmp/protocol-store-dryrun-evidence/protocol-store-dryrun.json; /tmp/protocol-store-dryrun-failure-evidence/protocol-store-dryrun.json. Handoff integration is still pending in this interim record.

Final controller integration: prepare_handoff persists six QUEUED handoffs; require_handoff checks all eight actual sends BEFORE STARTED reservation, permitting trusted first claim fence evolution. Canonical candidate template is imported from protocol_readiness; no duplicate local generator. All handoffs live_ready=False with unresolved real activation blockers.

Final focused suite: 7 PASS / 1 deprecation warning in37.12s. The added negative removes the persisted handoff and confirms zero calls enter the actual adapter. Both standalone CLI modes reran successfully (normal8 calls, b-sourceFAIL6). Actual wire bodies independently assert max_tokens1024, streamFalse, modelintern-s2. Ruff and diffcheck pass. Files SHA256: script29b4b232b7a363bcc971de52914777334a59c100f1a4b2b4d51c71325a5e2f40; testsbbbefb34b58a72d6aebec0afde219c71fb8722f65a781a77a603cbae4cd3d013. No source/UI/main-plan edits, commit, push, CI or LIVE.
