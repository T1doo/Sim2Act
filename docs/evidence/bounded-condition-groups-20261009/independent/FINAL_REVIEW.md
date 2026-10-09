# Independent review — LIMITED_PASS

Final exact candidate: `79b119b616a20d9347b5677c0d58fbbbe18127c8`.
Product freeze: `f4bf46355e009617775c056540fc45fcc4512a77`.
Original implementation freeze: `eeb368ccb338429637f271bf57bdb2781245b976`.
Baseline: `8c572154ff72ac61a506fb9313cb631996e76df7`.

The low severity four-leaf add-button finding is fixed. Final product diff from
the original freeze is exactly one statement-order change in `csv-dag.js`;
all backend and schema bytes are unchanged. The only other changed file is the
author's driver adding two boundary checks. Final 79b changes only the Python
UI wrapper's expected check count from 22 to 24; all product bytes match f4.
No remaining blocking finding was
identified in this finite all/any slice.

## Independent evidence and precise attribution

* Original eeb freeze: newly written `test_independent.py`, **21 SQLite/API /
  actual Worker cases passed**, zero failed / skipped; `pytest-final.log`,
  `junit-final.xml`. Cases cover bool/int/string eq/in/exists, four-leaf order,
  missing eq/in no short circuit, dependency skip priority / no Operation,
  invalid last leaves rejected before writes, observed-value tamper cold
  rejection, actual fence takeover / stale worker rejection, cold proof/key
  readback, and unchanged v1 permissions / budgets. Number is only a general
  preflight + pure decision check, not an actual registered numeric-output run.
* Exact baseline 8c source: **4 API group cases failed as expected**, all at
  HTTP422 (unsupported groups); 17 intentionally deselected. Evidence is
  `pytest-negative.log`, `junit-negative.xml`. These are sensitivity controls,
  not unexpected candidate failures.
* Original eeb JS: `review_js.cjs`, `js-result.json`, 12 records; found the
  clickable-at-four button while confirming the fifth-leaf append guard and
  original-key lock remained effective. During harness setup, script loading
  was corrected to preserve browser global bindings and the context fixture
  was corrected to satisfy the real deliveryCurrent predicate before these
  final checks; those setup failures do not count as candidate failures.
* Final f4 freeze: independent `review_fixed_js.cjs` **16 checks passed** on
  actual product DOM/JS in jsdom, `fixed-js.log`, `final/js-result.json`.
  Both legacy and composition modes check four leaves disable add, a fifth
  click cannot mutate the draft, deletion re-enables add, unknown original-key
  intent locks every control, restoration unlocks below maximum, and adding
  again disables at the exact maximum.
* The same fixed-boundary independent driver on exact eeb product source
  **fails as expected** at `legacy four leaves disable add`, recorded in
  `fixed-negative.log` and `fixed-negative/js-failure.txt`.
* Final `final/source-bytes.json`: **all 73 tracked src/schema files match
  79b frozen Git blobs byte-for-byte**. Actual loaded JS SHA256 values are
  in `final/js-result.json`. Original eeb checks stay in `source-bytes.json`.
  Final `csv-dag.js` SHA256 is
  `a890c0e6544c1a3df3dd04afca85ed6cbe0f126fd48499c5a2c4ba283d7b621d`;
  this literal is subordinate to the machine-readable byte evidence.

Source review confirms the original V5 product §5.3 and stage F2-T04 finite
logic-combination requirement. Every leaf goes through original schema and
declared-direct-predecessor preflight. Evaluation collects all leaves before
all/any reduction. Saved decisions remain part of intent/receipt/skip
fingerprints reconstructed on read/recovery. Binding and commit guard retain
authority, lock, version, lease/fence and conservative tool budget checks.
No new executor, API, table, grant, write, model request, or budget was added.

## Boundaries

This LIMITED_PASS is for the finite condition-group slice only. Independent
checks used isolated SQLite and disk-loaded jsdom; they do not constitute
independent PG, actual HTTP, old-source upgrade, native-browser, Windows,
semantic, owner or whole-F2 acceptance. Author's separate PG/HTTP/upgrade
evidence must retain its own attribution. The backend cases were not rerun on
f4 because their exact product bytes did not change.

PG resources-history / full-range timeout stays OPEN; HTTP200 damaged-response
feedback limit stays; Windows900 / Edge240 / Node150 remain unaccepted.
PROJECT PENDING/BLOCKED_PARTIAL, semantic UNKNOWN, owner PENDING,
overall NOT_ACCEPTED, LIVE=0. No product/author test/Git ref/PG resource was
modified by this reviewer. Evidence remains in the independent temporary
directory for the parent to copy into its final evidence commit. The author's
first final-UI wrapper run had three assertion failures because the driver
passed 24 checks while Python still expected 22; the test-only 79b correction
is precisely reviewed here, while the author's subsequent actual HTTP run
is separately attributed.
