# 73826ba7 有限字面应用真实链路

源码提交 `73826ba732a4c6f8791324c3e0a935ffa8077fec`。冻结包自带Python/API/Worker、实际专用PostgreSQL、实际Intern-S2。未操作原生窗口。

Run `run_b7d3ab2af34a44d5a7f393647f811ca7` 返回有效候选，技术状态PARTIAL、目标验收NOT_RUN。读取和候选共两次LIVE请求，实际用量4183+5394=9577 tokens，没有修复请求。

同一包通过：

1. 同会话准备/批准/原键恢复/接受生成任务，无需重启静态选择。
2. 模型候选通过原严格校验；明确确认后创建预览应用。
3. Alpha预览返回独立预期的第1、3行原文。
4. 原发布批准和提交创建Release/Instance。
5. 新输入Beta返回独立预期的第2、4行原文。
6. 数值类型term被拒绝，FAILED且无结果。
7. 后台干净关闭，再用相同包冷启动，旧结果完整一致。
8. 冷启动新输入owner返回第3行原文；再退出时API/Worker exit0、PG PID文件消失。

原始证据为 `managed-pa-field-source-v6.json` 和 `managed-pa-field-source-v6-cold.json`。API连接使用DPAPI凭据，未复制到报告或包内。额外用量读取只访问该Run账本，读取后停止数据库。

边界：一次成功不能证明生成稳定率；本次是合成短文本的有限字面应用，不是自然语义规划或完整规范P-A/P-B；原生窗口、完整AT、普通用户安装及R0仍未验收。保留85b8b619失败，不覆盖为成功。
