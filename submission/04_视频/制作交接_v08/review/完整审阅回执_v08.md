# Sim2Act：产品书与270秒影片交叉审阅回执
## 给 Windows 电脑端 Codex 的一次性修订与服务器交接任务

审阅日期：2026-11-08。输入基线：产品书v04／影片交接v07／故事事实v03／工程证据v02；用户指定材料提交 `1b2f7f106909a622a236dcf14325873991e716c8`。

**执行对象：电脑端 Codex。** 本轮先把产品书必要修订、动态分镜、实际参考原图、完整H3提示词和可校验交接包准备好并发布到GitHub，服务器再下载执行。不要让用户在旧Park文件、Sim新文件和不同版本指令之间来回搬运。

**已合并用户最新补充：已经认可的精美AI软件界面是可直接使用的定稿资产，不要求H3重新画。** 例如`A02_应用蓝图_v03.png`默认锁定原图内容；可以做整图展示、局部取景、精确交互和屏幕合成。要求动态丰富，不等于每个界面都要模型重绘。本文后续所有“生成产品视觉”均不得覆盖这一优先规则。

**本回执不是已经生成的视频，也不是产品功能验收。** 新镜头、新旁白、新参考图名均为修改建议；只有实际制作并检查后才能改记完成。

---

## 0. 总体结论与执行优先级

### 0.1 结论

产品故事成立。最有辨识度的内容不是“AI帮助整理申报材料”，而是：**把一次工作的专业方法变成有专用界面、动作、检查和权限的应用；换材料后重新运行，规则变化后受控维护。** P-A目标生成、P-B独立任务提取、T3依赖演进共同支撑这一主张，不能删成普通聊天助手或通用文档处理宣传片。

采用的UI原图已具有相对统一的蓝白淡紫、模块分区和清楚金额，大部分不应推倒重画。发布与运行分离、未知条件保留、旧结果独立等设计也已经比早期版本清楚。

**但是，v07还不符合用户已认可的Park ABC/A2动态宣传片制作方式，不能原封不动发给服务器批量生成。** 阻塞来自制作策略，而非缺少一句“更高级”的修饰词：

- 27个单元中只有S01是人物空间，S02–S27全部标成`T2VA_BACKGROUND_ONLY`。
- 其中24份H3提示词字节完全相同；S03/S27是另一份相同的深色背景提示词。
- 逐秒CSV的270行里，250行`within_second`为“保持阅读”。这不证明每一秒成片都完全静止，但证明导演表主要是在指定状态停留，而不是主体动作。
- 70张状态图只有61种不同SHA256；S06两个“阶段”与S10是同一图，S24三个“阶段”也是同一图。文字状态名称改变没有改变实际像素。

**执行顺序：先纠正对象与状态表达 → 重写动态路线和镜头动作 → 补必要的电影化参考图 → 重写实际H3提示词 → 输出统一可下载包。** 不要求重新开发产品后端，不新增赛事效果数字，不重做所有38张原图，不以第三轮样片审批拖住交接。

### 0.2 与Park保持同一标准，不复制Park的内容

沿用：主体实际运动、连续空间、少而精的后期文字、A2式无边框局部标注、统一字体色系、真实源分辨率记录、必要超分后再加字、清晰的生成与证据边界。

不要照搬：园区沙盘、会议室、设备车、接待台，以及Park的270秒以外时间线。Sim的动态主体应当是**科研协调人的工作、材料与应用结构的转换、同事独立复用、规则模块的受控替换、团队应用的使用**。

业务事实必须锁定；同时，用户认可的既有UI图片要作为`APPROVED_UI_LOCKED`直接保留，不经过H3重新绘制。允许生成的是人物、环境、动作、空间和必要的无字产品机制表现；既有UI通过后期合成参与同一镜头。关键中文、金额、版本、操作顺序、品牌与二维码由原图或确定性图层承载。几何取景与缩放不等于重画内容，但不得拉伸、裁掉关键语义或用AI超分改写文字。

---

## 1. 本次实际审阅范围与证据边界

| 材料 | 本次做了什么 | 没有据此声称什么 |
|---|---|---|
| 上传ZIP | 安全解压618个文件；核对公开清单列出的617项，大小和SHA256全部匹配，清单本身为额外1项 | 不等于618个文件全部逐行审计；旧版本只作必要对照 |
| 产品书v04 | 阅读16页正文并查看页面图；本地渲染检查；独立上传PDF与ZIP内PDF字节相同 | 未编辑原PDF；不是新版本验收 |
| 38张采用参考图 | 实际查看全部原图的可视内容与分组图，并对关键状态、数字和条款局部放大；分类为34张正式设计、2张技术图、2张原始工程截图 | 不把正式设计图当实际产品运行记录；不保证每个装饰像素均无瑕疵 |
| 70张状态图 | 实际查看全部合成图；全部1920×1080，哈希匹配；识别重复图与状态上下文问题 | 70张图不是70个已执行动作，更不是70条视频 |
| 技术图 | 查看ARCH-01、T1-01、T2-01、T3-01、T4-01五图 | 不等于相关机制已实测 |
| 影片文本 | 阅读27段制作说明、27份H3提示词、270行导演表、时间线JSON、上传映射、旁白、字幕与配音规范 | 未运行H3，不承诺其能逐像素命中参考图 |
| 缩小阅读 | 制作并查看S12_02、S23_02等关键720p检查图，结合原生图核对 | 不是整个影片全部帧的对比度认证 |
| 工程证据 | 阅读脱敏账本说明、用量、输入与成果；检查脚本后在独立副本运行`verify_evidence.py`，原材料不改 | 未调用模型、未启动数据库、未重跑业务、未验Windows |
| 音轨与预演 | 读取HTML渲染逻辑；WAV确为270秒、16kHz单声道；52块SRT无重叠、最多两行、每行最多21字符 | 本轮未试听临时音轨，未完整实时播放HTML；不能评价正式声音品质 |
| 外部规范 | 复核MiniMax官方H3提示词SKILL和base/ref格式 | 格式规范不等于当前服务器支持所有模式；赛事规则按用户给出的评分口径，未另做官方最新赛规认证 |

所有关键上传文件均可读取。GitHub公开PDF链接通过本次web读取未成功，但上传PDF完整可用，不影响16页审阅。未检查的Windows实际启动、全量产品源码、新模型调用及正式音视频不得写入“本轮通过”。

离线证据核对得到：5次请求、17,336 tokens、6条引用切片、90/94字节两份输入、同一限定发布与同一实例的两次结果修订；三个篡改负例均被拒绝。此结果只证明随包记录内部一致，边界保持`PASS_OFFLINE_RECORD_CONSISTENCY`，不是供应商独立背书或中文申报全链路通过。

---

## 2. 按评分维度审阅产品设计

本轮不报看似精确的总分；方案吸引力与运行证据覆盖范围必须分开。

| 维度 | 当前支持 | 需要加强 | 修改位置 |
|---|---|---|---|
| 实用性40% | 申报协调人、指南预算附件、甲乙新输入、规则改变均具体；不止一次问答 | 第一眼仍可能被理解成固定“科研申报助手”；需更早展示“此应用由目标形成、同事只换材料”及明确交付物 | PDF1–2、11–12；S01–S05、S15、S25–S26 |
| 完整性30% | 发布/运行/新结果分离，P-B独立来源与历史有事实源；证据可离线复核 | 当前视频准备对实际动态生成不完整；检查报告阅读时间不足；Windows开发预发布不能表述成已签收成品 | PDF7–9、13、15–16；S13–S23；交接manifest |
| 技术实现难度30% | 字段—动作—视图同源、单位拒绝、轨迹去旧绑定、依赖演进、未知效果核对均有明确机制 | 四机制不应变成连续框图；需要演示一个对象怎样穿过这些机制，保持“设计例”与限定工程轨迹不同 | PDF3–10、14；S05–S10、S16–S24 |

