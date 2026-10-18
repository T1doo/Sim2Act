Natural P-B v2 Run navigation and four actual downloads
======================================================

Deliverable: `test_natural_result_navigation_ui.py`, intended beside the UI
author's `natural_result_navigation_ui.cjs` under repository `tests/`. The CJS
contract was read at SHA
`095b6cc06c52df495d82a9e02dae80a632b03216b3aafb7c54820b84c35b5976`.
The actual checkout read was `0a0430223be5bf27d8dc72ee33a4a479bfd92fdc`, branch
`dev/natural-owner-run-navigation-20261018`, approximately 24 GiB free.

Only this new external directory was written. No close fixture, cancelled
installation window, old sealed evidence or old instance is used. No pytest
collection, product HTTP, Worker or model execution was performed while writing
the draft. Static compilation and Ruff are its current qualification.

One case, normal setup and a continuous page flow
------------------------------------------------

The test creates its own Store, mock Settings, synthetic identity and project.
Normal HTTP saves SOURCE and its Goal; unchanged original helpers generate a
single-node natural recipe (3 mock requests), explicitly confirm it and create
its Release and instance. One normal Worker executes that source Run (1 mock).
The existing P-B options/review/extraction APIs bind COLD to a saved P-B app;
normal approval/commit/instance APIs create its Release and instance. One normal
Worker executes P-B v1 (1 mock). The fixture then performs exactly one existing
owner PREPARE request, without DECIDE: this is synthetic pending fixture state,
not a human or semantic signoff. Its original request, contract fingerprint,
record and history are retained. THIRD and its Goal are saved for page selection.

The actual page finds the same P-B instance through the unified directory,
explicitly selects saved THIRD material and Goal, reviews the existing per-use
contract, acknowledges it and submits once despite a double click. The accepted
original-key receipt identifies v2. A single Worker RPC executes that exact Run
through a cold Store (1 mock), after which the user manually refreshes. The
source Run, P-B v1 and P-B v2 each require one actual successful claim, with no
test alteration of clocks, leases, deadlines or success rows.

Actual completion should therefore observe 6 mock requests: generation 3,
source 1, P-B v1 1 and page P-B v2 1. The three business Worker calls are separate
from the one generation Worker call. These counts are asserted from captured
requests/claims; this document does not claim they have already executed.

Only the fixture module's `httpx` reference becomes a `SimpleNamespace` holding
an observer factory and the original Response class. The shared `httpx` module,
real MockTransport class and Worker's `isinstance` guard remain untouched. The
original generation and inference handlers are reused unchanged. Their real
qualified names determine whether payloads enter generation or staged runtime
wire evidence. The THIRD request must contain THIRD and neither earlier source.

The owner dropdown must keep the visible machine detail, selected Run and owner
contract synchronized. After v2, v1 retains its original database payload and
history but presents only STALE metadata; v2 has an independent sequence-zero
PENDING contract. One bounded delivery control holds an actual v1 machine Run
GET 200, lets the user select v2 and fully read it, then releases the old reply.
The stale callback must not repaint detail/owner data or trigger an owner-v1 read.

A second entire JSDOM boot performs only GET requests. It explicitly selects
v1 and v2 and downloads each as JSON and Markdown: four real Blob/FileReader
captures, each preceded by a fresh authorized artifact GET. Each file is saved
as raw bytes and checked against that exact GET's JSON content or Markdown view,
Run, typed version, resource, SHA-256, UTF-8 hex, length, filename and media type.
Every one of the 27 production-served assets is hash-checked on each boot.

Fixed IPC and independent data checks
-------------------------------------

`worker {run_id}` is accepted once, only for the exact page-accepted queued v2.
It returns `{run_id,status:'SUCCEEDED',result_version:2}` after real execution.
`checkpoint {phase}` supports exactly these phases:

- `seed-readonly`
- `v2-queued-before-worker`
- `v2-complete-after-manual-refresh`
- `run-navigation-late-old-get-ignored`
- `cold-four-downloads-and-navigation-readonly`
- `final-readonly`

All ordinary HTTP is forwarded through TestClient with the page's actual
Authorization headers, without an authenticated client default. Every body uses
the original CJS `body_text` UTF-8 bytes as `content=`, checked against the actual
request bytes, rather than being re-serialized as JSON.

Whole-table snapshots are saved before generation, after source success, before
and after v1 execution/owner PREPARE, before page v2, while queued, after v2 and
after cold reads. Enqueue adds only one Run/AppRun/binding/contract, six existing
per-use/Run metadata rows and the one exact runtime READ Grant for THIRD. Worker
completion adds only one v2 typed record, JSON artifact, four verified operations
and intents, one local effect, attempt, reservation and owned Worker heartbeat.
The two normal artifact READ Grants go to owner and existing runtime. Thus the
page adds three READ Grants in total, and no new SAVE Grant, app, runtime,
Release, instance or owner declaration. Old v1 typed/artifact/owner rows stay
unchanged. All unrelated tables and existing rows must remain identical.

Evidence, execution and limits
------------------------------

The existing `_PageObserver` flushes every actual fixture/page HTTP response and
request as raw bytes with hashes, model requests, progress and failures. The
bridge also preserves raw Node stdout/stderr, IPC, original-key review/commit
bodies, worker claims and accepted clocks, all-table snapshots, per-stage model
wire, page checks/actions, served assets, downloads and their exact artifact RPC
mapping, the delayed Run response and hashes of production/test inputs before
and after. `finally` saves partial wires, final rows and source/v1/v2 claims and
closes only owned clients, engines and the owned Node process. Node has the
existing 900-second watchdog; the parent supplies its outer 900-second scope.

No separate weak queued-Run reproduction mode was added: the reported mismatch
requires two successful results for a genuine contract/detail comparison. The
parent may rely on its already established one-line source evidence, or execute
this same continuous case against the chosen pre-fix asset and expect failure at
owner navigation, before running the frozen corrected pair. No extra fixture,
second protocol or unrelated matrix is needed.

Actual execution remains the parent's next step after source and tests freeze.
Native browser, Windows, live models, real human/semantic acceptance, PostgreSQL,
deployment and remote CI are not covered or claimed here.
