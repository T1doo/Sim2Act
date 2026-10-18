# 四步文本报告与逐 Run 人工声明：交付证据

产品冻结 **`d7251b79d4dc17af6665f7a93eef8ffcfefa8603`**；测试与观察器提交 **`89c4d6ef9d223d99bd664311ed61d15943b96d7a`**。接续已有限独审的 `275455c6`，普通开发分支 `dev/text-workflow-result-owner-20261018`。统一目录中的既有四步文本应用现可在同一成功 Run 阅读两组完整原文引用及报告，明确 PREPARE、逐项填写理由和 DECIDE；新结果 PENDING，PARTIAL 无报告、不签收。没有新增 executor、Grant、业务 writer 或发布能力。

本轮 **13 个唯一用例分批通过**，不是最终 HEAD 一次完整全绿，也不是完整回归。精确用例、原失败及实际批次见 [资格清单](qualified-coverage.json)。

| 资格范围 | 唯一用例 | 原始证据 |
| --- | ---: | --- |
| 双输入同实例、精确 Goal／四回执／typed、逐项决定、冷 GET、防重、旧声明不迁移；PARTIAL、错账号／实例／家族、撤权及 Goal／来源／typed 变化 | 7 | [冻结轮 6P/1F](originals/author/frozen-backend-junit.xml)、[正例观察器修正后 1P](originals/author/qualified-positive-junit.xml)、[正例完整 HTTP](originals/author/qualified-positive-temp/test_actual_two_inputs_same_in0/text-owner-http.json)、[实际读回与保存合同](originals/author/qualified-positive-temp/test_actual_two_inputs_same_in0/text-owner-proof.json) |
| 实际 HTTP/JSDOM 目录→实例→新输入→正常 NoModel Worker→同 Run 报告→逐项声明；DECIDE 真接受后丢回执、原键只读恢复、防重、新 PENDING、PARTIAL 清旧 | 1 | [JUnit](originals/author/qualified-ui-junit.xml)、[46 项可见检查及页面请求](originals/author/qualified-ui-temp/test_visible_text_report_and_e0/page-result.json)、[真实数据库与 Run 交付](originals/author/qualified-ui-temp/test_visible_text_report_and_e0/actual-page-delivery.json)、[全部 HTTP](originals/author/qualified-ui-temp/test_visible_text_report_and_e0/http-trace.json)、[Worker 原件](originals/author/qualified-ui-temp/test_visible_text_report_and_e0/worker-log.json) |
| 实际迟到 HTTP 在工作区 ABA、Run 取消选择、实例、项目 ABA、同账号重连后的隔离；页面 Worker 0 次 | 1 | [22 项检查](originals/author/qualified-ui-temp/test_visible_text_report_and_e1/page-result.json)、[完整 HTTP](originals/author/qualified-ui-temp/test_visible_text_report_and_e1/http-trace.json)、[实际范围](originals/author/qualified-ui-temp/test_visible_text_report_and_e1/run-summary.json) |
| 受影响的旧自然 P-A/P-B、字面文本人工声明和 CSV 实际 JSDOM 声明 | 4 | [3P JUnit](originals/author/shared-regression-junit.xml)、[P-B 1P JUnit](originals/author/shared-pb-junit.xml) |

新流程的 3 次页面 Worker 运行产生 2 个成功报告与 1 个 PARTIAL；另有 1 次真实 fixture seed。导航场景只有 1 次 seed、页面 Worker 0 次。人工选择是合成 ACCEPT，来源与字面检查不能代替真实语义或用户签收。账号页面项实际是同账号重连；另一账号的拒绝由后端用例及 SQL 屏障覆盖。

非作者 [冻结独审](originals/independent/frozen-independent-review.md) 对精确源码有限通过，未发现剩余 P1/P2。独审亲跑的是短 SQL 控制流检查，Worker/UI 为作者实际执行、独审读取原件并复算；不混写为独审亲跑全部产品测试。独审发现的 WIP P1（旧自然端点借共享账本跨家族原 key／停止）及 P2（第一修正版只信 namespace）原源码、重现和修后拒绝原 SQL 均保留于 [过程报告](originals/independent/independent-review.md)。修后家族双 seal 门在账本和幂等短路前生效，不读取材料正文也不授予执行权限。

原 WIP 单 PARTIAL 为 1P；首轮新后端为 [5P/2F](originals/author/wip-backend-junit.xml)，分别误读 Goal POST 元数据和误判 UNSUPPORTED 的标准 HTTP400。冻结轮为 6P/1F，正例仍误读 Goal POST 层级；改为实际 GET 原 Goal 全文及保存历史／指纹后，唯一失败正例另行 1P。产品源码未因这些观察器修正改变，所有原日志、XML、HTTP 与合成数据库保留，没有改判旧失败。

[完整 Git 源码桥](originals/independent/freeze-source-integrity.json) 枚举全部 130 项生产文件，d725→89→封存前逐字节一致；[617 项源码／测试冻结清单](originals/author/qualified-source-sha256.json) 不代表执行了 617 个测试。UI 的 source-before/after 是 128 项生产文件＋2 项 UI 测试，前后零差异；不含两个软件资格 JSON，不能称 UI 期间监测了全部 130 项生产文件。两个 JSON 在完整 Git 当前字节桥中核对。[78 次实际页面资源观察](originals/author/qualified-page-assets.json) 均匹配冻结生产源。Ruff、定向 mypy、4 项 Node 语法检查通过；不是全仓静态检查。

所有 **139 件原始文件、33,138,842 字节** 按原字节保存，见 [manifest](raw-manifest.json)。[READABLE](READABLE.md) 直接链接全部 115 件 UTF-8 原件；较大文本另按原字节分块，拼接与 SHA-256 已验证。合成 DB 等二进制亦有独立原件和 [完整归档](raw-evidence.tar.gz)，归档 SHA-256 `0dd91d8f99a21decc7630be13a2e9336b1614eeaeb988671c4b9aef5c757f94c`，139 个成员均逐项校验，[证明](archive-proof.json)。pytest 的 current 便利软链接未充作原件，以上主链接均指向实体路径。

[普通分支源码推送回读](originals/author/source-delivery-verification.json) 记录的是封存证据前已推送的历史源码 HEAD 89，并明确不是最终证据提交的回执；最终封存 SHA 与实际远端一致性由交付消息给出。源码推送时远端共 152 个分支，仅新增本分支，其余分支不变。没有修改 main、强推、部署或改变 CI／凭据／权限配置。

未执行：Windows、原生浏览器、PostgreSQL、真实模型、真实材料语义／用户验收、远端 CI、部署、完整 P-A/P-B 或完整 T06。本轮共享自然应用兼容测试使用显式 mock，不是真实模型调用。旧满盘环境最后独审报告缺失没有补回；旧取消窗口 NOT_VERIFIED 保持原状态。
