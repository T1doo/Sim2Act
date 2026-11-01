# Explicit Source / Cold desktop consent

Application source: `462f08dad18e6d174df263e86ba75b8176f4f9e3` on `dev/cloud-g0-live-20261028`. Evidence and two extra test-only cases are committed separately. The folder label follows the ongoing session; XML timestamps record the actual UTC execution on November 1. No package or native Windows verification is produced by this slice.

## User-visible change

Inside the existing **独立试验准备** workspace, recover the original preparation/approval, choose Source or Cold, read the project's already accepted Runs, and select one explicitly. **审阅此阶段的实际范围** calls the existing authenticated stage-review API. The server still resolves actual provenance, accepted goal, instance revision, app, release, predecessor and authorization; the page does not manufacture those facts.

The review displays the full original material, all target fields, readable actual app recipe, exact Run/version/Release binding, original limits, deadlines and effect on an already-running controlled Worker. App and recipe fingerprints are checked before showing current steps. Digests are available under details; JSON is not the user's review workflow. This entry does not create a Run or implicitly advance a handoff.

The checkbox starts unchecked. Confirmation performs another exact readonly review, then saves/re-reads an opaque original-key intent under a Web Lock before sending one stage approval. A changed version, missing lock, failed storage or expired scope prevents that mutation. An unknown, rejected or malformed mutation response keeps the original key and permits only explicit readonly recovery. Durable metadata contains IDs/fingerprints, never the bearer or material. Switching project/identity/stage, pagehide and storage events invalidate late private views. A 403 clears both parent and stage private material.

**取消审阅** declines an unsubmitted review. During a request that button is disabled; with an intent it says that closing preserves the original key. Stopping already approved future stages navigates to the existing, separately confirmed whole-trial withdrawal. It does not silently check that confirmation or claim it can recall an already sent model request. Historical recovery does not reapprove or authorize dispatch.

## Actual checks and boundaries

| Evidence | Actual result | Scope |
| --- | --- | --- |
| `ui-final.xml` | 32 passed, 0 errors/failures/skips; 78.896 s | Original 25 preparation UI/API cases plus 7 stage UI cases. Delivered HTML/CSS/scripts loaded through the real authenticated test API into jsdom. Stage responses and app/Run metadata are explicitly typed wire simulation, not real stage acceptance. Real root authentication/preparation/withdrawal checks still execute. |
| `ui-extra-boundaries.xml` | 2 passed, 0 errors/failures/skips; 5.190 s | Concurrent clicks produce one approval mutation; a foreign target with a correctly recomputed authority digest is rejected. Same frozen application bytes. |
| `backend-controlled-clock.xml` | 1 passed; 74.553 s | Existing actual Worker/ledger/Source/Cold proof fixture, separate from the wire simulation. Synthetic clock, TEST_ONLY SQLite, seven Mock sends (3/2/2) and explicit synthetic account qualification override. Not a real-clock performance or production qualification result. |
| `http-historical-recovery.json` | Source/Cold 200 with identical original request; wrong key 409; wrong principal 403; DB bytes unchanged | Actual current Store and HTTP API reread a private SQLite backup of that explicit synthetic backend fixture. Existing rows only, no new authority inserted. |
| `independent-review.txt` | No remaining must-fix for this slice | Readonly source and boundary review, including final test-only cases. |

The 32+2 page checks are distinct cases. The backend functional fixture is a separate test, not an extra claim that the page used a production account. Actual live model requests: **0**. PG operations: **0**. New CI runner execution: **0**; previous ledger remains 487/900 seconds. No browser pixels, native WebView or user-PC execution was performed. jsdom validates interaction/DOM behavior, not visual quality.

Original 30-second lease, single-Run 300-second limit, original P-B total contract, 1 RPM trial cap and all server authorization/provenance/commit gates remain unchanged. This UI repair does not resolve the separate complete P-B timing-contract decision, provision formal accounts/PG, create stage Runs, or establish full R0/Windows/live acceptance. The previous native package does not contain this new source and is not relabeled as current.

## Reproduction

Use the existing isolated lock-matching project runtime and cached jsdom dependency. No new model/PG/CI is required:

```sh
/workspace/scratch/sim2act-pg-locked-runtime-20261101/venv/bin/python -m pytest tests/test_natural_trial_stage_ui.py -q
/workspace/scratch/sim2act-pg-locked-runtime-20261101/venv/bin/python -m pytest tests/test_natural_trial_deadlines.py::test_actual_seven_slot_v2_worker_fixed_clock -q
node --check src/sim2act/web/natural-goal.js
node --check tests/natural_trial_stage_ui.cjs
```

`ui-final.xml` also records the exact names of the original 25 preparation cases run with the stage suite. The test harness uses the locally cached jsdom at `/workspace/scratch/sim2act-ui-deps-20261029/node_modules`; it is not a bundled product dependency.

## Preserved failures and compatibility correction

`failure-index.json` retains SHA256/size/location and diagnosis of the first syntax-error run, test-driver change-event failure, and old backend-clock adapter failure. None is silently reported as passing. Original local logs remain intact. The old backend adapter failed with the exact unexpected `_heartbeat_state` keyword shown in `backend-adapter-before.log`. Its correction forwards that current argument and advances synthetic quota waits in valid steps using the original committed renewal. Production Worker/lease/deadline code and assertions were not weakened.

`manifest.json` binds frozen application files and evidence hashes; `backend-scope.json` hashes the private synthetic full fixture without publishing its database or raw wire records. New evidence contains test counts, code paths and synthetic metadata only; no user material or token/credential values.