要保留技术深度，但将观众记忆目标收束为三句：**构想变应用；换材料可复用；规则变化可维护。** T1–T4负责解释这三句，而不是四套彼此独立的炫技名词。

---

## 3. 问题工单：P0必须修、P1重要改进、P2可选

证据标记：`图`=本次直接查看；`文`=源文/JSON确认；`码`=生成或预演代码确认；`待验`=需要实际成片或运行才能确定。

### P0：服务器正式生成前必须处理

| ID | 位置与证据 | 具体问题 | 修改与验收 |
|---|---|---|---|
| P0-01 | `制作总览.md`、`影片状态时间线_v07.json`、S02–S27提示词；文/码 | 26段背景限定，主体被固定UI遮盖；继续执行必然偏向轮播 | v08重新声明生成主视觉／定稿UI直用／精确交互／工程证据四类路线；保留好的UI，不把所有镜头默认成背景限定，也不反向要求所有镜头重新生成；每个生成单元写明主体动作，每个UI单元写明阅读目的和前后衔接 |
| P0-02 | `逐秒导演表_v07.csv`、状态图S06/S08/S24；文/图 | 250行保持阅读；相同像素被命名成多个阶段；文字“光点/高亮”未在状态图中体现 | 表中分开动作、对象状态、相机、精确文字、剪辑。阅读停留可保留，但不能把状态名称改写当作已实现动效；不能把静态预演叫动态小样 |
| P0-03 | S16 150–153秒，`S16_01.png`；图/码 | 正文是P-A甲乙历史，页头却写“任务·申报材料核查”，提前绑定到P-B | 为每个state设显式`context`与对象ID；150–153保留“科研申报助手／授权案例历史”，153秒切独立任务后再切任务上下文。修时间线和`renderFrame`，不能只手改一张PNG |
| P0-04 | S18 170–180、S20 190–200；文/图 | 发布未运行的必要状态已存在，但阅读太短；运行覆盖层下仍透出“尚未运行／等待首次运行”，状态相互竞争 | 缩短非必要等待，把未运行状态留足辨识时间；运行时精确替换本次核对区域状态，不靠透明busy层让旧状态仍可见。具体秒数按§7同步更新 |
| P0-05 | S22/S23与PDF13；文/图 | 当前证据段是有限英文短文本工程切片；动态升级后最易被替换成漂亮但虚假的中文成功界面 | 保留原截图像素和真引用；证据段不交H3再绘，不改变PARTIAL、INTERNAL_ENGINEERING_ONLY、语义未验收与人工待签收。现有设计UI继续作为设计说明，不扩大证据 |
| P0-06 | 全片交接、片尾、H3模式；文/待验 | 旧包30fps，Park已验生成链24fps；“每段10秒”未区分编辑长度和模型实际输出。也未证明服务器支持I2VA | 明确`edit_duration`、`requested_generation_duration`、`actual_duration`与fps；建议v08主时间线24fps、270秒=6480帧，正式选择后全文件同步。模式以现场可用Ref2VA为优先，不假定I2VA/FL2VA已部署；禁止靠改fps头、循环或长定格补时 |
| P0-07 | GitHub交接与旧版文件并存；文 | 服务器可能继续从v07读取背景提示词或误把70张状态图当主镜头 | 新建独立v08根目录、唯一入口和一个镜头manifest。所有采用资产、提示词、图层均有相对路径和hash；标旧版仅归档，READY包不得包含悬空输入或未声明缺失项 |

### P1：同轮完成，不另开风格研究

| ID | 位置 | 问题与改法 |
|---|---|---|
| P1-01 | S01–S03，0–30秒 | 人物在看屏幕，但谁和为什么要复用主要靠抽象旁白。开头明确申报协调人；让第二套材料进入同一个应用入口的预告在30秒内出现，不展示新的真实运行成功主张 |
| P1-02 | S02与S04，10–20/30–40秒 | 同一目标页逐字节重复。S02改为桌面材料与同事交接情境；S04才表现目标进入专用工作区 |
| P1-03 | S06/S10，50–60/90–100秒 | 同图讲两次绑定。S06讲单位化后的输入如何进动作，S10讲同一输出如何驱动表单/按钮/结果面；画面动作和景别必须不同 |
| P1-04 | S17 169–170秒 | 五项范围检查报告只给1秒。把检查起点提前、报告在167秒出现，至少保留约3秒；可突出“旧依赖解除／新结果归属／业务待确认”三重点，五项完整版留报告 |
| P1-05 | S12与S22/S23 | S12条款已可读，不要再重画整页；工程并列图在720p能读大引用，细注不适合同时逐行读。每次只突出一组原句与结果，不重写原证据像素 |
| P1-06 | S21 200–205秒 | 当前结果3页面顶栏提前显示“授权案例历史” | 当前结果保持“项目甲／结果3”，205秒历史打开后再显示历史上下文；和P0-03共用state级修复 |
| P1-07 | S26 254–260秒 | 打开应用直接落到已有结果3，易读成“打开即运行” | 打开v2尚未运行页，或明确进入“查看最近结果3”并保持历史标识；不要额外生成新run |
| P1-08 | S24旁白 | “不重复写入”容易被听成所有外部工具恰好一次保证 | 改成“回执未确认，先核对原操作；不盲目重发，也不把未知当成功。”图内仍分回读、权威无效果、未知三支 |
| P1-09 | S25 240–250秒 | 两张密集应用页各5秒，场景价值主要靠字幕 | 5秒活动账目关联、5秒实验配置对照，配短对象镜头；保留8000净额、600退款、3项差异互不相加，seed差异不变成因果结论 |
| P1-10 | 全片字版 | 现有规范多是字体与字幕大小，未有场景标题/物体标注/重要数字统一布局 | 沿用Park A2原则，重做Sim专用tokens与safe zones；每镜最多一个局部说明重点，标题和标注分时出现，禁止默认drawtext堆字 |
| P1-11 | 新参考图与来源 | 现在只有一张人物场景，其他多为完整UI；不够支撑真实动态 | 按§8补有限场景母版与开始/发展/结束构图；禁止从大UI裁几百像素小块放大充当高质量电影参考 |
| P1-12 | 配音/字幕与270秒 | 临时旁白每10秒重新起句，统一+0.2秒发声；可能形成机械节奏 | 保留一条声线与事实，按章节连续录制；无需每10秒重起。S02临时发声约9.30秒，不再加词。按正式录音重新对齐SRT |

### P2：有余力再做，不能阻塞交接

- 产品书第2、11页分别侧重“工作方法复用”和“案例因果”，减少重复内容；不大改16页结构。
- ARCH/T1–T4在产品书中可升级更清晰矢量排版；影片改分层展示，不用精力给整个框图套一层昂贵玻璃。
- 片头片尾减掉部分纯装饰光带，保留Sim图标与品牌色；不用额外设计新Logo。
- 主体人物完整脸部只在有必要的镜头出现，其他采用手、背侧和应用的自然景别；不为面部一致性反复重生成全部素材。

---

## 4. 产品书逐页保留与修订

当前16页整体版式可用：没有在本次阅读中发现需要整本重排的裁切或缺字；正文结构比影片更成熟。不要把“视频动态升级”误解成“重做产品设计”。

