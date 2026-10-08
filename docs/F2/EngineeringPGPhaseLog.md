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

## One explicitly authorized captured startup and focused PG validation

After the independent review, the user authorized exactly one new diagnostic
startup to fill the missing boot evidence. Source freeze:
`f70115955a90d7b45a59569534796b09493127c9`; its283 runtime/source bytes remain
identical to reviewed f904. No product/test/workflow change was made.

Actual command (exit0):

```bash
.venv/bin/python docs/evidence/engineering-pg-phase-20261008/single-start-diagnostic.py /tmp/sim2act-single-start-20261008
```

The helper opens separate server stdout/stderr files before the only attached
`docker start -a`. It preserves pre-start, ready and pre-cleanup container State
(including OOMKilled), exact labelled ownership/mounts, timestamped full server
streams, every readiness result and the first authenticated host-connect timeline.
The existing pinned image ID327daa8f/RepoDigest2d2b8998 is used with pull=never;
no network/security/credential settings, permissions or unknown resources change.
The exact image entrypoint was also read from this owned running container and
retained with its SHA256. No restart occurred.

TCP readiness returned2,2,2,2,0. One authenticated localhost connection and
`SELECT 1, pg_backend_pid(), pg_postmaster_start_time(), version()` succeeded;
start-issued to successful SELECT1.671s, connect+SELECT0.014777s. No business
table/data was used for that probe. Logs show the socket-only bootstrap server
ready at04:10:19.019UTC, its fast shutdown at04:10:19.121, and the permanent TCP
server ready at04:10:19.262. This proves the current captured transition and
healthy TCP startup, not the old uncaptured failure's cause. Historical resource,
transport or transition attribution remains unresolved.

Only the explicit four-module affected/related collection then ran once, with
MOCK/LIVE0 and `--durations=30` retained:

|Module|Cases|Outcome|
|---|---:|---|
|test_fixed_goal_acceptance|16|PASS|
|test_natural_receipt_candidate|22|PASS|
|test_natural_activation_pg|7|PASS|
|test_install_preflight|13|PASS; no database dependency|

58PASS/0FAIL/0SKIP,1 warning, pytest116.17s; process wall117.383s, exit0.
The58-node multiset exactly matches those modules in the complete baseline;
all seven original failure cases are included. The45 DB-related cases use the
explicit owned PG fixture; preflight13 is backend-independent. Setup7.421s
(6.322%), call108.016s(92.020%), teardown0.604s(0.515%), remaining1.341s(1.143%).
Existing metric scope COMPLETE/pendingSQL0 is pytest-process-only; this selected
run is not a full cost envelope, a before/after speedup or Windows qualification.

The unchanged actual-PG cancel test used distinct backends157/158; confirmation
won(200), stale cancellation failed(409), then fresh cancellation reached the
original CANCELLED/lease0 assertion. No operations, unchanged authority, and one
mock wire were recorded. Revoke, expire and confirm-again also used distinct
backends and passed; their fixture JSON, two-worker/rollback/CRUD-role evidence
are exported. The expected CRUD-role CREATE TABLE permission denial is an asserted
negative test, not a startup error. No real provider request occurred.

Before/after census each: test schemas0, test roles0, public tables0. Source
before/after/current283-file hashes match. Before cleanup the container was
Running with OOMKilled=false and Error empty. Exact owner label verified;
`docker rm -f -v` removed only this container and its anonymous volume, both
absence checks pass. Attached exit137 follows this deliberate cleanup; it is not
an OOM/startup-failure result. Seven fixture PG receipts were verified/exported
before deleting only this run's fixture directory. Raw logs remain in owned /tmp;
31 exported artifacts have matching hashes and0 URL-credential redactions.

Recommendation: one complete actual-PG Engineering verification of the same
runtime source is now worthwhile, using capture from before startup and retaining
all original collection/stages. **It was not run in this round.** Current native
PG attribution, complete Edge tail and Windows900/240/150 still lack evidence;
NO_GO remains. All original failed-attempt evidence is preserved. Full records:
`docs/evidence/engineering-pg-phase-20261008/single-start/`.

## Complete frozen-source PG Engineering verification

Explicitly authorized once after the successful targeted run. Frozen source:
`193220054cd3268e6332875c7a7daa5937d65f15` (same283 runtime bytes as f904).
Actual command, shell/controller exit0:

```bash
.venv/bin/python docs/evidence/engineering-pg-phase-20261008/full-verification/controller.py /tmp/sim2act-full-verification-20261008
```

