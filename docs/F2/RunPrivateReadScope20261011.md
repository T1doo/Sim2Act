# 共享调度的 Run 私有读取边界修复

实现前合同，基线 2b53572ded47f83d51898356dae0e99a97a61bc9。父独审确认原 SQL trace 的两次无 WHERE 全表 SELECT 返回全部 Run.context/result；原探针仅检查 oldrun 是否出现在参数，漏检，原无旧内容读取结论不能签收。原 trace、脚本、LIMITED PASS 报告和所有历史字节保留；尚未证明用户泄露或旧结果复用。

1. 新资料的实际 CSV Worker 调度不得加载无关历史 Run 的 context/result、旧 CSV 内容/hash、旧 Operation input/output 或旧合同私有 snapshot。先用 ID/状态/租约/身份等调度元数据筛选实际候选，再对需要检查的候选查最小协议标记；完整载荷仅属于当前领取的 Run 或明确需要处理的到期协议候选。
2. 旧协议防降级不变量保留：job、accepted event、context.kind、result.protocol_result.kind、合法冻结合同 goal.constraints 中任一标记残存，均不能落入普通 F1 恢复/续跑。精确类型和合同指纹校验不删除；残缺及组合病例必须回归。
3. 审计全部 protocol_run_ids 调用者，包括 claim、到期恢复和共享协议池。协议池按实际 Attempt Run IDs 识别成员，协议标记只投影必要命名空间元数据；完整协议合同只为实际带协议合同标记的候选验证指纹，不全表加载无关合同。普通队列先锁定精确候选 ID，再读取它自己的载荷；旧行、fence、未知回执、取消和恢复语义不改。
4. SQL 测试采用实际按行/列求值的 SQLite 读屏障，不靠参数或 SQL 字符串匹配判断旧数据读取。必须先在原生产代码得到失败，再修后验证完整 read→sum→report Worker、新目标结果和冷 typed 历史；无 WHERE、IN、联表、别名、子查询与聚合访问负例要证明屏障有效。屏障属于测试 fault injection，旧持久行保持，不删除历史来获得通过。
5. 恢复上一轮 650 个选定节点的完整关联范围，并加入新材料/逻辑、SQL 读屏障和共享协议调度/恢复/池/基础 Worker 的完整相关模块。实际收集与 JUnit、源码冻结必须一致；旧 262 窄窗不代替本轮完整相关回归。保留所有红/失败/中断日志。
6. root 单写，正常原开发分支；不配置凭据、扩权、调用真实模型、部署、强推或改 main/coredev/原 CSV 分支。SQLite/进程内 HTTP/离线 JSDOM；PG、Windows/native、真实升级、完整 P-A/P-B/AT10、语义/owner、远端 CI 和部署未跑即明确 NOT_RUN。独审追加，旧 SQL 无读取结论以本次真实修复和新证据为准。

具体源码、原两扫描和执行记录保存在 docs/evidence/run-private-read-scope-20261011；实测结果仅实际完成后追加。

实现边界补充：SQLite 正常 API 写出的 JSON 没有重复键；对故障注入的重复 context/result 命名空间键，任一残存精确字符串标记均保守停止，避免 json_extract 取首键使旧 Python 最后键标记丢失。合同只先筛带标记的候选，再按解码后的 goal.constraints 合法数组及完整 fingerprint 复核，保留旧最后键语义，不把先标记后普通的重签合同误判为协议。PostgreSQL 查询仅完成编译检查；其实际运行、锁和 JSON 行为仍 NOT_RUN。

读屏障校准：Operation 物理输出列为 receipt，输入在 operation_intents.request；两者均按真实旧 operation ID/Run ID 保护，并以旧实际 CSV operation 做访问负例。保留原表和原值，SELECT 使用求值即失败的临时视图；authorizer 防止直接 main 私有列读取，并拒绝外来保留视图名以阻止同名 CTE 伪装，包含前置注释。候选内 JSON marker 谓词会在数据库内求值，池探针另核真实非 NULL Attempt 候选和 Run ID-only 返回；不声称全部历史 JSON 零物理求值，或该测试 helper 是通用 SQL 安全层。

终态实测：作者1730唯一选定节点1664PASS/66SKIP/0FAIL/0ERROR，另2真实升级deselected；原650逐节点恢复641PASS/9SKIP，30原预算串行页面全PASS。401源码/测试/scripts非pyc文件前后/当前同字节，原141材料证据完整保留。独审59检查LIMITED PASS另计、不并入pytest数量。原红轮、边界FAIL、前置安装/中断和材料页超时全部留档；后者最终串行PASS但完整原因仍未确定，不放宽预算。全树Ruff10/mypy5与原2b逐诊断相同，改动Ruff通过。完整终态、代码投影与所有NOT_RUN见 [本轮证据](../evidence/run-private-read-scope-20261011/README.md)，没有提升原生/语义/PG/远端CI验收。