| 页 | 结论与动作 |
|---|---|
| 1 | 保留主张、Sim2Act图标、品牌色。封面已经明确申报协调人，影片应跟上。副标题可保持，增加的解释不超过一句 |
| 2 | 保留“同事接手时只换材料”和首次构建成本。把痛点写成待验证的具体工作假设，避免听成已经访谈所得统计结论 |
| 3 | 保留P-A/P-B汇入同一应用定义。ARCH图区分规格→视图/工具/检查，影片无需同时显示全部文字 |
| 4 | 保留4+3.5+1.5万元→90,000元、UNIT_MISMATCH、禁止结果回填输入。不能把该设计例说成已发生的真实模型错误修复 |
| 5 | 保留书生选择、类型检查、工具反馈、受约束修订；删除影片中重复的全图静置，以一个有因果的对象路径解释 |
| 6 | 保留budget_total与budget_limit分离。图可作为精确校对底稿，视频不必整页停10秒 |
| 7 | 发布与运行分离做得清楚，保留。说明“发布的是核查工具，不是审批资格”，对应片中短状态，不堆免责字幕 |
| 8 | 保留独立一次性来源、参数化、旧文件不注入新上下文。P-B提取与P-A复用不能剪成同一来源 |
| 9 | 保留甲预算9万不变、上限10万→8万、超限1万。让新版本与新运行显式相继发生 |
| 10 | 保留三支核对语义；不新增通用exactly-once承诺。影片只突出原操作身份与不盲重发，不全文朗读英文状态 |
| 11 | 申报指南为自编规范的说明必须留在产品书。负责人在岗证明缺口和签字页缺失不是同一个问题，不能补签字页后把资格变绿 |
| 12 | 保留应用库责任人、适用输入、版本及两个扩展场景；补一段最小部署/维护责任，避免“应用库里有卡片”被误读成每种场景实测 |
| 13 | 证据完整性较好。保持五次用量、两次墙钟耗时与未验范围；正文可把耗时显示约203.90/249.81秒，精确数保留附表，不改统计口径 |
| 14 | 保留“比较方案/已测结果分列”；不得新增优胜百分比。未独立复核的新外部文献结论不扩写 |
| 15 | “按提示完成本机配置”与“首次使用待验收”应放在相邻位置，减少用户误读；不改为已验证开箱即用 |
| 16 | 保留Release与源码入口；视频链接待正式成片后填写。添加/维持“Windows开发预发布”短标识，扫码到下载页而非冒充成片链接 |

### 可直接替换的重点短文

**第1–2页定位补句（修改建议，不是新增实测事实）：**

> Sim2Act不只替用户完成一次材料核查，而是把目标、输入、工具动作、检查规则与使用界面组织成一个可重复运行的小应用。科研申报是本片的贯穿设计样例：同事换入自己的材料，得到独立结果；规则变化后，更新相关定义，而不是重新描述整套方法。

**第3页机制短文：**

> 两条入口汇入同一个有版本的应用对象：P-A从目标与材料生成候选，P-B从独立任务中提取稳定方法并解除旧文件绑定。书生负责理解、选择与修订；类型、权限、引用和数值检查约束候选；运行器执行已确认动作并保存可核对结果。专用界面是这份定义的使用入口，而非独立拼出的演示页面。

**第12页落地责任补段：**

> 团队负责人确认应用用途、适用材料和共享范围；领域人员维护指南、规则来源与人工判断分支；技术维护者管理运行环境、模型凭据、工具连接、版本与故障处理。首次部署先选择一项高频材料工作，分别记录构建、检查、培训和后续复用成本，再扩展到新的场景。上述为实施设计，不代表已经取得付费客户或完成组织部署。

**第15页开头替换：**

> 公开仓库提供源码与说明，Release提供Windows开发预发布包。下列为该版本的拟体验路径与依赖说明；包体可下载和EXE已构建，不等于全新Windows上的首次配置、窗口生命周期及完整业务流程已经验收。实际执行范围以随包记录和当前软件反馈为准。

---

## 5. 必须锁定的事实与镜头语义

沿用`故事事实源_v03.json`，不改数字以适应画面。新文件只同步必要的事件时间和展示上下文，维护业务字段与事件时间的独立差异。

| 对象 | 正确内容 | 禁止混写 |
|---|---|---|
| 项目甲 | 40,000+35,000+15,000=90,000元 | 不能把应用升级说成预算降为80,000 |
| 项目乙 | 30,000+28,000+18,000=76,000元 | 不复制甲的结果、实例或资料 |
| 原规则r1 | 上限100,000；甲余10,000；乙余24,000 | 数值通过不等于业务资格通过 |
| 新规则r2 | 上限80,000；甲仍90,000，超限10,000 | 不把超限画成预算已自动修复 |
| P-A结果 | 结果编号1=甲/v1/r1；编号2=乙/v1/r1；编号3=甲/v2/r2 | 显示编号1/2/3不是应用版本，也不是跨实例修订号 |
| 实例内修订 | 甲结果修订1、2；乙结果修订1 | 不能把乙“结果2”叫第二版应用 |
| P-B | 独立一次性来源，自己的应用v1/r1，新输入结果PB-01 | 不是P-A结果1再包装；来源轨迹不等于旧内容可注入新推理 |
| 两种缺口 | 签字页材料存在性缺口；负责人在岗证明的资格证据缺口 | 补前者不自动消除后者 |
| 工程记录 | 同实例限定版本；结果修订1/2；英文90/94字节输入 | 不与故事甲乙结果编号串为同一实际运行 |
| 活动运营 | 8,000净额、600退款、3项差异分别列 | 不再从净额扣一次退款，不相加差异金额作为收益 |
| 实验复盘 | seed42/43与其余条件并列 | 不仅凭seed不同宣称导致结果变化 |

三条事件偏序必须机器检查：

1. P-A：范围确认 < 发布请求 < 已发布未运行 < 点击运行 < 本次结果。
2. P-B：独立来源 < 提取 < 新输入检查 < 报告 < 范围确认 < 发布 < 另行运行 < PB-01。
3. T3：新规则 < 影响与隔离预验 < 用户确认更新 < v2发布 < 新运行 < 结果3；结果1始终保留v1/r1。

显示“样例预览”或“隔离预验”时可以有预览数值，但必须与实际保存结果的身份明确分开。不要因为预览出现90,000就误判成业务已经运行；也不能将它剪成真实运行证据。

---

## 6. 新影片制作方式：生成主视觉，不再只生成背景

### 6.1 四条制作路线（用户补充优先）

- **G / 主体生成**：H3生成连续的人物、工作空间、物体与必要的无字结构变化；不重画已定稿UI。可表现材料被整理、同事交接、规则模块的隔离更新，但不能只用漂浮方框或无关办公室人物替代产品机制。
- **U / 定稿UI直用**：用户认可的原始UI以`APPROVED_UI_LOCKED`身份进入剪辑，可以是主要产品画面，不只作为模型参考。采用原比例整图、适度局部、可编辑遮罩、高亮或屏幕贴合。不得重写文字、数字、按钮、图标和原有状态。补正已有确证问题时只改指定状态图/区域，保留美术与原版。
- **P / 精确交互**：发布、确认、运行、金额、资格条款等使用确定性组件或有证据来源的原操作素材。可以用实际可播放的HTML/合成动画，但应明确这是设计演绎，不假称产品录屏。不是每秒换一张全屏PNG。
- **E / 原始工程证据**：S22/S23保留原像素、原字段、原输入与结果关系。只做裁切、阅读布局、引导与剪辑，不生成或美化成另一份“运行结果”。

