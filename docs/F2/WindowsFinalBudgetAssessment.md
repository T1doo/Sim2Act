# Final-source Windows budget assessment

Decision: **NO_GO for another WindowsServerCI run from the present timing evidence**. Execution freeze is `7854029d702769e26c9cd9cf2d4f22e2a97750ce`, with an actual collection of 1309 unique cases. The original job900 / Edge240 / Node150 limits, full coverage and security guards remain unchanged. This assessment does not start CI or change its workflow.

The prior b232 run [37621453354](https://github.com/T1doo/Sim2Act/actions/runs/37621453354), job112792480092, was cancelled after912 seconds: engineering741, setup/smoke55, incomplete Edge at least110, cleanup6. The unfinished Edge segment cannot be used as its complete duration. The [saved decision](../evidence/native-budget-local-20261007/budget-decision.json) preserves these measurements and the unknown remaining browser cost. That earlier source had1046 collected cases; the current1309 collection has263 more, without a qualified current-source Windows cost measurement.

An older complete run on7c02 took896 seconds with only4 seconds observed headroom, including677 engineering and150 Edge seconds; it is another historical source, not current capacity proof. See its [original diagnostic](../evidence/combined-final-20261007/windows-budget-diagnostic.json).

The current Report49 targeted PG pass70.68 seconds and SQLite full599.26 seconds establish their respective Linux gates. They do not measure Windows setup, the complete engineering suite or protected Edge. Local Linux fixture savings previously estimated at20 seconds are also not verified Windows savings. The native fixture's lack of Report promotion paths is only a source observation, not a measured Windows saving from the Report-directory hint.

No complete same-capacity current-source timing envelope and margin has been established. Controller overlap remains an unqualified design: it needs an original-job-start marker, bounded complete Edge setup/seed/cleanup, isolated port and process ownership, descendant termination and fault cleanup, and joint complete gate evidence. No overlap implementation or reordered workflow is delivered here.

Full Linux PG subsequently exited0 with1305 PASS4 SKIP/1235.82 seconds on the same1309-case freeze. This is Linux evidence and cannot close this Windows budget gate. A future native run needs concrete capacity evidence or an explicitly revised user scope; blind retries, raised limits, skipped cases and reduced assertions do not follow from this assessment. Win11, full AT02 and formal F1/P-B acceptance also remain open independently of regression results.
