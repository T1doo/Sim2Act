# Sim2Act 动态总入口

## 2026-11-06 五镜头录制包与编号校验接续

[录制素材精选 v2](../deliverables/Sim2Act_录制素材精选_v2_20261106.zip)含五张未经标注的 2400×1350 产品原图，按材料、第一批 6,240 元、第二批 8,000 元、两批历史、书生简报排序。用 Windows 构建 `c38568d8` 只读打开既有成果并截图，未触发新业务运行。两批 CSV 各六条，金额独立复算，源字节与运行哈希一致。冷重开与页面导出都指向同一第二批运行 v2。简报输入从 CRLF 转为回执中实际读取的 UTF-8/LF 字节，文字及回执可逐字核对。五张图、提词卡和产物均列入包内校验清单。截图后的后台与该专用库均干净退出，原生窗口未自动操作。

复核 `56ad2e86` 原材料任务的唯一模型回执，发现模型输出 `req-1`、`exc-1`、`open-1`，命中运行器既有编号校验。`c38568d8` 冻结 `natural-spec-request.v4`，给新请求补上编号正则、明确反例及关联示例。既有校验仍拒绝无效编号，旧协议的六个典型请求样本与原封存包逐字节相同。原失败回执保留于本机证据，不进入录制包。

同一冻结包实跑书生候选生成、应用保存、原材料运行 v1 和冷重开回读。原材料三项清单、原文与引用均核对通过，语义验收未执行，人工签收待确认。[运行证据](evidence/r0-convergence-20261105/pa-indexed-20261106/verification.json)和[原材料成果](evidence/r0-convergence-20261105/pa-indexed-20261106/source-result.md)已归档。新材料在同一实例获批并收到完整响应，随后结算记录为 `VERSION_CONFLICT`，任务停在 `WAITING_RESOURCE/OUTCOME_UNKNOWN`。只读复核中，新材料原响应的解析、引用、使用量以及原账本证据链均通过。剩余问题缩小到执行时的结算校验，原任务未重发，也没有 v2 成果。三轮后台干净退出。

本地自然运行及软件资格套件 101 项通过，两项 SQLite 私有读取测试因 SQL 自定义函数异常失败。在原冻结包 `56ad2e86` 用同一测试复现两项失败。新版录像包使用已验证的固定 CSV 复用和独立书生简报，两条演示链的功能边界不变。

## 2026-11-06 参赛界面文案复核与自然生成接续

应用生成及任务表单移除了面向开发者的离线测试和传输适配器说明。界面按当前目标显示模拟模式、授权可用或任务未提交，保留操作确认与结果状态。生成导航 35 项、授权和回执恢复 8 项通过。P-B 来源导航断言在修改前的 `56ad2e86` 上同样失败，仍待单独核查。录制继续使用[产品原图和实际成果](../deliverables/Sim2Act_录制素材精选_20261106.zip)。本轮文案尚未在原生窗口重验。

自然生成候选在 Windows 冻结包 `41cca795` 完成真实读取、候选检查、结构化提交及应用保存。原材料运行收到完整模型响应后被精确字符引用校验拒绝。`56ad2e86` 加入由程序解析的原文行号引用，54 项资格回归通过。实跑再次完成生成和保存并启动原材料任务，原材料结果被清单条目或关系校验拒绝（`VERIFICATION_FAILED`），未启动新材料复用。两次监督进程退出码均为 0，专用数据库退出无 PID 文件残留。保留原失败结果与本地证据，此链未加入录制包或签收 R0。

## 2026-11-06 录制素材精选与 P-A 运行接续

录制材料集中为 [录制素材精选](../deliverables/Sim2Act_录制素材精选_20261106.zip)，包括三张无说明层的产品原图、报名核对和书生简报的实际产物、复现说明及 70 秒提词卡。本机产品入口仍可通过项目内 `.local/Sim2Act.lnk` 手动核对。

P-A 记账按批准候选的真实节点数验证。原材料真实运行进一步暴露 PostgreSQL JSON 比较错误，专用库复现 SQLSTATE 42883，修复后的查询通过真实回执匹配验证。原尝试的完整平台响应已归档，本地状态为 STARTED，旧工程退出声明保留。最新 v8 封存包 c9cdd19e 的生成验证仍在候选校验处结束，后续执行与新材料复用待验。[阶段证据与下一项](evidence/r0-convergence-20261105/pa-stage-count-pg-receipts.md)

## 2026-11-06 自然生成路径：真实候选与应用定义已保存

开发分支新冻结包 **942613ba02baa357e92ee6abb707f1b80f49845b** 已用书生实际完成读取、检查和最终候选校验，并确认保存“提交规则审阅助手”，状态PREVIEW_ONLY。v5原端口失败和v6普通文字调用失败保留；v7按名称选择真实阶段函数，未把自由文本伪造成工具回执。

实际应用ID `app_373d921dc36b87cc3c41ea9e16ba8309`，模型选择读取→单模型提取→引用核对→保存四步。原件：[规则审阅应用定义](../deliverables/Sim2Act_规则审阅应用_20261106/README.md)；[真实生成记录与接续项](evidence/r0-convergence-20261105/natural-v7-real-generation.md)。语义NOT_RUN，执行与新材料复用尚未通过，不作为新增可运行成果截图。

下一优先项是Source/Cold记账对合法单模型图的核对：当前代码有固定2次Attempt的谓词，必须绑定已批准冻结图的真实模型节点数并保持双模型漏调用拒绝，不能凑数或弱化权限。新端到端应在同一冻结版本连续推进，遵守900秒交接和300秒单Run期限；不得回写旧时间或证明。

