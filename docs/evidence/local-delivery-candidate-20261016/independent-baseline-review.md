# 可复现本地候选交付：基线只读合同核查

基线：986799d766e98744e29e038543299af13785ea36；分支 dev/local-delivery-candidate-20261016。初次核查工作区干净；可用磁盘约27GiB。根为唯一仓库写入者，本报告只写/tmp；未修改仓库、配置凭据、访问实际模型或运行重Worker/锁矩阵。

## 已有启动和构建能力

- scripts/manage.py:86 仅doctor/start/status/stop。start复用正常API工厂、独立Worker子进程，绑定127.0.0.1，已有进程记录+PID/create_time/完整argv校验；启动失败只终止本次保留子进程句柄。日志与processes.json保存到显式data_dir。
- Start.ps1/Common.ps1显式读取所选配置文件；Python Settings.from_env不读取.env或自动查找凭据。Setup.ps1锁定Python3.12依赖，显式InitializeDatabase才迁移；日常runtime使用独立CRUD应用角色。CLI migrate/init-user仍需显式操作者动作，API/Worker不隐式迁移。
- pyproject.toml已有setuptools wheel构建定义；包数据包含web/*及两份text software json。现有scripts没有固定commit、可复核allowlist、逐文件哈希的可分享候选包生成/验包入口。现有Windows安装文档仍标Win11原生未测，不得把Linux或合成分支当Windows签收。
- application_environment(src/sim2act/process_env.py:43)给子进程OS/TLS/proxy白名单及验证后的应用配置，mock不传modeltoken；不传owner/CI环境。新入口应复用该边界，不扩大父环境继承。

## 普通PostgreSQL与显式工程SQLite边界

- Settings.from_env(config.py:31)只接受postgresql+psycopg://；Store(db.py:580)默认test_only=False，SQLite仅test_only=True允许。普通API/Worker不能改为自动SQLite后备。
- API /api/capabilities 只读natural_spec_generation.availability在test_only、mock、!live_enabled、goal_planner_provider=intern-s2同时成立时给OFFLINE_TEST_ONLY，live_request_allowance恒0。
- 自然生成实际发送guard goal_applications.check_provider:583另核MockTransport，SPEC_GENERATIONS明确拒activation；per-use natural_spec_runtime.enabled:45另核同test_only/mock/notlive/provider/model/MockTransport。能力metadata本身不是授权，不能替代wire guard。
- scripts/natural_activation_demo.py是临时SQLite、公开合成身份、固定手写规划、两个冻结CSV只读目标。它不等于本次新的P-A/P-B生成/保存/实例/逐次执行产品流程；退出删除其自身临时合成数据。其他agent/protocol/first-use fixture也显式test_only、mock；部分依赖tests私有fixture/pytest/jsdom，不能未经区分直接作为普通安装入口。
- 新SQLite mock本地体验必须醒目标为工程夹具，显式启动、不读外部env凭据、不触既有数据库，只绑定loopback；所有模型响应为可见合成MockTransport，运行仍通过原API、Worker、权限和版本合同。不宣称真实语义、PG、Win11验收。

## 候选包隐私及可复核要求

.gitignore不足以当打包隐私边界：仓库已跟踪大量历史HTTP回执、合成身份/材料与raw证据。建议从固定commit读取明确allowlist：产品src、安装/启动所需scripts、锁文件、pyproject、模板配置和本次最小说明。默认不带.git、凭据配置（仅.env.example例外）、本地data_dir/DB/日志、历史证据/测试原件、venv、node_modules、编辑器缓存。候选manifest记录来源commit、每个条目相对路径+SHA256+大小及候选构建版本；验包检查缺失/多余/路径越界及逐文件hash，不自动执行文件。应验证包中命令可脱离原仓库位置/路径含空格工作；不能隐式依赖/workspace、tests、未打包文件或预装Node。

显式选择的输出目录不可位于源码内部或包含既有不明文件；不覆盖未知目标、不递归删除。验包不能把zip内路径直接join后提取，拒绝绝对路径/.. /重复项/symlink等非正常源条目。不应把完整Git归档（含已跟踪历史证据）称隐私过滤包。

## 真实模型最小要求：仅列要求，未配置或调用

自然P-A/P-B目前无可执行LIVE批准通路。api.py:519拒natural_spec.activation，check_provider拒SPEC_GENERATIONS activation，runtime.enabled只允许test-only mock；PANaturalSpecRealAcceptanceProposal20261013明确精确LIVE批准门、跨Run总账及零收费门尚未实现。交付候选应保持BLOCKED/真实请求额度0，不能写为只设token/LIVE开关即可运行，也不能用已有字面/CSV批准打开新家族。

通用已有Intern传输固定endpoint与intern-s2，请求需后端私有token与live_enabled，Settings有限预算上界为4请求、4工具、1修复、64000总tokens、1024输出tokens、300秒/Run，lease30；这些是平台上限，不是用户批准。后续真正申请必须绑定审查源码/提案hash、账户与唯一模型、所有者/项目/材料/Goal版本指纹、有限请求/工具/修复/token/时间/expiry、明确费用或可强制零收费证明，以及适用家族实现后的精确批准、扣额、撤销与未知结果停止门。token由所有者在授权的后端私有secret机制提供，不能入浏览器、包、聊天或报告；不探测token、模型清单或发送试请求。专用SIM2ACT_INTERN_TOKEN非空优先，空则INTERN_API_TOKEN别名；不启用自动dotenv/凭据发现。

## 执行证据边界与待审

本次只读静态核查，未运行新候选脚本（尚未冻结），未运行PG、Windows、真实模型或CI。后续必须对根提供的冻结SHA、实际文件清单及测试回执作最终独审。

保留前轮事实：安全总批45PASS/1FAIL；仅旧测试断言修正后定向2PASS；独立新模块9PASS。自然双Run最终均成功但未触发recovered分支；控制器真实SQLite BUSY探针证明恢复分支，旧F9自然WAITING时序未复现，不能声称全部锁问题已解决。本轮不重跑或改写这些历史证据。
