# 自然规范应用局部逻辑与明确新内部版本（2026-10-13）

从已接受的 d30b6e10554f352a676f5bc1e2523b22512e6ece 接续，独立分支 dev/natural-spec-local-logic-20261013，root 为唯一产品写入者。依据 F2-T07 / AT-13，沿用原 V5 的稳定 ID、应变/保留集、未知依赖保守重验与人工锁冲突合同；此前项目级有限 CSV 修改保持其已验范围，不把 UNKNOWN 当成可安全项目修改。

## 有限合同

仅允许已保存、原始六步自然规范应用中 requirements → qualifiers 的 prior_items / prior_feedback 两输入和精确 depends_on 增删；READ、requirements、MERGE、引用 VERIFY、SAVE 五个 action 定义逐字节保留，所有 action ID / step ID 不变，qualifiers/action binding/manifest revision 变为 2。原 draft、Goal 和全部人工标准、材料、来源标记及历史保持。不是人工 correction 或新材料绑定，也不声称模型同时并发。语义 UNKNOWN、owner PENDING、正式发布 false。

只支持有完整原来源的六步自然规范 P-A/P-B 编译家族；本轮完整正向路径实际为 P-A。新逻辑版本只支持原来源默认运行，不支持 per-use、新版本 correction、链式 patch、任意执行器或跨应用项目 UNKNOWN 修改。PROJECT unknown 在产品合同内拒绝；APP unknown 扩到整个应用检查，当前任何相关人工锁冲突保守拒绝，不解锁或覆盖。

流程是实例下 logic-patches/previews → 单独明确 checks 同意 → 隔离的原 Release 实例及正常 Worker 实跑 → 实际 readback PASS → 单独 version-approvals 同意 → 读取完整 snapshot / 原 Goal / 实际检查 → 新的明确内部 commit。检查本身不创建新 Release；新 Release 原 snapshot.draft 保留，以 natural_logic_source overlay 双 seal 封印原 preview、检查和完整执行摘要。原实例仍选旧 Release，原 data_version 不变；新版本须另建实例明确执行。

## 当前重验与恢复

事务冻结 project/principal、原实例版本、Release/app/draft/graph、Goal/source、精确批准、相关 READ/SAVE 及原预算；确认和 Worker 提交重查。使用既有正常执行器和确定性引用检查，不复制模型执行器。取消、撤权、Goal/版本竞争或新人工锁使迟到结果不提交，不留下成功 typed 或新版本。隔离实例、受理、binding、JOB 双 seal 与事件同事务，失败全回滚。

CHECKED 双 seal 只在实际六步完整 verify_job 后建立；最终版本确认再次完整 verify，后续读取每次重新核当前授权与原上下文及完整 immutable history digest。授权前四独立 artifact 指针和精确 typed scalar coverage 检查先于全文；缺 JOB/CHECKED 任一 seal、删 Release 来源、混源、foreign typed 或 proof 字节变化均拒绝。事务内同调用验证复用不形成跨事务缓存。

页面校验当前 graph 和 GoalCard、重建完整应变/保留集和精确有效 candidate，并以原 key check-controls 核实际检查指纹。版本批准读取完整正文后清空 ack，要求新确认。未知结果只按原 key GET，不自动重发；HTTP500不凭否定 proof 清 pending。迟到回执清理须 map.get(scope)===原 pending，对象门在异步 hash 后再次核对，保护同 scope 新意图。

## 验证与失败历史

最终产品源码冻结、测试计数、完整路径与控制器单列见终态 SUMMARY。Python 资格77文件，pin 18173c130264bf9cf137ba0eff74f3f316ce2e367cd092dc5c3347fd05c16072；仅 JS 最后修复后 Python pin 保持。每轮461个 src/tests/pyproject 文件前后映射与 HEAD 保留。原软件 anchor / CHANGED / config 排除不扩大。

保留真实失败：泛用图不支持自然模型、把 once() 当终态、SAVE 自产生 grant 导致全项目授权指纹变化、重复完整证明验证影响原时间预算、缺 JOB seal 的新版本降级、页面对外层自签名过度信任、HTTP500伪回滚清意图、同 scope 旧回执清新意图。已最小修复后重验。另保留夹具错误、页面尚未稳定时解析空 JSON及 semantic_status 字段位置误读，不改写历史为全绿；无预算/时钟/lease扩大。

