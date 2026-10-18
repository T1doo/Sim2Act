# 最终有限独立审查：当前 P-A 未见输入页面

有限通过，未发现阻断当前普通开发分支交付的 P1/P2。冻结为 `fddccd09a72d628cdb0ea382009c84545a29cb9f`，基线 `304bff97584ac157d56597f5ab52ea7f5ecb1d9f`。本审查者非测试作者；仅只读源码、Git字节和关闭后的原始文件，执行标准库纯文件复算，未运行产品、HTTP、Worker、模型、SQL或打开数据库。未写仓库或任一旧sealed目录。

本轮生产 **0变化**，两个新增测试精确对应预审稿：Python SHA256 `8f642cb517e4f3f362135741c77171d99682f28c941db4f69fd9343aa7937041`，CJS SHA256 `d220ad72ff1a0d73cf72a7de40c99ccbb7e50eb699693fa83d39d8af72f807b2`。133生产与304b/Git冻结/current逐字一致；689执行输入前后零漂移，直接source-before/source-after均为完整141项清单且逐字相同，未出现前轮source命名碰撞。已有P-A per-use/人工声明/回读能力不被称为新造；本轮增加的是当前统一目录中v1显式声明→一项错误输入→未见THIRD同实例v2→冷页两版本和同Run人工导航的连续实际资格。

## 实际执行范围

原件根 `/workspace/pa-current-unseen-flow-evidence-20261018`。`actual-junit.xml` **1个唯一pytest、1次执行、1PASS、0FAIL/ERROR**；case为 `test_pa_saved_unseen_input_after_explicit_simulated_owner_acceptance`，JUnit 283.170秒，`execution.json`外层285.657秒，900秒有界命令exit0。页面86 checks、71 actions，**不是86个pytest**。72页面API+54资产响应=126页面实际HTTP；含fixture共148响应，2 boots各27个实际当前资产。页面5 POST精确为：PREPARE、DECIDE、一个2049B错误review、一个THIRD正确review、一次明确consented v2 Run；未新增其他写入路径。

模型均为显式MockTransport：generation3、PA-v1 1、PA-v2 1，共 **5Mock**。single有限recipe，不是六步双模型。generation Worker1，业务Worker2各一次调用、一次CLAIMED、SUCCEEDED，页面请求Worker1；原时钟/预算/lease未修改。模型wire仅使用新THIRD，旧SOURCE/错误BAD未进入新Run模型输入。真实模型0。

## 原件独立核对

`final-pa-pure-artifact-audit.py/.json/.stdout/.stderr` 为可复核纯文件脚本；第一次运行即exit0，stderr空。核对时索引695个非DB原件的完整bytes/SHA，不查询DB。源码和预审桥另见 `fddccd-freeze-byte-bridge.json`、`pa-prequalification-review.json`。

- 对148组原HTTP request.body/response.body逐字核长度/SHA；126页面桥接记录与72页面API按RPC/方法/路径/状态/responseSHA对齐。54资产的精确路径集合、200、长度/SHA均与冻结文件一致。
- 页面真实PREPARE(sequence0)和DECIDE(sequence1)的POST201与返回账本、原请求fingerprint逐项一致。实际20项选项/理由均明确 `SIMULATED_TEST_ONLY`，独立核两条natural_owner_records和两条natural_owner_seals的scope、kind、status、序号、previous链、完整contract、payload/request/metadata指纹。除此两表，initial→accepted全表逐字不变。它是自动化合成声明，**不是真人语义验收**。
- 正常保存的2049 ASCII字节TXT有匹配Goal，原Goal快照/资料hash与实际错误review请求一致；真实响应为 **400 INVALID_INPUT**，提示2048 UTF8界限，页面显示同一错误并保持无review/ack/可执行提交。没有绕过前端伪造请求，也未把Goal不匹配的前端拦截当成服务器409。
- 7阶段 `checkpoints.json` 的实时全表断言均成功；保存的五份完整表快照为initial、accepted、queued、Worker-completed、final。**错误输入前后没有另外独立序列化两份快照**，不声称有7份完整原快照。该段零污染由最终PASS用例中实时 `snapshot==accepted_rows` 断言、actual400/原wire、checkpoint与终态仅THIRD增量交叉支持；本审查独立复算已保存快照。bad没有新Run/Grant/模型。
- 同app/runtime/Release/instance产生独立Run与typed v2；旧typed、artifact、Goal、Release和owner ledger逐字保留。允许表的旧行均保留，仅同实例data_version1→2。新增1typed、1artifact、3个既有协议派生READ、4VERIFIED operations/intents、1local effect、1VERIFIED attempt/reservation/heartbeat，无新SAVE Grant或app/runtime/Release/instance。
- queued6/completed10条journal的owner/scope/kind/key精确；新增两对正常offline正文archive及其base64/byte/SHA/Attempt wire/实际handler请求、保序ASCII compact响应canonical均一致。全部14条新增事件属于唯一v2 Run，两个NS_*原锚精确。最终全表等于Worker完成后快照，后续导航/读取无写入。
- 实际owner GET显示旧v1的ACCEPTED历史完整保留但当前为metadata-only STALE，无旧current/record/签收表单；v2为sequence0、空history、PENDING且绑定新Goal/THIRD，未继承旧接受。新旧机器成果仍PENDING/UNKNOWN/NOT_RUN、不发布。
- 冷新boot经统一目录重新选择同实例、分别选择v1/v2并各实际GET一次精确Run的spec-artifact。资源id/hash、输出fingerprint、canonicalJSON字节、原SOURCE与新THIRD内容及版本吻合；这些是**两次成果回读，没有执行下载**。无响应丢失、迟到回调、close/recovery或故障矩阵资格。

源推送原件 `source-publish-commands.json` 的10命令回执均exit0，`source-push.stderr`显示仅新普通分支 `dev/pa-unseen-input-current-page-20261018`，`source-head.stdout`为上述fdd完整SHA，scoped fetch后`source-left-right.stdout`为0/0。此处仅复核父级已保存回执，没有另作网络请求；后续docs/evidence提交、全部远端保护引用/最终clean范围仍由父级最终交付核对，不提前背书未来提交。

## 限制与保留边界

当前只覆盖一个合成账号/项目和P-A single的一条页面链，不是双主体真实授权、完整通用P-A或R0验收。本轮没有失败，不累加前轮PB的检查/模型或旧历史失败作为本轮计数。原方案要求的真实模型/语义/场景、真人验收、Windows/native、PostgreSQL、真实旧库升级、远端CI和部署仍未执行。永久取消旧安装窗口不重做；旧exit139根因Unknown与原满盘独审缺证不被本轮补签。

本目录保留较早的分诊候选与范围修订：初始六步/Goal-mismatch建议已由 `selected-pa-single-oversize-addendum.md` 明确替代；最终只有single+一个超界输入。所有较早PENDING记录按时间保留，由本终态有限结论更新，不倒签。旧 `next-user-flow-independent-20261018` 等sealed目录完全未改。封存后停止本目录全部写入。
