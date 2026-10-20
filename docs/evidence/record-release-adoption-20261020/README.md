# 原 F2-T08/AT-16 本地记录兼容采纳实证

实现与边界：[功能合同](../../F2/LocalRecordReleaseAdoption20261020.md)。起点与推送前目标远端均为完整 SHA `3312d0cd79f5d148351adc55314680d84fba1d2c`，其祖先含原 `441fdaa251fd2797857f557a16590946b22756ec`。本轮普通开发分支提交；最终提交 SHA 由 git 历史确定，测试使用本目录 `source-sha256.json` 的精确产品/测试字节。

最终实际结果：`actual-summary.json`、原 JUnit `record-adoption-backend-regression.xml.gz`（10/10、17.629秒）和 `record-adoption-ui-final.xml.gz`（4/4、21.346秒），均0失败/错误/跳过。四页面分别为release-adoption、content-edit、private-preview、navigation；GET/POST/检查数与源差异分别列出，不将此前通过轮次累计成更多独立节点。

`backend-final` 保留真正 API/Worker 的同 iid A/B→采纳→更正、独立 fold、冷读结果与负例结果；测试另对55表前后差异、不可变行和每次拒绝零写作硬断言。`ui-final` 保留逐次原 HTTP、IPC、页面结果、正常 Worker 日志、原资产 SHA 和前后输入清单；每例 `source-changes={}`。`artifacts.json` 给出159份原件各自原始及gzip字节数/SHA256，gzip固定mtime=0，可解压核实。合成账号/文本，仅本地fixture；未使用真实模型或用户库。

最终命令：

```text
.venv/bin/pytest -q tests/test_local_record_adoption.py \
 tests/test_local_record_apps.py::test_actual_a_b_and_done_fold_independent_records_preserve_immutable_events \
 tests/test_local_record_apps.py::test_account_project_instance_and_legacy_family_scope_before_private_bodies \
 tests/test_local_record_apps.py::test_project_write_revoke_rejects_before_historical_private_bodies \
 tests/test_local_record_apps.py::test_referenced_json_read_revoke_blocks_current_recovery_and_commit_before_bodies \
 tests/test_private_record_preview.py::test_real_private_storage_isolated_and_cold_readback_then_explicit_business_write \
 tests/test_private_record_preview.py::test_write_revocation_denies_content_but_original_metadata_cancel_remains \
 --basetemp=/tmp/record-adoption-backend-regression --junitxml=/tmp/record-adoption-backend-regression.xml

env NODE_PATH=/tmp/sim2act-node-edit/node_modules .venv/bin/pytest -q \
 'tests/test_local_record_apps_ui.py::test_local_record_page_explicit_flow_and_fenced_navigation_actual_http[release-adoption]' \
 'tests/test_local_record_apps_ui.py::test_local_record_page_explicit_flow_and_fenced_navigation_actual_http[content-edit]' \
 'tests/test_local_record_apps_ui.py::test_local_record_page_explicit_flow_and_fenced_navigation_actual_http[private-preview]' \
 'tests/test_local_record_apps_ui.py::test_local_record_page_explicit_flow_and_fenced_navigation_actual_http[navigation]' \
 --basetemp=/tmp/record-adoption-ui-final --junitxml=/tmp/record-adoption-ui-final.xml
```

Ruff检查三份Python改动/测试、mypy两个产品Python文件、两个JS的`node --check`、`git diff --check`均PASS。无新增依赖、表、执行器、凭据、权限或服务。

失败/中间轮保留：`ui-first-failure` 实际1 FAIL（EDIT丢回执后清空instance，校验误依赖当前instance能力）；修正为原intent Release的精确已验证能力。`ui-second` 新流程1 PASS。`ui-intermediate-nine` 原本意选四场景的 `-k ... navigation` 意外匹配公共函数名，实际执行9 PASS/36.22秒；该轮在第二P2最终修正前，不能代签最终字节。最终准确四个node id重跑，两个独审P2的回归均通过。此前作者后端3 PASS及旧内容更正6 PASS仅为诊断，未并入最终14。

`independent-review` 保留有限静态审查原件与最终原件核对；审查者没有重跑测试，作者实际执行和独审核证分列；最终原件复核有限PASS，独立重算事件hash/链/采纳边界prefix/最终fold/B保持。未独立重放SQL/事务回滚/Grant。三份产品哈希应与报告完全相同。范围只为本补丁新建业务v1→v2的一次显式采纳；基线旧软件实例仍受精确软件指纹拒绝。PG/CI/Windows/native/真实模型与语义、旧软件迁移、本完整PB的G0/W5/G1/finalguard、F2/R0、正式发布均未据此关闭。
