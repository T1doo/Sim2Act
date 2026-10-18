# 清单视图组合原件索引

合同及结论：[ManifestViewComposition20261018.md](../../F2/ManifestViewComposition20261018.md)。这是 text/table 实际功能，chart 明确未支持；不关闭完整 F2/真实语义或生产资格。

| 执行 | 原始结论 | 原件 |
| --- | --- | --- |
| 首次正常夹具＋页面 | 整例 FAIL/136.83秒；24页面检查通过，hold同步等待提前到期 | `/workspace/manifest-view-composition-20261018/command.json`、`pytest.stdout`、`actual-first/test_manifest_text_table_actua0/` |
| 同原DB/同3Run页面继续 | page-only 1PASS/122.76秒；46检查、50GET、54资产、2冷启动；55表全等、0Worker/模型/POST | `/workspace/manifest-view-composition-20261018/continuation/` |
| 非作者有限独审 | 源码＋闭合原件结论见独审报告；未另运行产品 | `/workspace/manifest-view-composition-review-20261018/` |

`executed-source/` 与 `executed-source-sha256.json` 分别标明两次执行的实际输入。首次产品 `internal.js` SHA-256 `fec807d475b3eca186fe6184f9cb84abe4df638d69dc1fcffaa0ff1bcd17c013`，`app.css` 为 `aa9764c29d45790bc4c253aff6230aa9775578a536fa3e865c88bc21ad4ca50a`，续验及最终产品字节相同。CJS同步修正单列；完整夹具测试修正后未重跑。`author-seal.json` 包含非DB原件清单，SQLite仅保留原本供此次继续使用，不把易变DB当封存副本。

独审中的 WIP 字节匹配观察器曾失败，原记录保留，属于纯观察器假设修正，不是产品或实际续验失败。Windows/原生浏览器/PG/远端CI/真实模型/真人语义均 NOT_RUN。之前证据和旧满盘缺失未被本片补签。
