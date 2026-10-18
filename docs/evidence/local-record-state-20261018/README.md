# 本地记录收集与版本化状态更新：有限工程证据

基线 `5322dfd7f8c6686be29c9989d2f02fb6f54cfc28`；分支 `dev/local-record-state-20261018`；最终产品与测试冻结 `d5eadc708ee2968bb574ec66e335c05451f66cf7`。后续证据提交不改变生产或测试输入。最初产品提交 `a38c33f7496dca3da079d59bab16f13b5c283d1e`，测试提交 `81ad223bf72fb6e15af03ef6aca87af70e9bf4f8`；a38→d5 仅本地 dict 注解和既有拒绝检查后的类型收窄 assert。合同见 [F2-T06 实施边界](../../F2/LocalRecordState20261018.md)。

页面从“应用 → 新建本地记录应用”保存固定表单，也可从统一使用目录打开已有应用。分别明确保存内部 Release、创建并选择实例；每次 CREATE 或 OPEN→DONE 都先预览、再单独确认写入，之后手动读取同一 Run、当前记录集合及不可变历史。服务端实际保存规范 JSON 事件并独立折叠当前状态，DONE 是业务状态。没有新 executor、写 Grant、Principal 或数据表；复用原 `artifact.save_text`，每次成功的两条派生成果读取 Grant 如实保留。

最终 d5 冻结分批执行：后端 **9 PASS / 46.15s**，页面 **3 PASS / 50.03s**。页面完整流程 62 个检查、3 次正常 NoModel Worker；导航 36 个检查、0 页面 Worker；真实撤权清正文 34 个检查、0 页面 Worker。后两场景各有 1 次实际夹具 Worker。页面为实际脚本/JSDOM及 ASGI HTTP，原回执丢失和迟到仅控制交付时机；不是原生浏览器。账号页面覆盖同账号重连；不同账号拒绝在后端实际 HTTP/SQL 屏障中验证。

旧共享入口首批只完成 CSV 实例和文本人工验收 **2 PASS**，随后旧 P-A 全生成页面长测在 **412.41s** 由根精确停止自有 pytest，记 **NOT_VERIFIED**；该项不计通过，也不换名重跑。原 Node 已自然退出，未碰未知进程。完整日志、XML 与 [精确停止记录](originals/author/shared-bounded-stop.json)保留；该 XML 另有匿名中断条目，不计产品用例。独审认为本次只改精确家族前置门，采用直接自然规范人工验收及完整 CSV 报告正例补足共享路径范围合理；后续两项分开留证，不宣称原批 4 项全绿。

后续直接共享回归 **2 PASS / 152.06s**，未重复首批已完成项。最终共 **16 个唯一定向用例通过**（9+3+2+2），另一个旧 P-A 页面中断未验证。[逐节点计数、场景与前后哈希](originals/author/final-qualified-summary.json)。这不是一次全套测试通过。

| 批次 | 实际结果 | 原件 |
| --- | --- | --- |
| 新后端 | 9 PASS | [日志](originals/author/backend-d5eadc70.log) / [JUnit](originals/author/backend-d5eadc70.xml) |
| 实际页面 | 3 PASS | [日志](originals/author/ui-d5eadc70.log) / [JUnit](originals/author/ui-d5eadc70.xml) |
| 首批旧共享 | 2 完成通过，批次中断 | [日志](originals/author/shared-d5eadc70.log) / [JUnit](originals/author/shared-d5eadc70.xml) |
| 有界直接共享 | 2 PASS | [日志](originals/author/shared-bounded-final.log) / [JUnit](originals/author/shared-bounded-final.xml) |
| 非作者独审 | 有限通过，未见剩余明确 P1/P2 | [后端/合同](originals/independent-backend/final-independent-review.md) / [页面](originals/independent-ui/final-ui-review.md) |

后端包括 A/B 两个稳定 ID 与 A→DONE，冷 Store/GET 独立投影及首事件保留、严格命令、预览零业务效果、原 key 冷恢复/精确幂等、两种版本冲突、账号/项目/实例/旧家族隔离、项目写/历史 JSON 读撤权屏障、撤权后仅元数据取消、真实 JSON helper 完成后注入异常全事务回滚。SQL 屏障精确允许两个标识投影，并记录底层 JSON 确实求值；不称“零 JSON 读取”。

独审发现并修复：原 key 成功恢复缺实际成果证明；实例/审批分类缺独立锚；失败路径整行读取私有 Run；读取失败后恢复正文残留。原 key 恢复现在走完整投影证明；分类交叉核对双 seal；失败只用元数据；页面失败统一清业务正文、保留原 key 和意图。独审范围、实际短 probe、字节桥与作者资格原件分别保留，不能把作者页面运行计作独立 UI 执行。

失败记录保留：最初 1 个实际闭环通过；加强状态断言误拒合法认领中间态的 8 FAIL/1 PASS；修后 7 PASS/2 FAIL（observer 错猜 OUTCOME_UNKNOWN HTTP409，实际 HTTP400，随后改为精确 code+status）；最终 d5 前的 9 PASS 和 2/3 页面 PASS 均按各自来源列明。mypy 首次 3 错误、最终 7 源文件通过。独立短 probe 首次 setup 错猜项目创建200、实际201，也保留。不是把所有历史批次相加，也不是一次全仓库全绿。

打包前纯原件校验首次把 pytest `current` 符号链接当作额外页面场景而断言失败，修为排除链接后核对 135 输入前后零差异、16 个唯一节点及 108 次实际资源载入 SHA。首次工具 stderr 未单独重定向；原脚本与明确标记的同条件失败再现日志保留，未将再现冒充原首次日志。

原件见 [可直接阅读的索引](READABLE.md)、[完整原件哈希/分段范围](raw-manifest.json)、[归档及数量](package-summary.json)、[原始归档](raw-evidence.tar.gz)。UTF-8 大文件按明确 byte offset 无损分段，同时保留完整原件；二进制 SQLite 都是合成夹具。归档成员与完整原件逐个 SHA-256 对应。

封存 **593 件原件 / 82,409,542 bytes**，其中 531 件 UTF-8、62 件合成数据库等二进制。归档 9,307,846 bytes，SHA-256 `47f3e6aeb9009469ecbb790a14762c3f3664edcf5b5b2dd4fd7a9b55c480e4b7`。这不是测试项数量。[源代码首次普通推送核对](originals/author/source-delivery-verification.json)只证明 d5 当时的远端状态，证据提交后的最终 HEAD 在交付时另查。

真实模型请求 **0**；新家族无模型 attempts/reservations。未执行 Windows、原生浏览器/设备、PG、远端 CI、真实语义/真实场景、部署或正式发布；不关闭完整 F2-T06、P-A/P-B 或 R0。旧满盘环境未落盘的最后独审没有补回；原取消窗口仍为 **NOT_VERIFIED**，未改名重试。没有访问、删除旧实例或依赖旧 bundle。
