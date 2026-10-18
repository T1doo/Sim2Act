# 自然调用接续：设计依赖与候选语义准备原件

基线 `5a348ce97325ebbe450c2beb09dff767a4376252`，普通分支 `dev/natural-call-readiness-20261018`。本轮是**docs-only准备交付**；没有新增生产调用代码、测试或许可，不把已有InternModel/原发送总账链重新计为实现。

生产接线状态：**未实现，NO_SAFE_INDEPENDENT_PRODUCTION_SLICE**。实际已有`request_captured→_sent→archive→settle/reject`及两个runtime调用；新生产行为仍依赖受信账户/合法免费与强制不可收费来源、生产准入发行及账本policy、生产Run/Attempt/归档/凭据身份和精确软件资格。当前缺少来源协议及可核实事实，不能用合成Permit、bool/hash、改mode或放宽门替代。开发授权充分，没有被拒的工具动作、待批真实调用或外发结果不确定；本轮不发起上述真实操作。

| 原件 | 范围与限制 |
| --- | --- |
| [独立设计审查](review/design-review.md)、[最终有限审查](review/final-review.md) | 具体已有函数、缺失接口输入/输出/错误与责任；本阶段不另造软件自资格对象或重复deny壳。不证明生产链、软件资格、免费或语义成功 |
| [准备说明](preparation/README.md)、[材料A](preparation/material_a.txt)、[材料B](preparation/material_b.txt) | 新合成候选材料454/519 UTF8字节、各5行；未用于当前实现/测试，没有模型答案。不同hash不证明盲性 |
| [完整Goal草案](preparation/goal_drafts.json) | 两份Goal卡字段，UNBOUND_ACTUAL_RESOURCE占位，当前不可提交；未创建实际资源、Goal、Run、权限或预算 |
| [人工rubric](preparation/RUBRIC.md)、[空表A](preparation/score_sheet_a.md)、[空表B](preparation/score_sheet_b.md) | 权重/人工标准草案，NOT_SCORED/PENDING，无自动PASS阈值；未owner确认。private_reference仅未接受参考草案，不是模型输出/gold，不应传目标模型 |
| [准备manifest](preparation/MANIFEST.json) | SHA256 `0d551c953b5c86e92b010ada120556dce51b22cc2f3c3e3706c700914dfa38f3`；9条23481B，含manifest10文件25280B，外部目录已只读封存 |
| [独立准备核验](review/preparation-verification.json)、[独审manifest](review/sealed-manifest.json) | SHA/行数/权限及准备内容一致性，无被测输出或人工评分；审阅者经授权接触private_reference，暴露记录保留。独审manifest SHA256 `27b54addc73360c858a42e1797626fc9b30f8487160ab934f41e4651919c32f7`；共8文件29043B，已停止写入 |
| [作者文件/schema结果](raw/preparation-verification.json)、[第二次stdout](raw/preparation-attempt-2.stdout)、[stderr](raw/preparation-attempt-2.stderr)、[核验器](raw/verify-preparation.py) | 仅文件hash/UTF8/LF/大小/行数、GoalCardInput schema/占位及空表标记；audit禁止network/DB/subprocess，事件为空。不是pytest或语义验收 |
| [首次核验器](raw/verify-preparation-attempt-1.py)、[首次stderr](raw/preparation.stderr)、[原因](raw/preparation-attempt-1-explanation.json)、[独审该helper](review/author-preparation-helper-review.json) | 首次误要求assumptions非空，原schema允许[]；保留原exit1及脚本，删除无依据assert后第二次文件核验通过。未改材料、源码/测试/资格门，未编造假设 |
| [源码字节桥](raw/source-byte-bridge.json)、[选择清单](selection.json) | 699个已有输入/134生产文件与前源快照完全一致，仅文件复算；前9个pytest未重跑/不计本轮通过。31份verbatim copy路径190800B，DB/工作树/bundle未复制 |

实现者仅复制原件字节、核hash与程序校验Goal草案结构，没有把材料/私有参考送入实现、mock答案或目标模型。独立准备者和一致性审阅者已接触内容，blind资格未建立；未来若被用于开发或评审角色不独立，应另行评估是否另制材料。私有参考目录名称及只读文件模式不是访问控制或不可篡改保证。

当前准备集只用于未来审议；真正执行前还需要实际授权资源及完整Goal绑定、材料owner/参考确认、受信来源/费用证据、当前软件/阶段准入及单独执行授权。机器结构/引用检查、保存成功与人工语义判定必须分别记录。当前没有被测答案、人工分数、owner签收或有效LIVE许可。

本轮0产品/API/DB/Worker/MockModel/真实模型/pytest执行，0真实外发/费用发现/凭据读写；仅文件及schema核验。Windows/native、PG、远端CI与旧永久取消窗口未执行，所有旧sealed目录保持，旧满盘未落盘报告缺口未补回。最终普通push/远端与未提交差异另见交付核验，不由本独审提前背书。
