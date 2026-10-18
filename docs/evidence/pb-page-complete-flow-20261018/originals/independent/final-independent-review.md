# 当前完整P-B正常链：最终非作者有限独审

结论：对冻结`491cd75b8600dc1794d6a153f68a9052af763bae`，未发现确定P1/P2阻断；本轮原连续P-B单例已实际通过，可以签收这一个当前源码的合成工程资格。没有新增生产功能或执行器，也不能把资格扩大成完整通用P-B、真实语义或正式发布。

父级root是唯一仓库写入者和本轮产品资格执行者。本人只做非作者源码、纯AST/字节、完成原件复算及最终合成DB的immutable只读metadata查询；零仓库写入、零产品测试/HTTP/Worker/模型执行。本人没有亲跑原页面资格。

## 精确源码与观察器

- 基线`f5d6cedb26fe549ad274951892a219c0b34b32b9`；491仅改原PB测试一项和两份F2文档。`freeze-byte-bridge.json`独立核对679项执行输入与inputs-before一致，132项生产文件逐字同f5和原生产冻结`cac7941062592df0a65783a9c147b06c22c7fd1b`。
- `observer-oracle-review.json`独立确认38条原Assert按词法顺序AST一致；原setup/ready/enqueue/Worker/transport/Store/TestClient/create_app调用序列及source_unchanged helper一致；第二导航测试AST和字节一致；原CJS字节一致，SHA256 `6065f9cfd1b5a4ec5031943419328ad94276ae5e26f0397a29ab8a21ad199ac6`。
- 详细审查见observer-source-review.md。观察器在setup前进入；外层总900秒覆盖前置fixture/Worker，Node timer仅操作本case持有的Popen。真正Node stderr仍是node.stderr；driver.log不能冒称Node stderr。失败finally不能吞异常成PASS。ready若未返回，局部生成wire未导出的限制明确保留。本轮未触发看门狗。
- inputs-after及本人结束时全部679项复算为0变化。最后HEAD仍491；父级在资格后修改两份公开F2文档，属于尚未提交的docs WIP，不能因此声称结束工作树clean。终态见terminal-status-readback.json，未发现生产或执行输入漂移。

## 实际通过范围与原始证据

原始目录：`/workspace/pb-page-complete-evidence-20261018/`。本轮只选原`test_successful_source_to_pb_directory_and_new_material`，未执行第二导航case或其它产品测试。

- full-pb.log：1 PASS，pytest整段298.97秒；full-pb.xml的唯一case为298.755秒。完整result/progress均PASS、Node exit0、errors空、watchdog false。
- 原页面63项检查、68次可见交互、3次冷启动；122个页面API响应和81个实际资产响应，加fixture源app/artifact两次读取及原授权撤销两次HTTP，共207个响应。本人逐个回读响应原字节，复算长度/SHA并与页面记录和当前资产匹配；完成纯复算原件清单460项，见completed-raw-evidence-audit.json及其实际stdout/stderr日志。
- 生成Mock3次，成功来源Worker Mock1次，新PB逐次Worker Mock1次；真实模型0。来源`run_3fdf4b5af9f84efab7c99f59d9d80914`和新PB `run_e00a977c00c34acb8bb8f1e0616928d3`均各1次真实claim并SUCCEEDED，原clock/fence/ownership oracle保留。最终DB还包含原ready创建的`run_576ea65eb70c4deeb72ef8b7ed018fde`，request_key=natural-generation、PARTIAL，且已由源app回执candidate.goal_application.run_id精确绑定；不是第三个成功业务Run。三Run各1个CLAIMED事件。
- 最终fixture.db SHA256 `091609cf7ab849ef60641aba47d68b1a7e75389222cda0892ac28fd87244a6e8`，本人以`mode=ro&immutable=1`读取前后字节完全一致；源实例和新PB实例各只有v1，task_extractions=1，natural_owner_records=0。

可见闭环具体为：实际成功来源→源成果授权读取→共享表单显式保存新材料和完整Goal→返回后重新审阅用户编辑图→明确提取；原实际201回执合成丢失后同页仅原keyGET恢复→独立明确Release ack和实例创建→返回统一目录→冷选择准确NATURAL_PB及实例→第三份材料/Goal保存及重新审阅/确认→独立新PB Run执行→第三材料结果读取及同Run人工入口→冷读→原例末尾当前源撤权后的fresh读取403并清私有内容。13个checkpoint和完整输入/结果绑定由原oracle保留。

人工入口只完成两次GET，均绑定同一新Run、第三材料、该Goal和result_version1，仍PENDING；owner POST=0，未实际提交人工决定或语义验收。新PB只有首次v1，没有其v1→v2保留资格。成功来源由原fixture生成和运行，不是此页面case从零可见UI创建来源。

来源保留的准确分母来自未改动的source_unchanged及原PASS：原app/Release/instance整行相等、原typed-v1结果行相等、原artifact资源整行相等、所有原Goal和Goal版本行保留。原grants逐行保留，唯一明确源read Grant按正常API撤销并revision+1。不能扩写为所有旧Run/AppRun/Attempt/events/全账本逐字保留；本人没有独立重建未导出的初始全快照。

## 自有取证错误与边界

首版纯observer把最终runs总数误设为2，在完成HTTP等复算后自拟DB分母断言失败。原脚本audit_completed_evidence.first.py和first-observer-failure.json保留；首次stderr只在工具返回中可见，保存文件明确标为原tool-output可见文本转录，不是假称当时已重定向的原日志。未额外重跑该失败脚本。依据原oracle和实际DB/源app回执改正为既有generation PARTIAL加两业务SUCCEEDED后，最终纯复算通过；没有改产品或业务测试断言。

另外保留一次只读schema探索误猜app_drafts.content列的observer错误，以及结束检查误要求父级正在编辑的公开docs也clean的AssertionError说明。它们均未执行产品、写DB或改变冻结输入。metadata-query-observer-error.json和terminal-status-readback.json明确采集来源与界限。

已有e039历史原完整PB63检查通过仍有效于其旧源码；本轮是491共享当前生产的fresh资格，不能声称PB此前从未通过。永久取消的旧精确安装digest并发对照窗口继续`CANCELLED_PERMANENTLY_UNVERIFIED`，未执行、改名或替代；当前原正常单页原key恢复没有第二actor、精确digest安装时序或修前/当前对照，不能补签它。

本例没有签收真实模型/真实场景或语义、native browser/Windows、PG、远端CI、部署或正式发布；既有额外只读性能探针exit139与产品的因果仍Unknown，本轮未重试它。旧满盘未落盘独审报告缺口也未补回。

后续真正可见功能候选仍是严格family/账号/项目/源Run范围的cold未知提取原意图发现与恢复：当前naturalTaskRequests、pbUsePending是页内Map，服务器by-key GET已有当前重新授权路径。该功能尚未实现或验收，不混入本轮，不等同永久取消的安装窗口。当前这一个原连续成功链的最新源码证据缺口已闭合。

父级告知491源码已普通推送新分支；本人未独立查询远端，不背书尚未发生的最终docs/证据推送。最终交付远端SHA和差异由父级实际推送后核对。

本目录最终manifest落盘后停止写入，供父级一次归档。无产品阻断遗留；以上范围限制和取消记录继续保留。
