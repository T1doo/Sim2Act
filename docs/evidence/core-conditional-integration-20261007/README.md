# 条件报告产品来源绑定整合证据

独占worktree `/workspace/Sim2Act-core-conditional-integration`、branch `dev/core-conditional-integration-local`。base `0126f5459d7385f0c33f3ca4d9d585d91e2a4a1f` 正常merge已独审修复core `fb239a5e95f217df473da1569195397b0a2dca2a` 得 `e02000279da1774f84badd84254a548ea5a1f2b5`，保留0126 native/docs；实施前Plan commit `19a55dc`。首次产品source1ea1d33因metadata失读缺口不准交付；固定source为 **eb90d6bdb7711f63d7e7f20ca1317b5a9b7458b2**，文档tip另由最终commit给出。12修改src/tests的精确SHA与base→source patch在本目录；没有编辑原core/native-capture树、共享venv、安全helper或其他容器。

产品应用页增加来源绑定区，与人工Report表单分开。显式打开授权A-S材料→输入源假设→创建实际Run→手动只读刷新已知技术receipt→独立有限check→当前检查绑定的sealed有限候选→read_rules→check_report的注册read-only DAG→显式新资料/新假设cold Run→新check。人工报告从不进入新POST或替代持久Run.result/sourceproof/候选；extract前GET与checks重新服务端核验，未用client eligible缓存授权。source/cold一直WAITING_APPROVAL、semanticUNKNOWN、NOT_ACCEPTED；有限check PASS和extract技术编译SUCCEEDED/NOT_RUN不代表整体Run成功。BUSINESS BLOCK可有技术候选，但事实UNKNOWN/未覆盖目标/未决receipt/FAILED/PARTIAL/不完整来源均无可提取证明。

`results.json`包含28个真实HTTP/DOM产品断言：正常4Mock链、首次422可纠正、已接受回执丢失同键精确body重试、坏HTTP200回执保持UNKNOWN锁定、source/冷新facts、source前check新读、候选actualreceipt、cold编辑后晚check拒显示、项目ABA、冷reload无自动POST、metadata实际hash变更即使人工ctx空仍清candidate、实际refresh资源HTTP503清真实Report/plan-text/eligible/cold、撤权失读清内容、实际默认noProvider WAITING_RESOURCE无完成检查。`actual-ledger.json`/`mock-wires.json`来自最终专项真实执行：4 RECEIVED Attempts、2 VERIFIED resource.read、4slots同offline14池；权限计数前后相等，LIVE请求0。Mock响应是测试手写Report，未读gold生成输入或响应；冷输入不携带旧Report。测试控制器的显式Mock注入只存在测试fixture，产品UI无provider activation。

隔离 `/tmp/core-conditional-integration-venv` local .pth先本src、再共享deps目录，未处理共享旧editable .pth/finder、安装新包或修改共享venv。controller与干净env child模块路径均当前tree；`isolated-python-provenance.json`保留。测试命令：

```sh
NODE_PATH=/workspace/browser-tools/node_modules:/opt/codex/runtimes/cua/lib/node_modules /tmp/core-conditional-integration-venv/bin/python -m pytest tests/test_conditional_run_product.py tests/test_conditional_checks_ui.py tests/test_conditional_run_bindings.py -q
/tmp/core-conditional-integration-venv/bin/python -m ruff check src tests/test_conditional_run_product.py
/tmp/core-conditional-integration-venv/bin/python -m mypy src
NODE_PATH=/workspace/browser-tools/node_modules:/opt/codex/runtimes/cua/lib/node_modules /tmp/core-conditional-integration-venv/bin/python -m pytest -q -ra
```

最终专项50 PASS/1 SKIP（39.94秒，SQLite没有PG CRUD role，完整PG独立核）；Ruff/node语法/mypy37/diffcheck通过。完整SQLite与PG已以固定eb90完成；PG仅额外传私有SIM2ACT_TEST_DATABASE_URL env，专用标签 `sim2act.core-conditional-integration=20261007` / container `sim2act-core-conditional-integration-20261007`，独立随机localhost端口、每fixture独立schema/角色，URL不进repo。全量终态及owned资源清理已完成，见verification-summary.json、cleanup.json和阶段Log。

独审当前eb90：25自编actualHTTP PASS（20.81秒）；9controlled DOM全PASS；独立扩展真实Uvicorn/JSDOM1PASS（7.44秒、28assertions），加prior UNKNOWN同key重试422仍锁定、latecoldPOST编辑后拒旧返回，Mock报告独立手写。final-review SHA `ab2c1a711e49b08f57079e9b10fee86898026098a7d857d1b77d712bfc00bcff`，14项manifest全部核对。只批准finite offline candidate技术范围，未PG/native/pixel/owner/整体P-B签收。

真实失败历史完整保留：首次漏静态route；次test-only空JSON拒绝；1ea metadata503 blocker及独审撤销、完整SQLite117PASS2SKIP/PG65PASS后SIGINT STOP_SOURCE_DEFECT（exit2，不称完整通过）；核清owned processes/schema/role0后才修源。修后oracle未捕refresh既有reject的49PASS1FAIL1SKIP日志也保留，再assert.rejects并检查DOM后通过。旧1ea不签新source。

当前仍缺：明确可信provider activation/真实模型批准、现实事实核验、开放语义/解释检查、owner接受、正式App/Release绑定。此片仅既有有限假设与注册DAG的产品入口，不启用准备器、不新Grant/真实身份/表/DDL/任意代码/LIVE/部署/push/CI。原生/像素本线NOT_RUN，其他独立线结果不作本source同源签收。下一片需在批准边界内扩大独立覆盖和确定正式App绑定合同，不能把当前UNKNOWN提升。

最终固定eb90完整结果：**SQLite976 PASS / 40 SKIP / 3warnings（542.53秒）**，**PG1012 PASS / 4 SKIP / 3warnings（1146.15秒）**，均1016 collected、exit0、0FAIL/ERROR。PG跳过仅Windows1、明确SQLite-only旧protocol UI2、保护Chromium1；新增产品DOM在PG真实通过，PG适用role/锁/进程分支通过。完整sanitize日志见sqlite-full-final-isolated.log/pg-full-final-isolated.log；warning真实保留，未改安全环境。

cleanup.json：仅owned schema0/role0/publictable0/controller及children0，唯一标签容器已删除且再次核对0；私有URL/rawPG log删除。12source SHA、独审14manifest全部核对；verification-summary.json汇总当前source，不使用1ea部分回归作修版通过。无push/CI/LIVE或准备器激活，仍是finite offline candidate-only产品入口。
