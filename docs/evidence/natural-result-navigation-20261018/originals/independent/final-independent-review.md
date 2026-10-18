# 最终有限独立审查

结论：在下述已执行范围内通过；未发现阻断普通开发分支推送的 P1/P2。审查对象为 `ba6e1e06babdf591cbd439ee769b1c2a9cd0aa98`。本审查者非生产/测试作者，仅只读源码与关闭后的原件、执行标准库纯文件复算；未运行产品、HTTP、Worker、模型或 SQL，未修改仓库、数据库及旧 sealed 目录。本报告不背书尚未独立核实的推送、后续提交或远端 CI。

唯一生产修复为 `src/sim2act/web/owner-review.js:199` 将自然 P-A/P-B 的 owner Run 下拉选择接入既有 `showInternalRun`，使 owner 下拉、工程 Run 和详情共同选择同一 Run。既有代际、实例、工作区、连接及迟到响应门保留；没有新增 API、executor 或 Grant。v2 逐次输入与 JSON/Markdown 下载本来存在，本次新增的是连续实际页面资格及上述反向导航修复。v1 仍严格 STALE，未为历史人工合同放宽版本门。

## 实际资格与字节桥

作者原件位于 `/workspace/natural-result-navigation-evidence-20261018`。最终 actual-complete 的原 JUnit 为 1 PASS，testcase 408.606 秒，外层执行回执 411.106 秒；页面 93 checks、29 actions、72 API、54 资产响应、2 boots、4 个真实 Blob 下载；页面实际 HTTP 126，含 fixture 的原 HTTP 响应共 160。原 synthetic 在 `8f76e09b11e21c728b0bc09a6d07bcacb4a82967` 为 1 PASS、36 checks，JUnit testcase 8.012 秒（pytest suite 8.13 秒）；仅为合成 GET/renderer stubs，无实际 HTTP/Worker 资格。其选中 Python 函数 AST、CJS、durable helper 和实际使用的 index/四脚本依赖逐字桥接至 ba6e，不重复执行。

因此为 2 个唯一最终节点分批通过，5 次执行中 2 PASS、3 历史 FAIL，不能称全程一次全绿。最终 actual 的 Mock 为 generation3 + source1 + PB-v1 1 + page PB-v2 1 = 6；三个业务 Worker 各单次调用、单 CLAIMED、SUCCEEDED，页面 Worker 1，真实模型 0。三轮实际共 17 Mock（5+6+6）、8 业务 Worker、3 generation Worker；失败轮不被抹去。当前实际参数是 P-B；本轮没有实际 P-A 页面验收。

三轮实际的各自 687 执行输入/133 生产前后均零漂移。c068→8f 只有两夹具变，8f→ba 只有本次 actual Python oracle 变，133 生产及 actual CJS 均逐字不变。最终 `source-before.json` 被正常 phase='source' 的 Run header 覆盖，原件保留，不能当源清单；独立以执行前 687 项 `inputs-final-source.json` 为权威，核对 `source-after.json` 的完整 141 项子集及当前 ba6e 字节，全部相同。测试内存 before/after 等值断言亦在最终 testcase 中通过。

## 对实际原件的独立复算

`final-pure-artifact-audit.py/.json/.stdout/.stderr` 为可复核纯文件审计，修正后 exit0、stderr 0 字节；JSON 索引核对时 1572 个非 DB 原件的完整字节/哈希，不查询 DB。复算包括：

