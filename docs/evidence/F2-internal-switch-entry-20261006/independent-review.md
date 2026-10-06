# E22 independent read-only review

Base HEAD bfc6fc593a099c533a8c8e36f9100cae32eceac3; review of uncommitted E22 source in /workspace/Sim2Act-pb. No repository edits, model requests, external writes, or browser-security changes by reviewer.

Actual finding: coherently rehashed switch approval could name same-owner P2 instance/from/target while persisted approval project remained P1. Authenticated HTTP rejected with403, but direct commit_switch accepted and switched P2 while locking/checking P1. This was service-layer corrupted-record defense, not a public API or cross-owner exploit. Reproduced baseline lifecycle SHA256 71f15025c7eb57fa560c9089c19ac5790beccdcc4c24a379d93d38adb8f42e33. Fixed service now rejects before instance lock with DomainError: Approval project differs from instance. Foreign-app and missing-instance approval records also reject with DomainError.

Final independently executed tests/test_internal_switch_api.py: 11 passed, 1 Starlette warning, 6.36 seconds, SQLite. Extra synthetic service scripts /tmp/e22_scope_review.py and /tmp/e22_project_scope_review.py produced the expected rejections. Node VM minimal-DOM /tmp/e22_switch_ui_review.cjs passed late prepare cancellation + duplicate single POST, and one-shot commit + cancelled late receipt with no reread/repaint/retry. This is not a real browser result.

Static review: owner/instance-scoped authenticated API, current grant/source/target checks, exact approval fingerprint, schema transition/retained-record checks, one-shot consumption. UI manual target/ack, generation guards, cancellation and expiry checks. Windows synthetic TTL marker narrows one approval in the creation transaction before its first receipt and preserves production 300-second TTL/clock/CSP; incompatible oracle uses existing services, no fixture HTTP endpoint. Windows browser scripts not executed independently.

Final SHA256:
- src/sim2act/lifecycle.py: 574b7a2e418e8dc93bc82e1b71dfa296ffd044f7a5c858d6b25d79d5449b734d
- src/sim2act/internal_api.py: 1835b49a8de953bc7591c3b85d705772625eae4e6db7435650277049370b1f21
- src/sim2act/web/internal.js: 91bf9dbef8092e67424400feebc2c15c53b47eee0e216c1106ed998e1881f145
- tests/test_internal_switch_api.py: 295f69641c0e0f4da55c83731741118c0e7085e8061e13cfd4d9a56d3e32c8b1
- scripts/windows_browser_ci.py: 02431ed896eaf7f916299c74056000a9ab70da22346785c9ac1e50947973c613
- scripts/browser-ci/internal-ui.cjs: a4b3bb644e9de7844579964f9080f52e42963c367c4339bed9ae740cb3b63ce3

No new concrete blocker found in final review. PG, aggregate regression, CI, and actual protected Windows browser not independently executed. Formal publication, Win11 and whole F2 acceptance remain outside this slice.

Final follow-up static review: additional upgraded Release worker result v2/rollback both ledgers and minimumCRUD-role switch assertions accepted. Browser SHA256 8b17ae8dce5fc87a21c9b9b93c47bee272f665f282566e68c6102688906979c6; API test SHA256 9a59f0b9573325111147ed17be073aee163a6635579bab57cd22e1db0e6266f4. Production/API/UI hashes above unchanged. This follow-up did not execute PG/browser.

After first protected CI failure, independent one-line static confirmation: browser check reads visible internal-run-status rather than hidden collapsed detail; original real QUEUED wait/assertion retained, all product/API/UI hashes unchanged. Final browser SHA256 8d0332e07a08fd8fd8a8b95d28858b5b9dee45fe7638ae4ab176a46a9551bb63. New CI/browser terminal not independently verified.