G、U、P、E可按叙事组合，不需要每镜都调用H3。允许高质量UI作为主要产品阅读画面，不能为了凑动态占比把它重画。原先“约三分之二动态”的目标降为整片观感指导，不是生成配额：既不通过背景微光伪装主体动态，也不因使用原图就判不合格。一个镜头有明确阅读/操作目的、与前后场景衔接合理即可保留。不要为了消除所有静止时刻剥夺阅读时间。

### 6.2 本次禁止的快捷替代

1. 全片批量使用同一“边缘微光+居中截图”模板；单个精美UI整屏阅读不受此禁止限制。
2. 将“框选一下、镜头推近5%、切下一图”当成所有镜头的动作。
3. 把新旧应用页面形变融合，导致文字、版本或结果先于操作出现。
4. 用办公人物镜头覆盖所有技术点。有人走动也不能替代“应用怎样形成”。
5. 把粗糙SVG框图换成相同布局的三维玻璃框墙。需要新的场景组织，不是同图加厚。
6. 给服务器一堆“可能参考”的图，却不指定每张图的角色；或把已有v07轮播视频作为必须完整保留的节奏源。
7. 用`The clip lasts exactly 10 seconds`替代真实模型帧数、时长和模式核对。

### 6.3 动作描述的最低内容

每镜必须明确：**初态 → 主体动作 → 可观察变化 → 终态 → 与下一镜的空间/对象关系**。摄影机只支持这个过程，不替代它。相邻镜头可以剪切，不强求270秒长镜头或模型跨屏穿越。

仅对确需新生成的场景，优先用单张高质量构图母版确定场景，再按能力提供发展/结束图。定稿UI不因这一要求重新生成。三张图片保持同一场景，并不意味着模型支持三个强制时点；Ref2VA参考与真实首尾帧模式分开标记。不要把九宫格作为唯一输入。

---

## 7. 27个编辑单元的具体修订（保留总长270秒；UI直用已合并）

以下是v08建议，不是已有视频。为避免全部重排导致旁白和素材返工，保留S01–S27的10秒内容容器。容器内可包含连续生成、局部精确状态和合理剪切；不是必须27次模型调用，也不是每个源片必须刚好10秒。

| 单元/绝对时间 | 路线 | 修改后的可见动作与画面安排 | 必须保留/核查 |
|---|---|---|---|
| S01 0–10 | G | 同一申报协调人接过同事递来的另一套文件，放到原工作堆旁，转向笔记本；镜头横移揭示“又一批材料”，不用从头到尾慢推 | 延续A01人物衣着、办公室光向；屏幕细字不依赖生成；不是已完成申报 |
| S02 10–20 | G | 手从指南定位页移到预算、再核对附件；纸张和工作区有真实接触与遮挡。结束落到一个尚未建立的专用入口 | 不重复A01目标页；新情境是设计演绎，不是客户纪实 |
| S03 20–30 | G+U | 原品牌字版短出现；材料和工作动作的生成画面通过构图匹配接入定稿应用图，不让模型重画图标或整页；短预告同事换资料，最后回到目标入口 | 结果预告明确是产品预告；不加入已发布/已运行新事实；30秒内看懂“不是聊天，是应用” |
| S04 30–40 | G+U+P | 协调人操作与定稿目标页衔接；直接用A01目标与材料原图，指针/输入/高亮由后期控制，保留未决项。人物屏幕采用后期贴合或切到正面原图 | 不凭空补完目标与资格；与S02不同动作 |
| S05 40–50 | U+P | 直接采用用户认可的A02_应用蓝图_v03.png；整图建立结构，随后突出“目标与材料→动作规划→界面规划”的阅读关系。原图内容不变，不交H3重画；可与前一场景的显示器构图匹配 | 不把生成定义当成已调用工具；保留“草案/候选”含义 |
| S06 50–60 | U+P | 直接采用字段动作绑定原图，按一条明确的输入到输出路径进行局部强调；如果需要无字结构动画，短接独立G片段而不扭曲原图。未完成标准化不先表现真实执行通过 | 4/3.5/1.5万元与90,000等由后期精确呈现；输出不回流为输入 |
| S07 60–70 | P | 单位不符导致通路停止；显示具体字段、换算需求；修订后再让标准化金额进入求和。可以局部组件运动，不播整页轮播 | 使用现有拒绝/修订图逻辑；不声称这次错误真实发生于工程账本 |
| S08 70–80 | G+U+P | 用无字结构视角说明界面、动作与检查同源，产品面使用既有UI贴图；精确关联在后期完成，不让模型重写ARCH或应用定义。无需把所有框图同时摆出 | 两条入口不是两个互不相关产品；精确箭头若承载因果由后期控制 |
| S09 80–90 | G+P | 人手补入签字页，转到精确交互：添加→重新检查→材料结构通过；资格缺口维持琥珀 | 不能把签字页存在性当签章真实性；不能消除在岗证明缺口 |
| S10 90–100 | U+P | 从既有绑定原图取对应字段与按钮区域，突出定义与界面映射；用确定性选区响应或局部层合成，不生成另一套UI。与S06的数值路径区分 | 同源绑定是主信息；不再重复同一A02全图10秒 |
| S11 100–110 | G+U | 协调人查看应用，接入原A04发布前预览/科研申报助手定稿图；使用屏幕贴合或正面匹配剪辑，而不是让H3再次生成整个工作台。减少加载转圈 | 材料、预算、问题、提交准备四区有层级；预览并非正式执行 |
| S12 110–120 | P | 点击问题→来源区域展开→条款与缺证明两项并读→返回。尽量沿同一画面位置展开而非整页跳切 | 第2页2.1条文字、资格仍待确认；原图已较清楚，不要求重画 |
| S13 120–130 | P | 精确显示读写范围、用户确认、发布请求、应用v1已发布未运行；用状态区域变化而非整页淡入淡出 | 保留125确认、127发布、128未运行的现有事件或同步修订；不能自动进入执行 |
| S14 130–140 | G+P | 人点击运行后转向结果区域；130–132未运行，132–135运行，135后编辑性时间跳转到结果1 | 切时不暗示实际仅耗3秒；9万元与人工待确认分开 |
| S15 140–150 | G+P | 同事换入另一套材料，同一应用身份保持；精确确认范围、运行、独立结果2，旧结果1作为历史而非输入 | 乙76,000，实例不同；不把复用演成复制90,000 |
| S16 150–160 | G+P | 先用甲乙历史作结，再明确切到独立一次性任务。来源轨迹中的稳定方法被选出，原任务与成果留在原处 | 150–153上下文为P-A；153后才是独立任务，禁止来源身份混合 |
| S17 160–170 | G+P | 固定步骤留在提取框架，旧文件绑定离开新输入路径，新资料接入；最后给范围检查报告约3秒 | 建议164开始检查，167报告；旧文件可留追溯，不注入新上下文 |
| S18 170–180 | P | 读范围→确认→发布→明确显示未运行→点击新运行→时间跳转PB-01，操作与状态连续 | 建议172确认、173发布、173.5–175.5未运行、175.5运行、177.3结果；人工待确认保留 |
| S19 180–190 | G+U+P | 新规则进入的动作接到A08变更影响原图。需要强调的更新区用精确遮罩/局部图层处理；资料和旧成果原样保留，不让整页融化变形 | 10万→8万；设计预验90,000/超10,000标为预验而非新结果 |
| S20 190–200 | P | 审阅保留/变更→确认发布v2→明确未运行→按新版运行；不以画面闪烁表示全部完成 | 建议192确认、193发布未运行至195、195运行；200后才结果3 |
| S21 200–210 | G+P | 先展示结果3，再把旧结果1和新结果3并列成两条有版本归属的记录；保持同一甲预算不变 | 200–205是当前结果3；205以后是历史；应用v1/v2与规则r1/r2准确 |
| S22 210–220 | E | 原工程全景短建立，再放大一条真实原文与对应引用；页内缺口说明保留 | 不H3重绘证据；旁白明确是限定短文本工程记录 |
| S23 220–230 | E | 第二份原文进入同一限定实例，两个原始结果并排；用各自未决项结尾 | 结果修订1/2不是故事甲乙编号；真实原句保留、不造性能结论 |
| S24 230–240 | G+P | 一个有身份的操作被派发，回执未确认时保持同一个操作对象，核对路径返回；分支按需显现 | 不分裂成多个重试副作用；未查明仍未知；这是机制设计，不是实际故障录像 |
| S25 240–250 | G+U | 活动人员查看款项关联后接A10活动原图，研究人员查看配置后接A10实验原图；每半段只一个动作与一个可读结果，两个精美界面都直接保留 | 两个场景是设计扩展；8,000/600/3与seed42/43不得改写 |
| S26 250–260 | G+U+P | 团队成员使用能力库，原A11页面直接合成，打开对象按真实设计状态切换；可从人物空间接近屏幕再转正面UI，不重画应用卡片 | 打开不是自动运行；若显示结果3，明确“查看既有结果3”；Windows开发版措辞准确 |
| S27 260–270 | G+U+P | 沿Sim图标/应用物体收束，264起使用稳定精确品牌与二维码；动态背景退至次要 | 264–270二维码、URL不位移、不被字幕盖住；不让模型生成二维码 |

