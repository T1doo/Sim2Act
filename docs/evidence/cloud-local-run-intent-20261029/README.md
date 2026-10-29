# 本地运行回执与取消流程修复

基线 `dc5cb9e02681699d8d624acde64a9f677c7f5415`，实现 `4a9a5e6235edc84407c6c623a43a0f9ed42c29d8`。程序只改 internal.js，未修改 Python/C/桌面宿主、资格校验、权限或 usable_product。没有模型调用、安装包、Release 或部署。

真实缺陷：后台已持久受理 CSV 运行，但响应损坏成 `{}` 时，旧 submitInternal 先删原 pending/key，再读 undefined；用户可能以新键另建运行。原基线通过真实 HTTP/SQLite 复现失败，见 baseline-failure.json。修复先核回执结构，再复用原有 scoped GET 核 Run/AppRun/实例及捕获的 Release，只有该回读成功才清除原对象/键；没有新增一次完整 GET。坏回执、详情读取失败、选择失效继续保留原键。实例回读另有代际检查，避免旧回读抢回后选的 Run。

撤权时原 owner control-status 和取消按钮照常呈现，但这份无内容控制状态不能当作接受确认、不能清键。当前权限、原请求指纹与后端同键幂等检查未缓存或放宽。独立只读审查已核上述边界，无代码阻塞。

最终一次定向回归 exit0，11 passed/30.29s。包括新建项目、真实 FileReader、保存及审批/实例、畸形/错目标/详情读取丢失四种故障；每个真实已接受 Run 用原键恢复到同一 Run、cached=true，双击取消仅一次命令。数据库最终是4条 CANCELLED（无输出、无结果版本）与2条 SUCCEEDED（20.25/v1、9/v2）；新页面只读回历史与两份结果，不提交。完整故障路径回执为 run-receipt-results.json.gz，原件hash及各例结果在 summary.json，JUnit在 functional.xml。

其他原有导入负例、迟到文件读取取消/项目身份变化、保存回执未知、保存后回读失败均实际执行。修正了旧测试误取“使用”首按钮（现在是材料授权而非实例）和过期v2文案，改用精确CSV实例与“结果版本 2”断言，没有跳过失败。原后端API另以其独立fixture验证新Store重开及撤权后取消。JSDOM不是原生像素或新Windows软件整体验收，0真实模型/0Mock模型交换。没有把这些局部路径改称自然语义或正式PG/live验收。

仍有独立边界：桌面启动未固定端口，完整关闭重开可能换origin；spec原key依赖localStorage同源分区，不能承诺跨完整桌面重启恢复。CSV历史冷读不覆盖这项能力。本轮未改变origin/安全绑定或发明恢复凭据；需受控同源方案或现有权限范围内的服务端原键发现流程。回执形状/实例/版本核对也不构成“同实例另一个伪造Run必属于原key”的证明。目标机新源码未验，正式PG/live仍缺已有连接及明确principal/project/trial/approval选择。
