# Generation first-producer transfer

This change transfers guarded Generation records at their original independent deepcopy/output boundary to complete immutable Source facts. Every consumer now reads the owned records; original SQL positions, lazy reads and repeated-return identity are preserved. Complete-source, FrozenRunContract and RawSeed remain on their original full typed paths. Every original graph/dynamic authority checkpoint remains. No permission or PASS is cached.

The final local correctness suite passed, including original malformed evidence, typed contract drift, raw-facet substitution and scope invalidation. Independent read-only review found no remaining code blocker. The two fixture representation changes still compare complete ordered SQL-visible values and reject a same-value different-identity history.

The component metrics are explicitly **pre-final** and are not a whole-flow performance result. Final-capsule Generation edges decrease from 9,705/9,597 to 3,401/3,401; full-encoding counts remain 453/463 and encoded bytes increase. Overall component timing does not show a gain (55.87s baseline vs 59.84s candidate, observer included). A frozen same-input complete settlement is still required. The original 30s writer-admission/first-DML lease and 120s SQLite settlement deadline are distinct and unchanged.

All execution here uses synthetic fixed Mock and test_only file SQLite WAL. No live Intern, PostgreSQL, Windows or target-machine acceptance is claimed. Raw DB/model logs remain private under /workspace/scratch.

## Complete-source follow-up

The follow-up migrates the remaining complete-source Run/material/authorities. Only the exact original raw contract dictionary remains a normal typed root; it is extracted **after the original final deepcopy**, published before capture, and shared with the owner through the explicit outside alias boundary. The collector checks that same raw dictionary by identity before the unchanged typed hold. The actual contract/Run/authority checks remain fresh.

Final Generation roots have 279 reachable edges in each measured scope (18 roots, including the raw typed boundary); total graph edges are 52,033/54,056. Encoding counts increase to 456/466 and byte volume increases. The original business prefix and real typed collector pass, as do actual Generation checks without the optional Source extension. These are component/correctness evidence; the previous whole-flow failure is retained under failed-0a23d780 and a new frozen whole-flow result is required.
