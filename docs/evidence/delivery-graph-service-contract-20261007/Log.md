# Independent real-service adapter contract

Base: `5b6b44de76659b7542604f61eae08ebb59430b31`. Isolated branch `review/delivery-graph-service-contract`; no product edits, PG, full suite, provider network, LIVE, push or CI.

Scope: map the frozen 17 black-box obligations to actual SQLite Store/create_app/TestClient HTTP. CSV sources use ordinary resource import and csv-preview creation. PROJECT sources use the repository's actual fixed-MOCK conditional source/check/promotion fixture. Baseline follows all fixture authority preparation. Independent per-case databases and peer CSV resources; cold reads create a genuinely different Store/client on the same database.

Observed final focused command:

```
PYTHONPATH=src:tests /workspace/sim2act-pb-venv/bin/python -m pytest -q tests/test_delivery_graph_service_contract.py --tb=short
```

Result: **17 FAIL / 1 PASS**, 15.86 seconds. Failures are live integration gates, not xfail or skipped. First version also yielded 17 FAIL / 1 PASS, 21.66 seconds; subsequent driver refinement made peer sources independent and source-version fixture mutation affect actual content/hash, preserving the service failures. Ruff for the two added test files passes.

Fifteen scenarios stop at the initial closed-envelope assertion: real successful HTTP returns metadata, receipt, scope_jobs and scope_expansion, without the contract's persistent core/expansion/outer_fingerprint envelope. Therefore later revoke/version/membership/tamper transitions in those cases are **NOT_REACHED**, not passing negative evidence. The two initial-lock scenarios reach real HTTP but are accepted: no currently consumed server lock-control interface exists. The driver explicitly records unsupported locks and never fabricates an accepted anchor or lock capability.

The extra direct test PASS covers actual HTTP plan receipt insertion with unchanged complete business and authority snapshots, cold Store/client cached replay with no database change, then real resource-scoped runtime Grant revocation and cold request rejection without data or further writes. Two additional real probes verify APP and PROJECT planning, no business/authority writes, and one persisted plan each. PROJECT returns two scope jobs plus BLOCKED_PARTIAL for its existing unsupported parent application; that is retained.

Status normalization is limited to HTTP201→200, request-validation422→400, and GRANT_REVOKED→PERMISSION_DENIED. Successful payloads remain unmodified: the driver never builds a trusted outer fingerprint from its observations, does not copy MemoryDriver business logic, and does not pass current_context or previous_receipt as authority. Full table snapshots are hashed locally; logs/report emit no tokens, credentials or raw environment/config.

Required backend work remains BLOCK: persist and return the closed outer envelope; bind/revalidate every peer graph fingerprint, authorization revision and lock snapshot; provide a consumed trusted fixture lock collection; preserve the prior core/source_versions review blockers. These test files deliberately remain red until service integration is completed. No semantic/publication/platform acceptance is implied.
