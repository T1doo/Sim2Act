# Independent initial review — BLOCK

Exact frozen candidate `501db575c06196259157e3ad5054456e2a830e2d`;
baseline `afb2f1f3813fc3a4744923f31bbcb4666b88cccd`.
Scope: original F2-T07 / V5 §9.3(6), canonical Report public manual edit locks.
No product, author tests, Git reference, or author PG/test resources changed.

## Blocking finding

`report-manifest.js` proposal catch deletes the local presentation intent on
HTTP400 LOCK_CONFLICT when no plan/body has been assigned. However a plan can
have been accepted durably while its HTTP reply was lost. Retrying that same
plan key after a same-project peer lock/rederive genuinely returns HTTP400
LOCK_CONFLICT from project expansion; no local plan/body is assigned and the
new catch deletes the original UNKNOWN intent. Local absence of a plan does
not establish that acceptance never occurred.

* `proposal_unknown_probe.cjs` / `unknown-probe.json` / `unknown-probe.log`:
  exact same plan requests twice, intent map size 1 -> 0, failed assertion.
* `test_real_accepted_plan_replay_can_return_lock_conflict_after_peer_lock`:
  actual SQLite API plan accepted -> peer public lock -> peer rederive ->
  same-body/key plan retry HTTP400 LOCK_CONFLICT. The original plan request
  remains persisted and no tables change on retry. `accepted-replay-lock.json`.
* Independent product DOM/JS `review_js.cjs`: 32 checks passed before the
  UNKNOWN-retention assertion failed; `js-501/failure.json` / `js-501.log`.
  Existing `deliveryReadPlanHistory` known/fatal separation, Report CSV-history
  omission, UI family tuples, first explicit rejection release, and original
  key retry equality pass before this blocking finding.

Suggested correction: track UNKNOWN before sending /plans and capture whether
an earlier submission was UNKNOWN. Only this exact plan-call's first explicit
HTTP400 LOCK_CONFLICT with no earlier UNKNOWN may mark planRejected and clear
UNKNOWN; completed accepted-plan validation/assignment clears UNKNOWN, while
network, shape, and stale-context failures preserve it. Outer release still
requires no plan/body and map object identity equality. A derive error or a
patch rejection after accepted plan cannot release the plan intent.

## Other independent evidence

`test_independent.py` is newly written. Existing synthetic archived source
fixtures are used solely to build a real bounded Report, sealed graph and Run;
none of the author's Report-lock tests are run as independent evidence.

* `pytest-final-initial.log` / `junit-final-initial.xml`: **17 passed, 0 failed,
  0 skipped**, 75.91 s. SQLite / actual API / cold Store, view and action node
  locks, lock revision + graph ABA, original-key cold receipt, immutable source
  and authority scope, actual lock conflict, unlock/new plan/original archived
  explanation finite readback, 6 CAS/request negatives, 6 source/owner/Grant/
  source-Run/canonical-kind/seal negatives, real accepted peer-lock retry, and
  a genuine server-returned sealed page fixture for independent JS.
* Exact archived baseline afb source: both view and action public Report lock
  API cases fail as expected at HTTP400 UNSUPPORTED_CAPABILITY;
  `pytest-old-negative-final.log` / `junit-old-negative-final.xml` (15
  deselected intentionally). This demonstrates the real capability gap, not a
  candidate test failure.
* `source-bytes-501.json`: all **73 src/schema files** match frozen Git blobs
  byte-for-byte. Product JS hashes loaded by the independent harness are in
  `js-501/failure.json`. Exact original/baseline archives retained.
* Harness setup failures are retained in initial `pytest.log` / `junit.xml`
  (recursive imported fixture), then `pytest-fixture-fixed.log` /
  `junit-fixture-fixed.xml` (14 passed, wrong action logical key and peer
  filtering in two independent tests). Corrected key is action:report; peer
  filtering skips noncanonical drafts. The initial negative log retains a
  corresponding harness node-key error. None is counted as product failure.

Source review traced load_family's complete owner, canonical proof, source
Run, resource hashes and Grant intersection before graph/lock/request reads.
Tuple extension accepts only original registered_tool/data.aggregate_csv and
bounded_report/intern.conditional_report. Existing CAS, sealed receipt,
source binding, canonical lock request and cold recovery mechanisms remain.
Only lock/request tables mutate for metadata operations; canonical Report,
Run, grants, budgets and archived output remain unchanged.

These checks are limited SQLite/API and disk-loaded jsdom, with controlled
response fault injection. They do not independently sign PG, real HTTP pages,
old-source upgrades, native, Windows, owner/semantic, or whole F2 acceptance.
Synthetic MockTransport setup makes four original model-shaped fixture
requests per prepared Report; no actual model/network authorization used.
PG resources-history / full-range timeout OPEN; HTTP200 damaged-response hint
limit retained; Windows900 / Edge240 / Node150 unaccepted. PROJECT
PENDING/BLOCKED_PARTIAL; semantic UNKNOWN, owner PENDING, NOT_ACCEPTED, LIVE=0.
