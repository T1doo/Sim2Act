# Correction receipt → exact child Run evidence

Base: `a7403b379b1278fd1be533ca21d790f0311244af`. Product changes: existing correction receipt UI gains an explicit GET-only child Run opening action, using existing instance/Run/owner controllers.

`author/` is an exact byte copy of the sealed local author evidence. Manifest SHA-256 `f28d69256f11a7af2a640610a3597d1590667d1ffb1993bf06a998a8e18f4ee9`; 16 evidence files plus the manifest, 54,472 evidence bytes. No DB, real account material, credential values or credential hashes are included.

- `second-run.json` and `pytest-qualified-temp/.../correction-run-entry.json`: 24 checks on actual HTML/controller JS with synthesized GET responses and renderer stubs. No actual backend/Worker/model or human semantics.
- `pytest-qualified.xml`, `.stdout`: 1 test passed (4.89s). First `pytest.xml` records missing jsdom caused by inherited NODE_PATH; the passing command used the existing `/workspace/node-tools/node_modules` installation.
- `existing-navigation.json`: existing synthesized GET navigation regression, 36 checks passed.
- `first-run.json`: initial harness failed after 19 checks because it attempted Run selection after that selector had already been cleared; corrected to the actual reachable selection point while Release GET was held. Preserved, not counted as PASS.
- `check-*.json`: exact command arguments, output and exit codes for Ruff, three JS syntax checks and diff check.
- `reviewed-source-map.json`: tested/reviewed input bytes. `implementation.diff` includes JS/harness tracked edits; the commit holds the new HTML control and new test files.
- `source-controller-static-audit.json`: source-only evidence that production account resolver/controller registration remains unimplemented. It is not an account probe or LIVE qualification.
- `summary.json`: execution boundaries and NOT_RUN items.

The modified existing full correction HTTP/Worker harness was **not rerun**. Windows, PostgreSQL, remote CI, native browser, real models/scenarios/semantics and real human acceptance were not run. Earlier 7-call chain and recovery matrices were not repeated.

No remote operation was attempted for this slice. Previous push acknowledgement and later independent authentication denial remain separate evidence; local tracking refs do not establish the current remote state.

The original failed JUnit XML contains three trailing-whitespace lines. Its bytes remain unchanged: a full staged diff check reports those three raw evidence lines; implementation/tests/explanatory Markdown pass the scoped check.

[Finite independent review](review/final-independent-review.md) passed with no new definite P1/P2; exact frozen-file scope only, no future commit/push endorsement. Its sealed manifest SHA-256 is `6e972e6016a5294b4ba53a1b4dcf3f8b41359084e1c32b27c25d4e97ffea2854` (11 files / 33,294 evidence bytes, manifest additional). The reviewer also preserved and corrected one file-audit fixture-count error; no product execution was performed by the reviewer.