### 7.1 时间同步规则

上述仅调整S17/S18/S20内部事件，27个单元起止不变，总时长仍为270秒。修改时一起更新：事实源`events`、时间线JSON、导演表CSV/MD、clicks、状态索引、说明、旁白校时及预演。禁止只改CSV而保留旧事件秒数。

建议的S17/18/20时间属于新设计，并不是已核历史。改后输出事件差异表，说明业务顺序未变、仅停留长度改变。

### 7.2 三组优先验证，不设置新一轮等待用户审批

这是服务器第一批生成顺序，也是电脑端最先做完整参考的三组；不是另造“ABC”分支替代整片。

1. **SIM-D1 / S04–S05＋S10–S11：人物工作进入定稿应用。** 人物与材料可生成，落到用户认可的蓝图/预览原图；确认既看得见主体动作，也保住原UI的质量与准确文字。不要把参考图重新画成空卡片。
2. **SIM-D2 / S14–S15：同一应用、两套材料。** 看是否保持应用身份，同时明确换输入、运行和独立结果；不能靠汉字旁白才能识别“交给同事继续使用”。
3. **SIM-D3 / S19–S21：规则变化与历史保留。** 看是否局部改变、旧记录确实留下；90,000不变、规则变为80,000，结果通过精确图层表达。

P-A发布、P-B提取、T3更新的精确状态检查仍全做。生成单元发现严重缺陷才针对修正，不要求每个镜头再做三轮美术比较。


---

## 8. 新增最高优先级：精美UI直接采用，不二次生成

本节源于用户本轮补充，优先于任何“提高H3时长占比”或“所有技术段都要生成”的描述。**原图是可交付画面，不只是模型输入。** 保留好看的UI不是退回PPT；只有连续套同一页式模板、缺少事件关系，才是需要避免的轮播。

### 8.1 用户发来的具体例子

`参考图/A02_应用蓝图_v03.png`：保留品牌、蓝白淡紫材质、三列布局、四类材料、四步规划、应用草案、资格待确认、100,000规则上限及原按钮。它表达的是**候选蓝图**，不能加“已运行”“已发布”“任务完成”的动画。中列已有勾形图标属于原图图形，后期不要把它扩成执行完成进度。

推荐S05十秒内容：
- 40–42秒：与前镜的工作台/屏幕位置匹配，使用原图进入；不强求生成像素等于原图。
- 42–46秒：原图近正面大尺寸阅读，首先看到三列关系；不叠长标题重复遮住原“应用蓝图”。
- 46–48秒：适度取景突出中间动作与右侧界面关系；资格待确认与草案语义仍可见或由镜头前后明确保留。
- 48–50秒：沿预算字段位置接S06的已核对绑定原图；不使用H3让两个UI形变融合。

这是一段产品阅读镜头，不要求10秒全程人物运动。H3应该用在前后的行动和空间，而不是花费计算重画这些已经好的像素。

### 8.2 三种允许的接入方式

| 方法 | 推荐用途 | 实施约束 |
|---|---|---|
| 原图作为主画面 | 蓝图、资格条款、版本/金额、团队能力库 | 原比例、足够屏占比、明确阅读停留；只围绕信息做局部取景/揭示，不套每页都一样的缩放循环 |
| 原图作为屏幕/产品面板内容 | 人物实际使用、手交接后查看、屏幕到产品视图 | H3生成可跟踪的空白/无细字屏幕与人物动作，后期贴原图；必要时四点跟踪、遮挡蒙版、有限反光。手经过屏幕需要遮挡，不允许图层压在手上。跟踪复杂时改成合理剪切，不能无止境研发 |
| 原图作为生成段的构图起止参考 | 产品页前后的短过渡、视角匹配 | 只有实机支持才选I2VA/L2VA/FL2VA；参考约束不等于全程文字准确。真正阅读时换回原图合成，不能把变形汉字保留下来。Ref2VA只能按实际参考角色使用 |

“原图放在画面中心”可以成立：它是当镜主角，而不是缩得很小、四周用粒子填空的贴纸。对字幕和旁白需要读的字段，优先正面大图或精确局部，不使用剧烈透视角度。

### 8.3 资产分类必须落到交接文件

- `APPROVED_UI_LOCKED`：定稿设计UI，直接用原图；`regenerate=false`。仍是设计素材，不改成实测截图。
- `GENERATE_SCENE`：人物、场景、行为或独立无字产品机制表现；需要H3提示词与参考。
- `EDIT_ONLY`：精确数值、状态、点击、图层、品牌、二维码；无需H3调用。
- `EVIDENCE_LOCKED`：实际工程证据原图；仅准许清楚的裁切、排版和标注，不改变内容。

这些是本项目**制作路由字段**，不是MiniMax API参数。需要由本地manifest和服务器导入器消费，不能原样作为未验证API字段发送。

`APPROVED_UI_LOCKED`保持原文件及hash。渲染缩放、透视和压缩自然会产生新的输出像素，验收应检查来源、文字、布局和状态保真，不声称变换后仍逐像素同原图。只对已确证错误作局部更正版并生成新hash；不能“锁图”阻止修正P0-03这类身份冲突。

### 8.4 画质与动作分离

H3场景先做已选定的必要画质处理，再贴高质量UI和字体。不要先把UI/字幕贴到低分辨率生成源上，再一起AI超分，避免汉字被二次推断。源图分辨率不够时合理取景/重排可编辑文字，不把普通放大称为新增真实细节。

允许对原图做少量高亮、点击、焦点、遮罩与可逆局部分层；分层应有完整底图和接缝检查，不为“三维效果”随意抠掉界面或生成遮挡区域。没有层就用整张原图，优先简单稳定的镜头。

---

## 9. 逐组素材处理清单

表中的“保留”指保留定稿资产；最终状态图仍要修复已识别的context与忙碌叠层问题。无需重做全部38张图，更不要求每个十秒单元新做三张图。

