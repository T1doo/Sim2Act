# Complete Engineering PG phase classification — 2026-10-08

New saved-environment instance, based only on pushed source
`5c06520bc31269d11b9bf2786b9e18ed89333a28`. Actual default `git fetch origin
dev/f1-foundation` completed and `git switch -c dev/pg-phase-diagnostics-20261008
5c06520bc31269d11b9bf2786b9e18ed89333a28` completed. The original instance,
uncommitted Engineering plan and blocking logs remain untouched and untransferred.
This is a reconstructed plan, not recovery of that worktree.

Read DeliveryRemainingChecklist, FreshSchemaInitializationLog, WindowsPhaseMetrics,
the original workflow, WindowsCI/Test/WindowsBrowserCI entrypoints and the existing
metrics plugin. No repository AGENTS.md or .agents/skills exists in this checkout.

## Scope and evidence

1. Record actual Linux/Python/Node/dependency availability. Use an isolated venv
   with requirements.lock. Use default package/image connections; stop any denied
   action without changing proxy, credentials, security or permissions. This new
   instance has Docker available but no local images, no native PG binaries,
   pytest/SQLAlchemy/psycopg or jsdom. Existing Python packages are not the lock.
2. Prepare only an owned labelled localhost PostgreSQL 17.11 container with
   synthetic private credentials generated in controller memory, and owned test
   data under a fresh /tmp root. Existing fixtures retain their schema/role
   creation and cleanup. Never use a preexisting database URL or user data.
3. Collect the complete unchanged default pytest selection, saving exact node IDs.
   Execute the original Engineering stages (ruff src/scripts/tests, mypy src,
   pytest -q) sequentially. Retain --durations=30, -ra and JUnit; explicitly load
   the existing phase plugin without changing tests, timeouts or assertions.
4. Save source SHA and byte hashes, dependency provenance, commands/exit status,
   collection, complete JUnit and log, fixture/initialize/table-probe/SQL metrics,
   actual stage wall time, skip/failure reasons and final schema/role/public-table
   census. Compare collected node multiset with JUnit. Nested spans are never
   added as wall time; plugin does not observe subprocesses or fixture teardown.
5. Analyze only observed components. A reproducible defect with established cause
   may receive a minimal fix and appropriate validation. Otherwise leave code
   unchanged and report unmeasured native attribution. Retain first-run failures.
6. Export reviewed safe evidence, remove only this run's resources, commit locally,
   recheck remote dev SHA and ordinary-push the independent diagnostic branch.
   Do not push to main or dev/f1-foundation, trigger CI, force push or call models.

## Qualification boundaries

All tests remain selected, including existing platform/dependency skips. Missing
native prerequisites are blockers, never converted to synthetic PASS. Keep job
900 seconds, protected Edge step 240 seconds and Node driver 150 seconds unchanged.
Linux collection and elapsed times are diagnostic evidence only. Windows900 stays
NO_GO; no native/Win11/real-provider/owner/P-A/P-B/F1/F3/R0 acceptance is claimed.
The historical Windows critical path remains 55 + 741 + at least 110 incomplete
Edge + 6 = 912 seconds, with unfinished Edge cost and current native PG attribution
unknown. No blind CI retry or extra permissions.

## Completed hotspot follow-up and next evidence boundary

The complete original PG gate and then one controlled hotspot follow-up are
recorded in EngineeringPGPhaseLog. [Hotspot results](../evidence/engineering-pg-hotspots-20261008/README.md)
prove the resource-list/REPORT graph grant lock race and validate one minimal
project-first lock fix, original two-DOM old/new measurement, four request
schedules and related91PASS. Original assertions/budgets stay intact; five
new regression nodes add coverage, never evidence of faster original selection.

Next performance candidate is repeated current/load_family/build validation
and current report history rereads. Their calls are measured, but removal must
preserve same-transaction origin/grant changes and later request revalidation.
Do not cache, reduce polling or rerun complete/native stages without concrete
evidence and the applicable task authorization. Current localized sample change
is not a stable speed guarantee; native capacity900 remains NO_GO.
