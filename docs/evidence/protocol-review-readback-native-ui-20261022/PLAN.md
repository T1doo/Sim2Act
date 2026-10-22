# 一次原生只读核查回执验收

基线 `9cdefd8cc2f5bc61d3b7b193395ede8b675f1785`。父级授权一次既有免费 CI 的真实原生冷页/硬刷新验收，复用封存 Source 和 Cold。准备阶段没有执行新 CI、模型、Source、extract 或 Worker。

显式新 action `review-readback` / `-ReviewReadback` / `[review-readback-ui-once-20261022]`，仍用原 Windows2025、官方已锁依赖、签名已安装 Edge、renderer token 审计与原安全参数。总工作 180 秒（从 setup 前算）＋共享清理 10 秒，Node 清理最多4秒。仅本窗口 60 业务 GET / 60 静态 GET / 4 PNG / **业务 POST 0**：两次完整加载/登录及硬刷新，保留原2500ms轮询；旧 action 的30/40/3不变。请求与终态在两端计量，外部 origin/其他方法拒绝，禁止自动重跑。

封存输入为 `protocol-cold-review-http-20261022/runtime/after.sqlite.gz` 的真实合成 Source+Cold 已接受事实及四份 sidecar。核旧 manifest/fixture SHA；不初始化、不迁移、不生成新事实。API前后55表全量指纹、sidecar、结果、原期限与原键均不变。父级仅批准合成工程验证，真实provider/PG/G0未验。

原生流程：初始空内存通过GET找回Source旧键→对**下一次显式Source locator**注入一次403→旧PASS/确认文案/成果/提取关闭并截图→只读再定位与新鲜复读恢复→真正CDP Page.reload(ignoreCache=true)→重新登录、确认Map0→GET找回Source旧键→首次选择Cold、GET找回Cold旧键。四个成功locator依次为Source/恢复Source/硬刷新Source/Cold，绝不以Source替Cold。四张截图分别initial/read-failed/completed/cold，DOM逐字段严格比较，不能用旧截图签新树。

为避免后台poll抢走测试403，403只绑定显式locator路径，不使用“下一个任意detail GET”。失败截图前：暂缓新Source详情GET、等此前已开始的详情请求finished并两帧排空；截图后及取消finally均释放。原poll计时/函数/身份不修改，暂缓的真实请求和释放时点逐项记录。这是受控失败展示验收，不是原始并发/时延性能验收。

独审发现真实UI读代次问题后，先离线复现再最小修：定位元数据用身份/Run/intent/workspace见证，普通后台读不冒充导航。WeakMap只登记本次已知回执后读的context/起始selection/current闭包；后来开始、同当前scope且精确匹配原回执的认证inspect才能采用，推进generation防旧失败覆盖。旧拒绝在新读尚pending时中性化当前投影，更新读匹配成功方可恢复；未知、无登记、错fence或intent ABA不采用。无新writer/SQL/POST或跨请求PASS缓存，独立Source completion不改。

离线有限证据：旧代码同脚本poll交错失败，修后7poll场景、3投影场景、25只读控制器、65原核查控制器通过；fixture/sidecar原字节及sparse依赖闭包通过。仅VM/离线启动检查，不冒充原生DOM。最终冻结20份源码/配置，Windows raw及LF规范化SHA同时归档，不混称CRLF原字节相同。启动前独审完成才推一次marker；未知结果先读取，不再触发或重试。
