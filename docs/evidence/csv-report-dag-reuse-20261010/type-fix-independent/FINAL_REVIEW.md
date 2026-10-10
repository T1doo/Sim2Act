# LIMITED_PASS — 两处严格typed指纹绑定增量

精确新冻结 `50b10417a99a070f6bcd614471cc00ec102b7836`。只读产品及refs，用本人独立CRLF/负数/中文CSV在私有SQLite新建材料与完成来源；没有PG、CI、真实模型或仓库写入，不重跑原12后端/5页面矩阵。来源/fixture创建和oracle由本人common/verify实现，非作者新四用例测试体。

最终6个场景/38个检查PASS，11.8755秒（不含冻结准备）；oldv1、report版各7检查正常新列运行+冷新Store。独立Decimal quantity=4；typed精确5字段/count整数2/source实际SHA；旧v1两Operation/aggregate sink，新版三Operation/完整文字report sink；model0/businesswrite1，冷读取全DB零写，冻结schema真实正例通过。

四个攻击为v1/report×row-only/joint，在各自正常新fixture的独立SQLite副本进行。row.count改2.0、recordFP与Run.result.instance_result.recordFP同改；joint另把AppRun.output.count改2.0，row-only保AppRun整数2。实际Operation/回执未改，冻结typed schema拒绝浮点值。每例公开instance、instance/run、DAG/run GET均409 VERSION_CONFLICT（共12个拒绝），全DB零写。原5588两个同攻击返回200的BLOCK证据保持，没有覆盖原件。

静态和Git字节核仅adapter ledger_result的两处Pythondict==改成完整JSON fingerprint相等，另一变更为作者测试文件。365文件before/after与Git/worktree及作者freeze精确相等；其余363文件和68产品逐字节同5588。JS/worker/compiler/授权/lifecycle/DB无增量改变，故本轮沿用上一LIMITED61中相同字节组件的限定结论，不伪称新源码重跑全部UI/API/native。

双FP足够绑定本适配器现有exact CSV五字段schema：原receipts先逐输出schema验证并用真实CSV独立重算完整aggregate tuple，report版还核完整report sink=render(tuple)。ar.output FP需等于该真实tuple FP，record.data FP再需等于{result:ar.output} FP，同时原rowFP/lineage门保留。传递使row和AR类型、字段和值都等于已验证真实tuple，2与2.0、bool/int不能被Python数值相等掩盖；只改AR比较会漏row-only，新修确实同时覆盖两处。没有新增DBschema读取、缓存或权力范围，不推导通用非DAG lifecycle的所有类型问题已解决。

初版自编脚本在首个正例已完成cold检查后NameError（忘导入validate_value），不是产品失败。原脚本/日志与初版私有SQLite原件保留，补导入后六场景一次PASS；未删失败或以作者用例代签。

本轮限定签收typed漏洞修复，5588BLOCK本身仍是旧source真实失败记录。未独立PG/native/真实浏览器视觉/完整oldf13数据库升级/全量；作者证据另记归属。历史Reportidle6/PGFuture10 OPEN、HTTP200其他入口限制、完整端到端900最低充足预算UNKNOWN、PROJECT PENDING/BLOCKED_PARTIAL、semantic UNKNOWN、owner PENDING、整体NOT_ACCEPTED及LIVE0不变。

白名单包含自编脚本、原失败、更正运行日志、4份完整实际拒绝body与冻结schema、2正常原始输出、有限DB JSON及前后source hashes；私有SQLite二进制和缓存不复制。
