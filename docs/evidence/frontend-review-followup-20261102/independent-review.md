# Independent read-only frontend review

Reviewer: `/root/frontend_readonly_review`, explicitly requested by the parent; sole source writer remained `/root`. Review target: first frontend delivery `91d272f6f342e2e921209bba5730052e47b41a7e` and the subsequent uncommitted app.js/app.css/test diff. Final implementation bytes are bound in `source-manifest.json`. No product source was written by the reviewer. The original `author-review.md` remains an author self-review, not this review.

## Findings and their disposition

The following table is the writer's trace of the reviewer's findings, not a claim of native/browser testing:

| Finding | Current correction |
|---|---|
| Historical application sources used current draft manifest | Run frozen contract only; absent contract remains unknown. |
| Historical restore used stale material availability | Recheck current full membership/disabled state, semantic directory version, connection and goal version before filling unsaved draft; failed confirmation preserves editor. |
| Unknown cancel showed old status as current in checks/versions | Both label unknown explicitly with last-confirmed metadata. |
| App history return focused hidden project history | App owner returns to visible application history. |
| Same-project quick lookup dispatched change and cleared drafts | Same ID focuses without change; other IDs use original navigation. |
| Picker ignored full directory/hash/disabled changes | Full snapshot plus semantic epoch/observer, including pending records; identical polls stay usable. |
| Retained previous result only covered answer string | Include previously verified MD/receipts/structured sums with scope/version, no copied mutation controls. |
| MD projection could cause a later update to replace a code block rather than original pre | Dedicated original-text target. |
| Late denial after instruction edit skipped private-source cleanup | Resource/identity scope separated from submit-intent freshness. |
| Global pending fragment preflight blocked new context after removal/switch | Clear logical pending check, retain ABA fence; late old reply cannot submit. |

The reviewer also checked measured disclosure/inspector motion, portal menu keyboard/clamping, same-directory polling and source/ordinary Run contract compatibility. A transient report about hidden fragment context was withdrawn after reading the current source: `clearFrontendRun()` already redraws the still-bound context.

## Final independent result

The reviewer independently ran the final fragment driver after the preview/download denial extension: **57 checks / 12 scenarios PASS**. Its final report states:

> 独立只读审阅结论：以 `91d272f6f342e2e921209bba5730052e47b41a7e` 为基线，针对当前 `app.js`、`app.css` 及相关测试的未提交 diff，未发现剩余 must-fix。审阅者未修改文件、提交或推送。
>
> 片段审阅期间发现的问题已收口：历史/结果清理后绑定仍可见；编辑使意图失效后，同来源的明确权限拒绝仍清理私密投影；移除片段、切身份或切项目会解除旧 preflight 的全局阻断。最后新增的 preview/download 权限拒绝清理具备调用方身份及连接守卫，helper 仅清同资源绑定及原文，不会误清后来不同身份或不同资源。
>
> 独立实际验证范围：
>
> - `frontend_review_fixes.cjs`：20 项受控检查通过，新增 API 请求 0，未捕获错误 0。
> - 最新 `frontend_fragment_ui.cjs`：57 项检查、12 个场景通过，包含 preview/download 撤权。
> - 另在内存独立复现旧 GET 悬挂后移除片段、切身份、切项目三种情况：新普通提交均解锁；旧响应返回后被拒绝，未产生额外 POST。
> - `git diff --check` 通过。
>
> 以上属于源码、受控 DOM、模拟几何及 WAAPI 调用验证。真实浏览器选区、页面像素、动画表现、剪贴板、缩放回流、读屏和 Windows/WebView2 原生流程仍未验；本独审未执行真实模型、PG、worker 或 CI，也不把作者另行运行的 API 回归计作独立验证。

The separate unlock message reported `unlocked=true` for removal/identity/project cases, exactly one new ordinary POST to p1/p1/p2, no fragment in those new bodies, oldCheckRejected=true after releasing the old GET, totalPosts still 1, and errors empty. These additions were evaluated in memory by the reviewer, not persisted by it as a new test file. The writer persisted the removal case in the final fragment driver.

The actual ASGI/SQLite freezing/unknown-recovery test was added and run by the writer. It is distinct from the independent controlled-DOM review and does not establish live provider, PG, native or browser-pixel acceptance.
