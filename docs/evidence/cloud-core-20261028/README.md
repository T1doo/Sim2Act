# 2026-10-28 云端候选：G0仍未通过

**最终状态：未完成交付。G0完整链仍FAILED_NOT_FIXED，真实业务提取和UI像素验收未通过；不合main、不认定Release。**

基线 `206153da27edb5353e7106ab52b6e5bcaad86627`；冻结实现 `6e46f871`。从指定新云环境实核：初始工作区干净，fetch 后 HEAD 与 origin/main 左右差异 0/0；Windows 候选 `89c08e27` 已是 HEAD 祖先。没有使用用户电脑、旧云工作目录或共享文件假设。

## 已实现

- G0 默认 pre/post 入口正式安装已有固定纯段 selector，在原完整内容边界之间合并纯计算重复工作。完整字段/别名/隐藏行存储、typed 值、审批、权限、Run/version/fence、stop 和期限检查保留；未知代码/serializer 回到原路径。不复用旧 PASS、不延长 30 秒租约。
- SQLite 模型结算在进入事务前持原 renewal_lock，提交一次原 guarded heartbeat 后继续持锁进入结算；不在读证明 epoch 内写租约，不用本地时间数字替换实际续租。
- `production_evidence.resolve_account` 已从无条件 SOURCE_MISSING 改成固定服务器来源：既有环境 token、`intern-s2`、`https://chat.intern-ai.org.cn/api/v1/chat/completions`、单一账号与 canonical quota。费用依据是用户 2026-10-28 明确零费确认，应用约束是 paid_cap=0、固定路由、无付费 fallback、错误停止；不宣称 provider 账单 API 证明。HTTP 客户端候选不能提供来源、token 或免费布尔值。
- production environment 检查实际 Settings token 与当前服务器优先环境 token 相同；缺 token、不同账户额度或过期原合同给具体拒绝。既有逐合同审批/撤回/权限/预算仍适用。
- 为本轮生产实现增加精确软件 manifest：130 个 Python 文件，manifest 字面 SHA pin，唯一 pin 自归零避免循环。旧 compatibility 门及旧 anchor 原字节保留；生产门仍核旧 anchor 完整性。只读独审实核全清单，模拟 anchor/manifest/model.py 漂移分别拒绝，恢复后真实 `_qualified()` PASS。
- UI 桌面主工作区使用 188px 固定窄导航、稳定工具栏和任务分区。任务列表/成果并排，Goal 列表/详情并排，资源表单/已保存材料分栏；长内容只在工作区域滚动。保留原控制器、数据和显式操作，不提交/取消任务来切换分区。颜色仍 #FAF9F5 / #D97757 / #141413。

## 真实模型与验收边界

本轮 `intern-current.json` 是一次真实固定端点调用：HTTP200，返回 `Intern-S2` 通过原身份规则，精确输出 SIM2ACT_READY，161 tokens，2.499 秒，无重试。仅核 token 非空，未输出、保存或新建凭据。

