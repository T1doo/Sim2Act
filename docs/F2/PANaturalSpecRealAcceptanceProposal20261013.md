# 未标注短规范：最小真实验收精确授权提案（未执行）

本文件只提出下一次独立授权范围。当前真实请求、费用和凭据读取/配置均为0；本次合成工程测试不授予真实模型或语义验收。现实现仅接受test_only SQLite +mock+显式MockTransport；现有字面检索/CSV批准不能打开新家族。真实试验还需要单独实现并审查精确LIVE批准门、跨Run总账和零付费门，不能只设置token或删除test-only检查。

## 模型、网络和合法入口

请求模型严格为`intern-s2`，返回名字只接受既有明确别名`intern-s2`/`Intern-S2`，不使用latest或其他模型。唯一拟议POST端点为`https://chat.intern-ai.org.cn/api/v1/chat/completions`，不跟重定向、不请求模型列表、不使用内置联网或其他外部工具。官方当前文档明确列出模型ID和该ChatAPI端点；这只是公开文档核验，不是账户可用性证明。[官方模型文档](https://internlm.intern-ai.org.cn/docEn/docs/Models/)，[官方ChatAPI文档](https://internlm.intern-ai.org.cn/docEn/docs/Chat/index.html?id=1748476800101)。公开文档检查日期：2026-10-13 UTC。

官方认证文档提供账户API Console入口，要求后端Bearer认证。仓库Settings.from_env已有合法显式入口`SIM2ACT_INTERN_TOKEN`，空值时允许`INTERN_API_TOKEN`；不自动寻找dotenv/磁盘凭据。**本次查验代码和本地非凭据运行参数，未查询凭据环境变量值、账户、API Console或任何token；当前凭据来源、是否存在、是否有效均NOT_VERIFIED。** 后续只能由账户所有人从官方入口取得凭据并通过已批准后端secret机制提供，不能把值写入浏览器、仓库、报告或聊天。[官方认证文档](https://internlm.intern-ai.org.cn/docEn/docs/Authentication/)。

## 唯一拟议试验和总上限

材料只有两份预先逐字封存的自造中性英文TXT：桌灯省电行为、花园传感器采样行为。每份≤1024 UTF8 bytes、≤20行，含普通条件、例外和待定选择，无标签语法、私人内容、用户数据、路径、URL、代码或外部检索。每份完整Goal和最多16人工未决项另行冻结；开发者人工答案只在本地独立语义核对表中，绝不放进prompt/checker或发给provider。

|阶段|请求上限|操作|
|---|---:|---|
|来源Goal生成|3|一次read反馈、一次候选出处检查、一次final；仅出处失败允许一次修订，PASS后只能原候选|
|明确确认后的来源应用Run|2|模型选择的1或2节点，逐个发送；本地引用核验后另行JSON保存/readback|
|明确新Goal/新材料的冷复用Run|2|同一图在第二材料重新执行1或2节点，消费实际新read/前驱反馈|
|整个试验|7|每个阶段用独立原key；最多两个应用Run，未用槽不转移到其他任务|

全部请求`stream=false`、`max_tokens=1024`；完整序列化wire≤32768bytes/次，响应完整归档≤32768ASCIIbytes/次。三个Run分别保守reserved envelope≤64000（完整wire bytes加1024输出额度），试验跨Run总额≤192000；总输出上限7168tokens。以上byte-envelope不是实际tokenizer计量，真实usage另核；任何wire/总账/usage超界立即停止，无截断、省略、自动repair或自动重发。客户端总deadline≤300秒/Run，lease仍30秒；整个批准还需独立不可延期expiry。账户速率≤1请求/分钟，等待只能在尚未扣额的槽进行，不延deadline。

允许外发内容仅为上述封存材料、完整Goal、注册schema/prompt和本次实际机械反馈。不外发本地人工gold、历史其他材料、身份令牌或私有审计。只允许指定项目授权resource.read和一次一个JSON制品的原子保存；无部署、发布、项目列修改或其他写权限。未知发送结果立即停，仅原key GET读取受保护状态；取消/撤权/竞争/迟到均不提交制品。

## 零付费前提和验收

付费上限严格为0。公开ChatAPI/认证/模型文档没有证明本账户对`intern-s2`在此日期具备无账单免费权益，也没有本账户余额、费率或强制禁止收费证据；因此**零付费条件当前NOT_VERIFIED，提案不可执行**。不得以“通常免费”、旧额度、请求很少或授权额度作为免费证明；不充值、不绑卡、不扩大账单权限。后续须先取得合法账户的免费权益及强制零收费证据；无法保证时不发送。

工程验收分别核对真实传输身份/usage、出处坐标、全原文/人工未决项保留、原子回执和预算。独立人工语义验收另核义务、条件作用范围、例外、未决项、关系和遗漏；错误摘要即使引用准确也不能语义PASS。任一语义项不确定保持UNKNOWN/PENDING。即使工程Run成功，本提案也不批准正式应用发布或P-B。

待用户批准时必须给出上述唯一模型、材料SHA、Goal SHA、项目/运行身份、三个Run及总账上限、批准expiry、强制零收费证明和合法secret入口状态的精确封存对象。用户现在无需提供token；本文件不是授权请求或已建立的LIVE批准。
