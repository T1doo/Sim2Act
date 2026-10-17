# 独立执行与源码审查：连续列修订 d74

限定结果：`d74f2fed55b6067e5d3c34ca6e4348b92e75f48a` 的三个页面用例 **3 PASS / 0 FAIL / 0 ERROR / 0 SKIP**，3 unique、3 次 pytestcase 调用，未重跑。此结论不准入随后新增的软件升级修复；d74 的旧 registry 图锚升级缺口已另报根代理。

从该 SHA 的精确 Git archive 建立本地独立快照，未使用旧 bundle。提取并核对 648 个 Git 输入：src 127、tests 474、schemas 7、评测 docs 37（bounded offline 32 + protocol/evaluation 5），另 pyproject 与两个 requirements lock。运行前后 648 个文件一致，再次从同 SHA 生成 Git archive 逐文件对照一致。共享仓库仅只读；依赖为既有 node_modules 的只读使用链接，无安装或下载。

运行命令与环境见 `command.json`、`environment.json`；原始输出为 `pytest.log`、`junit.xml`、`execution.json`。单进程串行运行 `test_visible_current_effective_revision_and_fenced_recovery` 的三个参数。执行起止 13:46:07.846–13:59:22.430 UTC，外层 wall 794.584 秒，pytest 789.10 秒，JUnit suite 789.103 秒。仅有既有 Starlette TestClient/httpx 弃用警告，无测试失败、跳过或重试；900 秒页面夹具 watchdog 未改动，也不是产品服务端 deadline。

| 用例 | JUnit 秒 | 页面断言 | 页面请求 | 结果 |
| --- | ---: | ---: | ---: | --- |
| same-navigation | 314.729 | 37 | 76 | PASS |
| next-unknown | 325.817 | 31 | 83 | PASS |
| navigation | 147.233 | 14 | 76 | PASS |

全部测试通过后运行独立原件校验 `verify-evidence.py`，其结果见 `independent-proof.json`。校验不再次调用 API、Worker 或页面：

- same-navigation 三次离返各自从新的 context GET 开始，到下一次显式 POST 前，分别有完整的 2、5、7 个 GET 200。原 preview、CHECK、Release 批准及 live approval、Release、采用批准按阶段原路径回读；完整服务端冻结 JSON 等值，quantity→amount 两列恢复并锁定，旧确认清空、新确认前按钮禁用。离返和重核段零 POST。
- next-unknown 的原 CHECK 202、Release commit 200、CAS commit 200 均实际受理后模拟丢回执，各路径恰好一次 POST。原键恢复段分别为 8、10、7 个 GET 200，没有重发。CAS 独立核对原实例、账号、项目、应用、runtime、版本、数据版本、目标 Release 指纹和 exact switch history。
- 两个完成链分别保留 Goal v2（零 Goal PUT）与显式保存同卡 Goal v3（恰好一次 PUT）。新业务 Run、typed app Run、Release 与结果版本 3 相互绑定，精确新 Run 的 owner-review GET 200/PENDING。只读 SQLite 再核三条独立业务 Run 的版本 1/2/3、列 amount/quantity/amount、字符串结果 30/5/30，三者 Run 和 Release 均不同；Grant/principal 最终计数与初值相等。测试还实际断言旧存储行保留。
- navigation 实际执行项目、实例、账号切换后的迟到回调隔离及原 CHECK 恢复，没有新增 CHECK。它刻意选中另一原始 root 实例，并在该实例上显式读取 baseline；原有 root derive 路径是该动作允许的 POST，不属于当前 v2→v3 continuation baseline。
- 每个页面实际加载的 26 个 HTML/CSS/JS 资产哈希均与冻结 Git 输入一致。三个页面及完整 fixture HTTP 原件中 HTTP >=400 共 **0**，无 protocol/contracts 旁路 400。

独立原件校验首版曾把“当前 continuation baseline 零 derive”错误扩大为整个 navigation 用例零 derive，因另一 root 实例的显式 baseline 动作而触发脚本断言。保留 `verifier-attempt-1.py` 和 `verifier-attempt-1.log`；修正只限定原 v2 continuation baseline，并明确 navigation 的另一 root baseline 例外后，所有校验通过。这是审查脚本范围错误，未改产品/测试，未重新执行 pytest，未把该输出隐去。

范围：合成 CSV、实际 ASGI/TestClient、原 NoModel Worker、完整实际产品 DOM 的 JSDOM。Python 证明使用新 Store/engine 重开读取后 dispose，**未进程重启**。未执行原生浏览器、PostgreSQL、真实模型、Windows 或远端 CI；未验证 ABA 回切后才到达的回调；仅看到进一步修订入口，未执行 v4。

原始材料全部保留在本目录的 `data/test_visible_current_effective{0,1,2}`（含 actual-http、page-result、SQLite、node.stderr、info，两完成链另有实际合同/新 Run 证明）。`source-before.json` 与 `source-after.json` 保留全部输入哈希。`manifest.json` 和 `SHA256SUMS` 仅列本目录证据文件，排除 snapshot/cache/node_modules/symlink，并不修改原始文件。新升级修复草稿的只读评估另见 `static-review.md`；需在其新冻结 SHA 上重新验证。
