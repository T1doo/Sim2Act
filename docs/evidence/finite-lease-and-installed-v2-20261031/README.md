# 有界期限修复与新安装包的真实目标

最终应用源码 **1a23c032fdc5ac83b4caf3ba07ed06f8a9d7669e**，分支 `dev/cloud-g0-live-20261028`。这是可安装启动的Linux限制候选，未修改main或发布Release。之前已验`fc978… / 1ada93…`及`6424… / fdb820…`保留，旧包未覆盖。

## 最终实际包

[ZIP及完整身份](../../../deliverables/limited-text-candidate-final-20261031/README.md)。ZIP 3,187,872 B，SHA256 `b63d954d892023adafbdf062130ca23c5261cae38f6c108972c18988246f194e`；wheel `sim2act-0.1.0-cp312-cp312-linux_x86_64.whl`，SHA256 `7133424e80ae46513c046c393db30a66f4c1f85d5443192fbfb8e8dd4ba7fed2`。

原打包器只认2扩展，setup实际有4，已修完整库存并保留缺扩展拒绝、平台tag和Python-preview隔离。最终从干净Git blob以已有CC=cc离线构建，pip使用--no-index／--no-build-isolation／--no-deps。223项包库存／全部hash核对，四个.so实际导入并逐完整C/header/Python输入核内嵌source SHA。无运行时、依赖wheelhouse、数据库或私有配置混入。

wheel实际安装到全新venv；通过一行显式.pth复用已有锁定运行依赖，不是干净机器依赖下载验收。执行的是新venv `python -I -B`，cwd在scratch源码外，sys.path无原src；9个关键模块（包含本轮db／model_settlement／natural_spec_runtime）逐Git blob核路径和源码字节。默认CLI新工程／普通API的自由目标明确FAILED/UNSUPPORTED_CAPABILITY，0真实模型调用；两次实际SIGINT退出均exit0、STOPPED clean、双EOF，首次新进程同持久结果、同键同Run。普通CLI端口39661→59287，文档正确要求按本次READY URL进入，不冒称桌面稳定origin。原输出见default-cli。

## 一次真实模型到目标完成

2026-10-31 19:21:30 UTC开始，以本最终安装包的显式--exact-read-live入口执行。正常任务表单可选择的单文本逐字合同／API acceptance=exact-resource-read.v1，原固定intern-s2和书生endpoint／已有注入令牌。没有MockTransport、结果注入、付费fallback、修复重试或新凭据。

输入与前次格式失败**相同**：`Read the final installed text.`、`Keep its final newline.`两行，末尾保留换行。新Run `run_e0902c4478304069a23c36aeddf83bb8`。原授权resource.read实际执行一次；独立核请求、完整原文、回执、身份／用量／预算、当前授权及原提交边界后才保存SUCCEEDED/PASS_EXACT_READ_CONTRACT。

| 项目 | 实测 |
| --- | --- |
| 最终新请求 | 2，LIVE／RECEIVED、返回Intern-S2且原别名策略验证通过 |
| 请求1 | 2.532817秒；672输入＋59输出＝731 tokens |
| 请求2 | 2.717308秒；991输入＋17输出＝1008 tokens |
| 总已知用量 | 1739 tokens，仅上述2次 |
| 完整目标轮询时长 | 6.391454秒；不是大型Cold G0／写锁时间 |
| 首次新服务重开 | owned-stdin同origin34571、完整结果相等、原键无重放 |
| 两次关闭 | 原STOP协议／同worker／exit0／双EOF／clean，数据保留 |

Run控制版本2不冒称成果版本。whole_task_accepted仅此单文本合同；通用语义NOT_RUN、人工确认PENDING、正式发布false。实际driver、九模块SHA、命令、原响应及STDOUT/STDERR在accepted-v2。首次HTTP重开新结果之前，SQL仅检查既有历史保全行，没有提前用SQL读取新结果。新服务前后源码同1a23、Git干净。

独立标准库解压两份SQLite至临时immutable只读副本，integrity均ok、非空WAL不存在；原4个Run的Run/Attempt/Reservation/Event/Contract五表全字段未变。重算最后2次完整wire fp和保守字节预算，JSON解码结果与原文／末尾换行逐字同。见independent-archived-ledger-audit.json，0模型请求。

## 格式失败保留与前瞻修复

中间安装包源码2175eae7f077ccc3736306cf099657a559f1eacc的同文本真实验收失败：模型在最终JSON外加说明文字及Markdown围栏，原严格parser正确拒绝为FAILED/INVALID_INPUT。2次请求均RECEIVED、用量615＋927＝**1542 tokens已知**；1个原读取操作VERIFIED但不能冒充目标完成。正常停止，未重试，未执行首次重开。原FAILED状态／错误／响应和7预约时的数据库在rejected-v1及rejected-v1-workspace，没有改签成功。

