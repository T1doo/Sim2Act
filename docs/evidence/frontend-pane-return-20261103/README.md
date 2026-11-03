# Tonight: one concrete task-pane return chain

Baseline `2a305556685a1efa683b31b5bd3b4bed1ea4d4f2` was clean. The remote branch was independently read back at the same SHA; stale local tracking refs were fetched explicitly and then compared 0/0. Document-only main `be1b29724d34d6bb2a24a468357c9eb4741bfc35` remains an ancestor and unchanged. Work continues on the original sole-writer development branch; no competing writer.

## Useful result

Approved DOCX v1 §4, §14B / figures V15–V16 and G07 require reachable instruction/result/inspection zones, retained context and appropriate return focus. The exact chain was reproduced with delivered HTML/JS and the existing stylesheet's 900px media rules projected in CSSOM:

Goal Cards → visible “成果” entry → same task workbench/result → Protocols → “指令” entry → same task workbench/input → ordinary section return to retained result → return to retained inspection.

Before the fix, the first “成果” click only changed the hidden workbench's dataset and left Goal Cards active. The baseline failure is in `before.log`. A related return selected the first workbench heading even when its instruction panel was hidden. The small fix makes the pane entry activate the existing task section and makes section focus choose the retained instruction/result/inspection heading. Original nodes, instruction, selected materials, Run state, request keys and controller operations are preserved.

## Current picture-path status

- **Requested action:** capture the current repository frontend at1440×900 using protected `/usr/bin/chromium`, `chromiumSandbox=true`; the previous target was `http://127.0.0.1:8765/`.
- **Known execution result:** historical `RUNTIME_ABORT_BEFORE_PAGE_CAPTURE`, SIGABRT. The SUID helper `/usr/lib/chromium/chrome-sandbox` was misconfigured. This was a runtime failure, not an automatic approval rejection. Original machine-readable evidence remains in `../frontend-day-20261102/browser-blocker.json`.
- **This pass:** action not attempted; stopped pending material recovery evidence. No current service/browser was launched, no alternate route/executor or user computer was used, no sandbox/SUID/security change was made. Environment startup alone was not treated as repair.
- **Available picture version:** archived native Source/Cold screenshots in `../protocol-review-readback-native-ui-20261022/` were executed at `caeb08a104616d0fe438c8f2c2beefbae7094511`. They are historical evidence for that version, not current frontend pixels. The approved DOCX images are design illustrations. Current-source product screenshots: **0**.
- **Tool-path check:** currently registered design-node/Figma screenshots or Site/deployment tools do not supply an authorized current Sim2Act product frame. No substitute capture, upload, deployment or external execution path was invoked.

The minimum recovery condition is a supported authorized cloud browser environment with the protected configuration materially confirmed repaired, followed by a bounded current-SHA page capture/check under the original execution limits. That would require a fresh source/frame binding. Native Windows/WebView2 additionally needs its supported native environment and a still-valid bounded execution allowance; an old package or screenshot is insufficient. This record does not authorize new CI, downloads, permissions or security work.

## Actual checks

| Artifact | Scope/result |
|---|---|
| `pane-return.json` | **12 checks PASS**, delivered controller, controlled DOM and projected900px stylesheet rules. Cross-section reachability, visible pane/heading, retained inspection return, instruction/material preservation. New API requests0/errors0. Not browser geometry, real keyboard or pixels. |
| `before.log` | Baseline driver fails at returning from Goal Cards to task workbench. No product mutation was needed to reproduce. |
| `related-interactions.json` | Existing39 controlled interaction checks PASS, including focus/input and unknown command behavior. The suite's existing controlled read failures/cancel are simulated wire responses, not real business requests. |
| `related-visual-contract.json` | Existing38 source/CSSOM/controlled geometry checks PASS. Not rendered viewport acceptance. |
| `related-scope.xml` / `.log` | Existing1 scope/density pytest PASS, no skip/error. Local jsdom/navigation check; no API/provider/worker/PG/native execution. |
| `independent-review.md` | Independent read-only 12-check execution PASS; no remaining must-fix in this bounded chain. |

Earlier full API, Source/Cold and 29-case results retain their original version/scope and were not rerun or relabelled here. Exact current source/evidence hashes are in `source-manifest.json`, committed together.

Remaining unverified items are current before/after pixels, real viewport/zoom/long-Chinese wrapping, actual focus scrolling/clipping, pointer/text selection/clipboard, screen reader/forced colors, animation/background performance and Windows/WebView2 close/reopen/DPI behavior. The absence of new frames prevents full frontend acceptance. No speculative visual redesign or unrelated review was added.

CI ledger remains **487/900 seconds**, **0 new CI execution**. No new dependency/download, cost, credential, permission, security probe, live model, PG, release/deployment, main merge or user-PC access. The original30s lease/300s Run limit is unchanged.

```sh
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_pane_return_ui.cjs
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_day_ui.cjs
NODE_PATH="$PWD/scripts/browser-ci/node_modules" node tests/frontend_visual_contract.cjs
NODE_PATH="$PWD/scripts/browser-ci/node_modules" python -m pytest tests/test_workspace_density.py -q
```
