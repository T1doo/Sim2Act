# DeliveryGraph UI integration plan

Base: bd502de9776acd19d2836e67ba5e264896921389. UI owns delivery-graph.js, minimal generic-app hooks and actual HTTP/DOM tests; backend/API/core remain separately owned.

An explicitly opened generic app may save a server-derived graph anchor, read current stable nodes and select existing nodes for an impact plan. This is PLANNING_ONLY; semantic UNKNOWN, owner PENDING, publication disabled. Pending scope jobs are durable plans, never executed checks or patches.

Acceptance: bind project/app/candidate/runtime/current authorization and the full saved graph/source versions; validate receipts against selected node versions and the persisted readback. Lost/malformed save or plan retains the exact request body/key for recovery. Known first rejection differs from a rejection after an unknown acceptance. Clear protected state on identity/project/app generations including ABA; reject coherent receipt/history substitution; render only textContent. Actual HTTP fresh-page tests cover derive/read/plan/history, changed arguments, node revisions, cross-project/identity/late responses, revocation and malformed receipts. No model requests, grants, publishing, PG, full suite or CI. Native NOT_RUN.

Read without an anchor is distinguished only by VERSION_CONFLICT and exact detail `DeliveryGraph anchor has not been derived`; other conflicts are failures. Source versions are server logical sealed versions, not invented resource database counters.

PROJECT contract correction (server Plan4660): UI verifies closed normalized expansion/core outer fingerprint and independent full native envelope fingerprint. Full native scope includes current membership, candidate/graph/graph-revision/authorization/lock snapshots; missing peer graph is BLOCKED_PARTIAL with GRAPH_NOT_DERIVED, never an invented graph. UI verifies applications/omissions exactly account for membership, scope jobs bind that same snapshot and request, and history invalidation clears evidence. No automatic graph reads on app open.

Authority fixture order correction: before/after full-row snapshots of principals/grants/attempts must explicitly ORDER BY id. SQL row order is otherwise undefined, including PostgreSQL. Preserve every row and field, no set/dedup or changed assertions; only the existing single revoked=true/revision+1 difference remains permitted. Commit plan before source, then rerun Graph CSV/Report actual HTTP/DOM only; no product UI, API, budget or original49 changes, no PG/full/CI.
