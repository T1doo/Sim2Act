# 官方资料核对

2026-10-21 在线读取，均为主要来源，只辅助说明对象接口，不替代安装版本和仓库的源码/回归证明。

- [Pydantic models / Faux immutability](https://docs.pydantic.dev/latest/concepts/models/#faux-immutability)：frozen 主要约束属性赋值，官方例子中嵌套 dict 仍可变。因此不能把现存 frozen model 留在消费者中当成递归 immutable 所有权证明。
- [SQLAlchemy 2.0 RowMapping](https://docs.sqlalchemy.org/en/20/core/connections.html#sqlalchemy.engine.RowMapping)：公开的 Mapping 视图支持列名/对象索引；keys/items 是行内容视图。这没有承诺业务 `dict(row)` 等于完整私有存储，本片继续沿用已审的 native metadata/全部 data/safe-index 控制投影，不自行序列化外来 Column key。
- 对 surrogate 的直接证据是本仓库当前 `contracts.strict_json`、`goal_applications.response_archive` 与实际 `_cold_graph_bytes`，以及 `PYTEST-UNICODE-BEFORE-FIX.txt`；不是纯 Python Pickler 替身或任意猴补丁。
