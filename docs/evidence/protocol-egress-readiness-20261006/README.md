# Offline protocol execution preparation

Baseline: `3cbd112be29549009f330b0235f3a9288b26e398`, branch `dev/f1-foundation`.
Local engineering only. No push, CI, LIVE request, model discovery, retry or new
approval request in this slice. Historical Windows success remains on `b6c8acd`;
it does not verify this new UI or handoff implementation.

## Deliverables

- `protocol_readiness.py`: a controller-only, immutable event-backed offline
  handoff. It binds accepted Run/scope/contract fingerprints, current resource
  hashes, fixed family/phase, public data projection and shared pool policy.
  Source dependencies are checked before taking the pool lock. Cold egress
  contains only fresh material; old source resources remain authorization
  dependencies. The complete cold candidate must equal a fixed public template,
  including schema, argument names and instruction. This closes a finite offline
  oracle; it is not a validator for arbitrary generated instructions or actual
  outbound message bodies.
- Provider stage must match the frozen server contract and phase. Extraction
  receives at most one request; source history is separately bounded by the
  authenticated original source allowance.
- `/api/projects/{pid}/protocol/contracts` exposes an owned, closed public
  catalog for the existing project canvas. Gold, expected output and evaluation
  metadata are excluded. Owner semantic acceptance stays `PENDING` even when a
  registered synthetic checker approves its finite fixture.
- `scripts/protocol-store-dryrun.py` demonstrates both shapes with authenticated
  HTTP, actual Worker/Attempt/Operation persistence, independent registered
  review, extraction and fresh cold inputs. Handoff is rechecked before every
  request reservation. Mock responses are constructed from independent fixture
  answers; those assets are never supplied as model inputs. Recursive wire
  auditing also rejects old source answers/material in cold requests.

Run locally from the repository with its installed dependencies:

```sh
PYTHONPATH=src python scripts/protocol-store-dryrun.py --output /tmp/protocol-demo
PYTHONPATH=src python scripts/protocol-store-dryrun.py --output /tmp/protocol-failure --fail-source b
```

Normal output is in [normal/protocol-store-dryrun.json](normal/protocol-store-dryrun.json):
8 MockTransport calls, 8 actual Attempts and DB slots, 6 VERIFIED Operations,
6 immutable handoffs and 8 pre-reservation rechecks. Both forms use the same
14-slot DB pool, with 160 known synthetic tokens. Maximum complete body is
5954 characters/UTF-8 bytes, `max_tokens=1024`, `stream=false`. This observed
geometry is not a guarantee for future model output.

The [failure demonstration](failure/protocol-store-dryrun.json) stops on the B
source's independent FAIL after 6 mock calls. No B extraction/cold request is
made, consumed slots remain, and usage is not refunded. A known semantic FAIL
does not masquerade as unknown cost or a global pool halt; this demonstration
controller stops the experiment, while existing unrelated protocol jobs retain
their original policy. Missing handoff fails before any reservation/send.

## Budget and outbound data: still blocked for LIVE

The proposal remains **unapproved**: 14 requests total, source/extract/cold
3/1/3 per form, output at most 1024 tokens per request, complete wire at most
8000 characters and 10000 UTF-8 bytes, and both known and conservatively reserved
totals at most 64000. The first reached cap stops execution; 14 successful calls
are not promised. There is no reliable currency estimate without account prices.
Prior exhausted requests and earlier pending proposals do not add allowances.

The final implementation enforces 14/64000 globally in DB for offline protocol
jobs. Six-stage quotas, six-second spacing and stage wall-time checks are still
per-sidecar; they are **not** a single cross-Run experiment policy. Production
pools default to zero; LIVE pool remains zero, HTTP/worker refuse LIVE protocol
execution, and production runner injection is forbidden.

The four approved-data **proposal** packages are developer-authored synthetic
policy/case texts, public goals/inputs/schemas, hashes and logical refs. Extract
also needs selected verified source output, tool feedback and safe model receipt
metadata; these must be separately frozen in the eventual outbound projection.
Cold uses new texts and a reviewed candidate's public instruction/schema, not
source answers. Gold/rubric, private reasoning, credentials, actual V5 content and
other project/repository data are excluded. The new handoff does not authorize
any of this to leave the machine.

Before real execution, engineering still needs a sealed experiment identity and
DB-wide six-stage/time policy, exact outgoing-envelope validation wired to the
actual sender, and an independently accepted cold instruction/source-evidence
projection. Owner approval must bind the budget, exact data, provider and private
durable ledger path. No generic continuation/resend is provided. Real model
semantics, owner acceptance, Windows/Win11 coverage for the new UI, formal
AppManifest/Release, complete P-B/F1/AT02 remain unaccepted.

Independent findings and earlier failures remain in the adjacent review JSONs,
Node race probe and [failure history](failure-history.md). Final checks and UI
coverage are appended by the local delivery log; no unmeasured native or LIVE
result is inferred from the mock demonstration.

## Final local validation

[Exact results](final-validation.json): **799 passed, 35 skipped, 0 failed** in365.72 seconds (834 collected, one existing warning); [full log](final-frozen-full.log). All157 source/test/script SHA256 values match [before](final-source-before.json) and [after](final-source-after.json). Role closure152 PASS; Ruff PASS, mypy32 PASS, Node syntax and diff checks PASS. Genuine registered cold material cannot be submitted as source; gold/PINS were unchanged.

The final real local HTTP/jsdom run verifies21 UI checks with a valid owned-other-project Run and strict fixture-ID oracle, actual served product hashes, and zero outside-origin fetch attempts. See [final DOM report](../protocol-ui-entry-20261006/final-frozen-http-dom.json). Native Chromium remains BLOCKED_SANDBOX;35 skips include unavailable isolated PostgreSQL checks. No new native visual, Windows or LIVE result is claimed. This delivery is a local commit only, with no push or new CI.

Raw pytest failure logs retain their original trailing whitespace (10 staged diff-check diagnostics). Implementation, tests and authored documentation pass whitespace checks; the original failure bytes were not edited to suppress those diagnostics.
