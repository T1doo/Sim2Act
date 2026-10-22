# Ordinary Source known-response completion — 2026-10-22

Implemented V5 §8.2–8.3 / F2-T09's missing known-completion path in the existing
offline protocol boundary. `complete-source` accepts only original key and
expected current version/fence. It has no sender/response/path argument. The
normal producer issues per-Attempt V2 wire/reservation origins; after the final
known response, READY mirrors bind every ordered Attempt, pool slot, verified
Operation/read receipt and the provider ledger. Recovery revalidates the full
set, current authorization and original clocks, fences the expired owner, then
uses the original atomic completion body. Source remains WAITING_APPROVAL with
semantic UNKNOWN. Registered review/experiment advance remain separate actions.

Legacy V1, missing usage/READY, STARTED/UNKNOWN, Cold, bounded-check, wrong wire,
extra rows and unresolved operations still cannot use this path. This does not
enable a real provider, production account, new credentials or a general resume.
Eligibility retains the existing test_only + mock + MockTransport boundary.

The existing state-only `/recover` is unchanged. READY also anchors v/f so a
single genuine CONTINUATION_NOT_IMPLEMENTED metadata transition can be proven,
using its original event; only that exact old error is cleared. Unknown ownership
changes are rejected. Cached commands check the complete nine-field response,
original completion time, original request and evidence. They also accept a later
legitimate review C+1 and exact experiment advance proof without granting more
execution time. No budget refunds or halt clearing.

The existing explicit-confirmation panel now routes Source to this endpoint and
matches its result fingerprint/WAITING_APPROVAL receipt. It preserves the same
in-memory command, duplicate-click lock, UNKNOWN key, and selection/late-response
isolation. Refresh/closing the page still loses the in-memory key; no durable
browser-key recovery is claimed.

## Actual validation

Frozen nine-file hashes: `frozen-sha256.txt`; all verified after the run.

`timeout 120s .venv/bin/pytest -q tests/test_protocol_source_completion.py tests/test_protocol_completion_ui.py --basetemp=/tmp/sim-source-completion-final-20261022`

- **39 PASS, 4.66s**, one existing Starlette/httpx deprecation warning. 36 new
  Source tests and three existing UI/extract compatibility tests. Ruff and both
  Node syntax checks passed. No SDK/dependency installation or new CI window.
- Final shared prefix: **7 Mock exchanges** (normal Source 2, interrupted
  experiment Source 2, three-response Source 3). Hard assertion stops at seven;
  all counterexamples use isolated committed SQLite copies and zero sends.
- Same pytest process, new Store/connection recovery. The original production
  reserve/record/dispatch/verified-read paths create the facts; interruption is
  after real READY and before the original completion transaction. No supplied
  response/imported receipt is used. Explicit synthetic business time preserves
  original 6-second spacing, lease30 and Run300 settings; not a G0 timing test.
- Exact fingerprints compare normal/captured/recovered protocol results. Actual
  experiment SEND/SETTLED are exercised, followed by original review PASS,
  original advance, next-stage binding with zero sends, then historical same-key
  replay. Explicit and automatic old recovery → completion → review are tested.
- Negative coverage includes wire/Run/index/origin/V1/usage/status/extra Attempt,
  slot, extra/misbound Operation, receipt, READY/mirror, reordered provider slots,
  provider usage/raw/total, live lease, cancellation, revocation, expiry, owner,
  expected version, closed HTTP schema, unproved ownership transition, damaged
  cached response/time and absent review. A fault on the actual result UPDATE
  rolls back the fence and completion; this is **not W5's five-write group**.
- `source-http-accounting.json` compares actual sealed before/after SQLite files:
  only runs/events/protocol_jobs differ; slots/Attempt/operations/quota tables
  remain byte-value identical. Provider sidecar remains byte-identical. Source
  TestClient commands: missing identity403, extra response field422, completion
  200. Recovery sends/reservations/candidate accepts all zero (test traps).
- Existing extract compatibility reuses sealed accepted facts: zero new Mock or
  Worker claims, one real loopback completion POST + controller result GET,
  plus the test's initial GET. No browser. Source's controller positive case and
  cross-namespace refusal are minimal-element VM assertions, **not DOM**.
- Owned prefix thread liveness assertion and fixture Store disposal passed;
  existing loopback test also joined its owned API thread. No unfinished test
  command/session remains. Fixture original/archives are intentionally retained
  as evidence; this is not a claim to have deleted them.

`before.sqlite.gz`, `after-http.sqlite.gz`, `original-received-sidecar.json`,
`original.json` and test/driver/accounting files are actual synthetic originals.
They contain only registered fixture materials and synthetic identity. Artifact
hashes are in `artifact-sha256.json`.

Two development runs each used seven Mock exchanges and reached 27 PASS before
a test-only HTTP assertion failed: first create_app argument order (2.58s), then
expected unauthenticated status401 rather than existing403 (2.71s). No production
fix was made for those assertions. Their original request budgets are preserved
under `failures/`. This turn's aggregate is **21 Mock exchanges across three
bounded test invocations**, all synthetic, no automatic model retry. The final
39-PASS version alone has seven, not21.

## Review and remaining gates

Independent reviewer statically ACKed the exact final nine hashes, after finding
and closing metadata-recovery and complete cached-receipt P2 issues. It did not
run tests or change files; do not treat its static ACK as extra runtime evidence.

No Source OS/API-process restart proof, PostgreSQL concurrency, new Windows Edge
DOM, real model, G0, Cold2, W5, formal semantic owner acceptance or publication is
claimed. The earlier integrated Edge window39750948446 remains a PASS for its
own frozen 8a310311 tree, with parent-provided source recorded in the sibling
`protocol-extract-ui-launch-contract-20261022/integrated-native-one-shot/`.
Its screenshots remain unavailable for pixel review; its successful cleanup and
29/27/2/0/3 browser counters are preserved. This Source change does not inherit a
new browser or G0 acceptance from that historical run.
