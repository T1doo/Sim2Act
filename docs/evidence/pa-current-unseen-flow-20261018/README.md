# P-A 当前完整页面：未见输入与一个错误输入

普通分支 `dev/pa-unseen-input-current-page-20261018`；上一交付基线 `304bff97584ac157d56597f5ab52ea7f5ecb1d9f`；实际执行冻结 **`fddccd09a72d628cdb0ea382009c84545a29cb9f`**。root是唯一仓库写入者，其他工作仅外部草稿/只读独审。约24GB可用、默认Git网络正常，原8fc祖先可见；没有访问旧满盘实例或旧bundle。

新增两个测试文件，**没有生产改动**。P-A既有使用/人工声明能力已存在，此轮取得当前统一目录到新输入v2的独立连续页面资格，没有新executor、Grant种类、发布开关，也没有重复下载或恢复矩阵。

## 实际结果

- **1唯一pytest节点、1执行、1PASS、0失败**；JUnit 283.170s、外层 285.657s。86是内部页面检查，71是操作；72页面API+54静态响应=126页面HTTP，另22 fixture HTTP，总148份原始响应。两个boot各27个实际资产逐字核对。
- 正常fixture通过原API/Worker生成single P-A与SOURCE v1；无fixture owner声明。页面实际打开统一目录NATURAL_PA、原实例，选择v1，机器Run、详情和人工合同一致。实际PREPARE201、逐项显式SIMULATED ACCEPT+理由、单独确认、DECIDE201，新增且核两条记录/两个seal。**这是合成选择，不是真人语义验收。**
- 页面正常选择已保存2049 ASCII字节TXT和其匹配Goal。预览实际POST400 INVALID_INPUT，显示实际错误、提交禁用；测试在该阶段实时全表比较并断言所有表完全不变；保存的checkpoint记录断言通过而非另存坏输入前后两份快照，结合已保存accepted/终态全表复核，新增Run/Grant/模型0。不是伪造响应，也没有跳过前端材料/Goal匹配。
- 改选未见THIRD及匹配Goal，明确预览200、另行确认，原per-use合同只产生一个202新Run。保持同app/runtime/Release/实例；正常冷Store Worker一次claim保存typed v2，手动刷新和owner选择始终对应同Run。
- 原v1 typed/artifact与原声明+seal原字节保持。旧声明当前STALE、原DECIDE历史ACCEPTED仍保留；v2 seq0/PENDING且不继承声明。关闭整个DOM、从目录重开原实例，两个版本各一次新的授权artifact GET，SOURCE/THIRD及各自Goal/Run/版本/hash均匹配；冷页全库不变。**下载0、故障注入0**。
- 实测5 Mock：generation3、v1 1、v2 1；2业务Worker各单claim（页面1），另generation Worker1。真实模型请求0。queue6/complete10既有journal、4 operations与4intents、1effect/attempt/reservation和3项READ受精确原合同约束；无新SAVE Grant/app/runtime/Release/实例。未改时钟/lease/预算/状态。
- 页面5个POST依次为PREPARE201、DECIDE201、错误review400、正确review200、use202。689执行输入/133生产全量前后0漂移，141直接执行源映射逐字一致；生产逐字等于304b。

## 原件与复现

[执行命令、冻结SHA、退出码及时间](originals/author/execution.json)、[原始pytest stdout](originals/author/actual.stdout)、[stderr](originals/author/actual.stderr)、[JUnit](originals/author/actual-junit.xml)、[实际摘要](originals/author/qualification-summary.json)、[独立有限复核](originals/independent/final-independent-review.md)、[独审封存清单](originals/independent/sealed-manifest.json)。

[逐请求/响应、Worker、wire、7阶段断言、已保存全表与finally等原件索引](READABLE.md)；[完整原件包](raw-evidence.tar.gz)、[原始字节清单](raw-manifest.json)、[包统计与SHA256](package-summary.json)、[全部交付文件SHA256](SHA256SUMS)。大UTF8原件另有无损byte分段，二进制SQLite来自全新合成夹具并保留原始bytes；不依赖旧环境bundle。

复现使用 Python3.12.14、Node24.19.0/JSDOM30.1.2，正常Mock与SQLite。命令原件中唯一节点为 `tests/test_pa_unseen_input_ui.py::test_pa_saved_unseen_input_after_explicit_simulated_owner_acceptance`。Node路径用 `scripts/engineering-ci/node_modules`，执行前后源映射与工具脚本均保存；独审只读取闭合原件，不重跑产品。

## 保留边界

仅单个合成主体/项目、single有限配方；不等同双主体真实授权、完整P-A、真实人工/材料语义或R0。JSDOM经实际TestClient HTTP，非Windows/native浏览器；PG、真实模型、远端CI与部署未执行。上一304b的v1/PREPARE仅fixture、无DECIDE，93/36是内部检查且只有2唯一节点；本轮不回改其事实。

旧取消安装digest窗口永久NOT_VERIFIED且未重试；exit139原因UNKNOWN，旧满盘独审未落盘缺口NOT_RECOVERED。下一候选是既有P-B首次局部逻辑修改的完整页面环，后台/修改版per-use已有历史通过，不把它误报为新缺失功能。整体真实环境门需要另有授权与Windows/真实模型及人工语义/PG条件，本轮不跨越。

源提交已普通非强推；最终文档提交SHA及全远端/零未提交未推送证明另见最终交付报告，避免在自身内容中构造自引用SHA。
