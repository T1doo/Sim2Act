# Fresh journal metadata projection

Base `e5954eb4668a61ec4874fbca4090296edbad8712`. This is one actual product-code optimization on the existing Cold lineage path, not a new model/Mock/G0 window or a production account source.

## Change and preserved boundaries

`pa_trial_dispatch._metadata` previously rebuilt the same 16 SQL projection expressions (kind, four request fields, nine response identities/digests, byte count and completeness) every time. A private data-free SELECT now owns only that fixed projection. Each invocation still builds the original WHERE predicates with current principal/Run/Attempt/family values and executes the original query. The separate event-anchor query is unchanged. There is no new input qualification, row/digest/PASS cache, merged read, omitted projection, body substitution or cross-write proof reuse.

The complete old function after its first SELECT remains unchanged, including guard order, body/seal comparison, phase and identity checks, exact event multiplicity and digest/completeness comparison. Dynamic authorization, SQL read sets, transaction/write boundaries, Run/fence/stop and all lease/TTL/clock gates in callers are unchanged. Nonexact strings, None and mappings retain their original expression construction and input-read behavior. A shared SQL expression is not an authority or proof.

The real call site is `_graph_journal_chain`, called for every Generate/Source ancestor by `_graph_stage_accounted`, and again by the postwrite `_model_settlement_read` path. This establishes reachability, not an attribution of historical total SQL or whole-transaction cost to this helper.

## Targeted correctness evidence

Final frozen version: **17 PASS in 0.23s**, no skip/fail, with one existing Starlette/httpx deprecation warning. Ruff on the three changed Python files passed. The development oracle initially omitted its `REQUEST` import: 13 FAIL/4 PASS, retained in development.log/XML. After fixing that test import and explicit loop binding, validation was 17 PASS/0.20s; the final 17 are the same tests, not 34 independent cases. Only import ordering changed between validation and the source freeze. No production change was made in response to those harness errors.

The tests create only isolated in-memory SQLite tables and synthetic rows, then compare the real old and candidate functions: exact result types, SQL text and parameters, guard trajectory; Request/Response and missing data; single/changed seal; wrong phase/owner; absent/changed/duplicate event; principal/Run/Attempt isolation, None, string subclasses and RowMapping; mutation of the Run or event between the two reads; original guard exception; fresh writes and rollback. The legacy oracle's function AST was checked equal to the base function after normalizing its name. SQLite and PostgreSQL statement compilation match; PostgreSQL execution was not performed. These tests do not instantiate a Worker or claim a whole-platform revocation/fence regression.

## One predeclared bounded comparison

`plan.json` freezes three source digests and the thresholds before measurement. Twelve alternating-order paired rounds, 60 calls per arm, 8 warm calls per arm, four synthetic scoped cases spanning Request/Response. Each call runs the actual helper, current predicates and bound values, both SQLite queries, JSON result decoding, and all its predicates. The guard is a lightweight counter, **not** the Cold graph pin: full caller traversal cost is outside this measurement.

Actual 1456 helper calls, **2912 SELECT and 8736 counting-guard calls**, equal checksums, 12/12 wall wins. Paired median candidate/legacy ratios: wall **0.46493425937276567**, thread CPU **0.46496089985035793**. The predeclared minimum was 9 wins and both ratios <=0.95; result QUALIFIED_LOCAL_METADATA. No tuning or second comparison occurred. Fixture schema/seed writes occur only in the memory database before measured reads, not in product storage.

`execution.json` independently records the exact supervised argv, start/end UTC, owned timeout PID1055, process exit0, and before/after source hashes matching the prior plan. Supervised process interval **1.309614167s**; script interval through engine disposal **0.918069218s**. Work bound30s, owned timeout35s, TERM cleanup grace5s. The supervised process exited normally, engine/connection were disposed, no service/background process was created. The before/after hashes witness those endpoints; they are not an independent guarantee against transient changes between samples. `checks-execution.json` records the final pytest/Ruff argv, time and exit status separately.

## Remaining original product gates

This does **not** prove 30-second G0 qualification, current whole-Cold speed, the full prepare/first commit/receipt/second commit/normal scope/final-deadline path, or a gain on all historical 28230 SELECTs. No complete Cold timing window, Mock exchange, real model, browser or new CI ran in this slice. Previously captured full-chain failures remain failures.

Production evidence is a separate unimplemented boundary: `production_evidence.resolve_account` still ends with SOURCE_MISSING after projecting original requirements. A reviewed source must actually bind the current provider account/quota subject to the original principal/project/contract, provide current entitlement and non-chargeable enforcement provenance, and handle expiry/revocation. User confirmation of no charges is not rewritten as official provider evidence; this slice neither installs a resolver nor bypasses source admission. The existing explicit configured synthetic path remains distinct.

After local review, normal development-branch push is authorized. main, force push, deployment, credentials, security permissions, paid services and browser sandbox are untouched. The unrelated warm UI remains awaiting new real pixel verification; none of its old screenshots signs this code or the warm candidate.
