# 独立验收：b589809375c89b4d93617d91c780a1e0f7f704e2

实际范围为以下两个 SQLite 用例，同一 pytest 串行执行，2 passed / 0 failed / 0 skipped，361.11 秒。仅有一条 Starlette TestClient 弃用警告。

- `tests/test_csv_derive_receipt.py`：原 derive POST201 的完整 body/request fingerprint/response 精确 GET200 恢复；缺 key409；撤回当前 runtime 对原 resource 的精确 resource.read Grant 后 GET403 GRANT_REVOKED。三次 GET 全库不变。SQL positive control 2 次 journal body SELECT，撤权后 0 次。
- `tests/test_csv_column_revisions.py::test_visible_current_effective_revision_and_fenced_recovery[same-navigation]`：真实 HTTP/JSDOM，合成 prior software registry 产生实际旧图409；显式 derive201丢回执，原 key GET200 恢复；三个确认阶段返回完整冻结 payload、重新显式确认；原实例 rev3/data v3、Goal v2、新独立 Run amount30/result_version3、人审 PENDING，旧 v1/v2 结果及记录保留。40 项页面检查通过。

此处是合成 prior registry 场景，未执行真实 ce3 二进制升级。

输入从精确 Git SHA 只读导出：src/tests/schemas/pyproject + bounded32/evaluation5/materials14，共661 Git blobs。运行前后每项 Git blob/SHA256 全一致，无额外输入文件。26 个实际加载页面资产逐项与冻结 Git 字节一致。唯一外部运行依赖是显式记录的 node_modules symlink；Python3.12.14、Node24.19.0、jsdom30.1.2。

保留轻 case 的0 Run 和页面 case 的5个 SUCCEEDED Run；每个 Run 恰好1个 CLAIMED event，两个DB的 model attempts均为0。没有重跑、没有预算/lease/产品超时调整，没有模型调用。Windows、PostgreSQL、远端CI及其他回归矩阵未执行。

证据：

- `run-command.json`、`commands.txt`、`pytest.log`、`junit.xml`
- `inputs-before.json`、`inputs-after.json`、`result.json`、`claim-audit.json`
- `artifacts/test_exact_derive_receipt_is_f0/actual-derive-receipt.json`、`actual-http.json`、`fixture.db`
- `artifacts/test_visible_current_effective0/page-result.json`、`actual-browser-delivery.json`、`actual-http.json`、`node.stderr`、`fixture.db`
- `evidence-sha256.json` 为运行代码、输入清单和原始证据的校验索引。

只在本 /tmp 目录写文件；仓库只读。启动时主工作区HEAD为d74，后续只读记录观察到root已切至b589且clean；本次执行始终使用独立冻结快照。
