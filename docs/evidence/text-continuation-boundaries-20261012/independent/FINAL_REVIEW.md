# 终态边界追加独审：LIMITED PASS

本轮冻结候选实际完成 **112 个唯一 JUnit 节点：112 PASS / 0 FAIL / 0 ERROR / 0 SKIP**。三个进程均实际 exit 0。只读仓库，root 唯一写入者；探针、SQLite克隆及报告仅在本新 `/tmp` 目录。没有覆盖旧 b244/80/12 或失败证据。

| 本轮实际集合 | PASS | FAIL | SKIP | 实际 wall 秒 |
|---|---:|---:|---:|---:|
| 既有后端58＋新增边界42 | 100 | 0 | 0 | 106.202 |
| 原实际HTTP/JSDOM/NoModel页面 | 4 | 0 | 0 | 54.423 |
| 独立合成持久错误与真实单元屏障 | 8 | 0 | 0 | 10.046 |

准确命令、exit、耗时在 `*-exit.json`，原日志和JUnit分别为 `backend/ui/independent.log/.xml`；完整唯一节点及分类见 `final-nodes.json` 和 `final-summary.json`。不累加旧80、旧72、父291或其它轮次；父291未在本报告独立解析。

## 精确版本资格

测试前后410个 `src/tests` 文件SHA256零差异，完整 map **973918a69af80c30b19436f09519e25f09dbf581892cdf24a3db7b2d9e49ef04**；实际67Python（config除外）implementation **7bc662bb1483693e96edf916d2177ad51f246e0cbde7a50d943675d8c9ec852d**。pyproject **49f68cb7901e719cd014141c69e5fa9ea562f51e9b9c40acd122ace6f2085d81** 不变。实际 base HEAD **b244a24b607688af169cc08ac13c90f84b4a275a**，branch `dev/text-compatible-continuation-20261012`；这是未提交候选资格，不把base称为新修复的最终commit。

`source-before.json`、`source-after.json`、`parent-freeze-original.json`保存完整映射；实际审阅12份原字节在 `source-snapshot`，diff在 `source.diff`。相对原401：只改变生产 `text_continuations.py` 和旧库构造helper，新增42项边界模块和两旧锚各4个empty-terminal原生成文件；无删除。原58测试 `test_text_continuations.py`、原4页面 `test_text_continuation_ui.py` 及其CJS，与原401精确字节相同，断言与轮询未放宽。合同文档的审阅快照保存，但文档可由root更新，不充当代码冻结资格。

## 两个有限修复及实际证据

`text_continuations.py:294–317`先读所选实例AppRun最小metadata，核AppRun principal；完整terminal Run查询WHERE同时包含精确RunID、当前principal/project/runtime。每个终态仍使用原ReleaseIndex双seal、原完整 `load_binding(archival_software=old_fp)`、frozen contract与历史Goal，且核精确iid/Release/AppRun。错误绑定不凭读取后的Python比较来隔离foreign私有单元。

`text_continuations.py:318–335`逐项匹配 `app_jobs.inspect_job:342–350` 冷读的六种潜在结果条件：SUCCEEDED、AppRun output、AppRun result_version、Run.result、typed存在、任一VERIFIED operation。任一种都进入未改正文的 `text_run_checks.verify`，保留原oracle、Operation/Intent/receipt及typed完整校验。只有verify成功的AppRun入集合；typed run IDs必须唯一并与该集合双向相等。删除原逐typed后的无scope整行Run读取；纯FAILED/CANCELLED无结果终端仍核完整已接纳合同，不能免除binding验证。完整jobs/data/owner/Goal等原批准CAS和提交事务门保持。

新增42实际样本：两锚×prepare/commit×三个错误Run scope=12（真实SQLite观察私有cell0、HTTP409、全DB零写）；缺成功typed=4（真实成功原Worker和receipt保留，仅损坏typed/data_version，完整verifier被调用后409零写）；失败五种残留=20（output/result_version/result/typed/VERIFIED-op均进入完整verifier且拒绝，全部表零写）；真正未运行空实例=2；旧Git真实FAILED-only与QUEUED→CANCELLED无结果实例=4。后6个合法无结果端实际commit201、cold读取成功，无typed增加；不把故障注入行当成这些真实旧Worker夹具。36份原负例JSON/SQL/response在 `boundary-proofs`，正例原JUnit和原克隆库保留。

