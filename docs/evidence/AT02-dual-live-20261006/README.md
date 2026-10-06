# AT02 dual-owner bounded LIVE slice — 2026-10-06

## Authorized scope, frozen before send

Parent relayed explicit user authorization for **at most four new Intern requests**, **512 output tokens/request**, synthetic inputs only, no automatic retries. This supersedes the earlier unapproved two-request proposal; it does not authorize unlimited usage. Both owners/projects must each perform their own tool→feedback→answer chain in the same fresh fixture. Actual returned identities remain subject to existing `intern-s2-returned-name.v1`; model weight version remains unknown.

Starting worktree: `/workspace/Sim2Act-pb`, existing `dev/f1-foundation`, local documentation HEAD `ce13864083feb34a8fcad19ab02b647c9401902f`; remote evidence HEAD `b91e4e318418fe107195500501d4cbf690ea3f02`. Original worktree and historical AT02/LIVE/V5 files remain untouched. Product source is unchanged. No new table/schema or production authorization changes.

## Gates and execution plan

1. Explicit controller migration on one disposable PostgreSQL17 container/database; independent API and worker use only non-superuser CRUD role with schema CREATE denied. Seed exactly two synthetic owners/projects/runtime identities and TXT values42/84; retain four active resource.read intersections. Cross-owner/project/resource/runtime and owner/runtime revocation negative checks must pass before any model call.
2. Persistent shared `wire.json` and `flock` protect the entire send/response interval. File and directory fsync precede each actual normal `httpx.Client.send`. Count and halt are recorded first; crash/unknown consumes a slot and blocks following calls. Fixed endpoint only; no models lookup, no retries, no changed proxy/TLS/credential routing. Invalid returned identity/response or non200 halts. Each full serialized body≤2000 characters and output cap512; ≥6 seconds since prior response. Never reset this LIVE ledger or rerun executed controller.
3. Two independently accepted intents, A then B, each normal one-shot worker with frozen requests2/tools1/repairs0/total-envelope5000/wall300sec. Only `Read; echo.` and own synthetic resource refs leave the machine. Require each to have two LIVE RECEIVED attempts with enforced accepted identity, one VERIFIED resource.read receipt, persisted assistant/tool/assistant context and exact own final42/84; preserve normal Run state PARTIAL and do not rebrand as SUCCEEDED. A failure stops B and records unused budget; no automatic retry or oracle relaxation.
4. Normal separate loopback API readback and cold store verify persistence, other-owner403, unchanged grants/data and shared account reservations. Archive whitelisted public assistant/tool/context fields, normalized usage/unknown usage and hashes; never raw headers, configured credential, private reasoning or private subprocess logs. Stop/remove only owned processes/container/tempdir; independent read-only audit of final evidence.

## Before-send evidence

`preflight.json`: 23 actual local checks PASS; zero model sends. `guard-offline-results.json`: four MOCK boundary checks PASS, external0. Independent reviewer first found missing fsync and malformed HTTP200 clearing halt; both fixed before LIVE and re-review requested. Preparation uses local TestClient; actual run/readback uses independent API and worker subprocesses.

## Acceptance limits

This is a bounded AT02 dual-owner LIVE slice, not whole F1/F2/P-A/P-B/AT16 signoff. Win11 native ordinary-user/physical-device/browser/accessibility boundaries are not covered here. No arbitrary code, external business input, deployment or non-CSV contract transmission is authorized. Preserve failed/unknown outcomes and unused budget honestly. Exact final results and cleanup follow in `results.json`; independent review and manifest to be appended after execution.

## Actual result and preserved boundaries

`results.json`: PASS_BOUNDED_DUAL_LIVE_SLICE, 26 execution assertions; A/A/B/B exactly4 requests and authorization remaining0. Both Runs remain PARTIAL, final trimmed answers42/84; each has two LIVE RECEIVED attempts, enforced ACCEPTED Intern-S2 identity, one VERIFIED resource.read Operation and actual persisted feedback followed by final answer. Fresh Store readback and separate API cross-owner Run/history403 passed. Initial and final resource/grant sets are unchanged. Same account quota has four reservations.

Full actual request sizes1170/1958/1170/1958 characters. Inter-response separation6.000398159/6.000344038/6.001173258 seconds. All usage reports known: prompt2506, completion299, total2805; each request max_tokens512. Counts are upstream reported usage, not independently tokenized price/weight claims. No models call, automatic retry, repair, third round or business material transmission occurred. The durable pre-send journal covers exactly this approved batch; unused slots0, never reset.

Owned API stopped; both worker returncodes0; only named owned PostgreSQL container stopped/removed and owned temp directory removed, confirmed in results. `state.json` is COMPLETE_NO_REEXECUTION. Standard TestClient deprecation warning remains; no product changes warrant repeated engineering CI. Historical malformed/timeout guard defects were found and fixed in pure MOCK before LIVE; initial offline-preparation AttributeError and original historic LIVE failures remain in their original archives. Win11/full-stage/formal acceptance and nonCSV real-source work remain open.

## Independent audit and source closure

`independent-review.json` records **58 actual independent archive assertions PASS**, with original executed script `independent-review.py`. It reconstructs all four complete serialized request bodies from public persisted messages and registered definitions, matches SHA256/bytes/characters to actual wire records, matches attempt fingerprints, checks source content SHA, owner/runtime/project intersections, exact Operation receipt→tool feedback→Run receipts/call IDs and VERIFIED-before-second-reservation/send ordering. All usage/identity/data/grant/budget assertions pass. Reviewer made zero network requests and did not inspect credentials or headers. This independently checks archived evidence; it does **not** repeat LIVE, re-query already removed PG or independently rerun the recorded cold Store/HTTP403 tests. Both Runs retain semantic goal acceptance NOT_RUN; exact42/84 is the bounded harness oracle only.

The execution transport briefly disconnected during documentation closure, after successful cleanup and independent audit. `wait_for_environment` returned ready and the same clean source/worktree/evidence were recovered; no model request was repeated. Source `src/scripts/tests/.github` and dependency/config manifests remain byte-identical to the final previously tested `c16cbae1723eeaf089e4cb36eef9874846705d9b`. Original worktree remains clean at `6f688e4dd80b5c81d41aecde90e360d3629f9c21`; V5, original cases/AT02, lifecycle AT05 and historic LIVE archive are untouched. Only docs and validation evidence are committed; existing workflow paths exclude docs, so no new ServerCI is expected or claimed.
