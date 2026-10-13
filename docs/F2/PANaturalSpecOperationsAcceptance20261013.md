# 自然规范应用运行恢复与成果使用：有限工程验收

本轮完成 [使用合同](PANaturalSpecOperations20261013.md) 中的应用 → 内部实例 → 明确运行 → 原 key 仅读恢复 → 精确结果版本 → 当前授权读取清单与 JSON/Markdown 下载。V5 P-A 的应用使用与历史分开要求得到这一有限补充；自然规范 P-B 的成功任务来源提取仍缺独立入口，不能以 P-A 新材料绑定代替。

基线 `147a6da63ecb8fe15b9dea99d1ff8035f31122c3`；源码冻结 `bea218d546cd1578e5bf0450c9be9ad9b1667f4e`。核心提交 `07c2acc225f2011f7e502fa022e842cf00c18d6c`，资格提交 `aac2c409e1e1895493e50e6c35ad30d7c1489a39`，最终覆盖措辞修正为冻结 HEAD。交付追加文档与证据，src/tests/pyproject 不再修改。开发分支 `dev/pa-natural-operations-20261013`。

## 实际最终结果

|范围|PASS|FAIL / ERROR / SKIP|实际执行证据|
|---|---:|---|---|
|作者后端|128|0 / 0 / 0|[JUnit](../evidence/pa-natural-operations-20261013/author/frozen-backend.xml)，退出码 0，1952.44 秒|
|作者页面|14|0 / 0 / 0|[JUnit](../evidence/pa-natural-operations-20261013/author/frozen-ui.xml)，退出码 0，1558.44 秒|
|独立定向复验|39|0 / 0 / 0|[最终独审](../evidence/pa-natural-operations-20261013/independent/sol61-final/FINAL_REVIEW.md)，退出码 0，965.67 秒|

作者两轮无重叠，共 **142 个唯一用例**。独审 39 项全部与作者重叠，不相加为 181；[精确分母与源码桥](../evidence/pa-natural-operations-20261013/author/author-independent-final-bridge.json)重新解析各 JUnit。双方全部 436 个 src/tests/pyproject 文件在各 before/after、当前工作树及独审 snapshot 同字节。独审期间的暂停只暂停模型工作；既有测试继续运行，无重复启动或进程终止。

后端实际范围包括自然规范、旧标注规范、4 个事件边界、10 个原键/制品 API、22 个资格篡改用例、两个既有精确旧锚 continuation 及关联 bounded 授权路径。原键与制品 GET 的成功/拒绝用例逐表比较整个数据库，业务状态零写入；撤权/其他主体的保护屏障未触及私有内容。原接受事件、binding 或制品损坏继续拒绝，没有放宽既有 HTTP 错误合同。

页面实际范围为自然规范 10 场景、旧标注规范 3 场景、旧文本 1 场景，共 [393 个检查、520 次实际静态资源加载](../evidence/pa-natural-operations-20261013/author/final-ui-summary.json)，每场景 20 项 HTTP 资产源码 SHA。通过可见按钮完成确认、实例、冷材料运行、读取与下载；16 个 Blob 下载捕获了实际 UTF-8 内容。丢失回执只按原 key GET，运行提交恰好一次；错误回执/Markdown/迟到响应不能被采用。每次下载重新授权 GET，与该 typed 版本的 JSON 原字节、资源 ID/SHA、完整作用域、输出指纹及独立 Run Markdown 对照。浏览器为 JSDOM，API 为进程内 HTTP，数据库为实际 SQLite；不等同原生浏览器或操作系统文件下载验收。

## 授权读取顺序与失败历史

基线的 SPEC_STEP_VERIFIED 后先 replay receipts、SPEC_COMMITTED 后先完整 Run 读取，均已用真实 SQLite 值求值复现。原 r3 四项均在最终 GRANT_REVOKED 之前观察到 5 个保护字段求值；修复后的同四项观察为 0。每项都以 9 个非空 Attempt 字段校准，合成正文 sentinel 可被观察，lease/deadline 仍有效；没有成功 typed 制品。SQL 与原值观察在完整证据包，紧凑对照见 [实际观察记录](../evidence/pa-natural-operations-20261013/author/final-callback-observations.json)。

修复使 fresh commit_guard / job_scope_gate 位于上述保护内容读取之前；保留最终完整 verify_job、账本/审计指纹、原 lease/deadline、原子保存与回滚。撤权 monkeypatch 是同事务故障注入，另一组是控制时钟使 Grant 到期。生产 Store.event 只 INSERT，SQLite BEGIN IMMEDIATE 排斥外部写者；本轮没有证明真实外部并发攻击或 API 正文泄露。

[历史分类](../evidence/pa-natural-operations-20261013/author/preserved-history-classification.json)与原 XML/日志完整保留：最初两轮各 4 个夹具失败（冻结时间事件排序、观察器误挡 NULL CAS），r3 的 4 个真实顺序缺陷失败，API 首轮 4 个夹具类型/既有状态码断言失败；中间修复与页面初测单独列明。原 final-backend/final-ui 退出码 2，主动中断后修正“非空白片段覆盖”措辞；它们不计完整 PASS。独审初读全 py 74 文件的枚举误差保留，按既有排除 config.py 的合同重算 73 文件精确通过，没有扩大资格集合。

## 质量、保存与边界

全 src/sim2act 与本轮改动 Python 测试的 Ruff PASS；三份改动 JavaScript 的 node --check PASS；git diff --check PASS。mypy **FAIL 5**，均在与基线同字节的 status_report.py / tools.py 两文件，详细输出见 [质量记录](../evidence/pa-natural-operations-20261013/author/quality.json)；不声称全项目静态检查通过。

软件资格为既有精确 73 文件映射，pin `7f9c65c847842687a227f05a4e991901e68387b5343a771cc5c613318ce25543`；ANCHOR_HASH、CHANGED、两个原来源指纹与归一化算法不变。只重钉实际软件闭包，没有为未知旧软件或语义自动放行。

[完整证据](../evidence/pa-natural-operations-20261013/README.md)含作者/独审完整 tar、逐项 SHA manifest、全部包成员回读、原 DB/SQL/wire/页面记录、源码快照与暂停接续记录。归档前核对 protected origin 四分支与原 owner 工作区两份 WIP 内容/状态均未变；main/coredev 不修改。普通新分支推送与最终远端 SHA 核对另有工作区交付回执。

真实模型请求与费用 **0**，semantic **UNKNOWN**、owner **PENDING**、publication **false**。原键 pending 保存在本页内存，页面重开读取既有服务端历史；没有新增跨版本冷原键 journal 承诺。真实模型/费用资格、用户语义、完整 P-A/P-B、自然规范 P-B 提取、真实 owner/正式发布、PG、Windows、原生浏览器、完整旧库升级、远端 CI、部署均 **NOT_RUN** 或尚缺合同，不能由固定合成响应替代。两个额外 baseline expiry probes 未启动；不影响已复现的四例对照。

旧取消的精确安装窗口资格永久 **NOT_VERIFIED**，本轮未重做。[术语澄清](../evidence/pa-natural-operations-20261013/author/review-boundary-clarification.json)纠正封存独审中将其合并写为 NOT_RUN 的一句，原报告不改写、39 项分母不变。实际模型、推理级别、service tier / Fast 无工具回读，仍 NOT_VERIFIED；显式提交参数不等于实际运行状态证明。真实模型最小提案仍 [未执行](PANaturalSpecRealAcceptanceProposal20261013.md)。
