# Complete Engineering PG phase result — 2026-10-08

Pushed baseline `5c06520bc31269d11b9bf2786b9e18ed89333a28`; independent branch
`dev/pg-phase-diagnostics-20261008` in the new saved-environment instance.
Default fetch and actual checkout succeeded. Main remains the initialization
commit `6f688e4dd80b5c81d41aecde90e360d3629f9c21`. The original instance and its
uncommitted Engineering plan/blocking logs were not accessed or transferred.
[Reconstructed plan](EngineeringPGPhasePlan.md),
[complete first-run evidence](../evidence/engineering-pg-phase-20261008/first/analysis.json),
[controller](../evidence/engineering-pg-phase-20261008/controller.py).

## Actual full baseline execution

Linux/Python3.12.14, exact requirements.lock, Node24.19.0/jsdom30.1.2,
owned localhost PostgreSQL17.11. Image digest and installed versions are in
environment.json. The controller strips existing model/database configuration,
uses generated synthetic credentials and MOCK with zero real provider calls.
No CI or native Windows step was started.

All **1586 unique default tests** were collected and executed; the exact JUnit
node multiset matches collection. All283 source/test/script/workflow files match
the baseline Git bytes before and after this execution. Ruff passed; mypy47
source files passed. Original pytest options include `-q --durations=30 -ra` and
JUnit; no cases, assertions or timeout gates were removed.

|Stage|Actual wall seconds|Exit|
|---|---:|---:|
|Collection|3.467|0|
|Ruff|0.060|0|
|mypy|7.365|0|
|Complete pytest process|1024.981|1|

Pytest reported **1552PASS /7FAIL /27SKIP /1022.56s**, with two dependency warnings.
The controller itself exits0 after preserving pytest's exit1; this is not a PASS.
The skips are23 separately gated R0 PG oracles, one actual Windows PowerShell
launch, two SQLite-only protocol subprocess UI variants and one protected
Chromium sandbox startup. Exact nodes/reasons are retained. Their gates were not
opened or replaced with synthetic success.

## Measured phase classification

|Observation|Count|Accumulated seconds|
|---|---:|---:|
|Reported test setup|1586|211.989|
|Reported test call|1585|792.304|
|Reported test teardown|1586|16.032|
|All observed Store.initialize|1195|72.950|
|Observed initialize labelled env|1134|71.904|
|Fixture setup labelled env|1341|204.563|
|PG initialization DDL cursor|46824|50.130|
|PG initialization existence cursor|3649|0.709|
|PG non-initialization SELECT cursor|1122065|270.235|

Existing plugin reports COMPLETE/pendingSQL0 for its **pytest-process-only** scope.
Fixture labels aggregate nested overrides named env;1341 is not a unique PG
schema count. The appended diagnostic observer records per-definition fixture
counts for a future run, but it has not completed a new PG execution.

Initialize totals are7.12% of process wall as a descriptive ratio, not an exclusive
wall component or possible speedup. Method, fixture and SQL spans overlap, and
SQL cursor spans omit connection acquisition, fetch and commit. They do not
profile subprocess internals or protected Edge. Non-initialization SELECT spans
include fixture work and test calls and do not identify which source-validation
or authority check can safely be removed.

The representative evidence points toward test call/runtime-query costs for the
next measurement; remaining existence probes are a small observed Linux aggregate.
It does **not** establish a Windows-specific root cause, causal optimization or
current900s capacity. No performance change was made from these aggregate totals.
The seven failures also truncate some business paths, so this is not a complete
successful business-path cost envelope. Historical Windows55+741+at least110
unfinished Edge+6=912 remains the established critical path; unfinished Edge and
current native PG attribution remain unknown. Keep900/240/150 and **NO_GO**.

## Established defects and minimal candidate fixes

Candidate source `2315fea1f803ca45e0cbd5ff3da6a329a40d1a1d`:

- Five failed cases use four new cold Stores without the owned fixture's schema
  translation. Their SQL hits missing public protocol_jobs/principals/heartbeats.
  The cold engine now receives the fixture's existing execution options, matching
  the established persistent-AppRun test pattern. It remains a new engine; no
  sharing, DDL, cache or grants were added.
- Real installation CLI test assumed the interpreter could not be the repository
  .venv. This valid new environment makes its assertion false. The exact script
  is now copied into the synthetic repository before CLI execution, preserving
  the original BLOCKED/redaction/no-write assertions independent of caller venv.
- PG cancel race reaches the original final lease-release assertion with None
  after confirmation wins. Confirmation now writes the established no-lease0
  instead of None. No locking order, authority, budget or status gate changed.

All137 assertions in the three modified test files have identical AST multisets
to baseline; the natural-activation PG test is unchanged. No tests were added,
deselected or rewritten to accept a failure. Independent preflight13PASS, then
the five affected/related SQLite modules105PASS0FAIL0SKIP/57.42s. Ruff/mypy47 pass.
The initial SQLite command omitted the owned NODE_PATH and yielded100PASS5FAIL
for MODULE_NOT_FOUND/48.76s; its logs/XML are retained, and only the invocation
environment was corrected before the105PASS run.

## Postfix PG startup blocker and cleanup