额外独立8项（两锚各4）：

- 三scope同时错误链接：使用真正deny型SQLite UDF屏障，故意直接读取foreign context的校准实际抛数据库错误；清空校准计数后产品preflight409，foreign保护单元求值0、全DB零写，并核实际整行Run SQL包含三scope条件。
- AppRun owner错误：在已成功prepare后仅改变所选AppRun principal，保护真实linked Run私有字段。commit409，linked Run保护单元求值0、全DB零写，验证最小metadata先门。
- 孤立typed：prepare后移除其AppRun/binding但保留真实成功Run/原typed。commit409、原typed不变、全DB零写，检查typed集合不能单向遗留。
- 真实旧FAILED仅把现存operation status改VERIFIED：其它输出仍空。prepare之后的late commit实际400拒绝（原oracle INVALID_INPUT），原typed不变、全DB零写。没有新增operation、重签旧对象或放宽原验证。

8份完整回执/SQL/校准证据在 `independent-proofs`。校准故意命中的private cell单独标记，产品计数均0，不能把校准当成产品FAIL或把观察型screen当作生产权限层。全部负例是获授权的本地SQLite克隆持久错误注入，不是已证明的真实攻击，更不是HTTP响应泄露；此前foreign 5cell是返回错误前SQLite求值问题，响应本已409。

## 冷页面与保留范围

原4页面实际TestClient HTTP↔IPC↔离线JSDOM，两个已接纳锚×正常/丢commit回包。合计60页面断言、12次boot、240当前静态资源SHA核对、4次真实冷NoModel Worker，每次新输入生成独立Run并追加精确v2、保留v1；旧owner签收不自动承接。原key冷恢复只GET，不再commit；target撤权后metadata仍可明确REVOKE。旧私有来源材料/Run及初始native Goal正文的实际单元屏障产品求值0。受权所选历史Run用于保留校验，与被禁止重读的原私有来源是不同集合。各JSON/请求/动作/静态资源/SQL/exit原记录在 `ui`。这些不是原生浏览器或socket测试。

## 原红例和失败历史保持

旧b244源80有限样本不覆盖本轮新两个缺口，不能把它当作当前7bc结果或完整历史安全证明。作者当前新证据目录原 `red.xml` 实际38节点36F2P（其中4个VERIFIED-operation唯一约束夹具失败），`red-operation-corrected.xml`修正夹具后4个真实FAIL；它们未覆写。`red-missing-typed-chain.json`两锚明确原c0源码preflight201→commit201→cold成功Run409，保留原成功Worker/receipt而移除typed；未重签旧对象。`old-empty-terminal-controls.xml`4真实无结果终态正控通过原字节保留。以上是已有作者红证据的只读核验，独审没有再执行旧源码或旧取消probe。

本轮前后903份既存证据文件散列一致，完整路径/hash在 `history-manifest.json`；原80 manifest中101文件及其history-manifest中244文件也逐项验证无差异。另唯一excluded文件为root当时仍在运行、正常追加的 `docs/evidence/text-continuation-boundaries-20261012/regression-final.log`，不是历史原产物变更。原旧轮真实失败/夹具失败、原断线错误和先前只读bridge都保持原字节；本轮无产品FAIL、夹具FAIL或新增transport错误。所有旧数不并入112。

## 边界和剩余事项

本有限独审范围无未解决实际FAIL。只证明精确已接纳233/a747合成旧SQLite、原AUTH TTL内固定fixture时钟、有限64历史合同及当前候选的这些样本；没有证明全部恶意同时重签/所有数据库故障组合，未改变生产TTL/Grant/权限/签章。人工语义与formal publication仍不因此通过。

PG、Windows、native browser/socket、真实或付费模型、真实客户旧库升级、人工语义、完整P-A/P-B、远端CI均NOT RUN；旧取消精确安装竞态/probe、已知拒绝浏览器路径及CI Forbidden未重试。没有部署/凭据/扩权/新环境/main/core/强推，未执行push。父291关联回归及普通开发分支提交/远端核验由root另行完成，不能从本报告推断其结果。