| 文件组（均在v07参考图目录） | 采用决定 | 本轮具体动作 |
|---|---|---|
| `A01_工作场景_v01.png` | 人物场景参考 | 供人物、服装、光向使用；新增动作可由H3产生，不将它标为客户纪实 |
| `A01_目标与材料_v02.png` | UI_LOCKED | 保留目标输入、四材料、资格待确认；S02不再原样重复，S04直接使用 |
| `A02_应用蓝图_v03.png` | UI_LOCKED | 用户明确认可，优先作为S05主画面；不生成替代版本 |
| `A02_字段动作绑定_v02.png` | UI_LOCKED | S06数值路径与S10界面绑定分工；同一原图可取不同局部，不必重复生成 |
| `A02_金额单位拒绝_v01.png` / `A02_金额单位修订后_v01.png` | UI_LOCKED+EDIT_ONLY | 先拒绝再修订，保留字段与单位；不要用形变产生第三组模糊数据 |
| `A03_缺项检查_v02.png` / `A03_材料补齐_v02.png` | UI_LOCKED+EDIT_ONLY | 缺签字页→明确添加→重检；资格证据不足不能跟随一起变绿 |
| `A04_应用生成中_v01.png` / `A04_发布前预览_v02.png` / `A04_科研申报助手_v02.png` | UI_LOCKED | 预览与运行结果各按自己的用途选用；生成等待不用静置7秒 |
| `A04_发布确认_v02.png` / `A04_发布授权已确认_v01.png` / `A04_已发布尚未运行_v01.png` | UI_LOCKED+EDIT_ONLY | 展示确认、发布、未运行三个不同状态；运行中只替换对应状态区域，避免旧文字穿透 |
| `A05_资格条款证据_v04.png` | UI_LOCKED | 原条款和缺证据关系已足够清楚；保留版式，做阅读局部即可 |
| `A06_项目乙材料待运行_v02.png` / `A06_项目乙材料已确认_v01.png` / `A06_项目乙结果_v02.png` | UI_LOCKED+EDIT_ONLY | 应用身份保持，乙资料与独立结果不混甲；点击后才能换结果 |
| `A06_两次运行历史_v03.png` | UI_LOCKED | 修的是S16合成页头，原图本身不必重画；P-A到P-B在切图时切context |
| `A07_独立任务来源_v02.png` / `A07_独立提取待检查_v01.png` | UI_LOCKED+EDIT_ONLY | 保留独立来源，旧文件移出新推理路径由分层表现，不重画新来源身份 |
| `A07_独立检查报告_v02.png` | UI_LOCKED | 延长到约3秒、突出三重点；不要为“更动”缩短阅读 |
| `A07_提取发布确认_v01.png` / `A07_提取应用已发布_v01.png` / `A07_独立新运行结果_v01.png` | UI_LOCKED+EDIT_ONLY | 检查后确认/发布/新运行，PB-01结果不提前；运行状态区域精确更新 |
| `A08_变更影响_v02.png` | UI_LOCKED | 已有9万/10万→8万/超1万正确；可局部强调更新与保留，不重新绘图 |
| `A08_v2发布尚未运行_v01.png` / `A08_应用更新后结果_v02.png` / `A08_更新后历史归属_v02.png` | UI_LOCKED+EDIT_ONLY | 修S20运行叠层与S21页头，保留版本与结果归属 |
| `A10_活动运营助手_v02.png` / `A10_实验复盘助手_v02.png` | UI_LOCKED | 与新增情境短镜头交替；保留净额/退款/差异及实验条件边界 |
| `A11_团队能力库_v02.png` | UI_LOCKED | 团队能力主画面保留；打开应用时不直接制造本次新结果 |
| `A12_品牌收束_v01.png` / `A12_下载体验片尾_v01.png` | UI_LOCKED+EDIT_ONLY | 品牌/二维码用高质量原层；264–270扫码稳定，正式压缩版再扫码 |
| `ARCH-01.png` / `T4-01.png` | EDIT_ONLY | 保留机制准确性，按需要拆分；不必批量H3重画，不整页朗读 |
| `E_书生规则清单_v1.png` / `E_书生规则清单_v2.png` | EVIDENCE_LOCKED | 保留实际像素、原英文和身份，只做阅读编排，不加伪造成功状态 |
| 五张技术图原目录 | EDIT_ONLY | 全部已经看过；产品书可保留，影片只选最必要的机制，不把每张都做10秒背景生成 |

### 9.1 只补缺少的场景，不补一堆替代UI

1. **协调人和同事工作母版**：用于S01/S02/S15/S26；同一办公室、光向和衣着，明确材料交接/使用动作。一个母版可以支持多个不同动作；不要每镜重新随机生成人物。
2. **可贴入原UI的屏幕镜头母版**：用于S04/S11/S15；屏幕完整可见、边界清楚、反光不过强，少量侧向运动。需要阅读时转正面原图，屏幕内不要求模型生成汉字。
3. **规则/方法的无字结构表现**：仅在现有图层不足时用于S17/S19/S24；三者动作分别是去旧文件绑定、局部替换、保持同一操作身份，不能一张通用玻璃架构图全片循环。
4. **扩展场景情境**：S25可选一段活动核对和一段实验复盘，各只一个具体动作；已有两个UI继续使用。

新增参考图数量按实际缺口确定；只给真正采用的G单元准备必需图。不能以“需要81张新图”作为服务器开工前置。缺少图像生成能力时写清需提供的具体输入，不用粗糙程序图冒充精美新素材。

---

## 10. H3提示词与剪辑说明的直接替换规范

### 10.1 删除通用背景模板的默认路由

v07中S02/S04–S26等重复模板仅能保留为少量可选背景材料，不再对应每个镜头。U/P/E单元直接设置`requires_generation=false`，提供合成说明即可；不为了27个目录形式一致而保留27份无意义H3提示词。

G单元使用当前官方六节Ref2VA或实际可用的三字段基础模式；英文描述，原话/可见短文保留原语言。Ref2VA六字段顺序：
`subject_definitions → summary → retention_analysis → detailed_description → overall_soundscape → non_diegetic_music`。

模式、帧数与有效时长是服务器实际参数，不是本地提示词能自行创建的能力。生成源可不等于10秒；交接写清需要的动作区间和编辑取用范围。不要预先把一个未知实际时长填成已生成。

### 10.2 每个需要H3的单元交两份不同职责文本

- `H3_prompt.txt`：只描述模型需要产生的主体、空间、动作、摄影和声音；不要把“后期贴图保证汉字不变”误认为模型能做的事情。
- `composite.md`：明确原UI文件、出现时间、屏幕/画布位置、遮挡、追踪、状态图切换和字版。这里保留业务精确性。

提示词开头加一段角色说明是允许的，但不能只有“保持不变、不要变形、相机不动”的禁令。合理动作来自场景和人物，而不是让整页UI自行改字。

### 10.3 示例一：S04/S11的工作场景＋后期原UI（拟替换模板）

以下示例以**实际制作完成**的办公母版作为`<Picture 1>`；这个输入名目前是待电脑端落实的角色，不声称本回执生成了新图。时长以服务器实际请求适配。它生成的是场景，不是应用截图：

