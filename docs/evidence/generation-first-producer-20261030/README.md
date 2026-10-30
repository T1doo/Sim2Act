# Generation first-producer transfer

This change transfers guarded Generation records at their original independent deepcopy/output boundary to complete immutable Source facts. Every consumer now reads the owned records; original SQL positions, lazy reads and repeated-return identity are preserved. Complete-source, FrozenRunContract and RawSeed remain on their original full typed paths. Every original graph/dynamic authority checkpoint remains. No permission or PASS is cached.

The final local correctness suite passed, including original malformed evidence, typed contract drift, raw-facet substitution and scope invalidation. Independent read-only review found no remaining code blocker. The two fixture representation changes still compare complete ordered SQL-visible values and reject a same-value different-identity history.

The component metrics are explicitly **pre-final** and are not a whole-flow performance result. Final-capsule Generation edges decrease from 9,705/9,597 to 3,401/3,401; full-encoding counts remain 453/463 and encoded bytes increase. Overall component timing does not show a gain (55.87s baseline vs 59.84s candidate, observer included). A frozen same-input complete settlement is still required. The original 30s writer-admission/first-DML lease and 120s SQLite settlement deadline are distinct and unchanged.

All execution here uses synthetic fixed Mock and test_only file SQLite WAL. No live Intern, PostgreSQL, Windows or target-machine acceptance is claimed. Raw DB/model logs remain private under /workspace/scratch.
