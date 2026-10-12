# 显式有限软件兼容接续：实际旧 SQLite / 当前 worker

root唯一产品/仓库作者；分支`dev/text-compatible-continuation-20261012`，从已推P2 `df5f422174c4eeea96e5dd16c141dc0a4b36b3e6`建立。[具体合同](../../F2/TextCompatibleContinuation20261012.md)不关闭完整F2/P-A/P-B、语义或原生平台验收。

## 已保存的真实起点

`tests/fixtures/text-legacy`保留精确233与a747软件实际创建的SQLite压缩库、数据库原字节SHA、完整软件map、普通fixture生成日志及info。旧233实际65-Python指纹为`7f464d1099210fe485bb08ef455267cadf9970d5d1a098b1d00253ee1ad0edee`；a747实际66-Python为`08334fd20f4b3187ca2d5350bff50ec8d24cff881c2f1abaad821bd692bf1d2a`。不是把当前AUTH重签成旧版；生成只执行已接纳Git软件的普通TestClient/helper/Worker，真实provider请求0。

旧233 worker实际typed v1；原instance创建回执data_version=0不代表当前DB版本。a747旧库另有该应用自有原生Goal、实际worker和SIMULATED ACCEPTED人工声明。两库原来源授权撤回、内容删除，另一个同应用实例仍未获软件续用许可。`before-current-api.json`记录P2软件冷读真实旧233的409与全旧行0变；静态Git差异未冒充升级。

合成测试在旧库原TTL内明确固定fixture时钟，生产时钟、TTL和原AUTH/Grant不延长。真实用户旧库、PG/Windows升级均NOT_RUN。

## 功能与冻结

一次从原不可变Release接续到当前精确软件。目标用户+app runtime当前授权在受保护候选、Goal、预检/批准/回执正文前核；每个保留结果完整复用原worker binding/frozen contract/Operation+Intent+receipt/Goal封印/oracle。新输入样例、软件、schema、candidate、revision/data/history、Goal/owner ledger、当前权限及预算冻结，300秒精确批准在提交与最后返回前重验。

新许可双seal、新不可变Release/索引、当前实例revision/history追加与消费批准同事务；旧typed/schema/Release refs/原AUTH/BIND/Goal/声明/其它对象行保留。普通preview/new instance/generic release/switch无法借归档读取执行；enqueue/resume/dispatch/结果提交和owner当前声明均核所选实例精确许可。旧声明STALE，新输入正常worker生成typed v2；不自动签收。

未知只原key GET，不自动重发POST。CANCEL晚提交拒绝，已提交后CANCEL有stopped=false的不可变回执；REVOKE停止软件执行而非撤回人工声明。冷项目索引只给安全停止元数据，target撤权后仍能明确停止，不读取保护正文。原key不能冒充其它操作；原失败与回执保留。

`r8-final-freeze.json`记录最终401个src/tests map `3bb07485d301ea8b01bd4e2b408e71b4789650934ebf8b1734dafc66ff08a32f`与pyproject SHA；本轮67-Python实际目标指纹`c0cdc4e98de6a043bb43f1b1d5b27d4b57f525164922fb65cf70173f3b1d2a93`。产品文件与测试前后核验分别保留，不能只靠一个Git HEAD假装未提交源码未变。`final-freeze.json`的393文件14be/316f是保留的中间候选，后因R8实际失败被取代，不作为最终源码签收。

R8独审在两个旧锚的克隆库中追加明确损坏的FAILED queue（原成功typed/data/history保持）实际复现预检/提交201后冷读409。修复将每个终态job的完整原binding/frozen contract/历史Goal、ReleaseIndex及身份范围核验并冻结；坏历史现在预检409且全库零写。另从精确旧Git实际API/正常NoModel Worker生成两份独立`233-failed/a747-failed`夹具，真实旧FAILED INVALID_INPUT/no typed正例通过；故障注入坏行不冒充合法旧Worker。

## 真实轮次，分母不合并

|轮次|实际结果|范围/限制|
|---|---|---|
|初实现 smoke|两次预检失败，随后smoke3/4完成worker v2|tuple返回解包错误修复；smoke1本地raw、第二次原工具输出在会话，未伪造新的本地原stderr|
|backend-first|19PASS / 23FAIL / 0SKIP，42项|自有Goal序列化产品错误、HTTP状态/限额字段测试错误；原log/XML保留|
|backend-second|42PASS / 0FAIL / 0SKIP|其后有新的授权门/停止功能修改，不能作为最终整源码签收|
|ui-first / second|各4FAIL|首轮fixture时钟；次轮实际handoff context被clearInternal清除，产品修复；逐输出保留|
|ui-third|4FAIL，Node过程12/14检查完成|SQL屏障新增规则在首checkout后安装，TEMP view缺失，不能把Node片段提升为整测试PASS|
|ui-fourth|4FAIL|屏障连接先dispose造成teardown失败及两并发页面状态读取问题；原错误保留|
|ui-debug|1PASS / 3deselected|只233-normal，未冒充完整4场景|
|ui-fifth|4PASS / 0FAIL / 0SKIP|两旧库×normal/lost commit，52并行assertions不是52测试；每例2boots、20资源/boot、普通冷worker、原来源私有单元0|
|root regression-first|114PASS / 2FAIL，主动SIGINT中止，exit2|仅116项完成，不能说全量；新冷读取顺序FAIL触发修复，不追认未执行节点|
|independent frozen old candidate|backend48PASS2FAIL，UI4PASS，custom6PASS4FAIL|custom中2真实私有投影FAIL、2HTTP400/409夹具错误。原f7e0275冻结失效，旧报告/源快照不覆盖|
|privacy-fixed|10PASS / 42deselected / 0FAIL|修复inspect_draft/supported_app/运行范围门、冷metadata停止；不是完整52重跑|
|independent new freeze|backend52PASS、actualUI4PASS、custom10PASS|各集合独立，不加总为一次root全量或语义验收；每页3boots×20实际HTTP资产，冷worker及停止另有证据|
|independent controlled UI|12PASS / 0FAIL / 0SKIP|只本地Promise/真实SHA/20源码资产；身份/连接/项目/工作区/编辑、late GET/ABA/错key/旧Release/当前错误；不是HTTP/worker/native|
|root regression-final，旧243节点|235PASS / 2FAIL / 6SKIP / 0ERROR|两旧页面驱动在异步读取未稳定时检查engineering.run=null；原log/XML保持，修复驱动等待SUCCEEDED及fetch/pending空闲，全部原断言及产品轮询不改|
|R8 terminal-fixed-first|6PASS / 52deselected / 0FAIL|两个真实旧FAILED夹具、损坏终态拒绝、job版本竞争；不加总为完整58|
|independent R8最终401冻结|80PASS / 0FAIL / 0ERROR / 0SKIP，80唯一节点|58后端+4实际HTTP/JSDOM/冷Worker+10独立SQL/后端+6独立页面+2损坏FAILED历史拒绝；五个实际进程exit0，旧72不累加|
|independent R8 controlled UI|12PASS / 0FAIL / 0SKIP|401文件和pyproject前后零差异；20完整资产、本地Promise/真实SHA；与80及作者249独立统计|
|root regression-r8-final，最终249节点|243PASS / 0FAIL / 0ERROR / 6SKIP|原进程738.40秒、原session21463恢复读取exit0；249个唯一JUnit节点，6PG前提SKIP，不是249全绿|