Only one new labelled localhost container started, using the same pinned image.
Separate server stdout/stderr files were open before attached start. Full streams,
timestamped streams, pre-start/ready/pre-cleanup State and20-second stage State
samples, readiness/first-connect timeline and stage PIDs/commands are retained.
First authenticated host SELECT succeeded; start-to-SELECT1.304506s and
connect+SELECT0.012804s. No startup retry/restart or second full process occurred.
Diagnostic fixture hooks record setup time/definition only; no assertions,
selectors, production code or SQL/parameter values were changed/exported by hooks.

|Stage|Exit|Actual process wall seconds|
|---|---:|---:|
|Original default collection|0|1.521|
|ruff check src scripts tests|0|0.064|
|mypy src (47 source files)|0|0.265|
|pytest -q --durations=30 -ra|0|1067.583|

Pytest summary: **1559PASS/0FAIL/0ERROR/27SKIP**,3 warnings,1065.03s.
Collection/execution/JUnit each contain1586, with exactly equal node multisets.
All original seven failed nodes now PASS. The27 skip nodes/reasons exactly match
the baseline:23 explicit R0 private-GO oracles,1 actual Windows PowerShell test,
2 SQLite-only protocol-UI subprocess variants,1 protected Chromium sandbox start.
The actual Chromium stderr is retained; no sandbox bypass. Three warnings are
one existing Starlette/httpx deprecation and two existing Pydantic authorization
alias warnings. No dependency or test was edited in response.

|Pytest reported component|Seconds|Fraction of pytest process wall|
|---|---:|---:|
|setup|217.710|20.393%|
|call|829.353|77.685%|
|teardown|16.696|1.564%|
|remaining process wall|3.823|0.358%|

Ruff+mypy+pytest total1067.911s excludes diagnostic collection, dependency
preparation, PG startup, source checks and cleanup. Mypy and dependencies are
warm in this instance. This is a complete **Linux** default Engineering result,
not a clean native setup/Edge cost envelope or Windows900 capacity acceptance.

### Actual call and fixture rankings

|Slowest individual call|Seconds|
|---|---:|
|report_manifest_apps_ui::test_report_manifest_real_http_dom|34.903|
|delivery_graph_apps_ui::test_delivery_graph_actual_http_dom[REPORT]|27.150|
|protocol_gated_execution::test_whole_package_actual_postgresql_two_forms|16.131|
|conditional_apps_ui::test_named_report_draft_real_http_dom|15.310|
|conditional_runs_native::test_conditional_bound_native_shared_actual_http[True]|13.793|

Call module totals: natural_receipt_candidate63.750s, fixed_goal_acceptance42.706s,
delivery_graph_apps41.819s, report_manifest_apps_ui34.903s,
delivery_graph_apps_ui32.142s. These module aggregates identify workload scale;
the individual-call table identifies the longest single cases.

|Fixture definition setup aggregate|Calls|Seconds|
|---|---:|---:|
|conftest.env, baseid tests|1053|195.990|
|test_protocol_jobs.env, baseid test_protocol_jobs.py|40|5.038|
|test_global_experiment_gate.sealed_protocol_fixture, module scope|1|2.639|
|test_protocol_jobs.env, baseid test_protocol_experiment.py|16|2.330|
|test_protocol_jobs.env, baseid test_protocol_pool.py|19|2.161|

Slowest individual fixture setup is sealed_protocol_fixture2.639s; slowest root
env is0.521s. The1053 root env hook outcomes all record PostgreSQL. Other env
definitions are reported separately, avoiding a false unique-schema count from
same-name nested wrappers. Fixture spans may nest; these totals are not added to
phase/initialize/SQL totals and do not attribute teardown/subprocess internals.

Initialize1195 calls/77.575s is7.266% of pytest wall as an overlapping descriptive
ratio. PG initialization DDL46824/53.314s, existence3649/0.751s; PG non-initialization
SELECT1138811/293.271s. Existing metrics COMPLETE/pendingSQL0 means only the
defined pytest-process scope. Cursor spans exclude fetch/commit/pool acquisition
and combine setup/call work; they do not establish source-level duplicate work.

**No causal optimization saving is proven or implemented in this round.**
The measured next targets are the longest actual HTTP/DOM/protocol calls, natural
receipt/fixed-goal call modules, and root env setup. Profile their subprocess,
Python, DB/round-trip and synthetic seed components before any minimal change.
The remaining initialization existence cursor slice is only0.751s here; it cannot
justify a Windows900 recovery claim. Keep independent schemas/roles, all negative
assertions, current-head revalidation, authorization and fencing. Frozen origin
tests explicitly reject same-transaction mutations and later-request revocation;
aggregate SELECT counts are not permission to cache or omit those checks.
The failed baseline has different source/outcomes and truncated business paths;
there is no controlled/uninstrumented before-after pair or Windows saving estimate.