用户当前稳定产品入口和最新直截图仍为4da58bd3（main界面交付0f659a24）；实验生成路径单独追踪，不以候选保存替代基础展示包或完整R0验收。

## 2026-11-06 产品界面文案与纯界面截图

用户明确要求：比赛画面只呈现产品，不添加演示配图/测试说明小字。已写入GOAL.md。当前最新已构建桌面源码 **4da58bd32af2af88646b602da2863f09728b9d8e**，前端清理冗余选列注释、工程式入口措辞；连接状态改为面向用户的已连接/模拟模式/离线/待确认，主画面显示任务版本，完整标识保留于详情。

交互、结果归属、下载绑定检查通过；连接状态浏览器检查9 PASS（旧测试夹具缺少共享errorFeedback抽取，补齐后通过）。新包实际只读核对应用成果、任务工作台、材料管理，页面脚本错误0，三张2400×1350原界面截图未加说明层，后端与专用PG干净关闭。原生窗口仍未自动操作。

当前画面优先使用[产品直截图](../deliverables/Sim2Act_产品直截图_20261106_v2.zip)，验证元数据独立存放于产品界面目录；本机产品入口为 `.local/Sim2Act.lnk`。此前素材包保留原版本，不把旧图改签为新版。

## 2026-11-06 冻结版跨批复用与死锁修复已复验

最新已构建桌面源码为 **a4cfe891371eb57533020928b4b2f062c229b259**。真实PG暴露Grant锁循环后，Store.authorize统一为项目锁先于Grant，保留所有权限、有效期、撤回及指纹检查。3项边界回归与54项资格回归PASS；限定证据见[csv-project-authority](evidence/r0-convergence-20261105/csv-project-authority-20261106.md)。

同一冻结包中新建演示项目，正常产品API准备模板与原实例，之后第一批运行、第二批授权/冻结/CHECK/Release/采用/运行和下载全由真实页面完成。原实例 `iinstance_3f7de5eadb8c618855951c3dad87fad4`，第一批6240/v1、第二批8000/v2；关闭API/Worker/PG再冷重开，两份成果、来源、版本保持一致，页面历史切换与重新下载通过，后台干净退出。该案例0模型请求，不称为自然生成。

素材：[跨批案例](../deliverables/Sim2Act_跨批复用演示_20261106/README.md)；三案例统一入口：[视频素材索引](../deliverables/Sim2Act_视频素材索引_20261106.md)。本机快捷方式更新到新包，不自动操作原生窗口。

旧20aba026工程在新包追加运行时先后被当前图基线/冻结图不一致明确拒绝，均NOT_ACCEPTED/事务回滚，旧成果保留；此跨软件版本接续没有通过，不修改旧证明。可选协议注册表仍缺Evaluation asset，完整R0和自然P-A/P-B未完成。近期基础素材继续交付，Goal仍active。

## 2026-11-06 书生真实模型案例与新 Windows 构建

视频素材最新统一入口：[两案例索引](../deliverables/Sim2Act_视频素材索引_20261106.md)。新增真实UI提交的书生任务 `run_880358c6e2504a30a7b121e754c54517`：读取合成活动交接MD，整理四部分执行简报，状态PARTIAL、工具VERIFIED、完整语义NOT_RUN。原模型运行包657418c2；新包冷重开同一持久运行，没有再次调用模型。

当前最新已构建桌面源码 **20aba0266bd0b7d4147a0acb7bac2b6eef0cc741**，优先于下方历史候选。前端仅修普通回答前置、安全加粗投影；已在1600×900、1366×768、1280×720实际渲染核对回答优先/无横向溢出/验收缺项可见。小窗口仍需成果区滚动，原生窗口自动操作未恢复。新包API、Worker、专用PG冷重开和退出通过，专用PG无PID残留。

新包同时封存此前待提交的v5 Python资格目标；本轮没有宣称v5真实P-A通过。资格补查96项PASS/1夹具失败，修复Windows换行夹具后原失败项PASS；前端控制交互与安全文本强调检查PASS。原始失败证据保留。当前Goal仍active，下一优先项是新输入复用与可展示生成链。

## 2026-11-06 视频素材首包：实际界面运行已通过

最新演示包：[Sim2Act_视频素材_20261106](../deliverables/Sim2Act_视频素材_20261106/README.md)，含 8 张 2400×1350 PNG、输入、实际输出、界面 JSON/CSV 导出、镜头脚本与哈希清单；同名 ZIP 可直接上传。演示使用冻结 Windows 包 `657418c2335ae45578ecc03d3ebf6b87c0f3fb0a`，不是把当前未提交资格文件当成已构建实现。

已验证第一批 6 条合成报名记录：39 人、6,240 元；原有 API 路径的请求键幂等和冷重开保留；本轮又通过真实页面按钮提交新的金额任务，成功运行 `run_953b9ef5665f4ea8b9d1eb4a37e537d0`、结果 v4，并核对界面下载的 JSON/CSV 同 Run、同版本和金额。截图无页面脚本错误；API/Worker/专用 PG 干净关闭，无后台残留 PID 文件。

这是已注册 CSV 只读求和能力，0 模型请求；第二批材料已准备但换材料执行尚未验收。截图来自真实 Windows Edge 无头页面，不等于原生窗口录制或完整 R0 通过。自然 P-A/P-B 继续收敛，完整 Goal 保持 active。用户本轮已授权 GitHub 操作，原生窗口自动操作仍暂停。

## 2026-11-05 最新目标修订：演示与视频素材优先

