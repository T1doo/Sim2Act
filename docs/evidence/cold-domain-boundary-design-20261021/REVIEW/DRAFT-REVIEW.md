# Concrete design review — final frozen draft

Decision: **ACK_DESIGN_ONLY / NOT_READY_IMPLEMENTATION**. No remaining substantive misstatement or safety regression was found in the reviewed architecture draft. This does not approve a runtime patch, changed tests, transaction split, new execution window, or performance claim.

Reviewed draft: `/tmp/sim2act-domain-boundary-design-20261021/DESIGN.md`, SHA-256 **`379d761e6655f82a44a1b4d2dddf6779278a880d72ad1311aad4a85dbfe2a841`**. This ACK binds exactly that text. The original `REVIEW.md/.json` remain unchanged.

## What the draft gets right

* It correctly separates V5 business requirements from private implementation oracles. V5 §§5.5/8/9/10 require current permissions, complete normalized business definitions and versions/read ranges, collection dependencies, immutable releases, lease/fence exclusion and atomic effects. They do not universally require Python helper-object alias topology, private pickle bytes, or arbitrary monkeypatch exception order. Mutation injections that model actual data/revocation/expiry defects remain in scope.
* The selected first scope is exactly the existing **test-only SQLite G0 prewrite branch**. Keeping the original connection and `BEGIN IMMEDIATE` does not solve writer-lock/heartbeat contention and does not predict a 30-second pass. PG, ordinary fallback, apps origin and postwrite validation are explicitly unmigrated.
* Controlled producer entrypoints still perform original authorizations, actual reads and complete business validation. Strict recursive owned values are required; frozen wrappers and live metadata are expressly insufficient. Every migrated consumer must use those values alone. A root with an outstanding raw consumer retains its old full checks. This prevents treating a new digest or an identity check as a substitute for mutable-input validation.
* Pure computation over already authorized owned input is correctly distinguished from a new external sensitive-resource read. Non-pure callbacks terminate that pure segment; the next affected consumer gets current authorization/control checks and necessary reacquisition. Unknown callback influence requires conservative complete coverage through the original gateways.
* The two original commit semantic gates, complete accounting/source relationships, original finite vector, fresh stop/clock **after scope closure**, W5 position/group, postwrite live/settle/tail and atomic rollback all remain. Time used by final normalization/digest work is consequently inside the original deadline.
* Persistent business/approval/source/receipt fingerprints remain compatible; only a new private domain/version is proposed. The unchanged origin/post consumers and their existing pickle V2 / row-storage-v2 `(raw,key)` contracts are explicitly protected. Software/audit anchor propagation remains an implementation prerequisite, not an unsupported compatibility claim.
* Cross-transaction readset/CAS is correctly a separate blocked extension. The draft records single-row and predicate/collection/absence coverage, possible expected write deltas, fresh T1 authorization and original non-extending caps. It does not use the still-unproven extension to justify the first same-transaction step.
* Existing tests are classified by protected behavior, rather than by whether injection uses monkeypatch. The draft preserves unknown usage, received response, original bounds, private-read order, no extra requests and rollback outcomes. It makes no claim that proposed new regressions already ran.

## Clarifications resolved before this final binding

The earlier draft's “continue v1” label was corrected to the actual existing pickle V2 / row-storage-v2 protocol. Retaining all hidden row payload positions was clarified as a conservative first migration policy, **not** a universal V5 mandate to hash driver layout; it permits only controlled recursive value projection, no foreign metadata/live alias. Unknown non-pure influence now defaults to full conservative coverage. Pure internal field access is explicitly distinguished from a new external sensitive read. None of these clarifications widens execution authorization.

## Remaining conditions are acknowledged, not closed

Section 7 accurately leaves open the complete producer/query/field/consumer and callback map, concrete immutable grammar and issuance/escape proof, dynamic-control coverage, and local/persistent compatibility matrix. Those are necessary before approving an implementation. A final manifest hash is not independent proof that its fields are complete, its issuance is legitimate, or its values remain owned. Required scope/generation/role/phase issuance and unchanged transaction/write invalidation must be made precise in that implementation design.

`STATIC-SEAMS.json` (SHA-256 `313897b0228a433648e50d18b57bb8d65e09d8fe1a663059abce658adbaff7a0`) is accurately labeled a starting AST inventory. Its 11 symbol entries contain 12 explicit recorded add sites; the artifact does not claim to enumerate all transitive consumers, dynamically composed graph additions or SQL predicates. It supplies no closure proof or permission to remove a check. The conservative hidden-row policy is acceptable for this bounded first design; it is a migration choice and its cost/representation must be assessed without turning it back into an unrelated product requirement.

The CSV section correctly avoids creating duplicate work or granting permission. Current source/UI presence was read-only checked; no independent UI acceptance, PG/Windows/native qualification, or grant action was performed by this reviewer.

## Actual verification and limits

Read the entire initial and corrected eight-section draft, original V5 sections and manifest, current selected runtime/Store/source-read/origin code, targeted existing test source and current CSV UI source. Independently hashed the 15 files in `SOURCE-HASHES.json`: all matched; both V5 document hashes agree with their original manifest. `SOURCE-HASHES.json` SHA-256 is `f181a0fbd5f498ed4d6636456cf65b896bb7604e0791f7fd80f96718e9af0c9c`.

No tests, profile, product imports, DB opens/decompression, fixtures, Mock/model, G0/launcher, signals or repository writes. Existing stage-cost values are historical evidence referenced by the draft, not a new measurement or a new causal codec breakdown. The supplied AST inventory was read, not executed. This is a bounded design-source audit, not a complete transitive dataflow proof. At the start of this draft review, HEAD was `c20b8b6baf2c023b5dc7c89f7e8282bad112f350` and `git status --short` was empty.
