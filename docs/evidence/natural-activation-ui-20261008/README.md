# Exact activation page / temporary offline demo evidence — 2026-10-08

Final execution source:642e18861a5983d47fe32e9a42a0a452f3ab301a. Root regression is SQLite-backed synthetic HTTP/DOM and pure/mock tests; no PG count is borrowed from334fae2. Controlled DOM uses ordinary HTML/JS over owned loopback HTTP. It is not a native browser/pixel/Windows result; native sandbox remained blocked and was not bypassed.

Root transcripts and JUnit are exported losslessly as `*.raw.json`: `text` reconstructs original bytes, `original_sha256` verifies them. `export-integrity.json` records original and saved hashes; no database, DSN, private credential, source archive or recovery package is included. Public demo identity is an intentionally fixed synthetic fixture value. Loaded-page JS hashes and frontend/oracle outputs are retained in results.json.

Failures remain evidence: first UI1P3F controller omitted JSON Content-Type; third8P1F malformed test goal fixture;181a5bc backend160P2F exposed volatile JSON clock and nested SQLite transaction oracle;791cdfb UI6P3F exposed actual `resource_` vs `res_` frontend bug. Original failure logs remain.181a5bc UI9P and8cfdb14 disjoint28P+146P=174uniqueP are earlier-source runs. Demo first1F was the example's incomplete card metadata; demo CLI first/second1P1F were wrong ID/project-list test oracles; third2P is pre-freeze, separate from final frozen regression.

Independent181a5bc BLOCK_UI_SCOPE_SHAPE_PROJECTION_ONLY is retained: frontend accepted counterfeit scope fields, although backend rejected and wrote nothing. Corrected ASGI4P retains original1P3F mistaken oracles. Independent8cfdb14 limitedPASS reran strict shape/digest negative DOM14, actual app.js header DOM3 and ASGI1P; it did not rerun the full confirmation chain at8cf. Root final regression covers that chain.

Demo independent review is static only. The642e188 addendum corrects stale prose about setup `finally`; snapshots captured after concurrent changes already equal final bytes. Windows and injected setup-failure lifecycle remain NOT_RUN. Root CLI test checks loopback HTTP, no charge on readonly reads, normal exit0 and owned temp tree removed; it does not prove Windows shutdown.

Original LIVE0, account/money approval0, no provider/models/account call, no new CI/native. Official public-site/assets metadata records URL/hash/links only; it did not verify currency/tariffs/provider hard spending caps. Source caps cover calls/tokens/RPM/time, not money. Entire P-B receipt extraction/reusable application/new-input/publish remains incomplete; PARTIAL/NOT_RUN/candidate_generated=false persists.

Final642e188:176unique PASS0FAIL0SKIP,80.81s; one existing dependency warning. `root/final-source-before.json` / `final-source-after.json` and `source-and-export-closure.json` verify frozen Git byte equality plus actual loaded assets. `owned-cleanup.json` records removal of only root-owned synthetic fixture trees after verified export.
