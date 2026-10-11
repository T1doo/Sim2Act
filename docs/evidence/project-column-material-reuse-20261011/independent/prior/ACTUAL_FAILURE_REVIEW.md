# Independent actual failure — coherent source-marker stripping

Current reviewed product has one reproduced UI origin-classification defect. Actual in-process FastAPI TestClient ↔ IPC ↔ offline JSDOM loaded 15 repository assets, all 76 src hashes identical before/after, frozen314 files unchanged. No browser, socket or network used.

`src/sim2act/web/csv-dag.js:551` restricts the target-source plan/proof/default verification to caller-supplied `execution_source.plan_key` matching reserved `(material|logic)-plan-`. Jointly changing the actual adapted release's key to `ind-ordinary-looking-key`, deleting its default or replacing it with valid-but-wrong `amount`, recomputing the snapshot fingerprint, and changing the Instance 200 response's release fingerprint causes the actual `dagReuseRead` to accept. Target actual approved column remains `quantity`. Single missing/null/wrong defaults are rejected. Instance has no prior runs, so run-history seals do not compensate for source marker removal.

UI actual result: **10 PASS / 2 FAIL / 0 SKIP**, two failures describe this same source-classification bug. Requests, asset hashes, source hashes and exact failures: `ui-first-result.json`; raw run: `ui-first.log`, `ui-0ce0mlsi/result.json`. Independent scripts: `ui_probe.js`, `ui_driver.py`; all immutable pre-fix copies have `pre-plan-key-fix-` prefix.

Backend same candidate: **13 PASS / 0 FAIL / 0 SKIP** in `pre-plan-key-fix-backend-result.json`, with actual worker numerical oracle, deleted-source SQL isolation, cold defaults/history, authorization seal key binding, typed rollback after exact injected expiry, and durable revocation after3 real receipts. This does not waive the actual UI defect or represent final candidate acceptance.

All independent fixture processes completed before root was notified and ACKed to repair. No product/test edits from independent reviewer.

Own first backend harness failure history: `backend-first.log`, `backend-first-result.json`, `backend-first-script.py`, `backend-first-error-classification.json`: extra textual decimal formatting assumptions (6.5 versus actual6.50; 9.5 versus actual9.500) after correct Fraction oracle, and empty initial hash selector fixed to use nested freeze files. They are not product failures and no old PASS counts are accumulated.

NOT_RUN: PG, Windows, native browser, old source upgrades, real/paid models, full P-A/P-B/AT10 completion, semantic/owner acceptance, remote CI.
