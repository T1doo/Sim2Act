# 当前独立 UI 分支与下一次既有 Edge 验收

当前本地dev/task-history-ui-local基于远端既有d3d4fa5，含657ea4f的页面回执恢复、442e90b0的闭合与本轮历史API/UI/测试/docs。发布候选的src差异仅api.py/web/app.js/web/index.html；无68443激活祖先，无protocol_egress空白修复，无新表/迁移/Grant/生产角色。空白独立分支bf3d1b7c及审查docs另列，不合入该UI候选。当前只整理本地分支，未push/dispatch/创建PR。

原生门仍OPEN：本平台Chromium已实际尝试并因SUID配置失败，不能以JSDOM39项、旧0389的Edge成功或旧PNG替代。当前fixture为合成SQLite，PG/Win11新切片未验。

下一获准轮次先将本次39项中的用户流程接入既有scripts/windows_browser_ci.py与原受保护Edge helper，再冻结精确源SHA并仅普通fast-forward推到既有dev/f1-foundation，监督其单次既有WindowsServerCI终态；不提前推送未经检查的helper。沿用现有Windows2025、contents:read、job15分钟/browser4分钟、已安装微软签名Edge、锁定playwright-core依赖、原AppContainer/restricted-token实际进程审计、原owned API/worker/PG清理，不增加runner/权限/secrets/外部目的地。时限不足应如实失败，不静默提权或关sandbox。

原生重点流程：真实接受后截断回执→同key恢复仅1Run；已接受GET失败只读恢复；真实Mock worker保留PARTIAL/VERIFIED；完整reload重连后按目标/接受时间/提交模式找到原Run；桌面与390px窄屏阅读目标/恢复按钮/历史，不横向溢出。并测项目往返、A→B→A、失败身份连接清空、迟到连接拒绝不覆盖、迟到列表/详情、只读列表失败、输入markup以文本显示、MOCK/LIVE提交模式不声称语义成功。统计实际POST/Run/Attempt、外域请求0和Grant/principal不变。

复用原命名browser-results.json/desktop.png/mobile.png输出槽，新增检查与截图画面纳入既有named stdout byte/SHA/2MB保护，不能增上传目的地或额外恢复包。原六PNG及历史记录保留，不覆盖历史证据；新证据按新的精确SHA存档。新桌面/窄屏PNG须实际像素检查并注明人工审查，不能把hash等同视觉PASS。Windows工程需含新API专项的实际PG路径及原有role smoke，明确SQLite/Mock/JS与PG口径；Win11/完整AT02/F1仍另行开放。

下一独立产品切片为普通成果画布的可读步骤/等待原因；只读已有回执，保持真实技术终态与目标验收分离，不自动续跑/外发/发布。
