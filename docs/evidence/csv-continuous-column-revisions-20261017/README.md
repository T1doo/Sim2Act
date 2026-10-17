# 当前有效 Release 的连续 CSV 列修订

在“使用已保存的本地应用”选择已采用 v2 的原实例，点击“基于当前版本再次修订列”，即可读取已验证有效规格、查看固定旧列 quantity、明确提交新列 amount，经过原独立 CHECK、Release 批准和 CAS，交付同实例 v3 新 Run 的合计30与独立人工 PENDING。原 v1 的30及人工声明、v2 的5、旧 Run/Release/合同/来源均保留。CHECK 实例仍不能用作业务修订或新业务实例。

同目标改列不 PUT Goal、不制造新目标版本。可选的“编辑 Goal”使用原编辑器，只有明确保存下一版本后才采用该版本；材料仍须与父版一致。

| 冻结维度 | 已采用父版 | 同目标修订 | 明确编辑下一 Goal |
| --- | --- | --- | --- |
| 有效应用规格/动作/绑定版本 | 2 | 3 | 3 |
| Goal 版本 | 2 | 2 | 3 |
| Release | 原 v2 id/fingerprint | 新 id，冻结 v2 父链 | 新 id，冻结 v2 父链 |
| 原业务实例 CAS revision | 2 | 3 | 3 |
| data_version | 2 | 采用时仍2，新 Run 后3 | 采用时仍2，新 Run 后3 |

新合同 `csv-column-revision.v2` 从验证后的父 Release 有效规格构建，不从保留的根 v1 draft 重造；根 draft、generation 及旧合同算法不改。继续复用原 Worker、CSV executor、CHECK/oracle、批准和 CAS；没有新增 executor、Grant、Principal、权限、付费资源或部署。父证明缓存只限同事务/写序号，命中仍重鉴权并核来源字节。

旧软件保存的图锚会因软件指纹变化而失效。明确读取基线时先 GET 当前图，200 不 derive；仅确切的 `VERSION_CONFLICT / Current graph baseline changed; explicitly derive a new anchor` 才使用原 derive。新只读 `derive-requests/{key}` 在当前授权检查后核对原请求及完整当前图回执；丢失201后保留原键，只 GET 恢复，其他403/409不触发重建。

## 精确来源与验收

基线 `ce3fa86677cdaa58e076cc03e15a9b5414fd1e77`；连续合同提交 `d74f2fed55b6067e5d3c34ca6e4348b92e75f48a`；升级恢复修复 `b589809375c89b4d93617d91c780a1e0f7f704e2`。`8fc70cc43a6ac81cd522249e8a3d367cd66c9238` 为祖先。

| 实际来源 | 范围 | 实际结果 |
| --- | --- | --- |
| d74 作者 | 原21项 API/完整页面/旧实际 HTTP/持久结果回归 | 21 PASS，662输入前后不变 |
| d74 独立合同测试 | 新2正例+5负例 | 7 PASS，660输入与 Git 前后相同 |
| d74 独立页面 | 同 Goal、明确 Goal3、导航隔离 | 3 PASS，648输入与 Git 前后相同 |
| b589 作者升级页 | 合成 prior registry、真实409、derive201丢回执、三阶段确认离返、完整新 Run | 1 PASS；660选定输入前后不变并全部匹配 b589 Git |
| b589 作者旧页面 | v1→v2交付、CHECK丢回执、CAS丢回执 | 3 PASS，663输入前后不变 |
| b589 独立升级 | 原键 GET/缺键/撤权屏障与完整升级页面 | 2 PASS，661输入与 Git 前后相同 |
| b589 独立另两页 | 明确 Goal3全链、账号/项目/实例迟到隔离 | 2 PASS，661输入与 Git 前后相同 |

