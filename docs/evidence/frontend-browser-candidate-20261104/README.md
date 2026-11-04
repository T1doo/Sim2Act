# Current-source real-API browser acceptance candidate

A new bounded browser candidate was actually produced using existing dependencies. A complete production/native Windows application is **not** required to inspect this current frontend. Application source is `4423923bbc1b7085c148c63f46f3dfa7be582996`, src tree `cd437b2eee4aa43a5ab2e28da2180b5b69d4b7ff`. All197 tracked source files were read back against that exact Git commit. The new preparation/server/check scripts and evidence are separately committed; they do not change the application src tree or main.

## Actual output

- Local file: `/workspace/outputs/Sim2Act-browser-review-4423923-20261104.zip`.
- Size: **19,339,258 bytes**; SHA256 **047140936dbffe54bf3e0d147d72d672ec0eba20624871344c242915c3abe8c2**.
- Created: 2026-11-04T09:18:45.825665Z. ZIP member dates are normalized; they are not the creation proof.
- 1763 ZIP members, including1762 frozen manifest entries; every member was re-read and its size/hash checked. Internal manifest SHA256: `3480da6992c7e5d1ad0fff47e4fa497e585ade868d3690785b11f6cba22be4ed`.
- This file really exists, but **no formal attachment/file ID/upload receipt exists**. It remains local and is not claimed as a user-downloadable attachment. The ZIP is not pushed via an alternative transfer route; only preparation code and textual evidence are committed.

## Why this can be inspected without a full desktop package

The archive includes the actual current HTML/CSS/JS and current API/Python source, an explicitly synthetic saved SQLite fixture, and an existing private Windows Python3.12 dependency image. `start-review.cmd` invokes that already included interpreter; it neither installs nor opens a browser. No .NET/WinForms/WebView2 host is used. The unique Windows coordinator can use the restored existing browser session after the candidate arrives through the supported formal channel, keeping candidate and browser profile within authorized `E:\Software`.

Windows runtime dependencies are1554 existing files from the old042 package (whole ZIP cc177eeb...), with **all old sim2act application code/metadata excluded**. This does not relabel the old package as new. The initial attempt to start with no application native dependency failed at the existing `_RAW_UNSUPPORTED` import; that failure is preserved. The current `_raw_snapshot.c` exactly matches the old frozen Windows raw module's recorded C source hash, so that existing Windows module is reused. The already built local Linux raw module is included only for this cloud verification. Other application native modules, including two whose C source differs from the old Windows build, are not reused. No native compilation or download occurred and no guard was patched.

Runtime app loading explicitly prioritizes the frozen candidate source and selects only the matching raw dependency by platform. Original API authentication, origin checks, security headers, versions and source contracts remain active. The server accepts GET/HEAD and explicitly rejects mutation methods with405 `FRONTEND_REVIEW_READ_ONLY`. It creates no worker, never discovers `.env`/provider credentials/production DSNs, and binds127.0.0.1 only. Original `Store.tx` is retained; the database is not falsely claimed to be filesystem read-only. Its unchanged bytes were checked after each bounded serve run.

## Nonempty results are actual deterministic facts

Preparation uses the existing actual loopback API and normal deterministic CSV Worker path in a new synthetic fixture: create materials/Goal/CSV app/internal version/instance, execute one CSV Run, then persist sum30/v1. There is **one seed Worker claim**, recorded in `seed-receipt.json`; real model requests0. This is a synthetic internal app version, not a product/GitHub Release. No P-A/P-B/model/PG experiment is run.

While serving, worker/model counts are0. The visible banner names the profile, source and public synthetic login and states that save/execute/approve/publish are closed. Existing client input controls retain local draft behavior; mutation attempts receive a real explicit refusal, not a fabricated successful run.

## Actual validation and independent review

| Evidence | Actual result |
|---|---|
| `http-check.json` | **137 checks PASS**, actual subprocess/loopback HTTP/current API/SQLite;26 real static assets exactly match frozen source. Source-bound headers, current module path, health, projects/resources/Goal/app/Run and persisted30/v1 read back. Mutation405, wrong synthetic login403 PERMISSION_DENIED, cross-origin403. Normal exit within10s; DB bytes unchanged. Linux, not Windows/browser rendering. |
| `ui-check.json` | **8 checks PASS**, actual current page/scripts in jsdom over real candidate HTTP. Login, project/materials, existing instance/history, nonempty30 result, theme control, explicit Run refusal and retained history.20 recorded API requests, including one denied action. This is not a real browser or pixels. |
| `first-complete-http-check.json`, `first-complete-server.stdout.log` | Prior complete136-check run, same candidate and immutable DB. Together with final run proves controlled stop and restart still reads persisted data; not Windows cold-reopen acceptance. |
| `without-raw-*` | Real initial missing-native import failure. It was fixed by exact-source dependency reuse, not a fallback or guard bypass. |
| `auth-assertion-before.json` | Test initially expected401, while the unchanged original API correctly returns403 PERMISSION_DENIED; test corrected to that exact contract. Server still stopped cleanly with DB unchanged. |
| `independent-review.md` | Read-only independent manifest1762-entry/hash/source/gate/stop-boundary review; no must-fix found. No service/browser/transfer run by the reviewer. |

## Current real-picture and transfer boundary

The parent confirmed that the unique Windows coordinator successfully obtained CUA application/window inventory and existing Chrome browser3, with getApp/getBrowser support. That is material UI-interface recovery; this pass does **not** report lack of a local UI interface as the blocker. Inventory is not yet screenshot/input/application acceptance.

The formal file-transfer helper's earlier failure has no confirmed recovery. No retry, alternate upload, Space/GitHub artifact workaround, invented download URL or user-PC action was attempted here. No formal attachment exists. Next concrete step is for the coordinator to obtain a confirmed supported transfer receipt and place this exact SHA256 archive in the approved E directory, verify/unzip, run `start-review.cmd` there, and use its printed loopback URL in the restored approved browser. This is not authorization for new installers, credentials, CI or security changes.

**Windows execution and screenshots remain NOT_RUN.** This candidate removes the need to first build a complete native desktop package; it does not prove Windows runtime/viewport/focus/clipboard/accessibility/animation behavior. Full production/PG/native-host qualification remains separate. The former protected cloud Chromium SUID-helper failure was not retried or bypassed.

CI ledger remains487/900 seconds: remaining413 is not a new CI approval; new CI0. New download/install/compilation/upload/model/PG0. No main merge, deployment or product Release.

## Reproduction with existing local tools

Preparation (new directory only, never automatic on Windows startup):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" python scripts/frontend_browser_review.py prepare \
  --output /new/candidate-directory \
  --runtime-archive deliverables/windows-full-20261101/Sim2Act-win64-042ab21c4fa9.zip
```

Existing Python3.12 environment and already built local raw dependency are required for preparation; nothing installs or compiles. The Windows consumer runs only the packaged server with the included existing Windows interpreter.

```sh
NODE_PATH="$PWD/scripts/browser-ci/node_modules" PYTHONDONTWRITEBYTECODE=1 python scripts/check_frontend_browser_review.py \
  --candidate /existing/candidate-directory --output /new/check-directory \
  --ui-driver tests/frontend_browser_review_ui.cjs
```
