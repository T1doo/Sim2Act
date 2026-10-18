# 项目历史原应用成果入口：原始证据

实际资格源 `c3aa1e4fa569e6ea08174e30811f216392b7ccd2`；生产初始冻结 `49e0e7b026126ba031141944b15f20e28b4358a7`；基线 `2c21d278dbe0d46e05c4ba4cccd473a8edfa4716`。唯一仓库写入者root，外部CJS作者与只读独审并行；生产仅app.js，沿用已有受鉴权API、实例/Run/成果及owner控制器，无新增executor/Grant。

项目→任务历史→查看任务→“在应用中打开此运行的成果与人工验收”：正确显示自然结果摘要，打开同一app/instance/machineRun/AppRun/Release，读取原成果v1和独立owner sequence0/PENDING。CSV精确金额字符串仍保留，不把所有内部任务当CSV或推定0模型。

最终1唯一pytest/1PASS，JUnit104.383s、外107.198s，29页内checks/9可见操作/33实际API GET+27实际静态资源（60HTTP），0POST/下载/页面Worker/页面模型。原成果JSON、原文与哈希实际读取；明确双击只一条导航；完整实例HTTP200仅延迟交付，换项目后释放不产生新HTTP或旧内容/工作区覆盖。完整55表before==after，持久每表行数/指纹与全局指纹；695执行输入/133生产零漂移。

首轮是页面启动前的测试记录器FAIL（JUnit51.244s、外54.219s）：实际异步调用完成3生成+1业务Mock，但同步记录钩子漏采，原mock-wire为空。仅补透明异步记录包装后重跑，生产/CJS与业务assert不变。两次合计8Mock/2业务Worker，只有第二轮4次完整原始模型线；首轮4次保留计数/fixture终态证据。真实模型0。失败没有被覆盖。

主要原件：

- [成功执行、命令与时间](passed-2/execution.json)、[JUnit](passed-2/junit.xml)、[pytest原输出](passed-2/pytest.stdout)。
- [页面请求/完整原响应、操作和检查](passed-2/actual-tmp/test_project_history_opens_ori0/results.json)、[逐步进度](passed-2/actual-tmp/test_project_history_opens_ori0/page-progress.jsonl)。
- [55表严格断言结果、行数/指纹与模型范围](passed-2/actual-tmp/test_project_history_opens_ori0/proof.json)、[四次Mock原始请求与响应](passed-2/actual-tmp/test_project_history_opens_ori0/mock-wire.json)、[正常fixture原始HTTP](passed-2/actual-tmp/test_project_history_opens_ori0/fixture-http.json)。
- [最终输入前](passed-2/inputs-before.json)、[输入后](passed-2/inputs-after.json)；[首轮FAIL](failed-1/junit.xml)、[首轮原诊断](failed-1/pytest.stdout)、[首9原文件保全指纹](first-failure-manifest.json)。
- [有限最终独审](independent/final-independent-review.md)、[独立纯文件审计原程序](independent/final-artifact-audit.py)、[结果](independent/final-artifact-audit.json)、[只读方法边界](independent/reviewer-method-and-provenance.json)。
- [初始远端](remote-heads-before.txt)、[基线](baseline.json)、[并行角色与来源](provenance.json)、[41项原件逐字节映射](selected-artifacts.json)。

41项所选原件1,779,854字节；另附来源说明、映射及本README，共44交付文件。新独审目录10文件的封存清单另计自身1711字节，SHA256 `2abb60ea4f3c2fce3949b460124e4fb14c5db19bd5e07d4588a2da4c82606cd9`。所选原件保持外部原路径字节，不改旧封存目录；最终交付另核全部Git blob与原件相同。

两份SQLite及重复HTTP JSONL留在 `/workspace/project-run-results-20261018/` 原位置，不复制数据库、整树或bundle。results保存每条API完整原响应文本；held行日志写入后仅多一个delivery_released观察字段，独审只对该字段作明确比较规范化。独审未开DB/SQL或重新跑产品，只核严格执行断言、持久指纹、原始HTTP及Git；不冒称独立重算55表全部行。

实际为合成P-A；CSV金额仅单独合成renderer检查，P-B共用接线及账号重连/同view实例Run/后台刷新围栏仅源码审查。本轮未动态重跑P-B、下载、恢复或旧故障矩阵。Windows/native、PG、真实模型/语义与远端CI未验证；不签完整F2/R0，旧满盘未落盘报告缺口未恢复。
