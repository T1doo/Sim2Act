# Independent continuous CSV revision review

Executed source: `d74f2fed55b6067e5d3c34ca6e4348b92e75f48a`. Final static source: `b589809375c89b4d93617d91c780a1e0f7f704e2`. Repository writes: none. No real model, PostgreSQL, remote CI, deployment, old Run replay or recovery matrix.

## Actual independent execution

One pytest process ran only the requested two API positives and five API negatives against a Git-only immutable snapshot. Actual result: **7 PASS / 0 FAIL / 0 SKIP, RC 0**. Pytest reported 904.04 seconds; the outer recorded subprocess interval was 906.696579 seconds. There was one existing Starlette TestClient deprecation warning. These seven repeat overlapping author coverage and must not be added to its unique-case total.

The snapshot contains 660 Git-object-verified files: src/tests/schemas/pyproject plus all 32 bounded-agent evidence files, 14 model-protocol material files, and five protocol evaluation files. Files are 0444 and directories 0555. Every file retained identical SHA256, Git blob ID and size after execution; no unexpected source-tree files appeared. The database URL environment variable was removed and runtime import origin resolves to this snapshot. Python 3.12.14 / SQLite 3.53.1 / pytest 9.0.2 are recorded in environment.json.

The two positives actually execute original NoModel Worker paths through an independently checked v2 parent, v3 effective candidate, isolated CHECK, Release, original-instance CAS adoption and a fresh sum30/result_version3. sameGoal keeps Goal2; nextGoal uses the explicit saved Goal3. New per-Run human acceptance remains PENDING. The captured original 11-table rows remain present byte-for-byte as SQL values; old Run and Release reads succeed, and grant/principal counts remain unchanged. This is the captured retention scope, not a claim that all old Run ledger rows were compared.

The five negatives actually reject both-seal parent-fingerprint tampering, both-seal action-binding revision tampering, Goal drift after successful CHECK, resource-read revocation after successful CHECK, and stale adoption CAS after a real intervening current-v2 result. Every measured rejected call leaves the complete 55-table snapshot unchanged. Both coordinated corruption fixtures recompute their ordinary checksums and request/response seals before rejection. All old captured rows remain present.

Seven SQLite fixture DBs and all raw HTTP/positive/negative JSON receipts are preserved under data/. Read-only postprocessing found zero model attempts in all seven DBs; all 29 fixture Runs were SUCCEEDED, fence1 and had one CLAIMED event. These counts describe this synthetic test run only.

## Static contract findings and resolution

The legacy effective/calculate ASTs remain unchanged from ce3; 17 legacy DTO/control/permission AST nodes were independently compared and unchanged. The v2 namespace shares existing paired journals, with unknown namespaces rejected. Parent Release identity, project/app/runtime/business-instance scope and source authorization precede parent body access. Historical parent bound never receives child CHECK overrides. Parent context refuses CHECK-pinned instances and insists on the original business instance. The private CHECK-create exception requires the exact current preview, namespace, Reference, parent Release and deterministic key; ordinary SOURCE instance creation still refuses.

The earlier mixed-depth bug is fixed: only real strictly shaped Release IDs count toward ancestry depth, while preview tokens independently detect recursion. Historical rule/check fingerprints now use frozen authority versions. The parent-proof cache is restricted by connection transaction identity/write epoch/thread/principal/Release/limits, installs only completed proofs with unchanged starting epoch, rechecks collected authorities and source bytes on hits, and deep-copies results. Current Goal, instance, graph and dispatch/commit checks remain fresh. No unresolved safety blocker was found within this finite review. definition_graph still computes registry hashes before discarding rule/check definitions; that is a performance opportunity, not an established root cause or a correctness blocker.

## Final upgrade patch and source stages

A separate review found that d74's currentRelease UI skipped derive even when a saved prior-software v2 canonical graph was stale. Root independently confirmed this with a copied closed synthetic database: context409, explicit existing derive201, then context200. The original d74 seven-case run does not test that upgrade correction. The finding and proposed correction are preserved in upgrade-blocker-note.md.

Final b589 changes exactly five files, all byte-identical to the reviewed upgrade draft. The new derive receipt authorizes the current app/source/graph before private journal access and validates exact key/body/candidate/fingerprint/full response against the current graph. The UI performs no derive for a current graph, allows the original explicit derive only for the exact authorized stale-graph conflict, retains original key/body in the existing durable request controller, and recovers UNKNOWN by exact GET without another POST. Navigation checks remain after asynchronous boundaries. The new endpoint test includes a real positive SQL read control, complete before/after snapshots and revoked-authority zero-private-body-read checks; it was statically reviewed here, not executed by this reviewer. No remaining blocking issue was found in this final static patch.

The csv_column_revisions, legacy csv_goal_revisions, lifecycle and negative-test files are byte-identical from tested d74 to b589. The positive test function AST is identical, but b589's shared retention helper adds two graph-history tables. The final receipt/API and three page executions reported by root/other agents are separate b589 evidence, not this reviewer's runtime results. Root's 21-case d74 batch is also separate and overlapping. **Do not describe the combined executions as one 32-green b589 batch.**

## Evidence and limits

Use execution-command.json, execution-result.json, pytest.log, pytest.rc and junit.xml for the actual run. inputs-before.json / inputs-after.json provide all source-to-Git and before/after hashes. sqlite-observations.json and data/* retain the seven actual DBs and HTTP/proof receipts. static-contract-proof.json and final-b589-static-proof.json record the function/source continuity checks; final-review-proof.json records the finite conclusion.

Not executed here: UI runtime, final b589 receipt runtime, v3-to-v4 or spec8 actual chains, cycle/depth/cross-owner injection cases, Windows, PG, real models/semantic scenarios, remote CI or deployment. Earlier WIP development failures were not changed or relabeled; the known dev-second oracle KeyError batch remains a failure and is distinct from this successful frozen run.
