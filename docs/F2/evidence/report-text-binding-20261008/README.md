# Report text 展示候选证据

最终源码 `ffda5b00a9a1469b454728adb5a0005016cd0a55`，分支
`dev/report-text-binding-20261008`。基线 dev 为
`cc368dbbda1e4452df64efcac76e184dafe65e6d`，包含最初指定的
`122b2e6f25402e5d693da05c945727b7cbf4ceeb` 祖先。独立候选，不覆盖 main/dev。

实现：原页面上的 `text: decision → explanation` 独立不可变展示定义、
原计划及来源账本绑定、确切历史 Run/version/fence/result 指纹确认、实际
有类型字符串回读、安全 textContent、新旧版本保留、原键恢复和冷浏览器读回。
原 canonical manifest/图/边/输入/schema/权限/计算输出/历史不改写。

## 测试范围和源码

| 阶段 | 精确源码/影响 | SQLite | PostgreSQL |
| --- | --- | --- | --- |
| 新后端边界/API + 原 Report/DeliveryGraph/CSV API | 580a88e；112 个唯一 pytest 案例，后端在 ffda5b0 字节完全相同 | 110 PASS、2 SKIP | 112 PASS |
| 初版 DOM | 580a88e，新增 27、原 Report 49 断言 | PASS | PASS |
| ABA 最小 UI 修复后的重新回归 | ffda5b0，2 个真实 HTTP/product JS/jsdom pytest；新增30 + 原49断言 | 2 PASS，66.35s | 2 PASS，95.25s |

最终影响范围共 **114 个唯一 pytest 案例**：SQLite **112 PASS、2 SKIP**，
PostgreSQL **114 PASS**。不是对 ffda5b0 重跑一次全量测试的宣称：后端/API
完整定向阶段在 580a88e 运行，随后只变更按钮同步及对应 DOM 夹具，确切改动
重新双后端验证。`source-hashes.json` 证明后端文件相同；四份最终 DOM
`results.json` 的实际加载脚本哈希均已重新逐项核对，见
`loaded-source-verification.json`。原断言/驱动/Windows 900 / Edge 240 /
Node 150 标准未修改。Mypy 53 源文件、Ruff、JS语法和 diff 检查通过。

原 API 回归：`test_report_manifest_apps.py`、`test_delivery_graph_apps.py`、
`test_column_patches.py`。新增：`test_report_presentations.py`、
`test_report_text_binding_boundary.py`、`test_report_presentation_ui.py`。
覆盖精确版本、非法 component/未知输出/HTML与表达式字段/bool 版本、撤权、
来源变化、目标 VIEW 锁、peer 成员/权限/锁/图变化、协调重签 definition/check
seal、Run fence/result 损坏、原键幂等、无关对象保持、DOM导航与同应用重开。
peer_graph 案例同时上锁，不能单独证明无锁图锚变化；身份交错是测试 token
切换，不能称真实 reconnect。独审为只读 LIMITED PASS，未运行并行测试。

## 失败与开放问题

失败证据保留，未以最终通过掩盖：

- 自有 PG 初始 socket 初始化两次失败；官方入口初始化 psql 使用默认
  `/var/run/postgresql`，最后同时声明 `/socket,/var/run/postgresql`，仍
  network none、无映射端口。这是自有夹具配置修正，未改产品或凭据。
- 新测试最初误猜原来源/撤权错误码，按现有 VERIFICATION_FAILED /
  GRANT_REVOKED 校准，仅修改新增 oracle，原断言不变。
- 最初 DOM 计数 26!=27；随后一次 lost-check 等待6秒超时。该次没有完整
  HTTP时序，原因仍 **OPEN**；单次成功重跑不能解释它。首次计数失败时还
  捕获 SQLite database locked；后续夹具明确关闭 interval、排空自身
  HTTP/actions，不把这种导航夹具当后台轮询验收。
- 一次 PG 初步测试在修改 peer 夹具过程中启动，加载了旧 DataBinding.format
  判断，18 PASS 后 StopIteration；最终固定测试完整 PG114 PASS。
- 新 ABA oracle 对580a88e静态脚本明确失败
  `late same-app completion reconciles new controls`（8.88s）。ffda5b0
  只同步当前已连接的控件；晚响应仍不画旧结果、不自动续写。
- 以前全量2051的 `resources-history` Future10秒超时继续 **OPEN**；本轮
  未运行该全量、未修改其上限、不用旧1591/2051结果证明新改动。

## 交付边界

`ARCHIVED_RESULT_PRESENTATION_ONLY`，工程证据为 `SYNTHETIC_RESULT_ONLY`。
未发现已配置产品数据库/默认产品目录/可核查实际 Report。实际材料验证
PENDING；语义 UNKNOWN、人工 PENDING、整体 NOT_ACCEPTED、发布关闭、LIVE=0。
原 Report 恒含 PROJECT未知依赖，原扩验/遗漏/队列保留 PENDING或BLOCKED_PARTIAL。
本轮未完成 canonical VIEW实际补丁、PROJECT检查队列、完整AT13/F2-T07、
通用P-B或人工签收，也未运行原生Windows/Edge。没有真实模型调用或业务写权限。

所有临时资源自有隔离。结束前 test schemas / temporary CRUD roles / public
业务表均0。已停止并删除自有PG容器、事件证明归属的匿名卷及固定镜像；
私有npm/测试目录等42条自有临时路径已清理，别人的pytest0/1/2未触碰。
见 `pg-cleanup-audit.txt`、`owned-volume-events.jsonl` 与
`temporary-resource-cleanup.json`。不强制删除、不扩大安全权限。

用户复现见 [Quickstart](../../ReportTextBindingQuickstart.md)，原冻结范围见
[Contract](../../ReportTextBindingContract.md)。候选普通push前后检查远端祖先、
目标分支与main/dev引用；不合并、不部署、不启用provider、不触发新CI。
