# Independent bounded review — initial freeze

Exact reviewed candidate: `eeb368ccb338429637f271bf57bdb2781245b976`.
Baseline: `8c572154ff72ac61a506fb9313cb631996e76df7`.
No product, author test, Git reference, PG container, or author test process changed.
Tests below were newly written independently. Existing isolated environment fixture
and original source-application fixture builder were reused, not author test bodies.

## Initial result

LIMITED_PASS for finite groups' backend behavior, with a low severity UI finding
awaiting the author's correction and a new exact freeze. No whole-project, PG,
native-browser, Windows, or owner/semantic acceptance is inferred.

1. `test_independent.py`: 21 SQLite/API/actual Worker tests pass in 13.46 s;
   zero failures and zero skips. Raw evidence `pytest-final.log` and
   `junit-final.xml`. One existing Starlette/httpx deprecation warning.
2. Four complete groups of bool membership, integer membership/existence and
   string equality pass under all/any and reversed leaf orders; durable leaves,
   original-key deduplication and cold readback are checked.
3. Missing final eq/in fails under an already-true any / already-false all.
   Skipped aggregate preempts downstream group evaluation, even with missing
   input/output, and creates no aggregate/report Operation.
4. Five invalid final leaves (boolean-as-count, self, undeclared predecessor,
   unknown field, nested group) reject before event/run/Operation writes.
5. Tampering actual observation values on executed or skipped persistent proof
   fails cold reconstruction. Grouped aggregate prefix is retained across an
   actual expired lease and increased fence; old worker is rejected.
6. v1/v2 manifest permissions, identity, dependency locks, limits, action
   definitions and conservative budget are equal. No models are called; actual
   execution uses a model adapter that raises if called. Number leaf type is
   checked only in general preflight and pure decision; bounded CSV outputs do
   not supply a number-typed floating-point field.
7. Exact baseline source was extracted read-only with `git archive`; four of
   the independent actual API groups fail as expected with HTTP422 because v1
   cannot accept all/any. `pytest-negative.log` and `junit-negative.xml` record
   these expected failures (17 intentionally deselected).
8. `review_js.cjs` loads all product JS and DOM independently from disk; 12
   records check observations, no short circuit, skipped-null parent priority,
   upper-bound guard, mode edit proof reset, original-key lock, and removal.
   This is jsdom, not a native browser or actual HTTP page.
9. `source-bytes.json`: all 73 tracked `src`/`schemas` files match frozen
   Git blobs byte-for-byte; loaded JS SHA256 values are in `js-result.json`.

## Finding

`src/sim2act/web/csv-dag.js`, `csvDagButtons`: the legacy condition-add button
is disabled at four leaves and immediately re-enabled by the following generic
branch-control loop. At four leaves it remains clickable, while append's guard
silently prevents a fifth leaf. This does not break the four-leaf bound or
original-key lock. Fix the assignment ordering and check both composition and
legacy max/removal behavior on a new frozen source.

Source review additionally traced every leaf through existing preflight type /
direct predecessor checks, all-list evaluation, fingerprints of saved intent,
executed receipts and skip events, binding/current authority / commit guard,
and source registry byte anchoring. The bounded change adds no API, table,
executor, write, grant, or budget allowance.

PG resources-history / full-range timeout remains OPEN; HTTP200 damaged-response
feedback limit remains; Windows900 / Edge240 / Node150 remain unaccepted.
PROJECT PENDING/BLOCKED_PARTIAL, semantic UNKNOWN, owner PENDING,
overall NOT_ACCEPTED, LIVE=0. Author's PG and old-source upgrade results remain
their own evidence and are not independently re-signed by this review.
