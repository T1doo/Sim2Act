# Fresh complete encoding optimization

Frozen f89e62305b5ba3e359e39cfab7a6f6b87aa5ac6b. Real-clock complete controller FAILED in 437.60s (exit1); no acceptance. Exact fixed provider/model unchanged. G0 completed49.0118s, method commit:first38.6630s and second3.9763s both returned; these are graph checks, not SQL commits. G1 failed after70.9674s at the total120.0961s finite settlement deadline. All five W5 SQL writes executed with rowcount1 and rolled back together; no saved Cold result. 6Mock requests and0real model calls. Full test uses test-only SQLite and MockTransport, not real Intern.

Diagnostic segmentation explicitly used virtual business and lease clocks; first complete G1 82.893s and owned KeyboardInterrupt exit2 after observation, transaction not committed. It cannot establish finite-lease acceptance. See diagnostic-g1-segments.json.

Source/Cold real Intern extraction remains separately proven in ../cloud-settlement-20261028/intern-v2-id-fix.json (2 real HTTP200 calls,2176actual tokens). This is not a real-model complete controller chain. Formal production PG connection/principal/project/trial selection absent; SQLite local synthetic full chain is independently still failing.

The three f89 changes are exact immutable bytes arithmetic reuse (strong references, prune removed leaves after fresh complete walk, clear at close), fresh complete no-memo schema metadata encoding with old matcher fallback and NaN/opaque fast-leaf exclusion, packaged row-index projection that retains complete keys/data and falls back BEFORE projection for unknown quoted conversion/destruction. Review found a provisional destructor timing false-pass before commit; it was fixed with preselection fallback and retained key/position lifetime, and the counterexample is a regression test.

Unit55passed and explicit revoke1passed. Preliminary regression65passed/1failed was not a full PASS: source/qualification edits occurred during that exploratory run and a fixture error escaped before the intended witness; that revoke case was rerun on stable bytes and passed. Logs retain the failure. No retry changed the runtime gates.

Pure-memory schema witness microbenchmark improved .1475→.0294s for20 full-catalog passes; actual18-column synthetic SQL row projection .0732→.0570s for10000 loops, with identical legacy encoded bytes. These did not establish full-window success. A separate uninstalled complete C codec prototype in scratch was benchmarked against all26 populated tables of this fixture: only~4% faster (.31275→.29967s/100encodes) and output grew804456→837500B. It was NOT connected to product code.

## Subsequent pair segment (source21b5d30be2615e71ec6468d457e56b751d19f4b7)

Two-query real SQLite unit reduced complete codec calls10→4 while preserving both queries/output/error mapping and post-SQL/late full pins.23 targeted cases passed. Independent review caught import cycle, serializer/fingerprint/deepcopy qualification omissions; these were repaired before commit and direct import probes passed.

The subsequent virtual-clock diagnostic completed after210.92s with owned KeyboardInterrupt exit2, not acceptance. G0 selected47.9044s; G1 complete88.8068s; graph_bytes9979calls/7431124254bytes compared with prior10273/7636079202. Fewer encodings did not establish sufficient whole-window speed. Source21b has not passed a complete real-clock chain. No repeated real-clock run was started with an unchanged candidate after this diagnosis.

Environment disconnected and was actually rechecked after recovery; no test process remained. Read-only terminal request failed to create a process. Local/remote source HEAD21b matched; only this evidence directory remained untracked before preservation.
