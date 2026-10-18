# Known correction Run: revoked source → metadata-only explicit cancel

Base `fe5d640c29533a68f5af77ddd7e4b8ceba27a98b`. Exactly two product JS files change; no API/backend/Grant/executor/table changes.

`author/` is an exact copy of 26 sealed non-DB originals, 3,245,125 bytes. Manifest SHA `fa010eb80292f6dc775b171f835f4a1d0779be3c2670251ee4be78ca2135acfa`. Synthetic SQLite stays local, not part of this manifest or commit.

- `execution.json`, `page-result.json`, `http.ndjson`: actual served page/JSDOM/TestClient case PASS153.797s,10checks/11gestures/43frontend requests, zero input drift. One normal new parent Run/Mock1 on an exact copy of the current legitimate synthetic saved-app DB; no gen3 rerun. New correction child QUEUED, original owner READ revoked through actual API, full instance403, metadata200, explicit cancel200, metadata200 CANCELLED/v2. Child model/Attempt0.
- `parent-worker-proof.json`: normal original parent, one real Worker claim; synthetic model only.
- `cancelled-child-proof.json`, `database-before-page.json`, `database-after-page.json`, `revocation.json`: actual final cancellation, no new typed output, precise original read revocation. The initially noted unsorted typed comparison risk did not cause a failure in this actual run.
- `observer-only-bridge.json`: removing only the later workspace invalidation Observer recovers the exact actual-tested `internal.js` SHA. Final30-check synthetic case covers that addition; actual cancel was not rerun afterwards.
- `synthetic-first.json`, `synthetic-final.json`, `unit.xml`, `unit.stdout`: 29 then30 synthetic assertions, and one pytest PASS7.94s rerunning the same final case; not59 or30 separate pytest cases. Actual backend/Worker conclusions come only from the actual case above.
- `final-source-map.json`, `static-checks.json`, `executed-*`: frozen final source, syntax/Ruff/diff receipts, and exact actual-tested bytes. Executed internal.js is explicitly reconstructed by stripping the sole later Observer and matched to pre-execution hash.

No real model, native browser, real semantic/human acceptance, Windows, PG, remote CI or remote Git operation. First fresh correction test FAIL and its separate existing-Run continuation PASS remain in the preceding evidence slice unchanged.

[Finite independent review](review/final-independent-review.md) PASS, no new blocking P1/P2. It verified all26 author files, real metadata/cancel wire and owner Grant change, child0 attempts and unchanged typed, exact Observer-only bridge and final30 synthetic assertions. Seal SHA `07c3e9ec4287e0a27a5b4a45d3a40da98326dad1b4c5d6fa0bdde05247f1839e`,8files/32406B. It did not execute product/DB/network or endorse later commit/push.