新请求才使用exact-read-direct.v2：原系统提示后明确JSON-only、禁止说明／围栏、正确转义及末尾换行。它进入实际原消息、完整wire fp和保守预算；旧direct.v1／None保留原提示、原25／8秒及原键policy。严格parser不剥围栏、不清洗或补造答案；新格式错误分类为MODEL_OUTPUT_INVALID，旧失败不回写重分类。最多2请求、1只读、0修复；原25秒单请求仍受原lease／Run截止约束，没有扩大时限。前次失败后只在此已独审实质修复下执行一次新v2目标，没有反复换键试到通过。

本次打包工作实际共6次真实请求：6424旧包成功2次1477 tokens；2175格式失败2次1542；最终新包成功2次1739，总已知4758。它们与更早fc978成功2次1513及最早9d未知用量1次共享原工作区／quota subject；合计9预约／Attempt，8已知RECEIVED、1历史UNKNOWN，**未知用量没有当0或退款清除**。closed-ledger-summary记录此范围，不冒充整个项目所有历史调用总额。

## 旧30秒期限的实际缺口与修复

旧TrialCaps/非extended SQLite路径此前renew后没有finite tuple；实际writer尾检拿interval=None只看stop。原独立反例在原lease内进入Connection commit callback，等原lease结束后仍COMMITTED并持久sentinel，0模型。原程序、结果及synthetic.db.gz保留于original-tail-counterexample。这仅证明writer提交尾窗，未冒称完整Cold授权或性能。

修复将**原已提交heartbeat返回的真实lease**与node/run截止、原更窄state.deadline取min，并从续租前绑定保守monotonic边界，持有原renewal/settlement锁及元数据至实际提交；无Graph／授权／PASS缓存，finally仅清自身token，外来替换停止。默认SQLite writer没有原finite scope会先拒绝。Store.heartbeat仅SQLite且指定Run续租，原owner lease、新lease及调用截止也在Connection callback之后／DBAPI commit之前复核，防续租本身在旧owner过期后提交。

进一步2个真实时钟反例（snapshot false/true）表明更窄state截止不能只在续租入口检查：此前callback越过state截止后仍持久写入；原失败完整保留legacy-state-deadline-before-726e。最终捕获该原截止后，同一回归要求实际异常、持久值回滚。小测试使用短合成租约，仅验证正确性，**不当大型30秒性能成绩**。签署的SQLiteSettlementCaps 120秒路径未改；PG／无Run存活心跳保留原调用接口，fakeconn接口测试不等于PG执行。

## 分版本验证及剩余范围

| 准确源码／阶段 | 实际结果 |
| --- | --- |
| 最终1a23，最后期限补漏＋exact/stop/UI/软件资格等定向组合 | **219 passed，0失败／错误／跳过** |
| 前一冻结726e（尚未补更窄state截止），完整组合 | 458 passed，0失败／错误／跳过 |
| 2175旧30秒原owner尾检，尚未v2格式修复 | 456 passed，0失败／错误／跳过 |
| 首轮lease局部组合 | 97 passed/1 failed；旧fixture缺deadline并以0冒充活lease |
| 冻结6424旧fixture单项对照 | 同KeyError，未误归本轮回归 |

只把fixture改为真实process_job初始deadline=None／run lease，保留原发布与停止断言，新增expired0拒续租/DB不变反例；原失败和基线XML均保留。**未把前版458/456或既有fc978的386改签成最终1a23重跑。** 最终219与所列完整祖先、全部原检查可核；不能叠加为互不重叠通过数量，也不宣称全仓绿。源代码、协议/历史兼容、stop/锁/PG接口及实际driver均分别独审。

额外原生套件早前17通过/12失败/28显式实验跳过也保留在前一安装证据：源/包相同12个旧图fixture会替换受保护compile_preview等生产者，被完整代码门拒绝，未删断言、放宽门或称已迁移。本包4扩展实加载/hash不等于全部原生业务验收；该未闭合范围继续存在。

最终包未验新版Windows、正式PG、完整大型Cold live，未新增Windows CI／PC操作／runtime安装／权限／凭据／费用。正式PG仍缺已有应用角色连接和明确principal/project/trial/approval/account来源选择；不阻断这里已验的合成SQLite入口。既有大图G0 29.41/31.34秒、writer区段44.29/45.97秒，原30秒目标仍不稳定，**本次安全尾检及小文本6.39秒不替代性能修复或大型整链验收**。当前包不称整体交付或正式Release。

两个历史和最终数据库均仅含本任务生成的合成文本／公开测试身份／原读取回执。包／嵌套wheel／gzip/SQLite原字节已比较当前注入秘密值无命中，不输出其值；不含用户私人文件或认证header。文件身份、来源／压缩及raw SHA见artifact-manifest与privacy-check；数据库证据仅供只读审计，不随候选ZIP初始化给用户。
