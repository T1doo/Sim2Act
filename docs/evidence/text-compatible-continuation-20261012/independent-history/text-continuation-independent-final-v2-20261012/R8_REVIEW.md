# R8：损坏的终态 FAILED 队列历史未在接续前完整验证

**实际 FAIL，两批准旧软件锚同样复现；本候选的先前72PASS不得提升为此缺口已通过。**

冻结source/tests map 14be76fa429605338b4fd0a818be0e7f9fa3a9c34750f75b454f8ff4c1f3e591；target implementation 316f8327b4e886365c850027ebcfd2634925f1d9a490073ceddcc9c487d9f9d3。新probe之后393文件仍零差异，见freeze-after-r8.json。

根唯一产品作者。此probe只写/tmp新克隆SQLite，未改源码/作者tests/原压缩fixture。保留该克隆的真实旧SUCCEEDED Run、typed v1、全部原data/history及旧AUTH/BIND/Release/Goal不动；新增明确标为FI_CORRUPTED_FAILED_HISTORY的合成FAILED Run+AppRun+binding：新IDs/new request key，terminal状态一致、无output/result_version、无新typed行；binding.fingerprint故设64个0。新合成Run也未添加真正frozen contract，不把它称有效旧Worker或合法旧任务。

| old anchor | preflight | commit | cold instance GET | cold corrupted Run GET |
|---|---:|---:|---:|---:|
| 233 | 201 | 201 | 409 | 409 |
| a747 | 201 | 201 | 409 | 409 |

cold拒绝具体原因为Queue binding fingerprint changed。preconditions仅核所有job的Run存在、本人/项目、terminal/equal status、无UNKNOWN；完整load_binding/frozen contract/Release/Goal校验只通过保留typed行verify调用，因此无typed的坏FAILED history未被拒绝。提交成功后正常冷instance API会遍历所有Run，才遭遇该损坏binding。

建议在当前target授权后，对所有选定实例terminal jobs先复用load_binding(...archival_software=old_fp)，并显式将frozen instance/app/runtime/Release+revision归入本实例合法历史；再给typed-success独立oracle、Operation+Intent+receipt核验。不修改正常executor、旧候选/数据/声明，不自动修损坏任务或将其称合法旧Worker。

实际原始证据：terminal-history/{233,a747}.json，terminal-history-v2.log/xml，test_terminal_history.py。精确拒绝要求的pytest本轮2FAIL，无SKIP/ERROR；原72节点结果继续原字节保存final-summary.json。首轮probe因我克隆runs.request_key未改造成UNIQUE约束的2夹具失败已完整保存在terminal-first-fixture-error；修/tmp request_key才得到上面的2真实FAIL。无产品探针复用旧被拒取消安装race，未调用CI/模型/native/PG。
