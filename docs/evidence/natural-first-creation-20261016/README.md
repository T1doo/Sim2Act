# 从空目录首次创建自然应用：产品交付证据

基线 `9d12e321d556c4b9c6ec2bf1ef4ccd7b958a645c`，普通开发分支 `dev/natural-first-app-guide-20261016`。开工本地/远端均为9d12，工作区干净、一个worktree，约27GiB可用；根为唯一仓库写入者，代理只读仓库并写自己的/tmp。未回旧环境，未用旧bundle或共享文件，未删除未知锁/进程。

入口位于应用目录上方“从 Goal 创建自然应用”。首次用户直接准备并分别保存新材料、新Goal，继续原生成面板，明确生成、回读候选，分别确认材料读取和项目JSON保存权限，再核查并确认内部版本、明确创建实例，最后从步骤卡返回目录。各写入/授权步骤独立确认，打开、继续、返回和冷页不自动生成/运行。

自然家族现有API不接收activation，当前没有LIVE批准路径。新的capabilities字段仅报告现有受限离线配置，不能授权发送；实际wire仍走未修改的check_provider，要求test-only Store、mock模式、live关闭、intern-s2 provider及MockTransport。配置不可用在UI生成POST前明确停止。没有新增executor、批准机制或Grant种类；显式保存及候选确认仍使用原授权效果。

## 冻结与实际测试范围

功能代码冻结 `9b7d30b8f4aec699b1c3b9574b6dc6971ca4262e`。随后 `eac24d0396c05d9a481337c42b1708e9824afccf` 仅修正HTML家族说明，并追加轻量测试。全部API/JS及主HTTP驱动字节与9b7相同；原HTTP测试body未改，只在wrapper末追加probe。新HTML仅legend和首段两个文本节点变化，tag/attributes结构相同，见 `html-copy-verification.json` / `html-copy-only.patch`。不把不同冻结阶段拼成一次全绿矩阵。

- `first-guide-pa-final/`：9b7完整实际TestClient HTTP + 可见JSDOM手势 + MockTransport/真实Worker，**1 PASS / 0 FAIL / 0 SKIP，334.53s，54 checks / 61 gestures / 63 asset loads / 3 boots**。初始apps/releases/instances/runs/attempts为空，SOURCE材料与Goal均从UI新保存；三次mock反馈完成原自然候选生成。双项候选授权、Release确认和instance创建均分别点击。目录返回、冷页打开只读，实例此前没有运行。第二份新材料与Goal经原per-use预览/明确确认，第一次实例运行得到v1，同Run人工入口PENDING；最后冷页不重跑。
  - 新app：`app_6a0d4bcaaa5ce3cc9f262853ccd9d1e1`
  - Release：`irelease_408507fab94f4df2ad420acdf3f6f88b`
  - instance：`iinstance_6acf3ba9802f1c4bc32e22d5914ff927`
  - generation Run：`run_d0788e85cb2443e7afde67b2a59be79b`，3次mock wire，候选状态PARTIAL/semantic UNKNOWN
  - 第二材料Run：`run_d97d29bd20cb4691a1e5d505e8a81241`，1次mock wire，首次实例结果v1；真实模型请求0
- `first-guide-blocked-final/`：9b7实际HTTP，**1 PASS，19.34s**。同样从空目录新建材料和Goal，到原生成面板，fresh capabilities=BLOCKED；零application-runs POST、零Run/attempt/app/Release/instance，冷页只读。
- `first-guide-shared-final/`：9b7，**6 PASS，72.35s**。原材料/Goal准备导航探针、Goal执行合成UI与实际HTTP、目录UI分类、metadata目录路由、CSV保存应用使用的必要定向回归。没有追加P-A/P-B恢复矩阵。
- `first-guide-light-final/`：9b7产品字节，**2 PASS，19.45s**。新导航探针30checks，覆盖workspace/project/identity/cancel迟到capability不提交、同Goal ABA旧锁清理后当前按钮可再点、first未知Goal reset退出、长Goal标题完整保留/默认应用名100码点、取消还原原form与CSV。另一例直接API原wire边界：默认disabled配置可接受一个等待资源Run，但实际Worker零模型attempt/wire、零应用/版本/实例；这与UI完全不创建generation Run的负例分开记录。
- `first-guide-html-final/`：eac新HTML，**2 PASS，15.56s**，实际HTTP缺配置完整前半链与30check轻量探针。新HTML上不重复Worker，未声称新HTML重跑了9b7完整正例。
- `independent/`：9b7有限静审与独立30check probe（1PASS，15.16s）；eac纯HTML差异静审与新HTML独立30check probe（1PASS，7.61s），无剩余必须修项。独立probe是合成API，不代替完整HTTP/Worker正例。

每阶段日志、JUnit、HTTP请求与响应、可见enabled手势、资源摘要、checkpoint与mock wire均保留。generation-wire=3 / runtime-wire=1是这条无预置应用正例实际记录，未调用真实模型。`initial-product-freeze.json` 与 `final-product-test-freeze.json` 分别记录源码/测试摘要。`static-checks.json`、`api-mypy.log` 和最终源码字节核对支持静态检查范围；不声称全仓类型检查通过。

## 保留的先前尝试与已修缺陷

- `blocked-ui-wip1/`：1 FAIL，实际可见first按钮在连接加载项目后仍disabled；根修在目录renderer完成后刷新向导按钮状态。未绕过disabled或降低测试断言。`blocked-ui-wip2/`随后1PASS（11.43s），最终冻结负例另有原件。
- `default-gate-wip/`：默认关闭的原后端wire边界探索1PASS（3.12s），仅补充；最终同例另在light批次执行。
- `first-guide-wip-regressions/`：早期2PASS（12.01s），不冒充最终冻结；6例批次另在9b7执行。
- WIP独审曾报告first未知Goal reset留下空向导、同Goal迟到gate删除锁后按钮不重绘、合法200字Goal默认名超100限制；均在9b7修复并由独立probe验证。旧WIP报告保留，最终冻结报告关闭这些项。
- 原候选打开控制器捕旧workspace的opening fence，在完成完整showApp且context.current通过后按函数引用解除，然后才进入Apps；异步打开期仍保持原守卫，后续内部动作使用其原代际守卫。
- 旧生成fieldset把自然家族描述成字面匹配的文案项已在eac修正，独立审查证明仅文本变化。

旧多历史fixture心跳锁失败继续OPEN，本轮未修复或补跑旧恢复矩阵。旧满盘环境最后未落盘的独审报告没有补回。真实模型、真实场景/语义与真实人工验收、Windows、原生浏览器、PostgreSQL、远端CI和部署均NOT_RUN。JSDOM可见性/实际HTTP与mock工程证据不等于真实语义通过；实例新结果保留semantic UNKNOWN/owner PENDING/正式发布关闭。

最终交付提交仅归档本证据；完整SHA与direct-remote-SHA ahead/behind、未提交/未推送差异见交付消息及仓库外 `first-guide-final-delivery-verification.json`。