当前目标以仓库根目录 [GOAL.md](../GOAL.md) 为准。用户要求接下来 1～2 天优先跑通能体现产品理念的基础演示，提供漂亮页面截图、演示案例、输出产物和操作/讲解说明，便于周末录制与撰写参赛文档；完整功能在提交后继续优化。

原计划现已逐字节复制并核验到 [docs/plans/执行版](plans/Sim2Act_Codex_完善与验收计划_20261105.md) 及同目录 DOCX，后续不再依赖 C 盘 Downloads。旧 Goal 或下方历史路径不作为外部文件依赖。

本轮演示交付与完整 UI-ready/R0-ready 分开。优先使用已能实际运行的能力组织主线，补演示阻断；高级路径与完整 AT 继续记录，但不阻塞全部素材准备。保留当前前端，不再以反复美化或细碎校验替代展示闭环。

## 2026-11-05 当前候选索引（优先于下方历史进度描述）

当前分支 `codex/ui-review-followup`，最新已构建并校验的桌面候选代码为 `fbfe58c4054ec0f6cdb813add9e1893742397432`。
远端 main 未在本阶段推送。最新用户窗口限制为“暂不操作窗口，继续后台和代码工作”；
下方历史窗口授权不作为当前自动操作许可。前端保持已认可设计，功能与真实结果优先。

| 能力 | 同版本证据与当前边界 |
| --- | --- |
| 原生宿主 | f55f1639曾实际打开LIVE窗口并正常关闭；此后自动登录、首次配置向导和当前候选的原生交互未验 |
| 首次数据库配置 | fe28440d组合包在中文新数据路径实际完成初始化及两次API/Worker运行；原生向导未操作，不能签开箱体验 |
| 专用PG生命周期 | 85b8b619真实模型测试API/Worker正常退出、PG停止；不是所有异常场景和安装/卸载验收 |
| 有限字面P-A | 82ba4db4完成真实生成、确认、预览、实例新输入/错误输入和冷重开；不是完整自然规范P-A/P-B |
| 新普通授权入口 | 85b8b619同会话准备/批准/原键回读/提交成功；该次模型候选无效，未创建应用；失败记录完整保留 |
| 有限字面字段修复 | 73826ba7采用v6字段来源Schema；真实生成2请求9577 tokens、0修复，候选确认/实例新词/错误类型/冷重开均通过；仅有限字面应用，非完整自然规范两路径 |
| 正式自然入口 | 新固定账户初始化、五字段Worker/API选择和目标readiness接线存在；be458799真实跨过账本后截断，a0534197第二请求超时，均未产生应用，不自动重发 |
| 最新期限修复 | f79b3e1d分离generate HTTP绝对期限与滚动lease，保留续约失败/取消停机及原300秒边界；fbfe58c4经52唯一节点回归（首轮50通过2环境失败、子进程同源修正后2通过），当前真实新范围在测，不预签通过 |
| P-B保存性能 | 68525f0a原回归81通过1失败，冷保存超120秒；cProfile原样失败保留，约45万SQL；独立租约大用例也失败，不能仅归因旧观察器。仍未关闭 |
| 桌面当前包 | `.local/windows-build-20261105/desktop-managed-fbfe58c4.zip`，SHA256 `49a681d6331c394020ae74fe408c1441f17c31e3cac5e2209a41d780a8ab046d`；宿主及包内原资格检查通过，窗口未操作 |
| 完整两路径与R0 | 尚未完成；Test.ps1的R0拒绝门仍保留，完整自然路径、原生用户路径及AT组合仍需同版证据 |

主要证据目录为 `docs/evidence/r0-convergence-20261105`。`consent-live-findings.md`记录85b8b619失败细节；
`field-source-v6.md`记录修复与受控测试。UI-ready及R0-ready均未签署。

下方涉及653669fc本地基线、最初1024截断、尚无PG安装或首次初始化等描述，保留为历史记录；
不可忽略后续同版本证据，也不可将旧版成功与新版实现拼成同一候选通过。

## 2026-11-05 赛事交付要求（用户提供原文，C0 独立追踪）

赛题为“大模型智能体关键能力技术创新赛”。以下具体规则来自用户本轮粘贴内容；
报名/提交截止暂按 **2026-11-10** 安排，精确时刻、时区和提交平台最终状态尚待官网核对。
页面中的结果公布/总决赛日期为 NAN，不能作为日期；正文“12月深圳”是拟定安排。

用户已明确选择方向3“开放赋能智能体”，官方赛题入口为
http://www.aiinnovation.com.cn/#/trackDetail?id=160 。将一次目标驱动的工具执行转成可复用应用，
用材料、计划、执行反馈、结果核查、复用与恢复证明价值。保持通用产品定位，
选择清楚的实际问题作为验收场景；不因参赛而删掉既定 P-A/P-B 或 Windows 交付目标。

