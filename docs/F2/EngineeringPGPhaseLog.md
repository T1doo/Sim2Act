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
