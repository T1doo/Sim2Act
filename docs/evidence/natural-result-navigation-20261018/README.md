# 自然规范同 Run 导航与 v1/v2 冷页下载

真实产品修改只有 `owner-review.js` 一行：自然 spec 人工 Run 下拉也复用既有 `showInternalRun`，机器详情与人工合同同步。原来合同可以指 B、详情仍 A 或为空。目录、逐次材料/Goal、同实例 v2 和 JSON/Markdown 下载已存在，本轮补此接线并取得当前完整页面资格；v2 是结果版本，同一 Release/实例不变。

实际完整执行源码 `ba6e1e06babdf591cbd439ee769b1c2a9cd0aa98`；生产一行首提交 `c068e165f7ac6bc38a5d474f26e7a99f8e0bac4c`。最终2个唯一 pytest 节点通过：

- [完整实际 HTTP/JSDOM](originals/author/actual-complete-junit.xml)：408.61秒，93项页面检查、29个交互、72个页面 API、54次资产响应、2次完整 boot、4次 Blob 下载。含fixture共160个实际HTTP响应，不是额外用例。
- [原合成导航](originals/author/synthetic-final-junit.xml)：36项、8.01秒，执行于 `8f76e09b11e21c728b0bc09a6d07bcacb4a82967`；选中Python函数/CJS/durable及全部5资产逐字桥接至最终源码。这是synthetic GET/renderer stub，无HTTP或Worker。

fixture正常生成3 Mock、来源Worker1 Mock、P-B v1 Worker1 Mock；预先正常保存THIRD/Goal，再以既有API PREPARE v1一次，无DECIDE，不能称页面创建v1或真人签收。页面从统一目录明确选择同app/iid，选择本次THIRD/Goal、预览、单独确认；双击仅1次Run POST，原key GET核回执，正常冷Store Worker1 Mock保存v2；手动刷新同Run。最终共6 Mock、3业务Worker各单claim，页面Worker1；未改时钟/lease/deadline。

验证原v1 typed/artifact/owner行不变，v2独立seq0/PENDING；v1当前人工门STALE metadata-only，下载保留原成果PENDING快照，历史签收不成为新结果的接受。一次实际Run1 GET200仅控制投递时序，切Run2后释放旧响应，机器/owner均保持Run2，无额外owner1 GET/POST；非实际网络并发。账号/项目/实例导航以36项合成探针覆盖，本轮actual只一合成账号/项目。

冷页4次下载各有新授权 `spec-artifact` GET，真实JSDOM Blob/FileReader UTF-8 bytes与原Run/AppRun/结果版本/材料/source/hash、JSON canonical及Markdown逐字一致，文件与索引见[实际页面原件](originals/author/actual-complete-tmp/test_same_pb_instance_navigate0/page-result.json)和[下载目录清单](originals/author/actual-complete-tmp/test_same_pb_instance_navigate0/page-result.json.downloads.json)。object URL受控，不是native OS下载验收。冷页与切换全库只读；页面仅review+run两POST，无owner写。新增1目标runtime READ、2产物READ均复用既有合同，无新Grant种类、SAVE授权、app/runtime/Release/iid。队列6条原metadata；完成另有4条既有OFFLINE请求/响应正文双封存，精确scope/key/pair、原bytes/SHA、Attempt与实际Mock wire匹配。

保留全部首轮失败：[synthetic 32项后缺Release模拟合同](originals/author/synthetic-junit.xml)；[actual c068先PREPARE后材料授权变更而STALE](originals/author/actual-junit.xml)；[actual 8f已保存v2但新oracle误期望6而实际10条journal](originals/author/actual-final-junit.xml)。只改两处fixture及精确封存oracle，生产/CJS不变；三次actual共Mock5+6+6=17、业务Worker2+3+3=8，另有3次generation Worker。5次pytest执行为2PASS/3FAIL，共2唯一节点，失败不改签。纯artifact初版canonical哈希断言错误和工具转录另存，依原ASCII保序合同修正；非额外产品用例。

三次actual各687完整执行输入/133生产前后0漂移；133生产在后两次修测试期间逐字相同。唯一新生产diff为owner一行。直接依赖的source-before文件名被正常来源Worker header复用；保留原件和首次纯汇总AssertionError，改以执行前外部687映射的141项投影逐字核source-after与冻结Git，未冒称补回被覆盖的文件。完整映射、JUnit、stdout/stderr、请求/响应原bytes、模型wire、Worker claim、全表快照、各阶段和finally都在[原件索引](READABLE.md)；[总资格](originals/author/qualification-summary.json)。[有限源码/原件独审](originals/independent/final-independent-review.md)与[新封存](originals/independent/sealed-manifest.json)不代表独立执行产品。

关闭GET旧过宽描述只收窄文档：CLOSE事务内完整来源重核，之后terminal GET核当前访问门与历史封存，不逐次重算完整来源指纹。闭后Goal/结果漂移时序未实测；永久关闭metadata不授权新提取。未改关闭行为或重跑关闭测试，旧sealed原件不改。

原件1616文件、50034836 bytes（1613 UTF-8/3二进制合成DB等）；[manifest](raw-manifest.json)、[原始压缩包](raw-evidence.tar.gz)，包SHA256 `028f739d60a8fad4a3ab91a077e68fe3d9f4a8f248aa07ccf245423df2fc380a`，6987828 bytes。原始bytes逐一比对压缩包及Git blob，大文本有无损分段。

Windows/native、PG、真实模型/语义/场景、远端CI和部署均未执行。旧exit139因果Unknown、永久取消安装digest窗口NOT_VERIFIED、旧满盘独审未落盘缺证均保持；未声称补回。普通dev分支推送，不改main/强推/权限/费用；此分支不触发现有仅dev/f1-foundation的push工作流。
