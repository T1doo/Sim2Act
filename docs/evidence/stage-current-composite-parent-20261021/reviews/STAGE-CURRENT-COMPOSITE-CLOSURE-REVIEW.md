# Stage-current composite: final limited review

Result: LIMITED_PRODUCT_AND_LOCAL_TEST_EVIDENCE_ACK. No outstanding product P1/P2 was found in the exact one-callsite change. The test-only cross-call assertion refinement is closed.

This report supersedes the pending-test portions of the earlier design/code review and frozen-test addendum, which remain historical originals. Reviewer read source, diff, hashes and author-produced logs/JUnit only; reviewer did not run tests, import product modules, open a database, run Worker/Mock/G0, invoke a launcher, or write the repository. This review creates or expands no grant/window and makes no performance or production qualification claim.

Baseline: `e4dddb1c8fd9a67a622e5d69c8637e07a38f8836`.

Final product SHA256 `src/sim2act/natural_live_admission.py`: `84195d0061f965b8f1cc2e1bc385941c2739e09dce02293596b3025f14b4433a`.

Final test SHA256 `tests/test_cold_accounted_stage_pin.py`: `9265b2ea628a34c9a93604e6688c41eada81dd2974845b08f8d13bdaf21a5392`.

The product diff remains precisely the replacement of the pin/stage-raw pair inside `_graph_stage_current._parent_pin` with the already-reviewed fixed `_graph_trial_stage_parent_pin`. Default fallback retains the pair. Exact ready-native dispatch, original first full graph pin, complete relationship predicates and close-on-exception remain in the existing composite. Typed cohort, independent public entry guards, SQL, query/external-return guards, business predicates, deadlines, final guard and returned authority are unchanged by this diff.

Read original evidence under `/tmp/sim2act-stage-current-parent-20261021/tests/`:

- `frozen-final.log` and `.xml`: 115 passed, zero failures/errors/skips; pytest 207.52 seconds, JUnit 207.516 seconds. `frozen-before.json` and `frozen-after.json` record unchanged product SHA above and test SHA `a6bcdedb5f92fa69a662fbee2840cb98f10dfcccbfd09468b28233a928d85627` during that batch.
- The final test-file diff from the saved `before-assertion-narrowing.py` changes only the four parametrized cross-call cases' exception observation. Inner `pytest.raises` surrounds only the second stage-current call; the same observed exception is rethrown through the original scope cleanup. Outside, `second_error is not None` and `scope_error.value is second_error` are required. Therefore unexpected entry/first-call failure cannot satisfy this test. Closure still requires the mode and graph inactive.
- `closure-before.json` binds that amended test SHA and unchanged product. `closure.log` and `.xml` show the four amended Source/Cold mutation/revocation cases passed, with zero failures/errors/skips; pytest 7.20 seconds and JUnit 7.203 seconds. The unchanged 111 other cases were not rerun after this test-only assertion change; this is not described as a second full 115-case run.
- `mypy-frozen.log`: success for one source file. `ruff-frozen.log`: all checks passed, associated with the broad frozen batch. These logs are not claimed as new checks of any later formatting change.

Actual stage-current observations in the broad log:

| Stage | Old codec calls | Composite codec calls | Parent calls | Difference |
| --- | ---: | ---: | ---: | ---: |
| Source | 376 | 226 | 25 | 150 = 6 × 25 |
| Cold | 754 | 526 | 38 | 228 = 6 × 38 |

Each original parent span was asserted to be seven codecs and each composite span one; complete family/run predicate sequences and authority fingerprint/job identity were equal. The real preliminary graph.add was separately measured as exactly two codec calls for the snapshot-derived precise Release-pointer key. Both compared calls then retained identical complete root keys. This proves local redundant codec removal on these synthetic actual stage-reader paths; it does not provide real-G0 wall time, lease margin, CPU/RSS bounds or complete-scope success.

The earlier `targeted.log` is retained: 28 passed, two failed, 46.50 seconds. The failed initial unprimed comparisons were Source 378−226 versus 6×25, and Cold 756−526 versus 6×38. The final test explicitly observes and separates the original lazy insertion rather than relaxing the six-per-parent assertion. Those failures are not relabeled as passes.

Historical actual G0's first-commit 0.5311813354492188-second deadline overrun remains its original result. This local evidence does not show that the full receipt interval, second commit and original context exit fit the existing deadlines. Those boundaries remain actual-window evidence questions, not conclusions of this local test review.
