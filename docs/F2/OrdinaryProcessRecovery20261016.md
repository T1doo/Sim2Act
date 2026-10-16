普通规范应用跨进程恢复验证，2026-10-16。

实际验证的实现提交为 `2a9ff5ab94031a838e60bfdbe39beef8704686f3`，基于已验 `95ff54e38588033a03a5ed7cd9ff870648f4f8cd`。新增三个回归测试文件，产品源码完全相同。本轮没有发现需要修改产品执行器的缺口。

合同限定为：同一 JSDOM 文档保留页面自己生成的原请求键；真实回环 HTTP 返回 Source 运行受理 202 后，在送达页面前控制性丢弃该响应；页面保留 pending，首次键控回执读取尚未发生。独立操作系统 Worker 在 SQLite 实际保存 Source 后，仅停止本轮登记的 API/Worker，再启动新 API。页面原生“原请求键读取”动作通过 GET 找回同一 Run/AppRun，随后显式读取已保存内容。再由页面选择完整 Cold Goal/新材料、预览并明确确认绑定、发布内部快照和创建独立实例，独立 Worker 保存 Cold。Source 结果、实例数据与两个 VERIFIED Attempt 历史逐字段不变。Source/Cold 各只有一次运行 POST。

最终测试：1 PASS、0 FAIL、0 ERROR、0 SKIP，pytest 退出码 0，172.338 秒。24 项页面检查，实际读取入口/CSS/19 个脚本共 21 个资产并核对原始字节哈希；517 个 src/tests/pyproject 文件执行前后及提交字节一致。生成/Source/Cold 的显式 MockTransport 调用分别为 3/2/2，Cold 线报含新材料且不含 Source。6 个启动记录均有同 PID/starttime/token/argv 的结束记录，清理回执为 PASS。两个新 Python 文件 ruff 与 Node 语法检查通过。

失败历史完整保留：首轮 1 FAIL，是 Popen 后立即读取 /proc/cmdline 暂空，且登记发生在断言之后，留下已完成三次生成调用的本轮自有 Worker；核对实际命令行、唯一 token、固定配置及完成回执，双查 PID/starttime 后仅停止该 Worker。Source 尚未提交。修为先登记 PID/starttime，限时等待 exec 稳定，停止前要求完整身份匹配。静审同时发现资产数量魔数不适用，改为从真实 HTML 推导精确资产集合。第二轮为开发 1 PASS/206.242 秒，24 检查，460 文件仅是当时冻结子集。最终另补完整 517 文件闭包、实际 bind/listen 后的进程归属就绪回执、逐子进程独立清理及增量原始 HTTP 日志，再以新目录/新库运行上述最终提交；不复用旧数据库或请求键，不将开发结果合并虚增独立用例数。

独审为只读静审及原始证据复核，没有另行执行测试、API、SQL或启动进程。完整证据保留三阶段原始日志/XML、首轮和第二轮当时的三个测试文件原字节、每阶段完整归档与成员 SHA256、最终数据库不透明字节、模型线报、实际 HTTP、资产、页面动作、进程记录、前后源码清单及独审记录。

边界：这证明同一页面文档在后端进程重启后的恢复，未证明浏览器刷新/新 DOM 恢复；原键仍在 JS 内存，JSDOM 自动 interval 在夹具中关闭，读取/刷新来自显式页面动作。release prepare 丢回执及实例创建的全阶段 GET 恢复不在本轮合同。Windows、PostgreSQL、原生浏览器、真实模型、人工语义验收、Trial、新资格证明、远端 CI：NOT RUN。资格材料、anchors、text_continuations.py 原字节保持；未配置凭据、扩大网络安全权限、部署、强推或改 main/core 分支。原本 95ff54 的测试没有重跑或重计。

最终精确提交原始 XML：[final.xml](../evidence/ordinary-process-recovery-20261016/final.xml)。[机器核对记录](../evidence/ordinary-process-recovery-20261016/FINAL_VERIFICATION.json)。首轮失败 XML/日志及第二轮开发结果位于同一证据目录，均不被最终结果覆盖。

[最终独审](../evidence/ordinary-process-recovery-20261016/FINAL_REVIEW.md)已有限签收。完整包 SHA256：`4a710d9388f8c6f3fc4a618a137198666a6440924969007f459b1cd3d0e9c598`，487236 字节，32 个外层成员；三个执行阶段的数据库/原始HTTP等保存在各自可逆子归档中。详见[完整包索引](../evidence/ordinary-process-recovery-20261016/COMPLETE_BUNDLE_INDEX.json)。

完整包已存入 Library：`libfile_5d065f4bd06081918f1e8cb8b7827a4c`；独立索引：`libfile_bf8349c83be881918746f2decfad96c5`。上传确认两文件成功、零 warnings；原文件记录返回的 Library 版本 xattr，内容 SHA256 不变。

原始首轮 pytest XML/日志保留其行尾空白，因此全量 git diff --check 会报告该证据的空白字符；不清洗原始失败证据。排除这两个原始输出文件后，对其余全部新增说明、JSON、独审及源码执行 diff 检查。