- 160 组 HTTP 原请求与响应文件的字节数/SHA；126 页面桥接回执与 72 页面 API 记录逐 RPC 对齐。页面仅两个 POST：一次 review、一次显式 consented run；双击没有产生第二个 Run，页面无 owner PREPARE/DECIDE POST。
- 两个 boot 各 27 个资产路径精确集合；全部 54 次响应的 status/bytes/SHA 与冻结生产文件一致。
- 四个 Blob 的落盘字节、hex、长度、SHA、MIME、Run/版本/同 app-instance-release、各自独立 artifact GET 回执一致；JSON 为精确 canonical 原文，MD 与该次 artifact 的 markdown_view 逐字一致。v1 JSON 2092B SHA `623c64c24a66e175c04f1886fcbbd0a8fd5fb221a0d69dadd2329721400e95ae`；v1 MD 1373B SHA `63d47753f3b8195abb150de005d0c5a1ec13897099a3552263db370b9e5f59a4`；v2 JSON 2134B SHA `8eeebca49407515731bc86c86b9e3fc655f229d81e427f21a427d41f05ea6b36`；v2 MD 1415B SHA `d88209deb8cfbaa13fe2e237d44d4ebec08125a3ba4a391e0274726093b001ff`。
- 全表快照旧行保留，只有同实例 data_version 由1到2；独立当前 typed v2、1 artifact、3 个既定派生 READ Grant、4 VERIFIED operation/intent、1 local effect、1 VERIFIED attempt/reservation/heartbeat，未增加 SAVE Grant、app/runtime/release/instance。最终 rows 与 Worker 完成后快照逐字相同，6 个只读 checkpoint 均成功。
- 精确10条新增 journal 的 owner/scope/kind/key、5双 pair、request/snapshot FP；两个正文 archive 的15字段、scope、规范base64、长度/SHA、唯一 Attempt wire、实际 handler 请求内容、响应 canonical ASCII 保序 compact 编码及 NS_* 锚。全部14条新增事件都属于 v2 Run，未遗漏事件到其它 Run。
- 实际 owner 响应显示旧v1 metadata-only STALE/无 current/record，原 history 不变；v2 为 sequence0、空 history、PENDING 且绑定新 Goal。原v1 PREPARE是显式合成 fixture，不是页面人工验收；无 DECIDE，未证明人工语义通过或发布。
- 迟到边界是实际机器 Run1 GET200 的受控客户端投递；核对回执 SHA，切换后 v2 owner/详情不被覆盖，旧 owner GET 计数未增加。不是原生网络并发或永久取消的旧安装 digest 窗口。

## 历史失败与边界

首 actual c068 在8 checks后因夹具先 PREPARE 后保存 THIRD/Goal，新增4条既有材料权限改变全项目 grant_version，owner 正确返回 STALE；5 Mock、页面 Worker0，未到v2/下载。只将材料/Goal提前，原业务断言不降。首 synthetic 因旧stub缺 instance.release_fingerprint/精确Release响应而在32 checks失败；仅补匹配 metadata，36项断言保留。第二 actual 8f 在正常 v2成功及既有业务/旧行断言通过后，被测试误期望6条而实际既有6+正文双seal4=10条 journal 阻断；6 Mock，冷页下载未完成。只补精确 oracle，不改生产/CJS。

父级纯 artifact 初版将 response canonical SHA误用排序 fingerprint，以及汇总将被覆盖的 source-before 当manifest的 AssertionError，均保留原件/明确工具输出转录；修正遵循原合同。独立审查自身的 Path+str、早期计数断言、缺失 page-result 读取、猜测模块 rg、最终纯脚本多一个右括号 SyntaxError 均在本目录原件/说明保留；最后一项保留 first-syntax.py 和当时真实重定向 stdout/stderr，修正后运行成功。它们均非产品资格或产品失败。报告未将工具输出转录冒称当时已重定向原流。

旧关闭回执准确性只作新 addendum：新 CLOSE 的 full-source 前后核验与后续已关闭 key GET 的历史封存证明不同；不承诺每次 GET 重验完整来源或所有闭后版本漂移都锁定，该时序未执行。旧 sealed 目录未改。本轮未运行 close/recovery 旧矩阵、永久取消旧安装窗口、真实模型/语义场景、native/Windows、PostgreSQL、远端 CI 或部署；旧 exit139 因果仍 Unknown、原满盘独审原件缺证未补回。

本目录封存后停止全部写入。早期 PENDING 报告保留为时间序列，由本最终有限结论更新，不倒签早期状态。