Retained server stderr also records three grant-row `FOR UPDATE` deadlock events
between backends345/346 at04:24:26.134,04:24:31.138 and04:24:33.640UTC. All executed
cases still PASS; the observer did not map backend IDs/lock waits to individual node
timestamps, so the exact case, recovery path and saving potential are not claimed.
This is a concrete next diagnostic target for lock-order/wait attribution, not a
reason to change locks during the frozen run. Background checkpoints also logged
278.570s/274.874s totals with paced writes and8.728s/4.451s sync aggregates. These
background elapsed spans overlap test execution; they are not measured pytest
stalls, additive product costs or evidence of an environment I/O hang. A scoped
resource point sample and periodic State are retained without causal attribution.

### Privileges, integrity and cleanup

Eleven application/runtime-role JUnit cases PASS, including the actual child
process role, CRUD-only conditional chain/checker, cold registered-run result and
history/lifecycle paths. The PG-role receipt confirms superuser=false,
createdb=false, createrole=false, DDL denied, business CRUD successful and no CRUD
DDL statement. Final schema/role/public-table census is0/0/0, matching before.

The original cancellation race uses actual distinct backends704/705; cancellation
wins200 and confirmation rejects409, with no operation, lease released and
authority unchanged. The preceding targeted run on identical runtime bytes
observed confirmation winning followed by fresh cancellation. Both actual-PG
orderings have now been observed, without forcing or weakening assertions.
Revoke/expire/confirm-again and two-worker/rollback receipts also PASS. Their wires
are original mock transports; real provider calls0, LIVE0, no CI.

All283 source hashes match before/after/current frozen bytes. Before removal PG
was Running, OOMKilled=false, Error empty. Label-checked rm -f -v removed only
this run's container/anonymous volume; both absence checks pass. Attached exit137
is the deliberate cleanup result. Seven PG receipts and36 driver logs were
verified/exported before removing only this run's fixture directory.76 exported
artifacts have matching hashes and0 temporary-URL redactions; raw logs remain
under the owned /tmp root. Original failed-attempt evidence remains untouched.

Candidate full Linux PG Engineering correctness gate is now closed within the
original27 skips. Native Windows/Win11/Edge/real-provider/owner/F1/F3/R0 acceptance
is not claimed. **Windows900/Edge240/Node150 remain unchanged and NO_GO.**
Full artifacts, commands, JUnit, measured rankings, optimization limits and
ownership receipts are under `docs/evidence/engineering-pg-phase-20261008/full-verification/`.

## Grant deadlock and two DOM hotspot follow-up

Frozen old source0f11dcd; [complete hotspot evidence](../evidence/engineering-pg-hotspots-20261008/README.md).
The original three server deadlocks align with the REPORT DOM call by retained
phase timing, but old logs lack exact HTTP/bind-parameter linkage. New original
REPORT DOM reproduction records five resource-list40P01/HTTP500 and their
competing graph plan/history requests. These are real multi-resource lock races,
not expected test refusals; background error handling can allow final DOM PASS.

Resource listing now takes the existing project lock before authorization,
matching REPORT's project-before-grants order. Owner/runtime checks, expiry,
revocation, return shape and fresh-source validation remain. Four bounded real
PG request schedules fail on old code with40P01/500 and pass on fixed code with
different backends, project-first waiting and200/201. One added actual CRUD-role
test confirms nonprivileged SELECT-only listing, foreign-owner403 and both
identities' revoke/expiry omission without authority/schema mutation.

Identically observed two original DOM nodes pass old/new. REPORT call32.686→29.401s;
report-manifest36.595→37.427s. The latter's27 history reads total12.058s, while
REPORT's8 graph-history reads total9.805s, with overlapping requests/functions.
Each node initializes only once (~.06–.07s). Repeated load_family/source checks
and2.5s background polling are measured, but no safe cache or polling reduction
is established. Single paired samples do not prove general or stable speedup.

Fixed related selection91PASS/0FAIL/0SKIP, pytest150.13s/wall151.312s; Ruff/mypy47
PASS. Original1586 nodes and all original test/web/script/workflow bytes retained;
default collection now1591 solely through five added regressions. No new full
run; the previous1559PASS/27SKIP remains evidence for its earlier frozen source.
Independent read-only review passes and validates the five new receipts. All
four owned runs have census0/0/0 and removed containers/volumes; compressed raw
timelines, JUnit and artifacts are byte/hash verified. Original instance remains
untouched, LIVE0/MOCK, no new CI/native/provider run. Windows900/Edge240/Node150
and NO_GO remain.