最终作者回归见`regression-r8-final.log/xml`；六项跳过为PG真实进程before/after commit崩溃恢复、pause/cancel无长锁、最小应用角色enqueue和内部生命周期应用角色。未取得PG设备/配置，均不能提升为PASS。断线期间曾明确标该249终态未知；同原环境恢复后读取已完成原结果，不新启动回归。401文件与pyproject恢复后仍零差异，原会话exit0和原log/XML SHA见`post-recovery-root-verification.json`。

最终80独审原报告、命令/退出码/log/XML、原21文件快照在`independent-r8-final/`；全部244份独审历史按原路径存于`independent-history/`，包括原R8两实际FAIL及夹具错误。最终受控12在`independent-controlled-r8/`；旧65份受控证据继续保持。`review-copy-manifest.json`记录391文件原路径、原SHA与保存路径，SQL压缩由独立lossless ledger映射，未把红文件改成绿。旧候选controlled12曾PASS，但全393后核遇作者后续修改，原AssertionError保留，不能倒签。

恢复后的独立只读[精确文件桥报告](post-recovery-independent/POST_RECOVERY_REVIEW.md)核401源/test、pyproject及20个代码/JSON/页面/配置快照与live全等，原80报告/101当前产物/244历史产物原SHA保持，并核作者249唯一JUnit和全部六项PG跳过。另一合同文档仅作历史快照；本次证据整理更新文档，不改已验代码或测试。`post-recovery-review-copy-manifest.json`保存该报告及七份核验产物的原SHA，`final-package-verification.json`再次核391份复制产物原字节（压缩SQL解压后核）、401文件和pyproject零差异。恢复后新增测试运行数为0。

## 验证边界与异常

改动Ruff通过；`ruff check src tests`10、`mypy src/sim2act`5为原基线错误，全部src 68文件含config。只查两改动Python时仍会报告依赖tools.py的2个既有注解错误，不能写该命令PASS。一次多余`ruff check .`遍历历史evidence/source archive，实际13843错误也留存；它不等于本轮产品src/tests基线或新问题数。

提交前索引逐blob核401个源/test与pyproject，402个SHA256全部对应已验冻结，见`final-index-verification.json`。全staged whitespace检查exit2，580条均在保留的pytest/ruff/独审原证据（原输出含行尾空白）；完整输出与分类保留于`staged-whitespace-raw.log`和`staged-whitespace-classification.json`，不清洗历史字节。限定产品、测试、配置及当前文档的相同检查实际exit0，未把全证据检查写成通过。

环境短暂断开原错误：`exec_command failed: CreateProcess { message: "Rejected(\"Failed to create unified exec process: exec-server transport disconnected\")" }`。独审和作者都暂停相应动作，没有换工具/环境或删锁；原saved环境一次只读pwd恢复，2026-10-12 14:26:03 UTC实核原HEADdf5、分支/工作区/默认Git网络，main/core/原CSV3e不变、无其它writer。连接故障不表述为auto-review权限解除。

后来相同transport再次断开，同原环境有界pwd仍失败，已停止环境操作并报告249终态未知、WIP未提交未推送。用户再次限定一次同原环境最小连接核实后，pwd实际exit0；核原HEAD/分支/WIP和401冻结、既存进程/原session/完整249结果，再整理证据。没有新建实例、删除锁、终止未知进程或重跑测试；两次完整原错误及恢复核实见`post-recovery-root-verification.json`。

既有精确候选安装竞态资格永久NOT_VERIFIED、CI Forbidden STOPPED，不重试、换名或补做。真实模型/付费API、凭据/安全权限配置、部署、main/core/force均未执行。真实用户语义、完整P-A/P-B/AT覆盖、PG/角色、Windows/native/设备崩溃/真实用户旧库、性能与远端CI均NOT_RUN。

SQL大文件采用lossless gzip，原bytes SHA与压缩SHA/字节数见`sql-compression-manifest*.json`；可解压逐字节核。失败文件、报告和源快照不改成通过，最终提交/远端核验单独记录。
