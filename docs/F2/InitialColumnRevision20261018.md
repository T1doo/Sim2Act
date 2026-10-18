# 首版应用保留 Goal、修改现有列绑定

基线 `b58584d101261bccbb43dce56b77f49fc5da0567`。原[分阶段计划 F2-T07/T08](../分阶段开发计划.md#4-f2两条生成路径与最小增量闭环)、[产品 §9.3](../平台产品设计.md#93-修改执行规则)要求可修改声明依赖、独立检查、精确版本批准及保留旧历史。

核查已有：`GoalOnlyRevision20261018.md`及`csv_goal_revisions.py`已覆盖新Goal保留列，`csv_column_revisions.py`已覆盖采用后保留Goal换列；`csv_material_revisions.py`只支持采用后的已有App授权新材料，旧测试明确预授App/B权限，普通空工程没有补该权限入口。`column_patches`只产归档草案，不生成Release或切换原实例。本片不新增Grant或绕过该材料授权缺口。

真实首用缺口：最初Goal v1/spec v1的应用即使只改同一授权CSV的列，也被Preview `goal_version>=2`、服务端 `original+1`和页面按钮条件强制先造下一Goal。空白合成工程的用户无法直接把amount绑定改为quantity并采用到原实例。

## 实现前合同

只补首版保留精确原Goal的列修改：当前已保存Goal仍等于原generation的card/version/snapshot/fingerprint时，允许明确不同数值列；影响请求仅ACTION，沿图扩大APP重验，未知PROJECT仍拒绝。原Goal+1路径保持原字段/计算/GOAL影响，旧冻结记录重构不新增字段。同Goal同列仍拒绝，不解释自然目标，不自动修订Goal或降低检查。

复用原preview双锚、CHECK隔离实例与原Worker、精确Release审批、原实例CAS及typed结果版本。无新executor、工具、Grant、DDL或发布。原草案/Goal/权限/材料/旧Release与结果不重写；同一原实例采用新规格后，明确新Run重算新列，owner独立PENDING、语义UNKNOWN。

最小验收从新的空白合成工程开始，经原页面建两列CSV（amount=10/20、quantity=7/8）和通用完整Goal v1、候选/内部Release/实例，旧Run30；不PUT Goal，页面明确amount→quantity，验证ACTION-only/稳定Goal，单个隔离CHECK真实执行15，分别确认新Release及同iid采用，再显式新Run得到15/v2；冷页读取旧30和新15/相应Release，原历史逐字保持。权限表前后相等，全部普通产品路径，不用fixture授App新材料权限；禁止真实模型。有限兼容检查保留既有Goal+1和no-op拒绝，不扩旧矩阵。

之前b585的两完整runner FAIL、分期PASS及提交核验脚本TypeError原件维持封存；本片是新的独立执行窗口，不将旧失败补成完整链重跑。Git远端/auth不重试，保留9个本地未推送提交；Win/PG/native/真实语义/CI未执行。

## 实际结果与使用

[空白工程上手步骤](BlankSyntheticWorkspaceQuickstart.md)现提供两列练习材料及原实例编辑入口。原Goal必须本来就适用所选列；工具求和成功不代表自然目标通过人工验收。

最终软件在新的空白合成工程完成整链 **PASS**：安装包实际页面20项检查/137请求；旧结果30/v1，Goal仍为原v1，ACTION-only预览，双击仅一次预览提交，单独CHECK PASS、保存Release、原iid采纳，再明确新Run得到15/v2并读取同Run人工入口PENDING。另一次服务进程冷重开页面9项检查/53个GET，精确回读旧30和新15及各自Release。3个任务均由同一原Worker执行、SUCCEEDED/fence1、3次CLAIMED、模型Attempt0。冷读55表仅heartbeats变化，54表逐字不变；原身份、Grant、材料、Goal、草案及历史保持。

本轮两个页面各有一个可选`/protocol/contracts` GET400（Evaluation asset unavailable）；因此全GET不表示全部HTTP成功。新建页面用时165.857秒，冷页43.512秒；完整窗口2026-10-18 21:21:40—21:25:28 UTC。JSDOM实际通过loopback加载安装后的原HTML/25脚本及CSS并触发原事件；未执行原生浏览器或视觉验收。

最终wheel 940967字节，SHA256 `7eb1c477f806a5f728201706e2951557afe74e6f10170e876f60f97088700cb4`。在checkout外的独立venv安装，显式复用既有锁定依赖目录；最终整链复用该精确已安装wheel/venv，并重新核对139包文件，没有再安装或下载依赖。143项执行输入及runner前后不变；之后仅补交付文档。不是干净机器依赖下载资格。

有限API验收2 PASS/6.64秒（外层9.317秒），覆盖本片预览/精确no-op与错误Goal指纹拒绝，以及已有Goal+1换列兼容；双拒绝55表全等，成功预览仅原journal两锚，另外54表保持。Ruff、两JS语法、两修改Python文件mypy及diff检查通过。API窗口早于启动器修复，CSV实现与最终字节相同；不累加或冒认旧矩阵已在最终包重跑。

## 失败保留与启动器修复

本片第一完整runner **FAIL**：旧30和CHECK PASS后，新版本批准已接受，后续读取未返回；Worker非正常退出，原异常类型未记录，首因UNKNOWN。其后原Worker.once诊断返回false，仅增加诊断心跳；没有复现原异常，不称修复证明。

第二完整runner **FAIL**：连接等待改为30秒后，新Release和采纳已接受，读取新Release仍中断；安全日志明确OperationalError/SQLITE_BUSY(5)，栈为Worker.once→heartbeat→Store.tx的BEGIN IMMEDIATE。30秒等待本身不足。启动器现仅在该合成入口的同进程API/Worker之间协调访问；原Worker、Store、租约、权限、审批及PG均未修改。诊断只输出异常类、SQLite数值码和有限文件名/函数/行号，不输出SQL或私有正文。该协调不认证取消时仍运行的sync线程、独立进程或所有竞争场景。

第三个同已采纳实例的接续runner **FAIL**：新软件改动启动器，而交付图冻结全包Python注册表。新Run被原版本边界409拒绝，精确回执NOT_ACCEPTED/ABSENT/TX_ROLLED_BACK；55表仅心跳变化、原2任务保持。脚本随后误读`/runs/null`得403，原件保留；现脚本先核对202和有效Run ID再轮询。三项注册定义与旧wheel完全一致，唯一差异为新启动器哈希，独审独立确认此拒绝正确。不重derive、不重签旧修订、不放松软件边界。

因此最终软件需要独立新空工程资格，上述完整PASS是**实际执行的新窗口**。它不回写之前三次失败，也不改写b585及更早两次runner失败、分期PASS、提交前observer TypeError或已封存原件。原满盘环境最后独审缺证仍NOT_RECOVERED。

[完整原始证据、封存与有限独审](../evidence/initial-column-revision-20261018/README.md)。未执行真实模型/语义/用户签收、Windows/native、PG或远端CI；真实账户材料仍SOURCE_MISSING。遵守既有远端/auth访问拒绝，本轮不重试远端、push或绕过；交付在普通本地开发分支，精确SHA及未推送差异由提交后记录固定。
