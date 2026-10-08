# CSV candidate development-baseline integration

父线程2026-10-08明确授权：同一第二reviewer已闭合slash/NUL两个P2，完整CSV候选及两键修复历史可进入dev/f1-foundation；DAG保持独立，不能混入此次整合。独审源f40d9751771166bc877fcfd10237f06fc9e59a48、候选4513b4eed9a9794333d7a30cf96b1ac9f88d48fb。parent-independent-review.json记录父线程回传的限定键处理独审38 SQLite PASS /37 PG PASS+1历史SQLite专属SKIP、实际body/path NUL400、非法SQL bind0、合法键/幂等/旧记录保持。未冒称持有 reviewer 实例原始文件或DAG签收。

显式fetch和ls-remote确认原dev/f1-foundation仍122b2e6f25402e5d693da05c945727b7cbf4ceeb、review候选451不变；122→a383112→eb2e5fb→451是完整线性祖先链。使用merge --ff-only推进本地开发分支到精确451，没有squash、rebase、main或force；src/tests与f40d975逐字节Git diff为空，无csv_dag文件/引用。DAG源码e8b1ed4及720例双后端证据先独立保存868fcd7，整合测试期间不更换源码。

本轮按实际整合451源码重新执行5文件135唯一用例：控制边界91、slash键13、列补丁28、实际列补丁DOM1、原CSV/Report图DOM2。实际SQLite135 PASS/0FAIL/0ERROR/0SKIP（112.97s），PG134 PASS/0FAIL/0ERROR/1历史SQLite专属SKIP（174.05s）。结果与skip名由test-summary.json从JUnit派生；provenance保留所有src/tests测试前后hash，确认source_unchanged。Ruff全src/scripts/tests与mypy48源码文件。原断言、Windows900 / Edge240 / Node150、CI/脚本/依赖锁不改；LIVE=0，无真实模型、新CI、main写入、forcepush、部署、凭据设置或安全权限扩大。

原amount30应用保留，新quantity15草案/实际受影响检查/无关对象保持证明见原列补丁证据及[用户指南](../../F2/ColumnBindingPatchQuickstart.md)。独审通过不代表真实任务gold、完整P-B、人工验收或正式发布。工程候选语义UNKNOWN、ownerPENDING、发布false；原生Windows/Edge NOT_RUN。旧1591全量不当新源码证据。

整合准备中显式--track因原remote fetch refspec仅main而失败，并部分替换工作树但未切换HEAD；已保存的DAG868提交未受损。恢复自己已提交的跟踪文件，确认无差异后用--no-track切换，再ff-only到451。首次误启动的两套pytest因文件缺失退出4，未创建DB夹具，不当回归结果；initial/记录失败、恢复与保留/缺失的诊断边界。正确回归仅使用451，源码前后hash证明没有混树。

测试使用DAG阶段保留的自有network-none PG17.9及私有Unix socket、jsdom30.1.2；每例仅自有schema/临时应用角色。两阶段结束共同核清理，最终PG schema/role与container/image/临时路径状态见cleanup证据。开发.venv保留供授权持续开发。
