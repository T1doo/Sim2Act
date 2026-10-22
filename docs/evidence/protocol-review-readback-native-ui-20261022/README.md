# Source / Cold 原生冷页与硬刷新只读回执验收

执行版本 **`caeb08a104616d0fe438c8f2c2beefbae7094511`**，基线 `9cdefd8cc2f5bc61d3b7b193395ede8b675f1785`。唯一窗口、attempt 1；未重跑。实际 Windows Server 2025 / 已安装 Edge 155.0.4283.62 / 合成 SQLite，复用封存已完成 Source 与 Cold，不生成新业务事实。

[原运行](https://github.com/T1doo/Sim2Act/actions/runs/39790804542) · [原 job / 第5步](https://github.com/T1doo/Sim2Act/actions/runs/39790804542/job/119866006325#step:5:1)。通过正常授权的 GitHub `fetch_workflow_job_logs` 接口取得 decoded log；未重试历史被拒的签名存储地址。`native/job.log` 保留 BOM/CRLF：472527 字节，SHA256 `f33a6babda6da17e5a452b9d0135e3b65b6a4ce679cd2f01bad56f3f7e8e3e32`。8 个 FILE/CHUNK 原件逐份检查完整0起序号、Base64、字节长度与 SHA，见 `native/transport-verification.json`。原件不改写，包括截图中的待人工核验标记；实际像素复核结论另存 `summary.json`。

本次结果：原生 DOM 17 项检查通过。初始空内存通过 GET 定位 Source 原键 `review`，一次显式 locator 受控403后旧 PASS、确认文案、可见成果/回执与提取路由关闭，原键和历史回执保留。再定位＋新鲜详情 GET 后恢复；真正 CDP `Page.reload(ignoreCache=true)` 后重新登录，两张命令 Map 清空，再仅 GET 找回同一 Source 原键/回执。首次选择 Cold，GET 找回其原键 `ddaef6fc-bbe7-4aef-9ef9-d7c883b4af71`，未以 Source 代替 Cold。四次成功 locator 顺序为 Source、恢复 Source、硬刷新 Source、Cold。

浏览器实际 **36 业务 GET / 54 静态 GET / 0 POST / 0 blocked**；服务端 **35 / 54 / 0 / 0**。差一次为浏览器受控403，未到服务端。90 条逐请求轨迹均保留方法、路径、开始/完成/响应状态。失败截图设计会暂缓新详情 GET，原2500ms轮询未改；本次轨迹没有实际暂缓条目，只有一条精确 locator403。不得据此声称原生 poll 竞争已覆盖；7 个交错场景的离线反例单独归档。

窗口限额为工作180秒＋共享清理10秒、Node最多4秒、60业务 GET /60静态 GET /4截图、POST0；旧 action 额度不变。实际 model/new_worker/new_source/new_extract 全为0，forbidden_calls/attempts 为空。55张表完整内容对照、4份 sidecar、原期限、原结果及回执均未变。API停止、AnyIO与浏览器/installer无存活、Node退出0、无强杀/错误、自有fixture删除、共享清理期限内均有原件确认；外层也记录正常退出及 owned_directory_deleted=true。

四张新1366×900截图已逐张查看：`initial.png` / `completed.png` 显示 Source 原成果与只读找回提示；`read-failed.png` 顶部与核查框均为“不可确认”，没有旧 PASS/“已复读确认”，只读重核；`cold.png` 为独立 Cold Run，保留 owner PENDING、未发布且没有 Source 提取按钮。截图只覆盖可见控制区与回执开头，未滚动展开成果全文；完整内容由 DOM 与原件严格比较验证，不冒充全文像素验收。

20份冻结源码/配置摘要仍匹配。运行 inventory 的14份原始 Windows CRLF摘要保留，14份 LF规范化摘要与冻结对应项全部一致，实际 checkout 为上述执行 SHA。为防后台 poll 抢占读代次，产品最小修改只在 `protocol.js`：定位与导航见证分离；有登记的原回执读允许同上下文、严格匹配且后来开始的认证详情读完成，推进代次防旧失败覆盖；无登记/错 fence/intent变化等不能采用。无新持久写入者、SQL、业务 POST 或 PASS缓存，独立 Source completion 不变。

离线证据与原生分开：最终7个poll交错、3个失效投影、25个只读控制器、65个原核查控制器检查通过；旧源码同脚本失败原件保留。fixture/sparse闭包、语法与新helper静态检查已在启动前完成。没有重跑37/20后台或进程恢复套件，没有另开模型/性能窗口。

限定：这是封存合成事实的只读恢复；未持久未知命令仍关闭，不生成新键补发。注册合成核查 PASS 不等于 owner 对真实任务签收，owner仍 PENDING/publication=false。显式合成业务时钟不证明真实期限性能；没有验证真实 provider、PG、G0/Cold2/W5、Windows11、API/OS进程重启或全 F2/R0。历史失败与访问拒绝证据均保留。
