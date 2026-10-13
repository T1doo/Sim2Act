# 修改后的内部版本继续处理未见材料

有限合同：共享 per-use 保留原 P-A/P-B 来源及身份权限，从当前已核验 natural_logic_source 的 effective candidate 获取实际 recipe。目标材料、Goal、预算、版本和精确确认逐项冻结，入队及每个实际 Worker 提交重验。旧 recipe 指纹拒绝。新结果独立人工复审，测试使用合成声明，机器语义状态仍 UNKNOWN、owner PENDING、发布禁用。

代码：pb_natural_uses.py 的 review/bound/audit；pa_spec_apps.py 的绑定及提交守卫；app_jobs.py 的 per-use 路由；lifecycle/apps/natural_logic_patches 的仅同事务完整来源验证复用；web/internal.js 的有效 recipe 预览、快照哈希、实例/选择/workspace/connection/render 等待栅栏。原始草案、旧 Release、Goal、typed 历史和人工锁均保留。

有限依赖开关只改变 qualifiers 是否依赖 prior_items/prior_feedback，固定两模型、六步骤，不扩大 PROJECT UNKNOWN 或任意语义依赖，不复制执行器。新逻辑候选不能混入原 goal_application/spec_task 生成标记。

性能修复只跳过当前只读 call、同 Connection/RootTransaction/user/Limits/Release 指纹完全匹配的重复来源验证。初次 bound 已验证当前完整 Release，入口 audit 可用其结果；实际 post-model commit_guard 不传私有 memo，再完整验证及实时摘要。无跨事务缓存，不扩大 lease、deadline、requests/tokens。

保留全部失败：独审 artifact READ 撤销红例及同 Release ABA UI 红例、P-B 夹具 import NameError、原三 claims/原300秒 deadline 未通过的两轮实际 P-B、旧 seed 图基线409/SKIP、外部测试/封存脚本错误。没有重签旧 seed 或重写 graph/软件/来源 seal。

NOT RUN：真实模型/付费 API、PG、Windows、native browser、真实人工语义验收、旧源码/旧数据库升级、完整 P-A/P-B、source 退休与链式任意修改、远端 CI、部署/发布。既有拒绝 browser/CI 路径未重试。

测试源冻结：398a77f35509e7b8280eee87c0725f07420ff7d2；最终只追加文档/证据提交，462 个 src/tests/pyproject 文件保持相同字节。77 个资格 Python 文件，资格摘要 16792a739267d9a1c497b86743220d9483e6e756f8442aa00f533ab43a94a2c8，core 4a55b395f2ad80bda2e51e372dccc53a2b960892。

| 实际验证 | 结果 |
| --- | --- |
| 软件资格 | 22 PASS |
| P-A 新版本第三材料、冷 Worker、独立合成复审 | 1 PASS / 274.74 秒 |
| P-B 独立同链路 | 1 PASS / 608.97 秒 |
| 实际模型返回时撤权、双 seal 缺失、Goal/实例版本变化、取消 | 7 唯一终态 PASS；6 个来自 r2，取消来自 r3 |
| 当前 HTTP/JSDOM 第四材料完整路径 | P-A/P-B 各 1 PASS / 共 428.29 秒；72 记录检查、110 可见操作、40 实际资产读取 |
| 项目 CSV 列修改、重验和页面回归 | 103 PASS / 0 FAIL / 1 SKIP / 910.33 秒 |
| 独立来源/同事务复用 | 1 组合 pytest PASS；11 探针（1 合法 + 10 拒绝），不是 11 pytest |
| 独立当前 UI 控制器 | 4 唯一节点 PASS、22 观察；与旧轮相同行为不重复累加 |

作者终态唯一 pytest PASS 136；独审另列。CSV SKIP 是 test_project_scope_check_crud_only_role，需独立 PostgreSQL 应用角色子进程环境；未运行不能计为绿。Ruff 和 Node syntax PASS；mypy 78 源文件只有既有 status_report/tools 5 个错误。

迟到测试历史：r1 外部夹具错读 resource.id，7 FAIL 尚未触发回调；r2 修为 resource_id 后 6 PASS，取消断言 1 FAIL。实际在途取消保守进入 RECONCILING，真实晚响应记为 REJECTED_KNOWN 且不保存成果，原 Run 按现有版本化取消命令关闭；r3 实际 1 PASS，仅一次模型请求，没有重提 Run。保留原脚本、XML、DB 和失败 stdout。

两轮 P-B 真失败（633.52、855.65 秒）及全部早期红例保留。最终 P-B THIRD 与页面新材料均在原300秒 Run deadline 内成功，未修改 lease、fence、clock、请求/token 预算。完整用例时间包含多个独立 Run、来源验证和人工复审，不能用其总耗时替代单 Run 时限。

证据：docs/evidence/logic-version-per-use-20261013/logic-version-per-use-evidence-20261013.tar.gz；成员摘要及逐成员大小/hash 回读，根 SUMMARY.json、SOURCE_FINAL.json、MANIFEST.json，作者原始 XML/DB/命令/闭包，独审封存报告与旧历史关联。页面脚本沿用部分 third 文案标签，实际第四材料字段为新的 beacon 文本、独立资源/Goal/实例，HTTP body 与成果内容已核对。

main、dev/f1-foundation、旧开发分支与旧 owner WIP 均不改；正常推送仅 dev/logic-version-per-use-20261013。不宣称远端 CI 绿，不重试既有拒绝 browser/CI 路径。当前有限合同无剩余实现阻塞；上述 NOT RUN 范围仍未验。

归档 SHA-256：`6754ac8b287b570433077b75cfdec213e7e5602b5664db16f61a0b44a672a217`；9,223 成员逐项回读一致，压缩 51,709,671 字节。