随后小规模调用产品现有 messages/parse/引用校验：默认模式 Source 因不完整结束原因被原 parser 拒绝（15.240 秒，Cold 未运行）。查官方 [Chat API 参数文档](https://internlm.intern-ai.org.cn/docEn/docs/Chat/) 得知有 thinking_mode 控制后，另一次显式 thinking_mode=false 的独立诊断收到 HTTP200/stop/525 tokens，但原精确引用校验拒绝引用区间（3.569 秒，Cold 未运行）。两次均停止，无自动重试、无扩大 token 限额、未删除校验，未把 thinking_mode=false 安装进产品协议。原失败见两个 intern-extraction JSON；首个诊断未在 parse 前独立保存 HTTP 状态/raw body，证据明确保留这个限制。**真实业务提取/语义验收尚未通过，连通性成功不等于业务完成。**

## 完整 G0 与结果保存链

原真实失败证据 `../g0-685d62e-once-20261025/README.md` 已读取。第一轮本轮完整执行在 Source 前因作者继续修改源码而触发 Trial software changed，原 log/XML 保留为 pb-full，不冒称是 G0 结果。之后冻结源码，独立 source manifest 为 frozen-source.json，再执行原完整生成→Source→提取→显式新材料→Cold→持久结果用例；被动 observer 只读原上下文返回/时长，不替换校验、时钟、transport 或输出。冻结执行结果见 pb-frozen.xml/log、full-timings.json 与后续结果说明。

原测试自身使用隔离 SQLite 和有限 MockTransport，并明确替代环境/account/software fixture；因此即使此链通过，也只是原控制器工程闭环，不是生产 PostgreSQL、真实账户请求或 owner 语义验收。

## UI 交付与明确阻塞

实际本机后端启动于云端 loopback，数据为全新空白隔离 SYNTHETIC_TEST_ONLY SQLite 工作区。HTTP 实读 app.js/app.css 均200且与冻结源码字节一致；node 语法检查通过。**未完成像素验收，没有当前截图附件。**

受支持的 Playwright sandboxed Chromium 在启动时主动中止：`/usr/lib/chromium/chrome-sandbox` 的 owner/mode 配置不符合 SUID sandbox 要求（需要 root owner/4755）。未关闭 sandbox、未改安全权限、未重试上传、未尝试用户电脑或外部部署。截图与 1366×768 / 1440×900 的实际像素验证需平台提供可正常启动的受支持沙箱浏览器；详见 screenshot-blocker.json。

## 正式执行所缺的具体配置

INTERN_API_TOKEN 本轮确实非空，固定免费模型不存在“缺用户费用授权”。当前环境没有注入 `SIM2ACT_DATABASE_URL`，没有可选生产数据库中的 existing principal/project/trial/approval ID；PostgreSQL 应用链未验。未创建凭据、OAuth、角色或安全权限。

使用现有生产环境时沿既有 Worker 入口选择已经准备/批准的合同：`python -m sim2act.worker --spec-production-user ... --spec-production-project ... --spec-production-trial ... --spec-production-approval ... --spec-production-account intern-ai-configured-account`。还需显式环境选择 LIVE、enabled、goal planner intern-s2 和 application generation activation，保持原有限预算；Python 不自动读取 .env。

固定账号 quota subject：`intern-ai-account-8a3c6e77f1e3dda560baf0a1a0789fc6dcfe955fe42543f8255f0e278685f56e`。原合同需绑定该账号额度；不能把既有其他账号批准静默迁移到它。现有 token 别名非空专用名称优先，空专用名称回落 INTERN_API_TOKEN。

本候选尚不是正式 Release，不部署、不强推。真实模型语义/生产 PostgreSQL/截图像素问题必须分别如实验收。

## 第二个实质修复：原生独立快照与严格比较

`6e46f871` 冻结执行真实失败：首个 Cold G0 为35.206922秒，首commit29.219976秒并在原 Run/lease 校验拒绝，未到第二commit/五写/post；完整用例351.85秒，非timeout。前面的 Source 两次已正常结算。失败不是通过，不把仅启用旧segment称为已修复。

新冻结候选 `8dc05115` 增加可选 CPython C 捕获器，针对深度≤64/访问≤100000、严格内置类型和字符串key的有界域，保留每次完整独立副本和原左右捕获次序。无 completed memo，DAG逐次复制；tuple/list不混同。dict仍先捕获原items/key门，再由真实迭代器DFS复制；没有borrowed输入视图替代快照。RowMapping/quoted key/陌生/深层/循环输入在执行前走原Python。native执行错误一次传播，不进行失败后Python重试。原Python标量类型门改直接is链，不删验证。

严格C比较只处理完整预检过的精确内置无环有限值；浮点单独按数值比较，保留同一NaN指针仍不等、signed zero相等、bool/int不同及list/tuple不同。中间版曾被既有NaN测试发现真实错误，原失败日志raw-snapshot-2保留；已修复，最终43个快照/并发反例/typed-stream检查全部通过，未修改原NaN期待。

只读原失败DB中65行的完整复制对照，old/current中位数0.099042/0.012018秒，严格值相同；是受控capture成本证据，不是G0或整业务性能推断。unknown helper身份变化会回原Python，定向抛错证明原helper调用一次。合同implementation指纹现绑定py/c/so/pyd实际字节和加载backend身份；加载后二进制在磁盘变化即拒绝。native-build-identity.json和frozen清单记录真正执行的源/binary hash。独审复核过C边界与8个严格比较案例。

云端使用已安装cc正常构建。默认Python的clang命令在本环境不存在，原始失败保留；没有安装SDK或改系统权限。native缺失仍可用原Python路径，但不据此宣称Windows同等性能。linux CPython3.12候选wheel的文件与测试二进制比对见wheel-verification.json；这不是正式Release。

104项相关账户/授权/纯段/后段检查在同一冻结准备阶段通过（144.11秒）；另6项自包含原生边界检查通过。不把这些数量替代完整闭环。最终完整真实时钟链正在用新Store/合同重新执行；见pb-native-frozen、full-native-timings与native-frozen-source。

UI独审找到并修复四处明确交接：Goal向导完成后打开Goal区；协议提交完成打开任务成果区；本人停止入口打开任务区；≤1000px分区链接保留显式滚动。均不在后台刷新中强制切分区。像素仍未验。

## 最终结果：G0仍未修复，不合main、不认定Release

`8dc05115` 的原完整真实时钟用例实际 **1 FAIL /359.15秒**，非timeout。生成和Source已完成，首个Cold实际接收响应后，G0 **39.563506秒**，第一commit校验32.623268秒，仍在 `_graph_run_context → _require_run_context_row` 因有限lease拒绝。第一commit没有返回、第二commit未进入、原结果保存链未完成。仅根据原异常位置可断定停在W5前；没有伪造动态W5计数。**不能用局部8倍复制速度、104项定向通过或源码独审替代这个失败。** 两个完整候选分别35.21与39.56秒，条件/代码不同且样本有限，不声称归因或稳定性能改善。

native-frozen-source.json中的所有源码与实际binary运行前后零差异。6次Mock交换，0真实模型调用；原DB、failure/lease/mock日志与closed-state在native-originals中gzip无损保全，原长度/SHA与压缩件SHA见native-originals.json。最终只读DB：生成PARTIAL、Source SUCCEEDED、Cold RUNNING/version1且Attempt REJECTED_KNOWN，result仍null，未伪造完成或恢复执行此失败Run。

当前仅交付**待审开发候选**：固定免费来源接入、紧凑任务工作区与可审原生快照实现；G0首个完整验证窗口仍超期，需继续降低整个read/typed/continuity链成本或另行设计经明确版本约束的租约协议，不能把缺口归为用户没授权费用。正式生产数据库链仍缺当前现有应用连接和具体既有trial选择；UI截图/像素仍被平台sandbox配置阻塞；真实提取诊断仍未通过。没有main合并、部署、正式发布、强推、用户电脑操作、新费用、凭据或安全权限变化。