所有模型回应均显式 httpx.MockTransport，真实/付费请求0。SQLite UDF屏障校准故意红阻挡1，仅证明所标 protected cell 未被非法求值；底层标量 JSON identifier读取单独记录，不能称所有底层 JSON 零读。

Ruff源码及新增测试、node语法通过；mypy仍有status_report.py3和tools.py2既有错误，78源文件检查，不称全绿。

NOT RUN：PG、Windows、原生浏览器、真实模型/费用、真实人工语义、完整 P-A/P-B、P-B完整局部逻辑路径、实际旧源码升级、来源退休、任意项目UNKNOWN、链式patch、远端CI、部署/发布。已知浏览器/CI拒绝路径未重试；产品UNSUPPORTED_CAPABILITY不属于工具拒绝。当前允许环境执行和默认网络正常，无当前工具批准阻塞。原main/coredev、旧PA/CSV分支及旧owner WIP保持。

## 终态范围与交付

产品源码冻结 `8cffbaa0c8cd28a9ee1b8a635ae18913aa07db10`（后端 core `761e8b874ba1e27b2f9ab33775ab2be0c6dca797`）。作者当前 **168 unique PASS / 1 SKIP / 0 未解决 FAIL或ERROR**：局部逻辑9、图/锁/列回归134、软件资格22、旧owner1、完整页面2。9例最终矩阵640.54秒，461文件前后零差异；包括两方向实际新版本执行、运行中取消/撤权/Goal/实例版本/人工锁五类失效，锁定应保留及原key/精确同意。SKIP为独立PG应用角色人工锁回归，未配置PG。

独审后端8188实际 **1复合PASS / 10 fault probes**，128.47秒；不是10个pytest节点。8188→8cff桥证明全部Python77/资格JSON同字节，461闭包只有internal.js两行变，未冒称重跑Worker。独立当前页面 **4 unique PASS / 26内部观察**，110.56秒，461前后零差异；与作者/后端pytest节点不重叠。合并终态 **173 unique PASS / 1 SKIP**，包含明确的后端同字节桥，不是一次全仓173节点clean run，也不增加旧候选的重复PASS。

完整当前HTTP/JSDOM可见路径两条：正常25检查/19手势/20资产，丢失检查回执→冷重开原实例→GET原key→实际检查→明确新版本→丢失commit回执→GET原批准/历史→新实例实际Worker29检查/28手势/两次boot40资产。合计 **54检查 / 47可见有效手势 / 60当前HTTP资产加载**；每次boot20资源，各路径实际check/future各两次合成模型回应。页面控制器4组单列，不增加完整路径。正常PATH源冻结轮的伴随冷PATH夹具FAIL已保留，精确实例选择修正后只重跑失败节点。冷路径新版本运行在原lease30、run300、至多3claims内SUCCEEDED（fence3），没有扩大预算或clock。

旧红例/夹具失败/中断、原始命令/XML/SQLite/HTTP资产、外部测试脚本、最终461源字节、独审封存报告、逐成员MANIFEST与终态SUMMARY均在[完整证据包](../evidence/natural-spec-local-logic-20261013/natural-spec-local-logic-evidence-20261013.tar.gz)。实际归档SHA/成员核验、完整交付Git SHA与远端、clean/ahead/behind、保护引用/旧WIP哈希见交付回执。交付提交只增加本文与归档，执行源仍为上述8cff冻结字节。

未另跑撤权后的新页面取消按钮完整路径、完整旧PA/PB correction/per-use相邻套件；本次没有升格这些声明。当前无工具批准阻塞。main/coredev和旧PA/CSV分支、旧owner未提交WIP不变；正常push不强推、不部署、不查询已知Forbidden CI路径。

归档 SHA256 `8f07be296d2b344c1738efced5505df373dd46ad5cb9033495df1ed65045c057`，5954 个 regular 成员、275528837 原始字节，逐成员 size/SHA256 回读通过；压缩包 30912109 字节。