```text
subject_definitions:
<Subject 1> is the research application coordinator in <Picture 1>; retain the same appearance, clothing and seated working posture.
<Subject 2> is the workstation environment in <Picture 1>; retain the desk, laptop body, nearby material folders and left-side daylight. The display is an editable screen surface for later compositing, not a request to recreate a supplied product interface.

summary:
[reference generation] Create an eight-second continuous working scene in which <Subject 1> brings a second set of materials to <Subject 2>, opens the relevant folder and turns to the application screen. The scene will be edited with an approved Sim2Act interface added separately; generate only the people, physical objects and environment.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - preserve the referenced person and clothing while adding the described working actions.
<Subject 2> (appears in [Shot 1]): partially_preserved - preserve the room and device structure; use a stable neutral screen surface without text, logos, numerical results or changing interface graphics.

detailed_description:
The video uses a restrained photorealistic technology-product style with clean blue-white daylight, a small amount of lilac reflected light and readable physical materials. Keep the desk grounded in a believable working space rather than a floating diagram.
[Shot 1] Begin in a medium over-shoulder view of <Subject 1> at <Subject 2>. The laptop is open at a stable angle. Its full rectangular display and all four corners are visible. Place the existing folder to one side so that the hands, keyboard and screen occupy separate, uncluttered areas. The display has an even pale grey fill; it does not show an application, a spreadsheet, badges or generated lettering.
During the first two seconds, the coordinator draws a second closed folder across the desk and places it beside the existing set. The folder slides with continuous contact, stops without bouncing and remains a single object. The free hand steadies its lower corner. The original material set stays in place, making the arrival of another input visually clear without implying that a result has already been produced.
From two to four seconds, the coordinator opens the new folder once and turns one page. The pages contain only indistinct print texture with no legible claims or amounts. The camera moves a short distance sideways to reveal the relationship between the physical materials, the keyboard and the display. Avoid an orbit, a lens zoom and any jump in viewpoint. The hands should remain below the display rather than sweeping across it.
From four to six seconds, the coordinator sets the page down, places one hand on the trackpad and makes a single deliberate input gesture. This is a working action, not a claim of authorization, successful publication or completed submission. The display remains a neutral surface for the editor to insert the approved state and exact click response.
From six to eight seconds, maintain gentle natural posture movement while the camera settles on a clear view of the screen and the material set. Keep the four display corners stable enough for ordinary planar tracking, without tilting the lid or introducing strong reflections. Leave a clean edge for a match cut to the original front-facing Sim2Act image. Do not generate the interface in the screen, a new result, green success marks or a QR code.

overall_soundscape:
Soft room ambience, one folder contact and a light paper movement. No dialogue, electronic success tone or automatic notification.

non_diegetic_music:
N/A
```

**对应合成说明：** 使用`A01_目标与材料_v02.png`或对应S11原预览图；原图不送模型重画。场景镜头里贴屏幕时保持透视和遮挡；需要阅读时剪到正面原图。没有足够清楚的屏幕几何就采用匹配剪切，不无限调试追踪。示例动作不是实际产品操作证据。

### 10.4 示例二：S15的复用，不复制旧答案（拟替换模板）

```text
subject_definitions:
<Subject 1> is the original coordinator from the approved office reference <Picture 1>.
<Subject 2> is the colleague and adjacent workstation from the approved reference <Picture 2>; preserve the colleague's appearance, clothing and device position.
<Subject 3> is the new material folder defined by its neutral cover and placement in <Picture 2>. It is distinct from the folder retained by <Subject 1>.

summary:
[reference generation] Generate an eight-second handover-and-use scene. <Subject 1> indicates the reusable application entry to <Subject 2>, who brings <Subject 3> to their own workstation and begins using it. Approved Sim2Act screens and the exact independent result will be composited in editing, not redrawn by the model.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - keep the original coordinator's identity and clothing.
<Subject 2> (appears in [Shot 1]): fully_preserved - retain the colleague, workstation and screen orientation; add a natural response and input action.
<Subject 3> (appears in [Shot 1]): fully_preserved - retain a single new folder and its visual distinction from the original materials; do not duplicate or exchange folder identities.

detailed_description:
Use the same blue-white office lighting and quiet product-film composition as the preceding working scene. Keep both people and their work areas plausible, without holographic dashboards or detached floating panels.
[Shot 1] Begin with a medium side view in which <Subject 1> is finishing a short pointing gesture toward the adjacent workstation of <Subject 2>. Their own material folder remains on the original side of the desk. <Subject 2> holds <Subject 3> and looks toward the indicated display, without speaking. The visual idea is the transfer of a usable method, not the transfer of private material or an already completed answer.
During zero to two seconds, the coordinator finishes the gesture and withdraws the hand. The colleague responds with a small natural nod and turns slightly toward their own keyboard. Do not switch faces, clothing or desk identities as the camera moves. The two folders remain separate and visible long enough for the viewer to understand the distinction.
From two to four seconds, the colleague lowers the new folder onto their own desk, opens it once and puts the first page beside the keyboard. The folder makes continuous contact with the surface. Hands and pages should have coherent contact, and the original coordinator does not manipulate this new input. Printed content is not legible and carries no generated amounts, qualifications or approval statements.
From four to six seconds, track gently toward the colleague's workstation as the colleague uses the trackpad once. The screen is a stable neutral display plane reserved for the editor to insert the approved application and the precise input state. No output appears automatically in the generated scene. Do not portray a click as a successful publication or an external submission.
During the final two seconds, let the colleague continue examining their materials while the camera completes the short lateral movement. Keep the screen unobstructed and maintain a useful matching orientation for the cut to the original Project B input image. Finish with the new folder on the colleague's side and the original folder still on the coordinator's side. Preserve the same device body, room geometry and direction of light throughout. The exact authorization, run request and independent result will be shown with the approved images in the subsequent edited interval, outside this generated clip.

overall_soundscape:
Low office room tone, quiet folder and paper contacts, and one restrained trackpad touch. No spoken dialogue or completion notification.

non_diegetic_music:
N/A
```

**对应合成说明：** 将`A06_项目乙材料待运行_v02.png → A06_项目乙材料已确认_v01.png → A06_项目乙结果_v02.png`按检查后的事件顺序使用；这三个原图不交H3变形插值。生成镜头8秒不是强占S15的8秒；可取前几秒建立交接，余下时间给确认与独立结果阅读，或跨S14/S15合理剪切。最终取用时长以实际素材为准。

### 10.5 S05不用H3的完整剪辑指令

> 直接读取A02_应用蓝图_v03.png，不调用模型重画。保持原图比例和原有草案/待确认语义，先建立三列全景，再在同一画面内按目标与材料、动作规划、界面规划的关系进行少量焦点引导。只允许整体取景、独立遮罩与原像素局部放大；图中已经清楚的标题不再覆盖另一个大标题。与S04/S06使用屏幕边界或预算字段位置匹配剪辑。需要新状态时选对应已核对状态图或可编辑组件，不让AI续写UI。交付采用原图hash、变换/取景、叠层、时间范围及输出文件，不为这一单元生成虚假的H3调用记录。

---

## 11. 排版、声音与检查

### 11.1 排版体系

沿用Park A2 v02的原则：无边框局部标注、少量细引线、标题与局部说明分时出现、字幕独立；不复制它每镜的绝对坐标。Sim软件原图已有标题与数值时，优先读原图，不再叠一层相同标题。

1920×1080建议起点：影片主标题约44–56px，局部短标注28–36px，旁白字幕32–38px。具体按当前画面测试，不能把数值规范当最终美术验收。重要标注不使用18px小字承担业务结论。可沿用已安装并有许可的同一中文无衬线字体，不为字体新增付费，不打包用户未授权再分发的字体文件。

主色沿用深蓝、浅蓝与淡紫；状态橙只用于待确认/需核验，不能将所有活动都做成绿色完成。原UI的材质和颜色先保持，不套重色罩改坏已经认可的设计。

720p检查必须看实际缩小画面：关键标题、金额、状态、条款和二维码可辨；细节不能同时读清时做局部或减少同时出现的文字。不能靠把字幕缩小解决遮挡。

