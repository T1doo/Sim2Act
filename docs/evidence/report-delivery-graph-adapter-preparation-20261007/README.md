# Report DeliveryGraph adapter preparation

Read-only preparation against `/workspace/Sim2Act-bounded-product-candidate` observed HEAD `2cad13afa72e8df6be1aa9c765e4c94586ad0532`. `canonical-report-fixture.json` is constructed by the actual current Report `canonical` and `compile_report` pure functions. It passes strict shared schema/preflight. IDs, origin fingerprints, revisions and authority context are synthetic; no persisted proof, actual read receipt, check, graph or acceptance is created. It is a compatibility fixture, not proof of a usable database adapter.

`manual-dependency-impact-oracle.json` is hand drawn independently of DeliveryGraph. It describes minimum dependencies and selected impact answers. It is not the module's final input/output schema. No ARTIFACT or RELEASE node is invented. Source and target have distinct IDs and the same registered synthetic text hash deliberately. Both are declared dependencies; cold execution is expected to read only target. Actual observation records remain empty/NOT_OBSERVED until a trusted adapter validates a real completed Run's operations and immutable seals. Source-origin Run reads cannot be relabeled current cold reads.

The Report check validates finite Report output, not explanation completeness or rendering. The known-view-only case therefore preserves the calculation and Report check definition in this hand graph, invalidates view/packaging, and can require a separate presentation check. Unknown/model semantic dependencies must widen revalidation, not manufacture semantic PASS or rewrite everything. Stable view/check identifiers in this fixture are supplied oracle slots; production needs trusted persistence.

Reproduce the pure fixture (no Store/model instantiated):

    PYTHONPATH=/workspace/Sim2Act-bounded-product-candidate/src /workspace/sim2act-named-report-venv/bin/python /tmp/report-delivery-graph-fixture-20261007/build_fixture.py
    /workspace/sim2act-named-report-venv/bin/python /tmp/report-delivery-graph-fixture-20261007/build_oracle.py

`adapter-evidence.json` records exact code locations and remaining version/ID interfaces. This preparation does not implement DeliveryGraph or its main entry, run DB/model/network calls, alter Grant/roles, execute CI, or sign off Report/V5 semantic acceptance.
