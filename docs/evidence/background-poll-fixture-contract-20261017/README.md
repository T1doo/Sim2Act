# Background polling fixture contract repair — 2026-10-17

Current delivered base: `2aacbb207aec5d00d199c5ac20e5660bcfba2e0b`. Historical failed current test source: `2acb62e5bcc2c596bcb591d109433243691aeecb` (same app.js bytes as2aac). Historical comparison base: `17b8b8cff345c96885dfb18dd52f4ae1a6b54454`. Fixed test source: `3e2ea675d3849181170a03f6f4f1dbda469bfcae`. Only tests/background_poll.cjs changes; full src diff from2aac is empty.

## Cause, not merely a matching baseline failure

The original failed assertion is `assert(gate.used, 'phase reached')` in background_poll.cjs:19, propagated as nonzero Node returncode at test_background_poll.py:13. Both old failure.json files retain exactly four successful health latch checks, followed by the unreachable refresh gate. The original current pytest is RC1/JUnit1.986s; the base comparison was direct Node RC1, not a pytest/JUnit run.

The original fixture returns `{mode:'MOCK',api:'up',worker:'up'}` in both default health and the held health reply. Backend api.py:247-249 actually returns uppercase UP and UP/OFFLINE; app.js createHealthSampler validates those same exact enums. Its existing catch correctly makes malformed health unavailable, shows the failure label and returns false. The timer returns before refresh and releases its latch in finally. The first four tests only assert pending/next-tick behavior and thus pass without proving a valid health response. The next test arms resources GET, but only health GET occurs and gate.used remains false. Extending the wait cannot make an unissued request arrive. The product health/timer block is byte-identical between17b and current.

Historical originals did not save a per-request timestamp list. We preserve that gap and do not invent one. New explicitly instrumented reconstructions (diagnostic-original-base/current) show the same ordered five requests: health twice in scene1, held rejected health then another health in scene2, and just health in scene3. Scene3 has gate.used=false, latch=false, blank error field and the failed health label. diagnosis.json contains exact newly observed monotonic offsets, responses/rejection and gate state. These are new synthetic diagnostic traces, not historical HTTP/time originals.

A second contract drift was dynamically isolated. With only health values corrected, a single background tick requests health→resources→goal-cards→`/api/apps?metadata_only=true`; the old mock matches only `/api/apps`, so it returns fallback `[]`. The unchanged product reads list.items.filter and catches a TypeError in its normal timer error boundary. The real backend metadata route returns an object containing items (api.py:789), not an array. Correcting that exact mock route lets the same single tick reach runs-metadata and grants, with a blank error field and released latch. Those one-tick diagnostic processes exit0 but are not counted as the21-check regression passes.

The evidenced defects are in the synthesized driver contracts. Valid modeled contracts complete in current and frozen17b product code; no product repair was needed for this regression. This is limited synthesized testing, not proof of real HTTP/worker/native behavior.

## Minimal change and retained protections

Both health bodies now use uppercase UP; the mock additionally recognizes exactly `/api/apps?metadata_only=true` as an items object, retaining the existing unqualified route. Passive request/reply and setup/gate timestamps are written to both success and failure records. Logging does not introduce asynchronous waits or change response/gate release order.

The entire scenario body through the original checks is byte-identical (SHA2569febe9bef5b4921797c5b4f387ddf0ceab7d08ef3caa3da1e245339dec0ae746). All21 predicates remain: health/refresh/showRun pending/finally cases12; explicit refresh1; project ABA2; identity ABA2; old Run isolation1; UNKNOWN retention, background zero retry POSTs and explicit frozen body/key recovery3. The original50 setImmediate gate checks,2500ms timer registration, Python30s timeout and wrapper21-count assertion are unchanged. static-invariants.json and independent review verify these facts. No product, executor, Grant, permission, deployment or waiting-limit change occurs.

## Actual bounded verification

Author frozen3e2 current pytest:1PASS/0FAIL/0ERROR/0SKIP, RC0, JUnit4.582s,21 checks,122 synthesized request entries,20 phase entries across11 scenes. The two synthesized POSTs are explicit submission and explicit recovery, both deliberately throw the mock lost-acceptance error; real HTTP/model/worker calls are0. Background itself does not retry submission.

Author frozen17b comparison uses the same fixed driver and an exact Git app.js copy; the actual loaded HTML bytes also match17b. Direct Node RC0,21 checks and122 synthesized requests. It is not described as a second pytest/JUnit or a new unique node. Independent current exact-source pytest:1PASS/0FAIL/0ERROR/0SKIP, RC0, JUnit3.597s,21 identical checks and122 synthesized requests. Six directly relevant file hashes match frozen Git before/after. The independent report and full originals are preserved; repetition adds zero unique nodes. No other regression node or adjacent matrix runs.

## Evidence and remaining limits

Ten selected historical failure/source originals have path/size/SHA256 and exact preserved copies in protected-original-failures.json. Original failure files and old evidence commits remain untouched. The newly archived raw diagnostics, terminal commands, logs, XML, results/timelines, source hashes and independent report have manifest mappings plus deterministic gzip and SHA256SUMS. Verification compares archived/decoded/live originals for this slice only and rechecks the ten protected failures, without mass revalidating earlier batches.

Real HTTP/API/Worker, PG, native browser/Windows, actual models/semantic scenarios, remote CI/Actions, deployment and other nodes/matrices are NOT_RUN. The historical full-disk independent-report gap is not recovered. Prior cross-Release and project-creation product conclusions remain limited to their separately recorded evidence.