The intended full candidate PG run did **not reach collection or pytest**. A
short-SHA invocation was rejected before container/test creation; its log is
preserved. The complete-SHA attempt created one sequential owned PG after the
first full run/container had finished, then its initial census connection failed
with `server closed the connection unexpectedly`. Stages=[], complete=false;
no JUnit or census was produced. After environment transport resumed, the old
terminal session was unknown, so a shell exit code is not claimed. Actual process
inspection showed no running controller/pytest/PG, and its finally receipt proves
owned container label verification and removal.

The controller's socket pg_isready could accept the image's temporary bootstrap
server. The [official entrypoint](https://raw.githubusercontent.com/docker-library/postgres/master/docker-entrypoint.sh)
starts that server with listen_addresses empty and later stops it. This is a
confirmed readiness-check weakness, but actual cause of the failed connection
is **not established** without the lost container boot log. Diagnostic controller
now requires localhost TCP readiness, preserves boot logs and records owned
mounts before container removal with anonymous-volume cleanup. Static command
review passes; these changes are not runtime-PG validated. Following the explicit
disconnect instruction, no further PG/test restart was attempted. Candidate full
PG and its original cancellation race therefore remain unverified.

First full run before/after census: test schemas0, test roles0, public tables0;
labelled container removed. Both executions originally left image-created
anonymous volumes because removal omitted -v. Docker mount/unmount events link
the exact two volumes to the exact labelled owned containers. After checking
anonymous labels and no remaining container references, only these two volumes
were removed; both absence checks passed. Evidence is in owned-docker-events.json
and owned-volume-cleanup.json. No original instance or unrelated resource was
removed. Owned fixture directories are cleaned after verified export; the new
instance's installed venv/dependencies remain available for continuation.

No main/dev-f1 write, force push, newCI, provider call, Win11/F1/P-A/P-B/F3/R0
acceptance, permission expansion or security/proxy/credential configuration change.
The remaining gates are candidate full actual PG validation, source-specific
runtime attribution and a complete qualified native cost envelope before any
Windows900 decision. Evidence and candidate are saved on the independent branch;
this is a diagnostic candidate with open gates, not a qualified release.

## Independent review on frozen source f904423

All four reviewers used `f9044237805e91438807d5acbf9b963ac8af83e4`.
The exact283-file candidate preparation snapshot, frozen Git bytes and current
bytes match. This follow-up changes only review evidence/documentation; no new
PG container, full collection, CI or real provider run was started.

- Cold schema review found no blocker: all four Stores retain a new engine and
  independent pool. Existing schema translation routes those connections to
  their already-owned dataset; there is no initialize, retry, error suppression
  or grant change. All103 assertions in the two affected files are preserved.
  Server connection closure would still fail. These are same-process cold-engine
  checks, not process-restart or every production-role path qualification.
- Preflight review found no blocker: production script bytes and all34 original
  assertions are unchanged; the real copied script executes in a subprocess
  using its own synthetic repository ROOT. Independent preflight13PASS/0.19s,
  exit0. Existing105 SQLite cases/JUnit/node multiset and61 evidence hashes plus
  six focused export hashes were verified;105 was not independently repeated.
  Original no-write/redaction coverage limits remain.
- Lease review found no blocker:0 is the established numeric no-lease sentinel.
  Claim eligibility, fencing, locks, versions and authority are unchanged.
  Two independent deterministic SQLite paths PASS/1.39s, exit0: confirmation
  then stale/fresh cancellation, and confirmation then claim/cancel/fenced finish.
  No real model request or new operation occurred. These sequential checks do
  not validate the original distinct-transaction PostgreSQL cancellation race.

Independent startup review found no retained server boot log in the exported
or exact owned raw log directory. Docker events for the exact deleted owned
container show socket pg_isready2,2,2,0 followed by cleanup kill(signal9),
die(exit137), destroy. There is no recorded preceding OOM/die;137 cannot be
reported as OOM. The socket readiness weakness is established, but bootstrap
transition, host forwarding/transport and resource causes remain unresolved.
Failure occurred before product/test execution. Current evidence does not meet
the user's explicit clear safe recoverable cause condition, so PG remains
blocked and no restart or affected/full PG run was attempted. The updated TCP
controller still has no runtime validation.

For the baseline Linux failed run, pytest process wall1024.981s splits into
reported setup211.989s(20.682%), call792.304s(77.299%), teardown16.032s(1.564%),
and remaining process wall4.656s(0.454%). Ruff0.060s, mypy7.365s and
pytest1024.981s total1032.407s excluding diagnostic collection3.467s; their
shares are0.0058%,0.7134%,99.2808%. Initialize7.117% and non-initialization PG
SELECT cursor26.365% are overlapping descriptive ratios, not exclusive phase
shares or potential savings. Instrumentation overhead is unknown, seven failures
truncate paths, and the candidate has no complete PG timing. Test counts and
the15 independent cases cannot be added to claim a larger/faster full suite.
Windows900/Edge240/Node150 evidence is still missing; **NO_GO** remains.

Exact review JSON, commands, targeted JUnit/logs, deterministic check source,
Docker events, timing denominators and SHA256 manifest are retained in
`docs/evidence/engineering-pg-phase-20261008/independent-review/`.
