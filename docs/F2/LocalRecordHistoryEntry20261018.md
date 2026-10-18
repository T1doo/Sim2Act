# 项目历史中的本地记录应用入口

从 `2ca34f24d4fdcf588bc42b461fb664df699b28a1` 接续。项目历史原已列出本地记录 Run，但点击详情仍调用拒绝该类型的 legacy `Store.inspect`，用户因此无法从历史重新打开已有事件。

既有 `GET /api/runs/{rid}` 先核 owner，再将本地记录类型分发到现有 typed 检查器。同事务核实例、Release、AppRun、当前权限、双 seal、投影、事件和回执，返回核验后的导航范围；typed 失败直接拒绝，不回落普通路径。原 `Store.inspect/command` 拒绝不变。项目详情显示同一 Run 的已保存事件，并提供明确按钮，打开原应用、原实例和该 Run 的现有控制器。不新增 endpoint、executor、Grant、表或自动业务提交。

入口以账号连接、项目、工作区、人为 Run 选择及当前应用/实例/读代次隔离迟到回调；双击只发起一次导航。有限独审发现一个 P2：迟到读取失败仍可能清空新画布。已在原 catch 的 DOM/状态变更前补工作区与连接代次检查，保留现有 intentional 跨工作区导航的共同 guard。

实际 ASGI/TestClient HTTP 与完整服务页 JSDOM：首轮两个选定 pytest 节点 **2PASS/15.32秒**；P2 后仅补跑变动页面节点 **1PASS/16.87秒，外层20.707557秒**。这是 API 与页面两个独立病例，不能计作三个。最终 Python 产品及 API 测试字节与首轮 API 通过时一致，输入桥列明仅变动的三个 JS/页面 harness 文件。

API 验证精确 typed 事件/输出、owner/project、legacy inspect 与通用 command 仍拒绝、外账号 403 在私有正文读取前拒绝、实际授权 API 撤权后 403 及只读快照不变。最终页面 **30检查、54前端 GET、27资源、1次 boot，输入零漂移**，验证正确类型详情、明确打开同应用/实例/Run、双击、workspace ABA、较新实例选择、project ABA、同账号重连及实际 403 跨工作区迟到无旧错误绘制。

页面 POST/Worker 为0；页面启动前仅创建一条 NoModel 种子。最终负例通过受限 fixture bridge 撤回唯一已知合成 owner artifact READ，revision1→2；这是夹具权限修改。已执行的严格快照比较确认其余54表、其余 Grant 行及原 Run 行保持不变；保留结果与指纹，未导出完整行供独审重算。原始首轮页面24检查与最终30检查分别保留，不合并扩张病例数。

[原始证据与有限独审](../evidence/local-record-history-entry-20261018/README.md)。真实模型调用0；原生浏览器、Windows、真实人工/语义验收、PG、远端CI未运行。真实账户官方 source 与可执行零新增费用依据仍缺失，未用合成事实替代。未重试远端认证、部署或触碰旧实例/私有 holdout。前片修正链原始 pytest FAIL 与同 Run 后续 PASS 原件不变，本片不将其改称完整 pytest 通过。
