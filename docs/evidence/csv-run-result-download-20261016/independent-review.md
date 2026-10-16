# CSV 结果 JSON 下载：独立实现与执行审查

**有限通过本轮新增功能工程门。** 执行源 `a0730fab025af68c10ae2706c7b9125d91ac2241`；产品 use.js 自 `897558064a9bf759b609e22edd7cbe4f6d589d42` 后字节不变，SHA256 `05718905ed710f7a134b4c69b632432452c2e172d4e432b981fc4856040304c0`。本审查未修改仓库；按明确授权只在新 `/tmp` 目录独立执行三个新增 SQLite/HTTP/JSDOM 用例，未运行 PG、真实浏览器或模型。

## 结果与测试计数

- 作者最终观察轮：7 PASS、0 FAIL、0 SKIP，pytest日志 85.56 秒 / JUnit 85.553 秒。包括三个新增用例与四个既有应用/实例/Worker控制回读用例。
- 独立执行：3 PASS、0 FAIL、0 SKIP，RC0，pytest日志 45.54 秒 / JUnit 45.542 秒，1 项既有 Starlette/httpx deprecation warning。与作者同三个新增用例，**不累计成十项唯一测试**。本轮唯一用例数为7。
- 两套新增回执各为 versions-and-rejections 52、navigation 22、revocation 9 项 adapter断言；这些是三个pytest用例内部断言，不另提升测试计数。

## 代码与实际工程证据

结果按钮位于已保存 CSV 实例中所选成功 Run 下。每次明确点击只 fresh GET 既有 `/api/internal/instances/{iid}/runs/{rid}`，后端重新检查历史Run所属身份/项目/实例、冻结合同、Release/来源权限和typed行。客户端将响应 queue Run、typed AppRun、实例、Release、结果版本、四项结果与点击时核对的选择及known_effects逐项匹配；错绑定、不成功、缺证据或结果不一致不生成Blob。历史Run使用该Run自身Release。

导出固定白名单 instance_id/run_id/release_id/result_version/result(resource_id,column,sum,count)，不展开服务器对象、材料、events或身份。实际v1大数 `9007199254740993.123456790` 和v2 `0.3` 保留字符串及原字节，不经 JS Number；filename由现有实例/Run/version标识构造，不使用column/name。独立 Node 保存的 captured-blob文件逐字节比对JSON投影，仅是JSDOM Blob证据。

实际工程用例覆盖：每次明确点击重新GET；双击与同Run刷新重绘共享in-flight Set；成功/失败后可再次点击；18项响应篡改、GET后transport loss、anchor激活异常均不得下载错误内容；工作区、Run、实例、项目、身份、同身份重连及刷新回切七类延迟隔离。所有URL被回收、anchor被移除，结尾pending/actions/pageerrors为0。下载保护绑定connection/workspace/readGeneration/DOM连接/实例对象和选中Run，迟到回调不恢复旧内容或文件。

实际撤权case在fresh GET到达鉴权前调用测试控制夹具，通过现有revokeAPI撤回一条合成Grant；随后真实GET403、0Blob/0anchor，并清理受保护结果与下载入口。此受控撤权不是下载功能新建授权。两套执行均由Python最终比较全48张meta表行快照：普通case前后digest完全相同；撤权case只有受控Grant变化，之后GET与撤权后整体digest相同。没有新增Run/Grant/其它持久记录，NoModel不允许模型请求。

## 两轮失败保留与解释边界

1. `89755806` 的 author-attempt-1 原XML/log/逐case回执保留：2 PASS、1 FAIL，53.56秒，失败为测试控制夹具空POST收到400，尚未成功执行撤权；已仅给测试控制请求加JSON {}。产品源码未改。该失败不能表述为下载产品撤权失败，也不能抹成首次全绿。
2. `eff53099` 的 author-final 原XML/log/逐case回执保留：6 PASS、1 FAIL，85.46秒。versions-and-rejections 初始化选择历史Run时8秒等候超时，原回执最后实例GET仍未记actual_status，下载尚未开始。**原始原因仍未确定**；不能将最终通过称为已定位/修复该超时。后续仅新增driver请求单调时间与排空后的final_state，保留8秒wait、75秒子进程上限及全部断言。观察轮与本次独立运行绿色是新证据，不改写旧失败。

## 限制和仍未完成的验收

本轮是SQLite synthetic test_only +真实loopback HTTP/既有Worker +JSDOM/Node Blob与anchor捕获，不是原生浏览器download事件、OS文件保存或PG事务验收。PG、真实浏览器落盘、Windows、真实语义/人工场景、远端CI、服务/浏览器重启四步普通用户流程均NOT_RUN；已知PG资源缺失及protected Chromium SUID sandbox启动阻止仍保留。本轮没有重试浏览器、下载镜像、增加凭据/安全权限、真实模型、部署或相邻恢复矩阵。

代码静态审查和上述工程范围内未发现阻断项；真实浏览器对Blob/anchor激活行为的最终验证仍需可正常保留保护的浏览器资源。已有源码说明需与最终交付报告一同明确这些边界。

## 最后传递与报告核对

已只读审查 `docs/F2/CsvRunResultDownload20261016.md` 与证据 README：7唯一节点/3独立重复、两轮失败及未知超时原因、48表比对与受控Grant变化、Node Blob工程适配器以及PG/真实浏览器/四步NOT_RUN均表述准确。作者50份归档payload与对应原件逐字节一致；失败未产生的database-proof/Blob没有补造。当前HEAD仍为a073冻结，src/tests/scripts/锁/工作流与该冻结无差异。本审查不替代随后普通推送的远端SHA/clean核验。
