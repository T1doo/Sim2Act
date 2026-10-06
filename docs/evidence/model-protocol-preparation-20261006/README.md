# 两形态通用模型协议离线准备

本地基线f70c32d，新增请求0；未push/CI/LIVE/权限扩大/部署。交付[材料manifest](materials/manifest.json)、[gold草案及量表](materials/README.md)、通用源/提取/冷运行协议、持久实验预算门和[统一执行计划](../../F2/ModelProtocolExecutionPlan.md)。

`ModelProtocol`默认disabled；可注入现InternModel+BudgetedProvider，source真实模型选择read/参数，extract返回有限read-only注册工具/语言JSON节点DAG，cold在新绑定上执行同一接受候选。没有预填任务答案/义务/规则优先级，也不新增固定任务家族。候选通过actual extraction response JSON指纹→持久receipt绑定，冷读重验；不能caller换合法候选并重算FP冒充模型。

[root回归](local-regression.log)145PASS/1SKIP/1已有depwarning，独立budget+protocol58PASS。[独立审核](independent-review.json)、[保留失败事实](failure-history.md)。ruff/mypy两新module通过。原产品源未改，原F1 PARTIAL/AT02历史不动。

[8个完整HTTP发送体](wire-preflight.json)由真正InternModel的httpx.MockTransport捕获；max4542chars/4542UTF8bytes、reservation29201，gold文件未加载，源模型构建不见cold文本、冷模型不带源答案。Mock响应/候选/语义verifier全部显式TEST-only，不能称模型实际规划/语义通过，也不是费用。未来真实body变化每次仍检查8000chars/10000bytes及全局64k。1024输出cap能否容纳真实候选尚未知。

重跑：`PYTHONPATH=src python scripts/model-protocol-preflight.py --output /tmp/sim2act-protocol-preflight`；仅MockTransport、fake token，不读真实env。临时ledger自动清理；使用现repo依赖即可。

此协议候选并非现ActionSpec/AppManifest已注册可执行产品版本，输出明确executable_by_existing_apprun=false。真实当前Grant/Operation/readback+独立语义proof/accepted source ledger callback、API/worker及编译器尚未接线；Windows侧车锁NOT_RUN。侧车仅controller私有实验计数，不替代Run/Attempt或提供新权限；删除/替换其目录是管理员重置，不是允许的恢复。owner未签gold，新材料/14预算外发未批，当前真实预算0。
