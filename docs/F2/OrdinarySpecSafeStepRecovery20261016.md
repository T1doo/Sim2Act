# Accepted ordinary-spec Run: safe-step Worker and page recovery

Baseline: `2b7068d59af47e79eeff241aa5bfad023d503f00`.
Branch: `dev/ordinary-spec-safe-step-recovery-20261016`.
The existing control API and executor already support this bounded path. This
change adds three executable process/page test drivers and inspectable evidence;
product source, qualification, anchors and executor guards are unchanged.
It closes this accepted-run safe-step evidence gap, not full F2-T09/R0 acceptance.

## Actual recovery contract

The fixture saves a six-step sequential natural-spec application through the
existing application flow, with three explicit mock generation responses. The
first actual page submits exactly once. After the actual HTTP 202 response is
received, a documented delivery-loss adapter withholds that response from the
page, preserving its real durable original-key record. No product Map or Run
state is injected. This makes the new-document recovery entry reproducible.

The old OS Worker runs the original Worker.once and actual spec executor. A test
observer waits only after the original advance returns True and its transaction
has committed the first model step. At that boundary the actual sender counter
is zero, one Attempt and two operations are VERIFIED, no unknown operation,
result row or artifact effect exists. The observer changes no product state and
leaves the original heartbeat active. Parent-authenticated HTTP pause, with the
actual Run version, returns PAUSE_REQUESTED; the observer is immediately released.
The actual next advance settles Run/AppRun PAUSED and lease_until=0. The old Worker
then returns and exits normally with code 0. This is graceful safe-step recovery,
not a crash or an interrupted in-flight response test.

A different OS Worker PID and worker_id reopen the same SQLite URL. Every child
forbids Store.initialize and records zero calls. The new Worker performs two
actual, unmodified Worker.once probes, before and after new-DOM recovery: both
return False with zero model calls. The entire selected paused Run snapshot,
verified prefix and effects remain unchanged. Heartbeat registration metadata is
outside that execution snapshot. This is a bounded pair of idle probes, not a
claim about an indefinitely running scheduler under every possible fault.

The first DOM is closed. A fresh JSDOM loads every actual HTTP page asset,
authenticates normally, opens the saved instance and restores its minimal durable
record. Its explicit original-key GET returns the same request_key, run_id and
app_run_id at PAUSED, without another execution POST. The visible enabled resume
button sends one versioned command for that same Run. Only then does the new
Worker execute the remaining steps. No Run is re-enqueued under a new key.

Original binding, operations, Attempt and reservation prefix rows remain byte
identical. Run fence/version/worker_id legitimately change. The original Run
created_at, frozen clock and accepted deadline do not reset: configured lease is
30 seconds, run limit 300 seconds, and the frozen deadline is created_at+300.
Final state contains six VERIFIED operations, two VERIFIED Attempts, one AppRun,
one typed result at version 1 and one artifact effect. A further actual Worker.once
returns False. Repeated authenticated readback leaves the final snapshot unchanged.

## Final executed evidence

Final suite: **9 PASS, 0 FAIL, 0 SKIP, 0 ERROR**, XML duration **165.424 seconds**;
one existing TestClient dependency deprecation warning. The suite consists of the
new process recovery case and the prior eight ordinary/rejection recovery cases.

The primary case records:

- Old Worker **1214978 / starttime 44357999**, new Worker **1215037 / starttime
  44359103**. Both runtime Workers exit 0. Page exits 0; the owned API is terminated
  during final cleanup (exit -15). Four owned children are registered by exact
  PID/starttime/argv/token; all are absent afterward. Unknown processes are never
  signalled. No cache, unknown file, lock or process is deleted by this slice.
- Request key `bb101873-8290-4c85-9c62-48889ab0b87a`, Run
  `run_22d49e3054ce45f387934d6c4baded04`, AppRun
  `iapprun_11c878f853584ca5bfc1179b7b12a93d` remain identical across recovery.
- **18 actual-HTTP JSDOM checks**, **100 HTTP responses**, two document objects,
  exact **42 assets** (two complete HTML-declared sets, including CSS), each
  hash-matching the executed files. Actions dispatch ordinary visible/enabled DOM
  events. JSDOM, file-backed Storage/Web Locks and controlled polling are declared
  test-platform boundaries, not a native browser claim.
- Explicit mock model calls: fixture generation **3**, old runtime Worker **1**,
  new runtime Worker **1**. The first verified model step is not resent. These are
  primary-case counts, not an aggregate for all nine regressions. No real provider
  request, credential discovery, LIVE scope or paid API is used.
- All **526 src/tests + pyproject.toml files** match before, after the process
  case, and after the complete nine-case suite. Source/config manifest SHA256:
  `35380f4a780d3cec86c102e837d12ab1dc7fd1fac3dfa16efe5f9f4f33026f45`.
  Both new Python drivers pass Ruff; the Node driver passes syntax checking.

Evidence is in `docs/evidence/ordinary-spec-safe-step-recovery-20261016`.
It includes the complete primary page proof, exact asset/request/action records,
raw snapshots, Worker wire responses, process receipts, source manifests and XML.
Raw SQLite and the additional append-only HTTP trace remain in
`/tmp/ordinary-safe-step-final-20261016/test_safe_step_pause_new_worke0/owned-safe-step`;
all nine raw cases remain under `/tmp/ordinary-safe-step-final-20261016`.
The delivery bundle is `/tmp/ordinary-safe-step-complete-20261016.tar.xz`; its index
and post-push verification are produced separately after commit, without changing
these executed source files or deleting their originals.

The initial source version also passed one actual process case in 77.932 seconds.
Its raw case, XML/log, before/after **525-file src/tests-only** manifests remain at
`/tmp/ordinary-safe-step-first-20261016`; the original three driver source bytes
were not separately archived before the final assertions were strengthened, so
that first run is not advertised as a complete archived source snapshot. The final
source above supersedes it. An initial Ruff E731 finding was recorded and fixed
before execution; no product defect or fabricated RED result is claimed.

## Preserved acceptance boundaries

The prior terminal absence scan cap of **128 bindings** remains unchanged. Neither
this safe-step test nor the earlier forced transaction ordering establishes strict
observation of a database row-lock wait, scan completeness beyond configured caps,
or PostgreSQL behavior. The old 2b7068d child was a new OS-process TestClient/Store,
not a Worker; that historical boundary is unchanged. Only this new, identified
old/new Worker pair proves the bounded safe-step Worker restart path described here.

Native browser, Windows, PostgreSQL, real provider/paid API, arbitrary process
crash with in-flight or unknown effects, network/API restart in this case,
old-source schema upgrade, broad cancellation/revocation/version-race recovery,
full P-A/P-B, semantic/owner acceptance and remote CI: **NOT RUN**.
No deployment, main/core change, force push, budget/credential/security permission
expansion, cache cleanup or removal of old evidence is part of this slice.
