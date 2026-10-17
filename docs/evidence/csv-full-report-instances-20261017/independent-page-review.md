# 完整 CSV MD 内部交付：独立 lost/navigation 验证

冻结源码 `d22e82a66fdb010d778ee6d8903e50a61f755c52`。本轮独立执行 **2 unique / 2 pytestcase calls，2 PASS / 0 FAIL / 0 ERROR / 0 SKIP**，无修改、重试或跳过。

从该 SHA 精确 Git archive 建立新 `/tmp` 快照，未复制旧 bundle 或旧源码。656 个输入包括 src128、tests481、schemas7、所需 docs37、pyproject 与两个 requirements lock，提取后与 Git 原字节一致；源文件0444，运行前后及再次 Git archive 均一致。仅链接并只读使用既有 `/workspace/Sim2Act/scripts/engineering-ci/node_modules`，未安装依赖。共享仓库只读；开跑时 HEAD 精确 d22、工作区干净，临时盘可用约7.8G。

命令见 `command.json`：单进程串行运行 `test_visible_complete_md_internal_delivery_and_original_run[lost]` 与 `[navigation]`。外层执行 14:41:16.972–14:42:23.461 UTC，wall66.490秒，pytest59.33秒，JUnit suite59.327秒。240秒夹具 watchdog、12000ms页面状态等待和 Worker 调用方式均使用已提交原样。只有既有 Starlette/httpx 弃用警告。

| 用例 | JUnit秒 | 页面断言 | 页面请求 | 完整HTTP请求 | 资产 |
| --- | ---: | ---: | ---: | ---: | ---: |
| lost | 34.720 | 54 | 48 | 84 | 26 |
| navigation | 22.132 | 43 | 66 | 105 | 26 |

`verify-evidence.py` 在执行结束后仅只读原件与 SQLite，不发新请求、不重跑页面或 Worker。其首轮验证通过，结果为 `independent-proof.json`：

- lost 实际 Release批准201、Release commit200、创建实例201、实例use202，均在真实响应后持有并丢弃，再经实际导航返回。四路径各一次POST（含双击），分别找到原键的GET200；从每次已受理POST至下一次明确POST/流程结束之间全部为GET200，没有自动写入。另保存流程源提取一次，页面POST总数5。新Run未被隐式确认，显式打开同一 ordinary Run 完整MD预览时，原workflow事件与新instance事件分开校验。
- navigation 实际覆盖迟到CSV列响应隔离、项目切换后的已受理use202隔离、账号切换后的已受理use202隔离；两个实例的材料、原键、Run和请求指纹分别绑定。两个迟到受理都没有继续发原scope回执GET。pending实例核验窗口实际断言旧workflow历史和open控件均不显示。
- 两页面的26个实际HTML/CSS/JS资产均与冻结Git字节相等。完整HTTP原件及页面记录中 HTTP>=400 均为0；两个node.stderr均0字节。
- 独立Python规范JSON/SHA256再算每次实例请求body指纹，均等于真实接受回执。只读最终SQLite再查lost的1条、navigation的2条ordinary Run及typed app Run相互绑定、状态WAITING_APPROVAL、无结果版本。每fixture仅保留来源任务3条operations；attempts、reservations、internal_run_bindings、internal_instance_data均0。两个用例执行的提交版后置断言还要求Grant全行、principal全行、app_drafts全行不变，均通过；最终每fixture grants18、principals4。

范围说明：来源完整报告由夹具的原 NoModel Worker 实际完成，两个用例没有调用新instance-use Worker、确认新合同或下载新MD。deliver、采用、成功执行和新MD下载属于根代理并行用例，本报告不代其声称通过。这里只证明合成CSV、实际ASGI/TestClient/SQLite、完整实际产品DOM的JSDOM；未运行原生浏览器、PG、真实模型、Windows或远端CI，未证明进程重启或ABA。

原始命令、日志、JUnit、info、HTTP、page-result（含资产哈希与接受/丢回执标记）、两个SQLite、node.stderr和page-worker-proof全部保留。`source-before.json`、`source-after.json` 保留656个输入哈希；`manifest.json`/`SHA256SUMS` 仅列证据payload，排除snapshot/cache/node_modules/symlink，不改写任何原件。本轮无未解决的执行阻塞；整体交付仍须与根代理的deliver和权限证据合并评估。
