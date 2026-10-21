# Target-only selector design addendum

2026-10-21. Read-only independent design review. No product, test, database, Worker, Mock, G0 or prepare/commit execution; no repository writes.

The author's revised proposal closes the initial P2 at design level: `StopBoundary.wrap(..., *, _target_context=None)` retains the exact original callable in the unbound / non-target branch. The existing target/current/version/attempt checks, Mock close and `arm_g0` remain in their original order. Only the protected target `try` block enters `_target_context` when supplied; otherwise it enters original. The original exception/else handling remains around that context's complete unwind.

The prefix retains original_context as the original runtime function and supplies a separately constructed exact-config partial only as this internal target context. None preserves original behavior and callable identity. No guessing target identity, weakening explicit runtime eligibility, account substitution, grant changes, public configuration or default activation is implied. Selector/construction failures must not become success or a silent default fallback; the target callable itself is not permission.

Result: CONDITIONAL_DESIGN_ACK_TARGET_ONLY_WIRING. This acknowledges the proposed correction and original inner candidate-before-CGR-exit ordering; it does not approve unreviewed implementation bytes, full prepare/G0 behavior, a new window or performance qualification. The earlier P2 report remains the initial design record. Frozen-source review is still required.
