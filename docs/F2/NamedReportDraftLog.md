# Isolated named Report draft delivery

The named PREVIEW_ONLY wrapper is persisted in existing app_drafts with independent
bounded-conditional-app.v1 task_extractions provenance. A fresh page lists and reopens it, types a
new Scenario, creates an actual protocol cold Run, and rereads durable history. Source/check/plan
refs and fixed target rules hash remain server-verified. No client Candidate, Report, Replay,
gold, runtime, permissions or verdict is accepted. No automatic check or owner sign-off exists.

Existing project runtime is server-selected and reauthorized for source and target resources;
no Principal/Grant is created. This is a shared engineering authorization domain, not V5's
independent AppPrincipal, and the wrapper is not AppManifest-compatible. Old CSV/agent lists
exclude this family; their loaders continue to reject it. Formal release remains closed.

POST create takes only closed SaveRequest; POST runs takes closed RunRequest (typed Scenario,
expected app fingerprint and request key). Recovery resubmits the exact original body/key.
A server-derived key persists actual Run identity across a lost response or interrupted history
binding insertion. History verifies original row key, exact actual Run key, owner/project/runtime,
sealed payload/plan and current grants; a same-input different Run cannot replace its receipt.
app_previews.status records intake only; displayed status and Report always come from the
verified actual Run, never the cached marker.

## Verification and remaining boundaries

Evidence: docs/evidence/named-report-draft-20261007/summary.json and http-dom-results.json.
Initial dedicated HTTP+DOM: 16 PASS (43.10s). Then exact original row-key and malformed-wrapper
hardening was added; three final targeted HTTP negatives then passed (3.52s): original row-key
misalignment, a missing origin extraction ID, and rehashed boolean version in both wrapper records.
The earlier entire HTTP set was not rerun while parent full verification was active. Final actual-HTTP DOM plus existing bounded-agent and registered CSV
HTTP families: 62 PASS, 1 SKIP (50.31s; PostgreSQL runtime-role test is not available on SQLite). The final DOM records actual HTTP-loaded source hashes.

The DOM proves UI source/check/model extraction/save; accepted save/cold receipt loss and malformed
200 keep exact-key retry locked; two fresh pages reopen durable app/history; typed 500 and
680/no-receipt produce independent actual ALLOW and BLOCK Reports, and unknown approval gets a
new UNKNOWN result. List ABA, late cross-project history and identity-switched accepted submission
cannot restore stale protected state. Actual target revoke fails closed and clears visible evidence.
The negative fixture explicitly revokes one synthetic target runtime read grant; counts and every
other Principal/Grant row are checked unchanged. Six actual Intern MockTransport responses are
accounted; zero LIVE. Initial HTTP also verifies both source/target revocation, extra fields,
wrong hash/project/identity, rehashed draft/plan/history corruption, actual receipt substitution,
unchanged Principal/Grant rows and no-provider WAITING_RESOURCE with zero new requests.

Developer jsdom dependency is explicit: NODE_PATH=/workspace/browser-tools/node_modules;
no product Node dependency was added. All Python uses isolated venv and PYTHONPATH=src;
third-party packages are shared read-only from the existing offline development installation.
Ruff, JavaScript syntax and git diff --check passed. No full suite, PG, native browser, LIVE,
CI, push, deployment or parent merge ran. Native/PG/owner semantic acceptance remain NOT_RUN
or PENDING, and total source acceptance remains NOT_ACCEPTED/UNKNOWN.

Early exploratory failures were fixture defects: test-only POST omitted required JSON body;
authority baseline preceded explicit creation of the other-project fixture. They were corrected,
not product timeouts relaxed. The subsequent final DOM passed. A tamper test initially used the
wrong persisted column name; corrected to result_snapshot before the 16-pass focused run.
Independent review is requested separately; local commit does not imply integration acceptance.

## Independent recovery rejection and final correction

Independent actual HTTP reproduced a missing composite negative on frozen da81199: accepted
cold response loss → same-key actual cached202 replaced by a synthetic transport422 → the
UI cleared pending state, and a new key created a second real Run. The original 3PASS1FAIL9.09s
review log and real receipt proof are preserved under independent-pre-correction-failure.*.
The previous 62-family/DOM tests do not sign the corrected UI source.

Scope correction was committed first as e348159. Only runReportApp changed: an explicit first
422 may allow correction, but an earlier unknown intent or retry preserves immutable body/key.
Permanent focused actual HTTP DOM tests cover lost accepted receipt and malformed accepted200,
each followed by later retry422. They also prove first422 allows correction, a new submit is blocked
while uncertainty remains, and eventual successful same-key receipt resolves exactly one cold Run.
Two tests passed in 6.73s; each has seven assertions and records actual HTTP-loaded new UI hash,
three existing source/extraction Mock requests and zero cold provider calls. Principal/Grant rows
remain identical. No large suites were repeated. Independent final-hash actual HTTP recovery then passed (1 case, 3.62s; 2 POSTs, 1 real Run,
no third key). Four independent controlled-DOM cases passed (malformed phase, first422 correction,
list ABA and history authorization failure); these are explicitly separate from real HTTP evidence.
Three previous independent backend attack probes remain applicable to the unchanged backend SHA.
No remaining blocker was reported within this finite PREVIEW_ONLY slice. This does not establish
full-suite, native, PG, AppManifest/AppPrincipal or owner semantic acceptance.

## Necessary baseline alignment

A normal merge of exact e6c03cf15b7473ebce4cd3d5b8c4dcc06405a676 into the isolated named
branch produced 08ad84ea16527dd126912131cd16267300bc518a without conflicts. Scope was
recorded first in NamedReportBaselineAlignmentPlan.md (4a25e60). All eleven named source/test
files retained exactly the same bytes and SHA256; the named behavior and recovery correction
were not rewritten. The e6 native namespace/FIFO guard fix is now included. Withdrawn 8de
cleanup was not merged, and no other tree or parent candidate was edited.

Only affected guards and named probes ran: 12 PASS, 0 FAIL/SKIP (21.92s). They cover no-queued
and optimized missing-root/wrong-owner/no-queued refusal, ordinary and optimized wrong-namespace
refusal with all durable tables unchanged, real gated FIFO four-default-run drainage/recovery,
named actual-HTTP recovery (2), and original row-key/missing-origin/bool-version hardening (3).
Evidence: docs/evidence/named-report-baseline-alignment-20261007/{before,after,summary}.json
and targeted.log.gz. No full suite, PG, actual native browser/CI, provider activation, LIVE,
push, publication, new authority or merge into the parent candidate occurred. Original review
evidence and old failures remain historical evidence; alignment does not sign off the parent CI
or promote UNKNOWN/NOT_ACCEPTED/PENDING to semantic acceptance. All test-owned servers exited.
