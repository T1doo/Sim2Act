# Independent read-only review

Separate reviewer `/root/polling_review` read the product diff, new actual HTTP
oracle and preserved baseline failures without writing or running tests.
Result: LIMITED PASS, no blocking product issue found.

The original background read increments runSelectionGeneration and invalidates
an awaiting foreground API / async hash render. The wrapper preserves all
existing identity/project/generation/selectionGuard/receipt checks and skips
only background detail reads matching the active foreground identity/project/Run.
Finally uses object identity so an older foreground cannot release a newer one.
No POST, grant, model or execution ability is added. The actual page oracle
captures the real timer callback and gates real loopback HTTP responses; it
reproduced the missing checkbox before the product patch. It is JSDOM, not Edge.

Reviewer raised one nonblocking oracle cleanup risk: a gate reached only after
cleanup begins could wait until the original Python 60-second bound. Add a
closing flag so such a late gate releases immediately; keep all assertions and
timeouts. Rerun the strengthened oracle on both backends.

The independent review does not resolve the unrelated original resources-history
10-second TimeoutError. Its five-test original-code recheck PASS is not proof
that the full baseline was clean or that this timeout is fixed. Preserve that
remaining diagnosis boundary for parent review.

Final independent read-only recheck confirmed exact candidate 3fe824b826df6f1040989ddb5f821290dfc33e4b and closing-gate cleanup. LIMITED PASS retained; no tracked uncommitted change, no test run by reviewer.