| 评分/要求 | 必须提供的证据或产物 | 当前缺口 |
| --- | --- | --- |
| 完整性30% | 同源 Windows 应用、首次配置、任务/导出/重开、复现步骤、失败边界 | 开箱初始化、完整原生用户路径、同版全链仍未关闭 |
| 实用性40% | 有明确用户与问题的任务集，独立预期、正确率/完成率、人工介入与时间用量 | 现有合成CSV/文本不足以证明实际场景价值 |
| 技术难度30% | 书生真实规划/工具反馈/生成复用记录，持久执行与权限恢复机制 | 普通LIVE文本链已有限证据；P-A本轮截断，P-B完整门仍未通过 |
| 技术文档 | PDF，含架构、创新点、实测结果、限制、复现及体验入口 | 待最终候选冻结后生成，不提前写成已完成 |
| 介绍视频 | 5分钟以内、至少720P、网盘链接 | 待实际可演示主路径；接收方须能打开 |
| 应用体验链接 | 提供可访问的体验入口 | Windows下载/试用入口能否满足平台口径待核实；不因此改回浏览器产品 |
| 关键代码和模型文件 | 内层ZIP；模型来源/权重说明，过大文件按要求提供Word/TXT下载链接 | 使用官方API时的模型文件提交口径待主办方确认，不自行宣称豁免或打包他人受限权重 |
| 外层ZIP | 单位简称-作品名称-队长姓名-队长手机号-日期.zip | 真实报名信息与最终命名在私有交付步骤填写，不写入公开源码 |
| 合规与访问 | 团队不超过5人、同题不重复参赛、原创/许可说明、接收方权限检查 | 主项目及第三方分发许可清单、最终链接核验未关闭 |

赛事允许任意 harness；MCP、A2A、多智能体等为可选技术，不为凑名词引入无用依赖。
API提额材料需备注“兴智杯+团队名称”；本轮不自动提交提额、报名、上传或对外发布。
软件包和演示材料不得包含开发者 API key、数据库密码或本机 DPAPI 文件。
先推进真实任务闭环、截断问题与普通用户安装体验，再做最后视觉细化与参赛包装。
本节记录参赛要求，不将 C0、UI-ready 和 R0-ready 混为一个通过结论。

### 用户确认的近期交付节奏

用户进一步明确：前端沿用已认可的视觉版本，优先跑通软件流程和功能，停止非必要的细节打磨。
后续界面修改限于阻断操作、误导状态、明显溢出或首次使用所必需的部分；
权限、数据完整性和真实结果校验继续保留，不以放松这些检查制造“能用”。

按2026-11-05起的两天优先完成可演示Windows候选，随后录制5分钟以内视频。
这是交付优先级与目标时间，不是未经验证的完成承诺；不缩减原UI/R0目标。
先解决真实任务/应用生成的阻断与首次使用，再完成演示主路径的界面和稳定性。
停止无验收收益的首页反复美化、额外技术栈与装饰扩张。

录制前必须冻结同一源码/安装包，走通启动、材料导入、目标执行、结果核对、应用复用、
导出及关闭重开；演示数据/模型/人工确认须真实注明。P-A响应截断仍是当前阻断，
不能以固定CSV或普通文本读取得出两条生成路径已经通过。
先制作演示步骤与独立预期，再录制真实操作；失败和未完成功能不剪辑成成功。

用户后续明确授权：新建 P-A 生成合同可以采用单次4096 tokens输出上限。
范围只限新的版本化 P-A 合同；保留最多3次调用、总预算64000 tokens、300秒期限和全部校验。
旧合同、旧批准、旧失败与普通任务默认限额不修改。实现须让范围准备、批准、Run冻结、
预算预留、实际发送与证据回读共同识别新版本，不能仅修改请求中的max_tokens。

## 2026-11-05 用户最新决策：Windows 桌面应用优先

后续明确授权：用户同意在 E 盘建立 Sim2Act 专用 PostgreSQL 实例，不改其他数据库。
安装、独立角色初始化与本项目迁移可在该专用实例内执行；不把此授权扩展为操作未知已有数据库。
拟使用 `E:/Github/Sim2Act/.local/postgresql16` 独立目录，先核端口占用和服务身份，
凭据不写入仓库或报告。用户也已允许原生窗口自动化；当前候选已完成一次启动/正常关闭，
并重开到同一回环地址和同一合成身份，尚不等于业务数据冷恢复或正式 PG 验收。

性能与后台运行约束：专用 PostgreSQL 不注册开机自启服务或登录启动项；采用按需运行。
正式桌面需整合自有数据库的启动/停止，退出时验证实际停止；无法确认停止须准确提示，
不得强杀其他数据库或删除锁。用户未运行 Sim2Act 时不应留下其 API、Worker、数据库常驻。
需实测空闲/任务/退出后的 CPU、内存、磁盘与进程状态，不能承诺未经测量的“游戏零影响”。

普通用户交付约束：最终应用包应包含数据库运行依赖并管理自己的首次初始化，
不要求用户另行下载 PostgreSQL、手写连接串或手动起服务。数据库运行目录与用户数据分离，
升级保留数据；原有外部 PG 配置方式可保留为高级入口，不能成为普通用户的必经步骤。
当前尚处于实现阶段：运行时归档筛选脚本已有离线边界检查，但一体化初始化、托管生命周期、
升级/备份及完整安装体验仍待实现与原生验收，不能据此宣称已经开箱即用。

本节是用户对《前端完善与 R0 收敛计划》的执行范围修订，优先于其中与本节冲突的执行安排。