### 11.2 音频与时间

临时270秒音轨只用于校时，不以其节拍冻结所有新动作。正式旁白按章节连续、统一声线；剪辑中保留必要呼吸与阅读。数字读法、Sim2Act与书生名称统一，演员不必对口型；生成源音轨未听过不直接采用。

现有SRT 52块无重叠，仅是时间草案；实际配音后重新对齐。音乐来源与许可记录。电脑端可准备文案和声音设计，但不冒充本轮已试听或已制作正式音轨。

### 11.3 轻量但必要的检查

只保留影响交付的检查，不重复做繁重流程试验：
- 原图hash和最终采用身份，素材无缺失、无错误版本。
- 发布/运行/结果的事件偏序；context按state切换。
- 关键数字、版本、来源和未知项；检查是否提前出现“完成”。
- 所有新生成片段的主体动作、严重变形、连续性与运动方向。
- 合成时屏幕贴图、遮挡、比例和阅读尺寸；最终字幕/字版不再次经过生成超分。
- 总时长270秒、全片可播放、声音字幕同步、最终压缩版二维码能扫码。
- 未跑/未听/未生成写明；不要把hash、自动播放或密集抽帧当成完整人工听审。

---

## 12. Windows端应一次性交付的v08包

### 12.1 工作范围

电脑端完成必要的产品书修订、素材分类、镜头设计、必要补图、实际提示词、精确合成说明和交接校验。**不修改产品后端、不跑H3视频、不停止或修改Park服务器正在运行的队列。** 不重复准备已存在且适用的原图。

已具备当前仓库发布授权时，在独立提交/PR中同步材料并上传具名v08 ZIP；无发布权限时说明这个唯一阻塞，但先把完整可下载文件准备好。不要覆盖v07附件导致相同URL对应不同字节，不擅自修改Windows应用Release。

### 12.2 单一目录与入口

建议新目录`submission/04_视频/制作交接_v08/`：

```text
制作交接_v08/
  START_HERE_服务器接手.md
  film_manifest.json
  business_facts.json
  asset_manifest.json
  ui_locked_manifest.json
  导演表_270秒.csv
  旁白稿.md
  字幕时间草案.srt
  style/影片字版规范.md
  assets/ui_locked/       # 直接采用的精美UI，保持原文件
  assets/evidence/        # 实际工程截图与必要来源说明
  assets/scenes/          # 仅所需的新场景、动作母版
  shots/S01/...S27/
      shot.json
      composite.md
      H3_prompt.txt      # 仅requires_generation=true时必须存在
  checks/
      文件与哈希核对.json
      状态偏序检查.json
      修改回执.md
      未完成与限制.md
  SHA256SUMS.txt
```

目录只是建议接口，不表示这些文件已由本回执创建。一个包内不能再让服务器在v04/v07/v08之间猜哪套时间线有效。正式产品书如修订，另出新版本并在入口写清；不用把完整266MiB历史包重复放进视频执行包。

### 12.3 每镜最少交接字段（项目自有schema，不是H3 API）

- `shot_id`、`edit_start`、`edit_end`、`route`、`requires_generation`。
- 实际源图路径/hash/原始尺寸/来源类别，UI锁定与禁止更改项。
- 生成段的参考顺序、标签、参考角色、提示词路径/hash；模式是“要求核实”还是“已核实可用”。
- 可见初态、主要动作、终态、取用意图与下一镜的接点。
- 精确UI/文字/数字所在合成层、相对时间、位置/取景/屏幕角点与遮挡要求。
- `state_id`对应业务对象、应用版本、规则版本、结果身份和context；不得只在shot顶层统一赋值。
- 音频与字幕角色、关键帧是否只是构图参考、失败替代方式和优先级。

新生成图/提示词未实际准备好时标`NEEDS_INPUT`；不要用`TBD`路径装成`READY`。不需要生成的UI单元标`EDIT_ONLY/READY`，不是未完成。

### 12.4 GitHub下载交接

给用户最终只交一条服务器启动消息，内容包括：固定提交、具名ZIP实际下载地址、SHA256、入口文件、当前版本组合与已知缺口。服务器能从这条消息下载后开工，不再要求用户额外上传03.md或单独图片。

若用Git LFS存视频/图片，校验下载到的是二进制实体而不是约百字节指针。ZIP用本项目已有获准发布方式传输；不能把私人服务器路径或Windows盘符当成可下载地址。下载验收检查大小和hash，SHA只是完整性证据，不是发布者身份认证。

`START_HERE`写明：先使用已批准的服务器模式和资源，不重选模型；定稿UI直接合成；只对requires_generation的单元调用H3；先生成D1/D2/D3相关的缺失片段作为优先队列，通过内部检查后继续剩余镜头，不再逐镜等待用户确认。遇新增付费、未授权GPU或真实事实冲突才集中说明。

---

## 13. 发给Windows Codex的执行总任务

> 请基于产品书v04和制作交接v07执行本回执，整理一套可由服务器从GitHub直接下载使用的Sim2Act 270秒视频准备包v08。
>
> 用户最新明确：已经认可的精美AI软件UI直接使用，不让H3照着重新画。`A02_应用蓝图_v03.png`等定稿图归入APPROVED_UI_LOCKED；原图可以作为全景主画面、局部阅读或屏幕贴图。真正需要生成的是人物行为、工作场景和必要的空间/无字机制表现。避免的是整片机械轮播，不是避免使用好图片。不要为了H3时长比例重做已经精美的页面。
>
> 先修S16/S21的state级上下文、S18/S20的旧状态透出、S17检查报告阅读时间和S26打开即显示旧结果的歧义；同步导演表、JSON、预演和图层，不只改一张导出图。保持所有预算、权限、版本、结果和证据边界。
>
> 保留270秒与27个内容索引，不要求每段都生成10秒H3。将各段分为G主体生成、U定稿UI、P精确交互、E工程证据；不用H3的镜头不配通用背景提示词。需要生成的镜头逐个写具体动作，并只补真实缺少的高质量参考。不得继续24份相同背景提示词，也不得把好UI重画成粗糙SVG。
>
> 采用Park已认可的A2排版原则，但针对Sim画面放置文字，不套绝对坐标；主体场景可超分，UI/字幕最后合成，避免模型推断汉字。不得让新版本、运行结果或成功状态先于确认与运行出现。
>
> 同轮完成产品书必要短改，不重做所有页面；工程附录原证据保留，只写本回执离线核对的有限范围。按照§12准备唯一入口、完整资产、参考映射、实际H3提示词、合成说明、校验和修改回执，并在已有授权下发布新具名ZIP与固定提交。生成视频不在本地任务范围，未知服务能力交由服务器现场核实，不在材料里假称支持。
>
> 最后给用户一段能直接发给服务器的启动消息，包含真实下载地址、哈希和入口，不要求再次搬运多个分散文件。先检查包能独立读取、引用无缺失、总长270秒、关键事件偏序和二维码，不以“写好了提示词”代替素材完成；未完成项显式列出。

---

## 14. 核查依据

主要依据是用户上传的`Sim2Act-Submission-Review-20261107-v07.zip`及独立PDF，而非远端最新分支。路径、版本、hash和实际检查结果见本回执§1及随附`审阅核对摘要.json`。

官方H3格式参考（读取日期2026-11-08；提示词语法不构成服务器能力保证）：
- https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/SKILL.md
- https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/base-en.txt
- https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/ref-en.txt

用户此次补充图片与ZIP内`A02_应用蓝图_v03.png`内容对应。本回执只输出审阅与执行要求，没有替换、生成或修改原始软件截图，没有启动服务器生成任务。
