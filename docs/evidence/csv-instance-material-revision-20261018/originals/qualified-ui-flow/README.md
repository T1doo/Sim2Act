# Material flow recovery acceptance after observer correction

Product freeze: `805afe60cdd94d6d4679e0da9c1f7fde752f67d2`. One qualified unique `flow-recovery` case passed. UI and test were authored by this agent, so this is author runtime acceptance, not independent UI code review.

- [Qualified result](qualified-summary.json)
- [Original JUnit](junit-flow-recovery.xml)
- [Original stdout](stdout.txt), [stderr](stderr.txt), [exact command](command.json), [runner completion](result.json)
- [Actual page assertions, requests and asset hashes](pytest/test_visible_material_replacemcurrent/page-result.json)
- [Original complete fixture HTTP trace](pytest/test_visible_material_replacemcurrent/actual-http.json)
- [Actual B Run, unchanged old A Run, frozen contract, instance and unchanged Grant counts](pytest/test_visible_material_replacemcurrent/actual-browser-delivery.json)
- [Node stderr](pytest/test_visible_material_replacemcurrent/node.stderr), [synthetic input identifiers](pytest/test_visible_material_replacemcurrent/info.json)
- [Input before](input-before.json), [input after](input-after.json): 646 inputs; product files and all other inputs match the frozen commit, exactly one documented CJS observer override.
- [Observer-only patch](adoption-observer-only.patch), [exact executed CJS](observer-csv_material_revision.cjs), [historical pre-run patch proof](patch-provenance.json), [evidence hashes](evidence-sha256.json)

The correction compares the complete existing GET adoption approval installed in the page. It separately checks the POST acceptance id/fingerprint/namespace, principal/project, original instance/revision/data version and exact checked target Release; navigation still deep-compares the complete approval. All material, consent, UNKNOWN recovery and no-duplicate assertions remain. No product change, timeout change or oracle weakening.

The earlier author-batch failing observer originals remain with the parent; this directory does not overwrite or reclassify them. Only this failed flow node was rerun. The passed navigation/backend/old-column nodes were not repeated. Real models, real semantics/scenarios, Windows, native browser, PostgreSQL, remote CI and deployment were not executed here.
