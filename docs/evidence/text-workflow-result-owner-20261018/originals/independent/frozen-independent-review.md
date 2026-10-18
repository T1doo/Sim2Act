# 冻结提交独立有限审查结论

**产品冻结：`d7251b79d4dc17af6665f7a93eef8ffcfefa8603`。核查时 HEAD：`89c4d6ef9d223d99bd664311ed61d15943b96d7a`。在本次有限范围内未发现剩余 P1/P2，原 WIP P1/P2 修正已对精确冻结源码复核收敛。** 本人是非产品作者，亲自完成源码审查、字节桥和短 SQL 控制流复核；实际 Worker、HTTP/JSDOM 产品资格由作者执行，本人读取原件并独立复算，不冒认为本人亲跑。

## 精确源码与修正

- `freeze-source-integrity.json` 枚举 Git `src` 全部 **130** 个文件：旧 275455c6 的129项中124项不变、5项本产品预期修改，另新增 text_workflow_owner.py。d725→89→working 全部130逐字节一致，无删除；此前审查6份源码 SHA256 全部精确匹配冻结 Git blob。核查时工作区 clean。
- 新适配器先 owned iid/rid/Run/AppRun/Release 与独立四步 RUN_META 双 seal，后允许原 key 或本人 metadata stop；当前材料鉴权在 Run/Goal/result/owner payload 前。完整 receipt/intent、Goal当前 head、instance revision/release/data_version、typed结果及新运行在途门均复用原 verifier，final_gate 在同一事务重复证明。
- 原 **P1** 是旧 natural 路由可借共享自然表在 context 前读 old key / 执行停止；原 **P2** 是第一修正版只信 namespace 标量。原未修源码、原重现 JSON 及合成 DB 均保留，详见 independent-review.md，未覆盖或删除。
- 最终 natural_review_scope 在旧 natural_read/natural_submit 的 ledger、old key、stop 前核对家族及现有自然 RUN_META 双 seal，只读标识、不引入材料授权。精确 guard SHA256 `7efd87cf634601a80c5132aecbdcbdf8b464000a1f4f036269c9b81fb8b74f69` 短回归：old key/stop/read 三项均在 owner 表前 UNSUPPORTED_CAPABILITY；单 namespace 污染在 owner 表前 VERSION_CONFLICT；owner 行不变、natural_context 0次，已知合成 Release 已恢复。这是存储/控制流检查，不新增为产品用例。
- 三份 UI 源码与此前非作者审查字节一致，Node语法通过。报告/人工状态绑定同一 Run、AppRun、Release、typed指纹、材料 SHA 与四个 receipt hash；所有异步 hash后重查当前 generation；安全 textContent显示完整引用与报告；PARTIAL不签收、新 Run PENDING不迁移；旧CSV spec:true fallback和旧自然规范路由保留。没有新增 executor、Grant、业务 writer 或发布能力。

## 已读取实际资格原件

以下是**作者实际执行、本人独立读取**的分批证据，合并 **13个唯一用例**；不是某次全套一次绿，也不是13项独立作者审查亲跑。

| 范围 | 实际结果与原件 |
|---|---|
| 新后端7项 | frozen-backend-junit.xml 原轮 **6PASS/1FAIL**，正例在旧observer取错字段后 KeyError；qualified-positive-junit.xml 正例另行 **1PASS / 26.20s**。产品源码相同，原失败保留。覆盖2个实际完整四步Run、同实例结果v1/v2、新PENDING、原记录/业务与权限不变、冷独立Store GET、重复意图、PARTIAL、外账号/实例屏障、撤权、Goal/source/typed失效。 |
| 新实际HTTP/JSDOM2项 | qualified-ui-junit.xml **2PASS / 78.87s**；flow46 checks、navigation22 checks。原page-result、IPC、http-trace、worker-log均已读。flow为3个页面实际NoModelRun（2成功+1PARTIAL）加1个fixture seed；navigation只有1个fixture seed，页面Worker调用0。两项均标UI_AUTHOR。 |
| 共享兼容4项 | shared-regression-junit.xml **3PASS / 132.13s**：旧自然PA声明、旧literal声明、旧CSV实际JSDOM声明；shared-pb-junit.xml **1PASS / 150.137s**：旧自然PB声明。 |

- 正例29条原HTTP回执和保存合同已读；本审查用18项独立断言重新从保存材料计算源SHA、两组完整行引用和报告，确认两不同Run/AppRun、同iid、新结果版本、cold精确合同及旧STALE只含元数据、新Run空PENDING。源码中的独立Store/TestClient和全业务表快照断言结合合格JUnit支持冷回读和声明无额外业务写入；本审查没有重跑Worker。
- UI **78次实际静态资源观测**（52+26）逐项SHA均等于冻结Git源。作者UI source-before/after清单的130项实为 **128项生产src+2项UI测试**，前后0差异，全部匹配相应冻结产品/89测试字节；该清单没有监测 text_software_anchors.json 与 text_software_qualification.json，不能写成UI期间全部130生产源前后监测。这两个JSON属于本人的完整Git src130当前字节桥，未宣称补造作者早期记录。
- navigation实际覆盖workspace ABA、Run取消选择、instance选择、project ABA及**同账号重连**后的迟到真实HTTP响应隔离；不是另一账号登录的页面测试。外账号拒绝由后端实际用例覆盖。部分成功和历史声明未被当作当前完整成果。

## 可复核原件与限制

- 初始发现与WIP过程：[independent-review.md](independent-review.md)。
- 全130产品源+此前6源码桥：[freeze-source-integrity.json](freeze-source-integrity.json)。
- 实际资格原件哈希、JUnit清单、18项独立复算、两UI检查与asset桥：[freeze-author-evidence-independent-readback.json](freeze-author-evidence-independent-readback.json)。
- 精确guard原SQL：[fixed-scope-result-7efd87cf6346.json](fixed-scope-result-7efd87cf6346.json)、[fixed-namespace-result-7efd87cf6346.json](fixed-namespace-result-7efd87cf6346.json)。
- 实际作者证据根：`/workspace/text-workflow-result-owner-evidence-20261018/`。所有原WIP失败、冻结observer失败及修正来源保持其原证据归属。

本结论仅覆盖上述冻结产品与合成、NoModel工程资格。不代表真实用户/真实语义人工验收、Windows、native浏览器、PG、远端CI、部署、完整P-A/P-B或完整T06通过；未新增费用/凭据/权限。旧满盘独审缺失报告未恢复，旧取消项NOT_VERIFIED未更名。当前无本片代码审查阻塞；推送/最终封存SHA及远端一致性应由唯一写入者另给真实回执。