- 本轮目标是可独立启动并完成实际工作的 Windows 应用。暂停 Linux 的开发、打包与验收；保留已有跨平台代码和历史证据，不为此破坏底层实现。
- 默认交付入口必须是 Windows 应用窗口（现有 C# / WebView2 宿主），不是外部浏览器 URL。浏览器仅作为内部调试工具，其测试不能代替宿主验收。
- 复用现有 configured supervisor，由宿主整合 API / Worker 的启动、就绪、停止与异常反馈；普通用户不应手动打开终端启动服务。不删除权限、租约、批准或恢复检查来制造一键可用。
- 将 Windows 同源构建与宿主验证提前，与前端主路径收敛共同推进：应用入口、图标、窗口、实际模型接入、明确的配置/登录、材料导入、任务与结果、导出、关闭重开及错误恢复须形成完整路径。
- PostgreSQL 等必要条件应有明确的准备与诊断流程；存在缺项时在应用内准确说明。是否自动安装/迁移仍遵循用户授权，不隐式操作原有数据库。
- 最新用户已提供书生密钥并授权模型测试。凭据仅保存在项目外的当前 Windows 用户 DPAPI 加密文件；报告不含密钥。历史“额度耗尽”不作为本轮禁止调用依据，原产品预算与精确任务批准继续保留。
- UI-ready 必须包含 Windows 宿主中的主路径体验；R0-ready 仍需同版本正式环境与完整 AT 记录。仅网页截图、连通测试或一个能弹窗的 EXE 均不足以宣称完成。

下一交付重点：核对当前宿主构建输入 → 生成同源 Windows 候选 → 原生窗口启动与生命周期 → 在应用内完成任务/导出/恢复 → 分别出具 UI-ready 和 R0-ready 结论。

## 2026-11-05 当前收敛状态（保留以下历史记录）

本地候选基于 `653669fcf67965d3b3c8877336b3289746b5d00d`，分支为
`codex/ui-review-followup`，包含未提交前端改动，不能将其归为 main 已发布能力。
执行依据为用户提供的《Sim2Act 前端完善与 R0 收敛计划》。UI-ready 与 R0-ready
分别验收；历史 221 项检查及截图不代替当前版本完整组合验收。

- 配置式 supervisor 已存在于 `src/sim2act/desktop_service.py`；Windows Host
  `scripts/windows/Sim2ActDesktop.cs` 已有 Configured 分支。
- `scripts/package_windows_portable.py` 已有 `--configured-runtime` 与 PostgreSQL
  驱动装配逻辑；详见 [ConfiguredDesktop](ConfiguredDesktop.md)。旧 042 包的缺口
  不能扩大为这些新源码尚未实现，但新同源包、正式 PG 和目标 Windows 联合验收仍未关闭。
- `scripts/Test.ps1 -Suite R0` 仍明确拒绝；完整 AT 用例注册与同版本执行证据尚未完成。
- FE-00 已核对上一轮四份源码哈希并保存源码快照；完整页面能力矩阵仍待完成。
  FE-01 正在审查结果绑定，新增缺标识、重复记录及跨运行/实例/版本反例。
- 下列早期阶段表、预算记录和失败属于各自历史范围，不表示当前全部实现现状，
  也不构成追加模型调用、CI、数据库变更或发布授权。


2026-10-07 subsequent NL UI/confirmation: exact117bb5db2d2161e6a6f346eecd289cd6f1fc11bc connects saved goal→strict planned-runs→validated exact plan→explicit confirmation→actual durable receipts/history. New valid plans stop WAITING_APPROVAL0Operations; defaultdisabled or selected-but-LIVE0 is honestly blocked. Targeted250unique249PASS1explicitPGroleSKIP68.34s, five actualHTTP/fullDOM paths42/8/8/7/8 checks and9loadedJS hashes, independentbackend14actual LIMITEDPASS and corrected UI staticPASS. Protected Chromium aborted due installed SUID configuration; JSDOM is not native/visual evidence. No newLIVE/full/PG/native/CI or R0/P-A/P-B acceptance. [Stage log](F2/NaturalGoalUILog.md) and [proposed two-hour real-model acceptance](F2/NaturalGoalLiveAcceptanceProposal.md), not authorized/executed.


2026-10-07 bounded natural-goal planning: final source `82a3ef838807c1b7540232671f68bf09408ffafd` adds the explicit saved-goal planned-runs API → frozen provider/schema/budget → strict received plan → durable registered read-only tools/receipts. Production provider defaults disabled; intern-s2 selection still has zero LIVE allowance. Final targeted 225 PASS/1 isolated-PG-role SKIP/226 unique, 41 new planning cases; independent21 PASS on eight byte-identical product files. Source/collection/JUnit/original failures retained. No new NL UI/browser, full/new NL PG/native/CI/LIVE or semantic/owner acceptance. Earlier full7854 is a different source and is not a full test of this addition. [Plan and log](F2/NaturalGoalPlanningLog.md); P-A/P-B/R0/F1/AT02/Win11 remain open. Optional metrics b89 is separately merged with no core/conftest/workflow changes; Windows900 remains NO_GO.


当前基线：V5；F1 IN_PROGRESS，两个 MOCK 工程增量已验证，尚未通过阶段门。仓库开发分支：dev/f1-foundation。

规范：[平台产品设计](平台产品设计.md)、[分阶段开发计划](分阶段开发计划.md)。
来源：[V5 原始文本与校验](sources/V5/manifest.json)。原始正文完整保留；修订见 [DocumentReview](DocumentReview.md)。

| 阶段 | 状态 | 当前证据 |
| --- | --- | --- |
| F1 | IN_PROGRESS | [任务](F1/Plan.md)、[日志](F1/Log.md) |
| F2 | PARALLEL_ENGINEERING / 正式准入 BLOCKED | 用户授权隔离并行 [CSV 草案预览切片](F2/Plan.md)；不是完整 F2 或发布签收 |
| F3 | PLANNED | 独立真实评价等待原阶段前置 |
| R0 | PLANNED | F1—F3 通过；禁止执行任意模型生成代码 |
| C0 | BLOCKED | 截止、体验链接、托管模型文件要求从 F1 并行核实；R0 后最终验收 |
| F4—F7 | PLANNED | 本轮不实施 |

