# DeliveryGraph 历史回执类型修复

基线：`e66a437be14d40ff7ad70bad2a96e30a1d3db572`。

历史回执原用 Python 字典相等比较；其 `False == 0`、`1 == True == 1.0` 可放过 JSON 标量类型篡改。现在比较规范 JSON 的 SHA-256，保留排序无关的合法重放，同时拒绝类型替换，错误仍为 `VERSION_CONFLICT`。当前权限、版本、图锚和锁检查顺序不变，既有 schema/API 不变。

独立回归覆盖 false→0、保留对象 revision 1→true、1→1.0，并验证原回执可重放。核心严格模型的 revision bool 拒绝行为原已存在。此修复不涉及 API、UI、Store、数据库、规则实现或目标存储；调用方仍须提供可信上下文和历史回执。

验证：Linux/Python 3.12.14；图原 83 项与新回归 3 项合计 86 PASS/0 FAIL/0 SKIP（0.51 秒），Ruff PASS、Mypy 38 source files PASS；另合同辅助器当前 14 自测 PASS。只有既有 Starlette 弃用警告。真实 Win11/DB/API 未运行。

独立审查确认源码仅一行修改，3 项回归另行复跑 PASS/0.05 秒，包含合法重放。修复后的当前计划先重验授权和版本，协调重签旧回执也不能替代新鲜计划。
