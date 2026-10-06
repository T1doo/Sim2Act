# Persistent experiment and actual serialized send gates

Baseline `d64550772115d02c4e0dd744d5ef6e9efae474cd`; existing `dev/f1-foundation` checkout. Local engineering only: no LIVE requests, model discovery, push, CI, security changes, new tables or runtime DDL.

## Executable offline package

```sh
PYTHONPATH=src python scripts/protocol-store-dryrun.py --experiment --output /tmp/gated-normal
PYTHONPATH=src python scripts/protocol-store-dryrun.py --experiment --fail-source b --output /tmp/gated-failure
# Private JSON {"url": "<isolated PostgreSQL test-controller connection with explicit schema/migration permissions>"}; never copied to evidence.
PYTHONPATH=src python scripts/protocol-store-dryrun.py --experiment --database-config /private/test-database.json --output /tmp/gated-pg
```

The demonstration explicitly migrates an owned synthetic Store (and creates/drops its isolated PG schema when selected), imports the four manifest-pinned synthetic packages, and runs authenticated source→independent persisted checker acceptance→extract→fresh cold→independent acceptance for A, then B. Real HTTP/worker, Attempts, Operations, exact InternModel sender, MockTransport and controller hooks execute; no model socket exists. Gold assets construct Mock **responses** and independent reviews only. They are never request inputs. The injected controller clock simulates explicit passage; product code does not sleep or retry.

`protocol_experiment.py` adds sealed events to the existing fixed pool, not another allowance. Default experiment request_limit0. Explicit offline demonstration14 tightens the existing shared14/64000 pool. Six stages3/1/3, reserved and actual token24k/8k/24k, stage300seconds, one inflight, and **last known settlement+6 seconds** apply across Runs/processes. This conservatively guarantees actual dispatch spacing after a delayed reservation. Reserve+Attempt+slot+send seals commit together; results+settlement seals commit together. Missing accounting, UNKNOWN, failed review, clocks and stage order refuse continuation; no refill/reset/resend. Failed stages cannot bind successors; the controller's explicit advance records permanent STOP after failure. A fresh production/LIVE pool remains0.

`protocol_egress.py` first validates the original protocol input against frozen provenance and actual authorized read receipts, then constructs one exact public outbound envelope. Source sends the public goal/inputs and canonical registered read calls/white-listed synthetic read data. Extract sends a versioned public template (complete schemas deduplicated once plus fixed public DAG rule) and only five safe receipt fields: run_id, result_fingerprint, independently-reviewed status, verified_read_count, received_attempt_count. It omits previous output, answer, source text, trace, proof, usage and evaluator metadata. Cold sends only the fixed public instruction/schema and newly read cold material. Fixed-template extraction is engineering, **not an experiment demonstrating learned reuse or general semantic extraction**.

Complete serialized model/messages/tools/streamfalse/max_tokens1024 bytes are frozen before reservation. InternModel uses `Client.build_request(content=bytes)` and validates that actual Request immediately before `Client.send`; it never rebuilds checked JSON. Complete8000-character/10000UTF8-byte limits hold. Endpoint/method/headers are closed; frozen settings/token/transport/validator identity prevent metadata substitution. Attempt protocol_wire SHA256/bytes/characters and an independent event seal commit atomically; actual dispatch rechecks these with type-sensitive canonical fingerprints and the current unique STARTED origin, lease, fence, grants, stage deadline and global-stop state. Error paths expose fixed codes/descriptions, not request body, credentials or provider-private metadata.

The [normal report](normal/protocol-store-dryrun.json) and [failure report](failure/protocol-store-dryrun.json) record exact request geometry and durable counts. Full frozen validation is recorded separately after both regressions end. Raw failure/probe history is retained; no earlier mixed or interrupted snapshot is promoted to a final result.

## Protected Edge preparation

