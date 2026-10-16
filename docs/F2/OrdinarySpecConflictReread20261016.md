# Conflict recovery: explicitly reread the original task

Baseline: `84039cf36461c9d9725ec8fb4d880d89d3e9992a`.
Branch: `dev/ordinary-spec-conflict-reread-20261016`.
Product changes are limited to `web/internal.js` and one workspace cleanup call
in `web/app.js`. No API, executor, database schema, dependency, qualification,
credential, model permission or budget changes are involved.

## Delivered behavior

A current task command receiving VERSION_CONFLICT still invalidates protected
content, then offers the explicit button **重新读取这个原任务**. Its in-memory
target contains only original principal/project/app/instance/Run/AppRun IDs and
selection/connection/workspace generations. It retains no old result body or
command payload and writes no new persistent recovery record.

Clicking it sends exactly two authenticated, no-store GETs: first the original
instance, then its exact original Run. The existing server routes authenticate
and authorize again. The client checks instance owner/project/app/ID and
Run/instance/AppRun IDs, and checks the captured context after each await.
Only then does it display the latest task detail and status. It offers only
another explicit reread; it does not issue resume, enqueue a Run, restore old
command controls or infer success from cached content. Double clicks do not queue
another read. A new read clears both old detail and status before authorization;
denial or mismatched binding leaves no old terminal displayed as current.

Identity change, same-token connection-generation change, workspace leave/return,
instance or Run selection change and app replacement invalidate old callbacks.
Workspace cleanup also clears an abandoned reread/loading state. Task reads use
the workspace generation at GET start. An explicit task command instead captures
the workspace at that new click: leaving and returning does not leave an enabled
command button silently inert, while a command response arriving after navigation
cannot offer an old recovery entry. Identity and instance selection remain frozen
for both paths.

## Final actual execution

Final suite: **11 PASS, 0 FAIL, 0 SKIP, 0 ERROR**, XML **268.575 seconds**, with
one existing Starlette/TestClient dependency warning.

```
env -u SIM2ACT_TEST_DATABASE_URL PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
 /workspace/Sim2Act/.venv/bin/python -m pytest -p no:cacheprovider \
 tests/test_conflict_reread_protocol.py tests/test_safe_step_process_recovery.py \
 tests/test_spec_run_terminals.py tests/test_durable_recovery_protocol.py \
 tests/test_internal_submission_rejection.py \
 --basetemp=/tmp/ordinary-conflict-verified-20261016 \
 --junitxml=/tmp/ordinary-conflict-reread-20261016/verified.xml -q
```

The real loopback HTTP/JSDOM cancellation case has **30 checks**, **136 HTTP
responses**, **3 documents** and the exact **63 source-matching page assets**.
Actual old Worker **1220847/start44817397** exits after a safe pause; new Worker
**1220879/start44819346** reopens the same SQLite without initialize. Every child
reports initialize_calls=0. The new document recovers the original key and same
Run/AppRun; another page explicitly cancels it. The retained old page's actual
resume click receives HTTP409 and visibly offers the new reread button.

Its first reread performs only the two authenticated GETs and displays the same
CANCELLED Run. A second explicit reread receives the actual HTTP response, then
a test delivery adapter withholds its Run body. Actual visible workspace
navigation leaves and returns before delivery is released. The old result does
not restore task detail, the reread entry or loading text. No second execution
POST occurs. The complete selected execution snapshot/project Run-ID set and
verified prefix remain unchanged by readback: one AppRun, zero result versions,
zero artifact effects. The new Worker has two pre-cancel and two post-cancel idle
probes and zero model calls. Primary mock counts are fixture3/oldWorker1/newWorker0,
not totals across the whole suite. The existing resume case still saves one
result version/effect. Four exact owned children exit and cleanup passes; unknown
processes are never signalled.

Cancellation-case identity:

- key `62c5c5c0-2bbd-45a8-be28-54b4b2778fe0`
- Run `run_c70f9c7d620848148661f5c76e75a6b6`
- AppRun `iapprun_8a5e7d8d643245f5ad9d14800c6f8c7b`

The separate **synthetic HTTP/JSDOM protocol** has **27 checks**: 25 GET-only
recovery fault checks and 2 explicit-command workspace checks. It covers both
authorization-denial stages, owner/project/app/instance/Run/AppRun mismatches,
double click, both await boundaries across identity switch, a controlled
same-token connection-generation ABA, actual workspace navigation and the actual
instance-selection function with synthetic GET403. The two command checks
explicitly send rejected commands; they are not evidence that the reread button
mutates. These fault injections are not real-server revocation, native browser
or a full race matrix.

All **528 src/tests + pyproject.toml files** match before/after both final process
cases, after the complete suite, and the final full source archive. Manifest SHA256:
`af4212eab65643828b9ebe88e3e9d01668d3230896b16b7bcad98d3d29fd5384`.
Ruff passes for the three checked Python drivers; four changed/new JavaScript
files pass Node syntax checks. Whole-repository lint/type-check success is not claimed.

## Preserved development and failure evidence

Initial protocol: 1PASS/3.53s. A new success-then-403 regression then produced
1FAIL/0.85s: the candidate left an old terminal status after clearing detail.
Clearing status at read start fixed it. Candidate1 subsequently passed 11 tests
in 230.44s, but independent review found its workspace-return command was silently
inert. An added regression produced 1FAIL/3.06s after the 25 GET-only checks.
Separating selected context from click-time workspace fixed that regression.
The final 11-case suite above re-executes the strengthened 27-check protocol and
the real Worker/page paths. Both defects arose during this implementation and
were corrected before delivery; the baseline had no reread entry.

All earlier changed-source variants, manifests, XML/logs and raw outputs remain
under `/tmp/ordinary-conflict-reread-20261016` and the five raw directories listed
in `RAW_MANIFEST.json.gz`. The earlier full-suite directory named
`ordinary-conflict-final-20261016` is Candidate1, not the delivered final source;
the final source/evidence uses **verified** names. No failed history is overwritten.

## Evidence and acceptance limits

Committed evidence is in `docs/evidence/ordinary-spec-conflict-reread-20261016`.
The compact page proof is explicitly **derived**: every HTTP response retains
its body hash/UTF-8 size; keyed-receipt and command bodies retain full text.
Complete original page/HTTP bodies, SQLite, process receipts and snapshots remain
in place. `RAW_MANIFEST.json.gz` hashes **145** current-task raw files, including
both full suites and all protocol attempts. The complete final source, earlier
changed-source variants and all these raw originals are bundled after publication
at `/tmp/ordinary-conflict-complete-20261016.tar.xz`, with an external index.
Full source archives also remain separately in the metadata directory. Independent
review verifies candidate execution and then live publication/archive separately.

JSDOM and Storage/Web Locks adapters are not native-browser acceptance. The old
Worker exits gracefully at a committed safe boundary, not during in-flight effects.
The **128-binding cap** remains unchanged; strict row-lock-wait observation is
NOT RUN. Historical `2b7068d` remains a TestClient/Store process, not a Worker.
PostgreSQL, Windows, native browser, real provider/paid API, arbitrary in-flight
crash/UNKNOWN recovery, API/network restart, old-source upgrade, broad
cancellation/revocation/version-race matrix, full P-A/P-B, semantic/owner
acceptance and remote CI remain **NOT RUN**. No main/core changes, force push,
deployment, new fee/credential/security/model permission or unknown-file cleanup.
