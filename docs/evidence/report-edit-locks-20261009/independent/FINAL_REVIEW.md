# Independent final review — LIMITED_PASS

Exact final candidate: `a567e08fcf0e2135bdd02bd62e0e8c2ceb842a47`.
Initial implementation: `501db575c06196259157e3ad5054456e2a830e2d`.
Baseline: `afb2f1f3813fc3a4744923f31bbcb4666b88cccd`.

The UNKNOWN-plan recovery blocker found independently on 501 is fixed. There
is no remaining blocking finding in this bounded canonical Report manual edit
lock slice. This is LIMITED_PASS, not overall F2-T07 / project acceptance.

## Precise evidence attribution

* **501 backend: 17 independent SQLite/API cases passed, zero failed/skipped**,
  75.91 s. `test_independent.py`, `pytest-final-initial.log`,
  `junit-final-initial.xml`. Existing synthetic source/archive fixture builders
  establish a genuine canonical Report and persisted Run; no author's new
  lock test body is used as independent evidence.
* Cases include public VIEW/ACTION lock, cold Store exact original-key receipt,
  graph/lock ABA rejection, CURRENT/SUPERSEDED history, zero changes outside
  lock/request metadata, actual locked-view plan rejection, unlock/new exact
  plan/archived explanation readback, six CAS/type/key negatives and six
  owner/source/hash/Grant/source-Run/canonical-kind/seal negatives. Canonical
  Report, grants, budgets, Run and archived output remain unchanged.
* A real accepted Report PROJECT plan was retried with exactly its original
  key/body after a peer's public lock and rederive. Actual API returned
  HTTP400 LOCK_CONFLICT, while the accepted plan remained persisted and all
  tables stayed unchanged during retry: `accepted-replay-lock.json`. This
  validates the genuine server path behind the 501 UI recovery regression.
* **Exact baseline afb: two new Report public lock API cases fail as expected**
  at HTTP400 UNSUPPORTED_CAPABILITY; `pytest-old-negative-final.log` and
  `junit-old-negative-final.xml` (15 intentionally deselected).
* **501 product JS fails independently on UNKNOWN retention**:
  `proposal_unknown_probe.cjs`, `unknown-probe.json`, `unknown-probe.log` show
  equal original plan POST bodies, map size 1 -> 0. `js-501/failure.json`
  records 32 successful checks before the blocking assertion. All failure
  logs remain preserved, including initial independent harness setup errors
  described in `REVIEW_501.md`.
* **Final a567 product JS: 42 independent checks passed**:
  `review_js.cjs`, `js-a567-extended.log`,
  `js-a567-extended/result.json`. The script loads actual product HTML/JS from
  disk with a real server-produced canonical Report / sealed graph fixture;
  controlled API faults exercise page behavior. This is jsdom, not a native
  browser or independently run actual HTTP server.
* Final same independent driver on archived exact 501 source again fails as
  expected on UNKNOWN retention: `js-final-negative-501.log`,
  `js-final-negative-501/failure.json`. The successful final JS controls are
  sensitive to the actual source fix.
* **All 73 tracked src/schema files match a567 Git blobs byte-for-byte**:
  `source-bytes-final.json`. Initial 501 byte checks stay in
  `source-bytes-501.json`. Final JS load hashes are in the final result JSON.
  Relative to 501, the only product file changed is `report-manifest.js`;
  backend and Schema bytes are identical. The 17 backend cases are not claimed
  as rerun on a567. Other a567 changes are documentation and tests; the old
  derived-Report read test correctly expects authorized read-only HTTP200.

## What was independently verified

The public family tuple adds only bounded_report/intern.conditional_report
beside original registered_tool/data.aggregate_csv after load_family's full
ownership, canonical source/Run proof, hash and Grant intersection validation.
Existing exact graph/node/lock CAS, canonical request, immutable accepted seal,
source binding and cold receipt remain unchanged. No executor, API, table,
identity, Grant, budget, business write or real model call is added.

The final 42 JS checks cover current sealed graph and proof retention on only
the known Report lock / exact historical project-binding errors; tampered
seal, revoked Grant, authorization and unclassified errors clear current
evidence. CSV history errors remain fatal and Report never requests CSV column
history. Only the correct Report/CSV executor tuples show manual controls.

Proposal recovery now sets UNKNOWN before each plan POST, remembers previous
UNKNOWN, and records an explicit first rejection only at that exact /plans
call's HTTP400 LOCK_CONFLICT. Context and shape validation and assignment of
the accepted plan precede clearing UNKNOWN. The independent checks cover:

* First known rejection releases the unexecuted draft and a fresh same-page
  proposal uses a new exact plan key.
* Earlier lost acceptance plus later LOCK_CONFLICT retains the same intent
  and exact plan body/key.
* Invalid accepted-plan shape followed by LOCK_CONFLICT retains UNKNOWN;
  non400 LOCK never releases an intent.
* Late plan response after selection change leaves UNKNOWN and sends no
  presentation patch; derive same-code failure never proves plan rejection.
* Already accepted plan plus rejected presentation patch preserves the exact
  intent; an old closure cannot delete a replacement intent object.

## Preserved boundaries

Independent scope is SQLite/API/cold Store and disk-loaded page JS with fault
injection. Author's PG, real HTTP pages, source upgrades and native evidence
retain their own attribution; this review does not independently sign them.
Fixture setup uses original synthetic MockTransport responses only (four
model-shaped fixture exchanges per prepared Report), no actual provider calls.

PG resources-history/full-range timeout remains OPEN; HTTP200 damaged-response
feedback limit remains; Windows900/Edge240/Node150 remain unaccepted.
PROJECT PENDING/BLOCKED_PARTIAL, semantic UNKNOWN, owner PENDING,
overall NOT_ACCEPTED, LIVE=0. No product, author test, Git ref, author process
or PG resource was changed by this reviewer. Evidence remains in the private
temporary directory for the parent to copy into its delivery evidence commit.