The existing Windows helper now owns/cleans a third protocol API. The same protected Edge browser creates a separate loopback-only context; `scripts/browser-ci/protocol-ui.cjs` covers actual protocol/recover entry and receipt/project/identity races. Its dedicated fixture uses the **new** experiment/egress guards, canonical candidate, three stage bindings and four real Mock requests, then verifies default worker/recovery add0 requests. A permanent HTTP fixture test exercises this chain.

Protocol summary is embedded in the existing browser-results.json. Original eight emitted names, browser security arguments, workflow permissions and150second timeout are unchanged. Additional protocol PNGs remain in the owned fixture directory and are not emitted/uploaded; pixels remain NOT_REVIEWED. **New native Edge/Win11 execution is NOT_RUN** until the parent chooses a CI run; local HTTP/DOM/fixture checks do not replace it.

## Exact pending real-request proposal and remaining code boundary

No approval is requested or inferred in this delivery. Earlier exhausted10 and pending2/3 proposals add no allowance. The pending scope is **at most14 requests total**, A and B source≤3/extract≤1/cold≤3 each; the first stage/global request, time,1024output,8000characters,10000UTF8bytes, conservative/actual64000total token cap stops. Six seconds after known settlement and300seconds per stage apply. Unknown usage/status globally stops; no automatic retry, recovery send, discovery or extra request. Account currency pricing is not known, so no cost estimate is asserted.

Proposed outbound data is exclusively the four developer-authored manifest-pinned synthetic material packages and exact public templates/schemas, current permitted read feedback, and the closed five-field source receipt. No gold/rubric/expected answer, old output/answer, private reasoning, real V5/business/repository/other-project material, arbitrary header or error payload. Owner approval must bind exact artifact hashes, provider/endpoint, experiment identity and private durable ledger path; owner semantic acceptance remains PENDING and real-model behavior NOT_RUN.

**The two offline engineering gaps are closed. LIVE is still technically disabled, not merely unsigned.** Existing `initialize_experiment`, egress and ProtocolAttemptRunner require offline/test-only execution; HTTP/worker forbid LIVE and the fixed LIVE pool is0. A user's approval alone cannot make the current offline CLI send real requests. The minimal remaining implementation for a real run is one trusted production controller/activation path: consume an authenticated owner-approved sealed14-request/provider/data/ledger specification; bind it to the existing LIVE pool/Run provenance without refill or test injection; permit the same stage and serialized sender guards for that approved mode only. Current raw BudgetedProvider `approved=True` is not a substitute for that binding. This delivery does not create that approval or weaken these existing restrictions. General extraction semantics, generic continuation, formal Release, complete P-B/F1/AT02 and Win11 acceptance remain outside this finite package.

Machine-readable review proposal: [pending-14-request-proposal.json](pending-14-request-proposal.json), with individual manifest-pinned synthetic material hashes, exact provider/model/limits and unresolved owner/identity/ledger bindings. It is not an activation specification or permission grant.

## Final frozen validation

[Final validation](final-validation.json):894 collected, SQLite **858PASS/36SKIP/0FAIL**396.87s; isolated PG17.11 suite **891PASS/3SKIP/0FAIL**738.98s. Env-backed cases use realPG; explicitly SQLite sender/Mock/JS cases remain their own backend.147 source/test/script hashes match before/after;4 registered evaluation assets match baseline. Ruff/mypy34/Node2/diff checks pass. PG nativeWindows1 and ownedSQLite-only UI2 skips remain explicit. New protectedEdge NOT_RUN.

[Owned cleanup](owned-cleanup.json): interrupted residual schema1 removed, roles0; remaining synthetic schemas/roles0/0, owned server stopped and private connection file removed. Prior failed wholePG886/3/1 and pre-fixSQLite854/36, AT05 reproductions and all interruptions remain in failure-history. Startup fix uses retained original Popen handles; persistent identity checks are unchanged. Raw pytest logs retain original whitespace rather than being edited to satisfy whitespace lint. No LIVE/push/newCI occurred.