正式分批共 **39 PASS、0 FAIL、0 SKIP，32个唯一测试 id**；其中 d74 是31次/31唯一，b589 是8次/7唯一。没有声称在最终 SHA 单批跑完32项。b589 作者升级页在候选快照上先执行，随后660输入逐字节匹配该 Git 提交；独立升级页从已冻结 Git 构建。导航隔离 case 保留 Goal2，仅接受 CHECK 并核迟到隔离，没有驱动该 CHECK 或交付 v3，也没有测试 ABA。

- [完整分批与逐用例结果](author-originals/coverage-summary.json)、[最终32项收集](author-originals/final-collection.log.gz)、[源代码连续性](author-originals/source-continuity.json)。旧 effective/calculate 及原图校验函数 AST 不变；Worker/tools/Store/contracts 文件字节不变；d74 到 b589 的连续修订后端文件字节不变。
- [d74 独立合同审查](independent-d74-api/final-review.md)、[证明](independent-d74-api/final-review-proof.json)、[d74 页面独审](independent-d74-pages/independent-review.md)。包含联合重签父链/绑定损坏、实际 CHECK 后 Goal/权限漂移、真实新结果导致 CAS 冲突、旧成果逐行保留及零模型 attempts。
- [b589 独立升级及权限屏障](independent-b589-upgrade/README.md)、[另两页实际汇总](independent-b589-next-navigation/summary.json)。原键读取200、缺键409、撤权403均零写；正向 SQL control 看到私有 journal body，撤权后私有正文读取为0。
- 页面核对完整冻结 GET 对象、三次返回的新 GET 顺序与新勾选、每阶段防双击、真实 accepted 回执丢失后的原键 GET、精确 CAS 历史、当前账号/项目/实例隔离。新30与旧30通过不同 Run/AppRun/Release/result_version、typed row、冻结 Goal 和该新 Run 的人工 GET PENDING 区分。

开发 WIP 另有10次调用：8 PASS、2 FAIL，原日志/XML/数据库全部保留。两次失败分别是测试误期望普通 SOURCE 实例创建状态码（实际400）及把 inspect_job 的 id 误写成 run_id；当时尚未执行后续断言，未计正式通过。独立 d74 页面原件还保留首次审查脚本范围误断言及修正后的校验；产品测试未重跑。

## 原件与边界

343份原始文件、50份 SQLite 副本列于 [ORIGINALS.json](ORIGINALS.json)。数据库、日志/XML和大文件采用 gzip；编码前后 SHA256、原路径和长度均保留，全部解码后逐字节校验。[归档统计](archive-report.json)。保留原始请求/回执、完整页面输出、静态资源哈希、独审和失败原件；不含 snapshot、依赖或缓存，源码从精确 Git 提交重建。

这是合成 CSV、SQLite、FastAPI TestClient、完整产品 DOM/JSDOM、原 NoModel Worker，以及旧 localhost 实际 HTTP 回归。JSDOM 不等于原生浏览器。升级页采用受控的 prior registry；另有本次已关闭旧 WIP 合成数据库副本的实际409→原derive201→context200 [探针](existing-wip-upgrade-probe/actual-http.json)。两者均不是实际 ce3 旧二进制升级，未接触用户真实数据或旧满盘实例。

未执行真实模型/真实语义或真实用户场景、Windows、PG、原生浏览器、远端 CI、部署、v3→v4/spec8 深链或额外故障矩阵。目标语义 UNKNOWN，人工声明 PENDING，内部未发布；规格上限8是实现边界，不冒充已实际跑到8。原旧满盘环境最后独审未落盘的历史缺口仍存在，没有声称补回。

`SHA256SUMS` 覆盖本目录除根清单自身外全部文件，包括嵌套校验清单。最终交付 SHA、远端一致性、原远端分支/main 与未提交/未推送差异以推送后 `/workspace/csv-continuous-column-evidence-20261017/final-delivery-verification.json` 为准；该含自身最终提交 SHA 的文件留在提交外，避免自引用。