目标平台为 Windows 11 x64 原生 + PostgreSQL，尚无用户环境实测。Windows Server2025云原生工程已通过：六PowerShell接口、独立API/worker、PG111项及清理；[实际证据](F1/WindowsCI.md)。Server和云端Linux工程测试不等于 AT-01/27 通过。
Server CI可复现性收敛已完成：独立完整Windows版本锁、pip check/精确包集合核验、真实首次py-launcher Setup通过；本轮一次CI成功（df31fe9），原Linux锁、V5来源哈希与历史失败保留。F1整体及Win11门仍未签收；后续用户授权 F2 隔离并行预览工程，正式准入仍 BLOCKED。
独立审计后：[owner环境继承缺陷的本地修复](evidence/F1-env-isolation-20261005/README.md)及PG114项回归已完成，修复后的Windows CI未运行；Git认证阻塞时不重复push。旧公开运行成功不替代这项隔离复验，111计数仍为开发方日志证据，F1安全准入待复核。
运行后端仅书生；2026-10-05在已授权安全注入与有限预算下完成合成LIVE只读反馈子链，完整LIVE验收仍未通过。10次HTTP预算已耗尽，停止真实请求；缺新预算时真实调用BLOCKED，不发现隐藏凭据。
保持项目、应用、资源三个工作区；应用发布与两条生成路径在 F2 实施。

## 最小待确认

- 参赛主体/成员、准确截止时间与时区、体验链接接受形式、托管 API 模型文件要求（F1 并行；未核实 BLOCKED）。
- 用户 Windows 环境及数据库安装条件（BLOCKED，仅影响原生验收）。
- 后续书生调用需新的明确预算；已完成的合成LIVE子链不授权追加请求（当前剩余0）。
- 授权真实材料与独立验证者（F1 收集条件，F3 评价）。

当前工程证据：[F1 TestReport](evidence/F1-TestReport.md)、[架构与限制](F1/Architecture.md)、[LIVE能力缺口](F1/capability-report.json)。Windows、LIVE、完整AppManifest编译和R0目标验收尚未通过。

