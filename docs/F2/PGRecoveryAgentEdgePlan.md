# PG恢复诊断与既有保护Edge新增agent路径（2026-10-06）

当前基线047bf447ea50839419d7c4ad37cad41f4fd41248；父对照4e7010b3a5e2697fa3bf45a53e0b992f71f6f7c5。授权仅本地诊断、独立审查、全PG重跑和Windows测试接线；不得push/CI/LIVE，不改LinuxSUID helper/安全设置。原fullPG515PASS1FAIL1SKIP及focused2PASS保留，后者不视为修复。

## 先闭合PG实际观察

固定四轮A父/B当前/B当前/A父：共同tests/test_persistent_app_runs.py相同文件hash/顺序，独立schema与既有临时最小CRUD角色，同PG17/venv/环境，detached父工作树不影响旧work。opt-in插件启动原child fixture的runpy观察包装，仅一次调用原claim/guard/heartbeat/once、原返回/异常/lease1/timeout不改。时间记录wall与monotonic；失败guard后仅取本Run的状态/fence/lease，成功不增SQL；pid取已有driver属性。角色采样只pg_stat_activity/locks的安全列，无querytext；测试teardown前保存本schema状态和事件kind、operation状态/结果数量，不存结果/inputs/receipt/凭据。每个子进程200记录、父采样200次，独立supervisor每轮300秒上限；注明插桩/采样扰动，未插桩原失败不覆盖。

首先比较实际模块路径/hash和失败阶段；四轮全部PASS只能写有界未复现。若有真实失败时间线，实施最小且不放宽失效lease写权限的修复，添加原失败对应oracle并独立审查；否则明确未知，保留下一诊断入口。检查测试污染、锁、lease/heartbeat时间线及异步等待，不能简单扩大timeout。独立审查后完整PG重跑。

## PG之后的新增Edge接线

复用现有WindowsBrowserCI.ps1、安装Edge签名验证、chromiumSandbox=true、真实命令行/renderer token保护审查、相同job/permissions/actions依赖和当前受限输出链；不造新runner，不将旧38项或旧PNG作为agent验收。新增agent候选实际来源链、离线响应、审批、冷Run与历史、迟到响应、撤权/篡改及390px控件/引用溢出检查；真实desktop+narrow新增PNG明确命名、保存hash，之后实际查看像素前始终NOT_REVIEWED。本轮Linux不原生运行、不push/CI；只接线及本地结构/语法/fixture检查。若PG无法闭合，不提前声称新增原生已验收。

证据新增于docs/evidence/pg-recovery-agent-edge-20261006；旧证据不重写。

## 固定对比结果（先保留未知）

A1父38PASS99.90秒、B1当前38PASS83.79秒、B2当前38PASS92.72秒、A2父38PASS82.38秒；共同测试hash一致，child实际模块path/hash核查，无产品/lease/timeout修改。每轮claim返回剩余最小lease0.95–0.97秒；观测clock offset波动<0.001秒，不证明原失败时无时钟问题。未复现原RUNNING，无法归因；该公共模块顺序不覆盖原全套前置测试污染，插桩和采样亦可能扰动。终态heartbeat拒绝SUCCEEDED/CANCELLED、lease0不是恢复失败。

独立检查发现首版observer错误路径附加SQL/日志I/O可能覆盖原异常，实际首版副本冻结于新证据，成功四轮不提升此错误路径。新版删除guard错误后的SQL，I/O、PID、元数据与诊断清理best-effort；外部采样/snapshot独立read-only连接保持本schema，connect1秒、statement/lock200ms、pool1秒；收尾thread_stopped可检查。实际无DB self-check故意日志失败，原异常identity/一次调用和返回identity保持。独立复审后完整PG观察重跑开始，依旧不称产品修复，原全套FAIL保留。

## 实际复现与最小修复

第三全PG（047产品/测试，两个有界observer）515PASS1FAIL1SKIP927.55秒，原before_commit再次FAIL。正常恢复claim从8780.61950到8781.42164耗0.80214秒，lease8781.61953仅余0.19789秒；prepare在8782.06315完成，heartbeat等待Run transactionid后guard拒绝、commit亦拒绝，PREPARED/结果0/RUNNING。该区间wall-mono offset跨度<0.000001秒；claim采样无未授予锁，慢claim的基础负载来源未知，不据此声称时钟/污染根因。只修已观察到的lease起点缺陷：expired扫描now保留，新lease在reconciliation/候选行获取后以fresh time赋值，长度、guard、fence、事务顺序不改。

实际确定性oracle在RECONCILED后fakeclock推进2秒，无sleep/timeout改动；旧式1FAIL归档，修复式通过并验证旧fence及到期拒绝。独立时间线/diff审核无阻塞，focusedPG3PASS14.28秒。修后全PG启动，不启用crashchild/锁采样插桩；AT05保留bounded身份观察包装以定位另一次startupUNKNOWN。修复不保证任意后续超长事务能在lease内完成，仍禁止过期写入。

第二全量的AT05首次start返回1（API/worker exited；日志空）仍无充分归因；targeted和第三全量通过不替代解释，也不将该失败归于lease修复。

## 接线审查要点（尚未实施）

独立只读建议同一protected Edge browser另context/独立agent SQLite和API fixture；新page及后续新renderer实际再CDP+Windows token审查。保留原150秒node/4分钟step/15分钟job约束。真实Replay文件选择、审批手动ack、冷默认worker与来源引用/semantic UNKNOWN、持久历史、迟到approval/File/appresponse、篡改和撤权、Grant不变分组单独计数。延迟route handler必须等待实际fulfill完成再unroute并传播routeFailure，避免既有故障重演。

新输出仅agent-results.json、agent-desktop.png、agent-narrow.png、agent-failure.png具名白名单，每文件原2MB上限和原stdout输出；截图记录hash/尺寸/页面布局测量。视觉审查字段恒初始NOT_REVIEWED，390px真实像素需随后单独查看；本轮原生NOT_RUN/screenshots0，旧38或旧PNG均不提升新增验收。

## 本地终态

独立审查后修复完整PG517PASS0FAIL1WindowsSKIP803.04秒；保留原失败，AT05另次启动UNKNOWN。PG闭合后已接同保护Edge的agent模块、独立fixture API和新renderer PID基线/三次实际token审查；独立静态终审无阻塞，修复可见details读取与每ownedchild独立清理。实际本地HTTP/DOM22PASS、foundation SQLite24PASS、ruff/mypy及语法PASS。新模块尚未native运行，实际截图0，390px像素NOT_REVIEWED；旧38/旧PNG不计新验收。用户授权边界为本地提交，未push/CI/LIVE。安全数据与原失败均见证据目录README/result.json。
