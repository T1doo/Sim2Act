# Independent one-node material acceptance

Product freeze: `805afe60cdd94d6d4679e0da9c1f7fde752f67d2`.

Actual result: **1 passed**, four real synthetic NoModel Worker Runs. This is a separate corrected-observer run. The parent's original failed 805 result remains a failed original.

- [JUnit original](junit.xml), [stdout original](pytest.stdout.log), [exact command and timing](command.json).
- [39 main-client HTTP request/response originals](pytest-temp/test_authorized_B_same_instanc0/actual-http.json).
- [Complete delivery identity chain, CHECK, Release, CAS, business result and PENDING response](pytest-temp/test_authorized_B_same_instanc0/actual-material-delivery.json).
- [Actual retained SQLite fixture](pytest-temp/test_authorized_B_same_instanc0/fixture.db), [read-only raw material/Run/old-owner extraction](actual-independent-database-proof.json).
- [653 original Git blob/SHA256 input freezes](frozen-inputs-before.json), [post-run zero source/file drift proof](frozen-inputs-after.json), [original input archive](original-frozen-inputs.tar).
- [Original observer patch](cached-assertion-original.patch), [path-adapted applied patch](cached-assertion-applied.patch), [single hunk/patch SHA proof](observer-patch-proof.json).
- [Inspectable outcome summary](summary.json), [complete artifact checksums](artifact-checksums.json).

The only snapshot change was the explicit `cached:false` / `cached:true` assertion; all other response fields still require exact equality. All 129 `src/` files matched the original Git blobs before and after, and all 653 selected tracked inputs remained unchanged during the run.

The unchanged test fixes quantity, freezes saved Goal2 provenance at A, runs the new authorized B with independently fixed sum18/count2, adopts onto the same business instance, requires a new PENDING owner context, rejects old A acceptance, verifies old immutable rows, and asserts three cold-client GETs and a read-only database snapshot. The main-client trace captures 39 requests; those three cold-client responses are asserted by the test but are not separately captured by its main-client trace fixture.

No real model, Windows, PostgreSQL, remote CI, native browser, real semantic scenario or genuine human acceptance was executed. Only the requested single pytest node was run. B App-runtime grants were test-only preconditions established before the operation baseline; the complete Grant/principal/App tables were compared unchanged by the test.