工程源码提交：[f496f22](https://github.com/T1doo/Sim2Act/commit/f496f225ae109e4415cff3a1fa8117451a82fda3)（MOCK底座，F1未验收）。

第二工程增量：[契约语义](F1/Contracts.md)、[人工核对](F1/Reconciliation.md)、[实际检查与离线探针](evidence/F1-2-TestReport.md)。64 项 PostgreSQL 工程检查通过；LIVE/Windows 和完整发布门仍未通过。

第二增量工程源码提交：[637cca9](https://github.com/T1doo/Sim2Act/commit/637cca93aeb7022cb1062c73bb43ff40cab9c29d)。

第三工程增量：[F1/F2边界与验证前置](F1/Scope.md)、[90项回归及账本证据](evidence/F1-3-TestReport.md)。最小候选预检、手动Run冻结、可信本地未知效果核对完成；F1整体仍IN_PROGRESS，等待真实账号/原生环境及相关验收，F2能力未提前实施。

第三增量工程提交：[a38b98d](https://github.com/T1doo/Sim2Act/commit/a38b98d4d39712afcbf256fe7b697ce8ed16db8f)。

接入兼容修复：[模型身份规则](F1/ModelIdentity.md)、[111项回归证据](evidence/F1-model-identity-TestReport.md)。保留原返回Intern-S2并规范化为canonical；工程修复本身未消耗真实预算，随后独立复测结果见下方归档。

返回模型身份修复工程提交：[3707ef6](https://github.com/T1doo/Sim2Act/commit/3707ef63e249095d9ffabbb8a3671bd3099a0fc0)。

独立真实接入归档：[LIVE-20261005](evidence/LIVE-20261005/README.md)。测试源码精确提交dd195681；正常API/独立worker/PG两轮反馈子链最终PARTIAL/LIVE、答案42、resource.read VERIFIED。旧失败记录保留；累计10次请求，已知usage3143 tokens，预算耗尽。AT-02仅合成子项已验证，Windows、语义、F1整体门仍未通过；本轮不开发F2。

2026-10-05 后续用户决策：网络阻塞期间继续本地开发，开始 [F2 CSV 草案预览](F2/Plan.md)。固定可信模板、应用最小身份、声明式输入输出和持久预览历史；无 Release/业务写入、无模型请求。PG/Win11/完整 F2 验收保留，不以本地预览反向签收 F1。

2026-10-05 E11：[P-B可信PREVIEW来源受限提取](F2/PreviewExtraction.md)工程已交付；成功合成预览回执经独立oracle核查后绑定新CSV并冷客户端计算新结果。源码3d87f5e，ServerCI37340717581SUCCESS/PG208PASS/0SKIP，Linux203PASS/5SKIP。来源不是F1 Run签收；完整P-B/AT10/Release未完成。真实Chromium无可用沙箱而BLOCKED，Node/jsdom12项不替代浏览器验收；[精确证据](evidence/F2-preview-extraction-20261005/README.md)。原F1/Win11/AT02和真实预算0不变。

2026-10-05 E12：[现有两路径可用性收敛](evidence/F2-usability-20261005/README.md)已交付：独立只读旧基线复核4项缺陷，主开发修来源/模板接线/迟到选择/数值溢出失败，精确d3de155的ServerCI37343525441SUCCESS/PG219PASS/0SKIP。前端小范围样式和状态已改善，美观与手机一致性标准见[F2下一路线](F2/NextSteps.md)；真实视觉0/BLOCKED、20DOM不能替代截图。修复未独立复验，完整P-B/AT10/Release及F1/Win11未签收，模型0。

2026-10-05 E13：[来源请求锚定与回读恢复](evidence/F2-origin-recovery-20261005/README.md)已交付，精确4d01fb7/ServerCI37346429353SUCCESS/PG224PASS/0SKIP。5新专项、本地219PASS/5SKIP、DOM33明确非浏览器。完整P-B需先明示旧来源文件运行依赖、制定来源退休权限策略及完成合成task fixture，见[路线](F2/NextSteps.md)；当前未实施，不以冷页替代AT10。真实视觉BLOCKED、模型0、F1/Win11/Release未签收不变。

2026-10-05 E14：[合成完成任务来源与显式退休切片](evidence/F2-task-retirement-20261005/README.md)已交付，精确c776fa2/ServerCI37349609291SUCCESS/PG260PASS/0SKIP。36新专项及三表显式迁移/业务CRUD路径；本地254PASS/6平台SKIP，原33+新14DOM/HTTP不是视觉。owner显式清旧内容保留最小证明，当前source授权及target交集保持、撤权/过期拒绝，无grant恢复。仅LOCAL_DECLARATIVE_TASK固定合成来源/新内容冷会话子项，完整P-B/AT10/Release/F1/Win11未签收、模型0/真实视觉BLOCKED。

2026-10-06 E15：[来源退休与消费者PG串行](evidence/F2-retirement-race-20261006/README.md)已交付，精确53dc124/CI37411714116SUCCESS/PG269PASS/0SKIP，9真PG barrier/冷Store子项；LinuxPG268PASS/1WindowsSKIP、SQLite254PASS/15SKIP。基线grant锁阻止观察direct失效app，未虚写复现；消费者共享project锁和持久化前当前状态重验补强。冻结AT10合成子项映射不签收完整P-B/Win11/F1/Release，0LIVE/真实视觉BLOCKED。

2026-10-06 E16：[内部合成Release/Instance/AppRun生命周期](F2/InternalLifecycle.md)已交付，源码e029922/CI37413258268SUCCESS/PG302PASS/0SKIP；五表显式迁移及33新内部检查、原AT05进程回归保留。独立复验32PASS/1PGSKIP，两个schema缺口关闭；LinuxPG301PASS/1WindowsSKIP、SQLite286PASS/16SKIP。不可变快照/精确批准/独立instance结果账本/真实网关新AppRun/兼容升级回退历史，复用现runtime及Grant。正式发布入口/部署未启用，完整P-A/P-B/AT10/F1/Win11/protected browser未签收，0真实模型；[精确证据](evidence/F2-internal-lifecycle-20261006/README.md)。

2026-10-06 E17：[固定内部AppRun持久worker](F2/PersistentAppRuns.md)交付，精确源码8b14cee/CI37415214667SUCCESS/PG340PASS/0SKIP；38新项含4真实worker子进程及最低角色enqueue/控制/worker CRUD。复用现Run/Worker租约fencing/heartbeat，短事务取授权快照、事务外可信计算、当前Grant/Release/Instance重验后的原子结果版本+receipt+双终态，失联/暂停取消/unknown保守恢复。LinuxPG339PASS/1WindowsSKIP、SQLite319PASS/21PG平台SKIP；独立33PASS/5PGSKIP、source/test hash一致。[精确证据](evidence/F2-persistent-apprun-20261006/README.md)。无newGrant/preview复制/真实模型，正式发布/部署关闭，AT17受控写隔离OPEN，完整P-A/P-B/AT10/F1/Win11/protected-browser门仍未签收。

2026-10-06 当前来源生成切片：[成功 registered CSV AppRun → 可复用草案](F2/RegisteredRunGenerationSlice.md) 已按用户授权实施并独立审核，精确1413cbf/独立ServerCI37472996465 SUCCESS（559 PASS/1 SKIP）。服务端模板由可信成功回执生成，用户只选已有授权的新CSV应用与名称；冷worker新列新结果，不新增权限/表/模型请求。真实HTTP-DOM16与PG最小CRUD角色已测，生成入口原生UI/像素仍未验；不签收语义目标、完整P-B、F1/AT02/Win11/正式发布。[精确证据与失败历史](evidence/registered-run-generation-20261006/README.md)。先前独立UI修复9104b2a/CI37471361854已成功，新agent桌面/窄屏实际双像素审查通过有限当前捕获范围，旧空白根因仍UNKNOWN。


2026-10-06 本轮真实入口阶段闭合：普通push精确源码 `447b597fefd6c2a191ef4e9ff6d4bf2f0c06d3d5`，唯一原标准CI [37476996252](https://github.com/T1doo/Sim2Act/actions/runs/37476996252) 首次SUCCESS，无重试。Windows工程564PASS/2SKIP；原Edge38、旧agent33、新registeredGeneration29分别PASS。真实受保护浏览器完成源amount3→服务端草案→既有授权新CSV→人工确认版本→新实例冷worker quantity15/resultVersion1，并实测回执恢复、撤权、篡改、旧响应、跨主体/项目、空目标及窄屏。两次capture及最终实际保护审计PASS。两原PNG按stdout字节/SHA/尺寸与里程碑核验，主审及独立实际像素复审接受本次健康历史展示范围；runtime NOT_REVIEWED保留、人工审查另存。Report/Cleanup成功。最短说明补明预览列与新任务列分别设置，每次新任务需选quantity，历史刷新后amount默认不改变既有quantity15结果。见[证据](evidence/registered-run-browser-20261006/README.md)及[使用说明](F2/RegisteredRunQuickstart.md)。此有限原生入口缺口闭合，不提升Win11、完整AT02/F1、语义或完整P-B；旧空白根因UNKNOWN、失败历史保留、模型请求0。

2026-10-07 本地普通任务回执恢复切片：实际HTTP/DOM24项与相关47PASS，受保护Chromium启动BLOCKED且无截图；不push/CI、不带activation、不提升完整P-B/F1/Win11验收。[范围与限制](F2/TaskSubmissionRecoveryPlan.md)、[最终证据](evidence/task-submission-recovery-20261007/README.md)。

2026-10-07 持久任务历史定位：本地39项实际HTTP/DOM+4API、相关52PASS，独立两身份缺口复现后闭合；原生浏览器BLOCKED，PG/Windows未测，不push/CI/activation。[范围](F2/TaskHistoryPlan.md)、[证据](evidence/task-history-20261007/README.md)。

2026-10-07 final bounded source7854029: serial complete SQLite1267P42S599.26s and PG1305P4S1235.82s, each1309 unique actual collected cases; independent per-node/source/21actualPG-role/Report49/ownedcleanup audit LIMITED_ENGINEERING_PASS. See [final full log](F2/DeliveryGraphFinalFullLog.md) and [independent audit](evidence/final-full-preparation-20261007/independent-final/independent-final-audit.json). Windows original900/240/150 budget remains [NO_GO](F2/WindowsFinalBudgetAssessment.md); F1, Win11, AT02, semantic/owner and full P-B remain unaccepted. R0 readonly Doctor draft is isolated and excluded from this freeze; its dedicated realPG oracle is a later separate scope. Old failures,111JUnit missing, PGsafe rawSHA missing and DB-row NOT_EXPORTED are not overwritten.

2026-10-07 subsequent R0 bounded component6bbe28f: readonly Doctor catalog/authority checks integrated after7854 full; root45unit PASS0.46s/Ruff/mypy42src, dedicated23 PG16 PASS8.372s with independent LIMITED_PASS and unchanged23 before/after fingerprints. See [R0 phase log](F2/R0DatabaseReadinessLog.md). Overall R0 remains PLANNED/unaccepted pending clean Windows installation/restart/native/owner criteria; no new full/CI or permission bootstrap. Full7854 and later R0 scopes must remain separate.

2026-10-07 ordinary-user prerequisite: saved GoalCard version → actual durable read-only task implemented on02ddceb, normal API/worker, full frozen conditions and original acceptance/source anchors. Focused actual101 collection:100PASS1PGSKIP; controlledDOM27 + actualloopbackHTTP7, source/permission/version/erased-source/resume negatives. [Phase log](F2/GoalCardRunLog.md). This is no new full, P-A planner, provider activation, R0 signoff or successful P-B source. [Windows ledger/optimization](F2/WindowsFinalBudgetAssessment.md) remains NO_GO;0LIVE/no authority expansion, ordinary dev push with skipci.

2026-10-07 saved bounded activation stage: source9406e4e,304unique targeted303PASS/1PG-roleSKIP,19 independent local actual cases on byte-identical productc51. Default0LIVE persists; immutable exact synthetic scope/two-call budget/expiry/revoke code is verified offline. Migration/PG production concurrency, protected native, Windows900 CI NO_GO, full owner/semantic P-A/P-B/AT02/F1 remain open. No real-model approval is inferred; see docs/F2/NaturalGoalActivationLog.md and its conditional acceptance proposal.

2026-10-08受控条件分支独立候选：原F2-T04/产品§5.3，执行源码041cf8ec5fbfeffde6ee3103bba8a4188eb08861。既有只读Run/Worker/Operation及页面新增typed eq/in/exists、输入/已核前驱、持久跳过与冷重领；未产出必需报告PARTIAL。756冻结范围SQLite741P15S/PG755P1S，另实际子进程各1P；源码不变，候选待独审，不合已验dev，不签收通用运行器/原生/语义/完整P-B/owner/发布。LIVE0/原900-240-150/依赖/断言保持，无新CI/新权限。[范围与日志](F2/ControlledBranchesLog.md)。


2026-10-08受控分支＋所有权P2修复整合：父线程独审source6181bf7限定闭合（双端各28P、39拒绝轨迹）；原dev5bbc快进AEA，产品字节同已审版本，无新逻辑。冻结必要整合/三种真实旧源码升级40例每端40P0F0S，历史JSON字节保留，旧证明失效并重新精确确认；旧候选/失败证据保留，不机械重跑757/跨源码认证。额外旧清理目录查询失败限制及最低角色/原生/真实并发转移独审缺口保留；LIVE0、原900/240/150、新权限/部署/新CI均不变。开发整合不等于业务/人工/F1/P-B验收。[最新范围与指南](F2/ControlledOwnerIntegrationLog.md)。

2026-10-20 原F2-T08/AT-16有限接续：[本地记录实例显式兼容采纳](F2/LocalRecordReleaseAdoption20261020.md)补上本补丁新建v1实例一次明确采用同应用v2内容更正能力；同iid/record ID、旧事件/typed/Run/制品/工具回执和Grant保留，批准前缀指纹每次全投影重算，旧Run只读不能写。最终10后端+4实际HTTP/JSDOM页面PASS，源码独审两P2已闭合；原件及失败史见[证据](evidence/record-release-adoption-20261020/README.md)。旧软件迁移、新切片PG/Windows/native/真实模型语义、完整PB/G0与F2/R0及正式发布仍开放；无新CI/权限/部署。
