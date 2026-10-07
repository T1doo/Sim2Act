# 有界条件/例外检查与零网络一次性准备器

基线5a49ea6ad119cf2afae350d7cdb6aabfe877e68d，独立dev/bounded-semantic-suite-local。产品只在本地，未push/未触发新CI。5a纯docs已普通同步dev/f1-foundation；交付前ls-remote exact5a。原V5/AT02/旧终态不改。

## 实现与适用范围

新增GET/POST conditional-checks API：当前user/project/runtime resource.read交集、可信读取、固定公开虚构A-source实际hash与注册合同版本。显式假设员工案例，逐R1/R2/R3检查适用状态和原文行引用，检查500/501边界、审批与缺收据、10日期限、过期/未知事实、矛盾事实及下一步行动。逐项FAIL提供定位；自由解释文字NOT_CHECKED。手写Mock报告不从checker/gold生成；无真实模型请求。

PASS仅有限人工注册结构化规则符合，semanticUNKNOWN、ownerPENDING、正式发布false、run_approvalfalse。不是模型理解、自动语义抽取、用户确认或完整P-B；未接Run签收/既有source_proof，不提升FAILED/UNKNOWN/PARTIAL。无新表、迁移或API建表；检查只读。新GUI/原生/像素NOT_RUN，HTTP TestClient与MockTransport是实际本地验证。

准备器只封装四个既有固定公开资料、当前代码/检查组件fingerprint、proposed预算、完整前/中/后检查清单与待批metadata。实际默认CLI生成[准备清单](one-shot-preparation.json)：BLOCKED_PENDING_NEW_FULL_APPROVAL_AND_EVIDENCE，live_ready=false，effective_request_budget=0，network_requests=0，无真实身份/凭据。完整metadata即使齐备也只有DECLARED_NOT_AUTHORIZATION；不验证真实签名/权限/服务，也没有LIVE执行器。wire尺寸/JSON envelope实测通过不代表外发许可，egress_authorized/gold_screened始终false。下一次真实实验必须新完整批准、新未撤销身份及实际阶段证据；本轮不创建它们。

## 验证

最终源码SHA见[source-sha256.json](source-sha256.json)，独立报告六文件SHA与当前一致。Ruff PASS；mypy36源文件PASS；diff检查PASS。

- 新增专项45PASS，1warning，4.49秒。
- 相关SQLite319PASS/1SKIP/0FAIL，77.20秒。跳过显式PG应用角色子进程。
- 相关PostgreSQL321PASS/0SKIP/0FAIL，165.31秒，1warning。含新增最小应用角色：NOSUPER/NOCREATEDB/NOCREATEROLE/NOSCHEMACREATE；实际API所有SQL均SELECT，完整业务行及schema对象不变。相关集合含既有显式SQLite-only fixture，不称全部PG物理连接。
- 独立手写HTTP34检查、准备25oracle、新增规范45专项通过；网络硬拒绝下CLI/准备验证。独立报告见[independent/final-review.json](independent/final-review.json)。独立PG/原生未跑；上列PG为主执行器实测。
- 主执行器PG清理前test_% schema/role均0，随后仅删除本轮sim2act-bounded-semantic-pg，docker列表验证无该容器。

测试包含跨项目/外身份、双授权撤销与过期、sourcebytes/hash篡改、合同指纹、bool数字、伪引用/重复规则/错误决策、未知/过期不自动成功、无写。准备包含过期/旧批准、撤销身份、跨scope回执、预算超额、缺清理/用量、reseal篡改、代码/资料绑定、秘密字段拒绝且CLI不回显、独占创建文件、UTF8字节/字符上限、NaN和坏JSON。

## 失败保留

首次collection误用metadata名造成ImportError，0执行；随后stalehash测试误期望409/422，实际正确网关400 VERIFICATION_FAILED；另两次测试工具误patch不存在方法/误匹配异常code，均修测试后通过。原日志压缩保留。独立复现准备器可变CAPS/CHECKLIST返回引用污染模块常量的真实缺口，改deepcopy并用独立进程和reseal负例重验；旧报告/FAIL仍保留。未伪称首轮全绿。公开测试资料为合成规则，非真实业务规则；不使用gold证明一般语义。

剩余核心：语言目标到有限工具/语言DAG规划仍不完整；真实source/cold/usage/cleanup完整执行需新完整授权；通用语义、用户确认、Win11、F1正式签收/AT02及完整P-B仍未完成。
