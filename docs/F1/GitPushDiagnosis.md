# 文档推送阻塞：有限只读诊断

2026-10-05；工程提交df31fe9已推送且CI成功；文档提交6145bb8b2bbeecd0bb263b6f6703a3da1f1b16e1保留在本地。本次不重试push、不换身份/地址/协议/发布通道、不读取凭据内容。

已有失败操作：`git push origin dev/f1-foundation`。已知配置目标：`https://github.com/T1doo/Sim2Act.git`。原始完整非敏感stderr：

```text
fatal: could not read Username for 'https://github.com': No such device or address
```

没有HTTP状态可供判断；后续ls-remote同样失败的既有输出没有增加HTTP信息。本轮不重复任何网络调用。错误原档见[documentation-push-blocker](../evidence/WindowsCI-lock-20261005/documentation-push-blocker.txt)。

当前非敏感元数据：工作目录/workspace/Sim2Act，Git可执行文件/usr/local/bin/git，stdin/stdout非TTY；GIT_ASKPASS、SSH_ASKPASS、GIT_TERMINAL_PROMPT、GIT_CONFIG_COUNT、GIT_CONFIG_GLOBAL、GIT_CONFIG_SYSTEM未设置。GH_TOKEN变量存在且非空，只检查存在性，不读取或验证内容；GITHUB_TOKEN与GH_HOST未设置。未检查credential helper配置/存储、Authorization header或私有配置文件。快照不能证明失败发生时的环境完全相同。

能确认的机制：该Git操作没有取得可用HTTPS用户名，并且无法从当前非交互终端读入。根因仍未知：可能涉及既有凭据注入/辅助程序、配置生命周期、凭据有效性或其他认证条件；没有证据在这些候选中作选择。不能判为GitHub仓库权限拒绝、不能补造403，也不能以GH_TOKEN变量存在证明Git已获得认证。GitHub连接此前能读Actions，不证明此Git HTTPS写入路径当前可用。

建议最小恢复步骤（本轮未执行）：

1. 由环境负责人通过当前Codex环境/已有GitHub连接的原有登录和凭据注入流程恢复同一账户的Git HTTPS认证；若连接已失效，仅按原连接流程重新连接。不要求在聊天中贴token，不新增身份、Secret或扩展仓库权限。
2. 核对仍为T1doo/Sim2Act、origin既有HTTPS地址、dev/f1-foundation；保留本地6145bb8及其后文档提交，禁止reset/force-push。若负责人确认同一身份的既有认证已恢复，可按已有开发分支授权做一次正常同步；若有并发远端变化，先取回并核对，不覆盖。
3. 成功同步后记录远端SHA；若再次失败，保留新原始错误及有则记录HTTP状态，停止重复尝试。当前恢复机制和负责人操作入口未由本轮确定，因此不承诺某个具体重新登录按钮一定能修复。

这是文档同步阻塞，工程提交及既有成功CI证据不受影响；不以此阻塞本地审计和计划准备。
