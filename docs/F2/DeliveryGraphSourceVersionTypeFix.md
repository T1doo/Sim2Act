# DeliveryGraph 外部版本输入严格类型修复

2026-10-07，独立分支 `dev/delivery-graph-source-version-types`，父提交 `0836bf7518e4e175d228bd5c0be28fae8ac83463`。这是 derive 的 source_versions 输入问题，与前次历史回执类型敏感比较位置不同。主线报告整合基线 3f07b751；本线不修改该主线/API/Store，只提供可 cherry-pick 的纯核心修复。

## 复现与根因

实际运行：可信 context.source_versions.revision 保留严格整数 1；单独将外部 source_versions 某一项 revision 改成 true 或 1.0，两者均被旧 derive 接受。原入口只校验有限 JSON，再用 Python dict 相等比较 trusted context；`True == 1.0 == 1` 导致漏检。原 bool 负例同时修改 context，因此提前被严格 Context 模型拒绝，没覆盖这个单独输入路径。

新增 `_source_versions` 校验映射容器/128 项上限，并逐条通过现有闭合严格 SourceVersion 模型，拒绝 bool/float revision、非法版本对象与额外字段，返回 INVALID_MANIFEST。合法整数版本与可信上下文不一致仍返回 VERSION_CONFLICT；合法输入的图和稳定 ID 保持不变。没有改变接口/schema、授权和锁逻辑，没有修改共享 Store/API、安装/CI、规则或目标存储。

## 同类边界审计与回归

22 项新测试包含：全部外部版本逻辑键单独替换 revision（bool/float），derive 的 context 嵌套版本、plan 的 current_context 嵌套版本、authorization_revision、node_revisions、request.expected_revision、持久 graph node revision 与 graph authorization_revision；两类型均严格拒绝。另校验闭合映射/对象和合法整数版本冲突。原历史 receipt 三项类型回归保持通过。

Linux x86_64、Python 3.12.14，隔离测试环境，显式 PYTHONPATH 指向当前工作树：

```bash
PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_delivery_graph.py tests/test_delivery_graph_receipt_types.py tests/test_delivery_graph_source_version_types.py tests/test_contract_semantics.py tests/test_model_protocol.py
python -m ruff check src tests/test_delivery_graph_source_version_types.py
PYTHONPATH=src python -m mypy src
```

相关全模块回归 169 PASS/0 FAIL/0 SKIP/0.82 秒（图原 83 + receipt 3 + 新版本输入 22 + 既有契约/模型协议 61）；Ruff 全 src 及新测试 PASS、Mypy 38 source files PASS、diff whitespace PASS。仅既有 Starlette/httpx 弃用警告；没有网络、数据库或模型调用。真实产品 API、DB/Windows 未测，由主线继续整合验收。本修复拒绝外部畸形版本，不能替代服务端实际实现源码/FrozenGoalSpec 内容绑定。

独立审查另行运行图全回归 108 PASS/0 FAIL/0 SKIP/0.61 秒，确认无新增阻塞、允许提交；未修改文件或连接外部服务。
