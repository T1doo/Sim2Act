# PG恢复失败对比诊断与新增agent原生路径

本轮父授权仅本地工作，基线047bf447ea50839419d7c4ad37cad41f4fd41248，对照父4e7010b3a5e2697fa3bf45a53e0b992f71f6f7c5。无push/CI/LIVE/模型查询，不改Linux SUID helper、sandbox或系统安全。原bounded-agent-ui-offline-20261006/full-pg.log中515PASS1FAIL1SKIP以及focused2PASS原文件保持。

## 固定AB/BA对照

相同PG17、venv、共同tests/test_persistent_app_runs.py文件hash与原顺序，每个用例仍独立schema、既有临时最小CRUD角色。父源码在/workspace/Sim2Act-pg-parent detached独立工作树，旧work不动；PYTHONPATH显式对应目标src，实际childimport和src SHA已记录。四轮固定A父/B当前/B当前/A父，各38PASS：99.90/83.79/92.72/82.38秒。comparison-summary.json含实际来源、clock offset与claim剩余lease；没有复现原完整PG的RUNNING，结论**无法归因，无产品修复**。共同模块顺序未复现原全套前置污染；观察器也会扰动时序。全PASS不证明原故障不存在或时序根因成立。

首版observer/plugin冻结副本及四轮trace保持；只有明确自有role的activity/locks、PID/安全状态，200记录上限，不存querytext/material/credentials。A1观察到heartbeat guard拒绝的状态为SUCCEEDED/CANCELLED、lease0，是终态保护而非恢复失败。初次脚本路径配置错误中断在initial-probe-setup-interrupted.log，残余两条import-only trace单独分离，不计正式A1。

## 独立审查与新版观察器

首版失败路径附加SQL与emit异常存在替换原异常风险，独立审查如实指出，不能用成功四轮证明错误路径语义。新版guard失败不查询被测事务，日志/PID/元数据/诊断清理best-effort。父采样和终态snapshot使用独立同ownedURL/schema read-only engine，connect1秒、pool1秒、statement+lock200ms。无DB self-check故意I/O失败，验证原异常identity/一次调用及原返回identity。仅观察，不改原方法、lease1、原子进程等待或重试。

完整PG观察重跑仅opt-in plugin，实际终态/独立归档审查随后记录；未取得终态前不宣称通过。PG诊断收尾后才接既有保护Edge路径；真实新增截图/窄屏像素查看仍未运行，不借用旧38项或PNG。
# PG恢复故障与新增保护Edge接线

基线047bf447ea50839419d7c4ad37cad41f4fd41248，父4e7010b3a5e2697fa3bf45a53e0b992f71f6f7c5。当前只本地；无push/CI/LIVE/provider请求。本目录只合成测试/安全诊断列，旧失败日志保持原证据路径。

- 固定公共38项ABBA：父38PASS99.90s，当前38PASS83.79s，当前38PASS92.72s，父38PASS82.38s。共同测试顺序/hash一致；不覆盖原全套前置顺序，不视为原失败修复。
- `full-pg-observed.log`：515PASS1FAIL1SKIP739.18s，另一个AT05启动失败。空API/worker日志安全观察在`at05-safe-log-observation.json`；根因UNKNOWN。定向AT05 PASS和随后全量AT05 PASS不能解释此失败。
- `full-pg-identity-observed.log`：515PASS1FAIL1SKIP927.55s，再现原before_commit RUNNING。`reproduced-lease-diagnosis.json`引用实际trace hash及时间线：claim耗0.80214s、lease剩0.19789s，prepare完超期0.44363s；随后heartbeat/commit拒绝，PREPARED/result0。
- `lease-oracle-before.log`：原lease表达式下确定性oracle1FAIL，实际保留。`lease-fixed-focused-pg.log`：修复后oracle/两崩溃用例3PASS14.28s。独立实际trace/diff审核见`independent-lease-timing-fix-review.json`。新lease只在reconciliation/候选行获取后取fresh clock，长度、expired扫描、guard/fence不变；任何随后长事务仍受过期拒写。
- `comparison-observer-v1.py`及`comparison-plugin-v1.py`为原四轮冻结版本；首版错误路径附加SQL/I/O异常掩盖风险经独立发现修正，不改既有记录。`full-observer-*-v2.py`及当前`scripts/diagnostics`是opt-in最佳努力观测，guard原返回/异常一次保持，独立只读own schema有界采样；插桩可能扰动时间。修后完整PG禁用crashchild观察，仅AT05保留身份观测以捕获未归因启动失败。

修后全PG终态与新增Edge实施/本地检查结果待追加。原生浏览器本轮NOT_RUN、真实新增截图0、窄屏像素NOT_REVIEWED；不得将旧38项/旧图代替新验收。LinuxSUID限制不改helper/权限/sandbox；下一正常WindowsCI需父授权后运行，当前没有调用。

## 本地终态

修后`full-pg-fixed.log`：517PASS、0FAIL、1WindowsSKIP、1warning、803.04秒；没有crash子进程插桩，AT05仍使用有界身份observer。`foundation-sqlite.log`24PASS4.00秒；实际合成HTTP/DOM22PASS（`agent-dom-after-wire.log`/`local-dom-results.json`），这不是新native模块运行；ruff PASS、mypy23文件PASS、2JS语法与Python编译PASS。

新增`scripts/browser-ci/agent-ui.cjs`已接到既有受保护Windows Edge browser。独立fixture/API/SQLite，真实新增context前PID基线和其后3次CDP/token审核要求新renderer；这是browser集合差集，不是严格page→PID映射，仍核查全部观测renderer。新结果单独计数，手动Replay/审批、可信sourceRun/resource、冷v1/v2、实际接收丢回执/冻结手工幂等重试、持久历史、输入/File/app/project迟到、当前篡改/撤权、Grant不变。390px控件/引用溢出及desktop/narrow PNG的真实hash/尺寸均在未来原生运行中检查；当前NOT_RUN/截图0/像素NOT_REVIEWED。

独立实际diff/语法审核已修closed-details可见性与两owned进程独立清理，最终无具体静态阻塞（`independent-final-edge-wiring-review.json`）。原workflow/PS/job/timeout/security不变，无push/CI/LIVE。具名白名单新增agent-results/desktop/narrow/failure，沿用原2MB限制和原GitHub stdout链，不输出profile/DB/API日志。

自有测试API停止并删除临时fixture，自有PG容器移除、两自有端口关闭，旧work仍HEAD6f688e4干净；父比较worktree留作审查。原全量失败/中断配置和observer首版均保存；源claim慢的基础负载原因及另一次AT05启动失败未归因，完整P-B/语义自主生成/Win11/F1未提升。
