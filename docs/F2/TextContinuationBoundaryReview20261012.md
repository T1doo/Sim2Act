# F2-T08 续接历史读取范围与结果完整性复审

起点为已推开发提交 `b244a24b607688af169cc08ac13c90f84b4a275a`。父级只读复审指出两个有限合同缺口：终态 AppRun 的损坏 binding 可让代码先读取另一个主体/项目/runtime 的 Run 整行再拒绝；只遍历已有 typed 会漏过仍有成功 Worker/receipt 的缺失结果，或失败任务的异常结果残留。本轮 root 唯一产品/仓库写入者，独审只读并写 `/tmp`；不扩展两个原软件锚、一次续接或声明式算子范围。

## 原版实际证据

原版两锚的12个 prepare/commit 错链场景均返回409且全库零写，但 SQLite 实际求值了各5个外域私有单元，包括 context/result。观察器不改原单元值，单独读取 context/result 的校准先命中，再清空记录观测产品路径。这证明合成错误绑定下的读取顺序缺口，不表示HTTP响应泄露或真实攻击。

在精确旧 Git 实际生成库的克隆中，仅删除唯一 typed 并把所选实例 data_version 改0，保留原 SUCCEEDED job/AppRun、binding、frozen contract、Operation/Intent/receipt。原软件两锚实际 preflight201 → commit201 → 冷成功历史Run GET409。此链的完整命令、退出码和JSON见新证据，不是仅从源码推断。

异常 AppRun.output/result_version 或 Run.result 残留可获原预检201；预检后这些改变通常被既有 jobs CAS拒绝，但没有完整结果验算。VERIFIED operation 残留不在原 jobs指纹里，实测预检和迟到提交均可201。typed残留本来会被 data_rows 的部分lineage检查拒绝，本轮再将其与冷历史的完整verify准入规则对齐，不能把原409说成原来通过。

首轮38项为2PASS/36FAIL，含4个操作记录唯一约束夹具错误。旧失败原字节保留；改为修改既存失败操作的状态后，对应4项在原产品真实全部FAIL。正常未运行空实例2PASS；两个旧Git新建库中实际 INVALID_INPUT FAILED-only、正常队列明确CANCELLED-only控制4PASS。取消是普通Run控制，无安装窗口、竞态probe或权限改变。

## 最小产品变更

唯一生产变更文件为 `src/sim2act/text_continuations.py`：

1. 只读取 AppRun 的标量身份/状态/Release及binding run_id，先核所选主体。Run整行SELECT必须同时约束精确id、principal、project及runtime，错链不能投影外域正文；删除原逐typed的第二个无范围Run查询。
2. 对每个合法范围内终态job完整核原 accepted binding/frozen contract、历史Goal、ReleaseIndex。按现有 `inspect_job` 规则，SUCCEEDED、AppRun.output、AppRun.result_version、Run.result、typed 或 VERIFIED operation 任一存在，均调用原 `text_run_checks.verify`；检查原receipt/Intent/oracle/schema/结果行而非自建弱检查。
3. 全部typed的AppRun ID集合必须与完整验算通过集合双向一致，且一对一。缺结果成功job、孤立或错链typed、非成功结果残留都不能续接。真正无结果FAILED/CANCELLED仍只核原接受合同，不误要求typed。

prepare和commit均调用相同preconditions；失败回滚且全数据库无新增/修改。原数据/Release/Goal/人工记录不重签、不修补损坏历史，不降低原权限和预算。原key读取、300秒批准、取消撤权、迟到结果和软件精确指纹合同沿用。

## 冻结与验证边界

410个 `src/tests` 文件 map：`973918a69af80c30b19436f09519e25f09dbf581892cdf24a3db7b2d9e49ef04`。
67-Python（config除外）目标实现：`7bc662bb1483693e96edf916d2177ad51f246e0cbde7a50d943675d8c9ec852d`。
pyproject与b244相同。新增两份 `233-empty-terminals/a747-empty-terminals` SQLite库由原已接纳软件API/普通Worker生成，旧四库与所有前轮证据不覆盖。

作者及独审最终实际分母、退出码、源映射与文件桥见[本轮证据](../evidence/text-continuation-boundaries-20261012/README.md)。旧249/80/12只是b244历史执行，不能代签本轮新软件。真实用户旧库、PG/Windows/native、真实模型/人工语义、完整P-A/P-B/正式发布/远端CI仍NOT_RUN；原取消精确安装竞态永久NOT_VERIFIED，Forbidden CI保持停止。
