# 原 P-A 自然规范完整页面：停止定位与继续验收

父级已有限通过基线 `475777cf0c4c23f83a50d9e957adb6cf9d374ca0`。在普通分支 `dev/pa-page-complete-flow-20261018` 接续同一关键路径；保留原停止、失败与缺证，不用另一个小功能替代完整页面。

原共享批次完成两项后，于409.13秒对自有pytest精确SIGINT，总412.41秒；不是产品自动超时。原日志仅有两个完成项，原页面没有落下最终 results、driver、wire 或 RPC 进度，因此不能恢复“当时最后一条 HTTP”或直接断定死锁。原合成数据库与交付归档 SHA 相同：`fd4f2e4ebcf4060ac28f250399165deefbfae38c576f78dbd7e2a24738868d45`。

该原库已持久化生成 PARTIAL 候选、确认及新材料绑定、Release、实例，以及冷正常 Worker 的六步 VERIFIED、SUCCEEDED、typed 版本1和 JSON 成果。SPEC_COMMITTED 事务内事件时间为04:13:03.108984，文件mtime约04:13:06.95；均不等同于 Worker IPC 返回时间。停止为04:14:17。只读可证业务保存完成；后续刷新、读取/下载、检查标签和最终页面证明未闭合。NODE_PATH/jsdom正常，未证管道死锁。

在物理只读 URI 上，原实例 GET 实际200、数据库逐字不变。开启 cProfile 后36.94秒，35,984条SQL、589次source_scope_gate、7次model_source、14次verified_candidate、5次read_release、2次verify_job；SQLite实际执行约2.18秒。观测本身有开销，这不是无观测基准。主要已证机制是多层重复来源证明；页面刷新又依次读取应用、目录、实例以及两个消费者各自的同一Release，放大等待。该新观测不能补写为原停止时已抓到同一栈。

本次只做两个有界减重：

1. 实例读取完成原owned instance、Release、typed、Run完整验证后，给路由本次新建的私有输出盒导出 `{id, fingerprint}` 元数据。路由核对其严格字段及Release ID，替代第二次深度读取；后续Run检查仍完整执行。输出盒不是跨事务授权能力，不改变HTTP协议，不缓存私有Release正文。
2. `showInternalInstance` 为本次选择fresh读取一次Release，将同一个响应传给本次两个渲染消费者；两者仍核对主体选择、实例、版本和完整snapshot SHA。未提供响应的原调用仍实际GET。每次刷新重新获取，不跨刷新缓存。所有异步点保留或补全workspace、connection、instance selection守卫，避免hash等待后的ABA回调重新显示旧面板。

不扩大现有 `_reuse_origin` 的资格，不移除test_only/SQLite边界，不使用跨请求缓存，不新增executor、Grant、Principal或模型调用。原权限前置、来源/版本、真实回执、typed及CAS检查保留。

验收必须fresh执行原 `test_natural_spec_page_actual_nodes_and_cold_material[valid]`：目标→三次合成协议反馈生成→明确确认→新材料/Goal绑定→内部Release/实例→冷正常Worker两次合成模型节点→同Run保存结果→实际清单读取及JSON/Markdown下载。原CJS功能断言、15秒局部wait、3+2 Mock请求保持；新增增量RPC/HTTP/Worker日志、失败finally证据及900秒自有进程看门狗。外层同样有界，不等待整点，不重复其它故障scenario矩阵；原中断项不改签为当时通过。

原方案关键门仍是两条实际生成路径分别完成，并在统一入口用新材料/Goal运行、查看同Run结果、人工验收及最小依赖变更。当前任务优先关闭这条P-A页面工程路径和读回效率；真实书生、真实语义/场景、完整P-A/P-B、Windows/PG/native仍各自开放。当前授权仅合成/mock，不能以更多固定模板替代真实模型验收，也不得擅自调用真实模型或增加费用。

## 本次实际结果

生产冻结 `cac7941062592df0a65783a9c147b06c22c7fd1b`，测试观测冻结 `c958a679f527bd209ff2916bee2f4c1a9eb771ba`。原完整 `valid` 用例 fresh 执行 PASS，整批306.10秒；原32个页面检查、94次页面API、54份实际加载资产和148份原HTTP响应均有原件。两次正常Worker完成，3次生成及2次冷运行均为MockTransport，真实模型0。JSON/Markdown实际下载只含新材料，原owner PENDING和语义UNKNOWN保留；本例验证人工入口前置选择边界，没有提交人工验收声明。

另三项原回归PASS/69.04秒：普通CSV实例、full-report双fresh运行、本地记录实际HTTP/JSDOM导航。总计4个唯一pytest节点，139项生产/测试输入前后0变化。Ruff、两模块mypy、两份JS语法及源码diff-check通过。非作者有限独审通过，无剩余确定P1/P2；独审执行源码/只读元数据、四项精确函数控制和262项原件复算，没有独立重跑完整页面。

原中断仍NOT_VERIFIED；本次fresh原完整场景单独关闭当前工程证据缺口。额外只读cProfile/native traceback探针退出139，原件保留、原因未定，不计产品失败或性能结论。仅一次去除两种观测器的SQL计数重试200，库SHA不变、31,054条SQL。前后fresh ID及观测条件不同，不能用36.94/13.85秒宣称性能倍数。

[完整可读原件、JUnit、冻结桥和独审](../evidence/pa-page-complete-flow-20261018/README.md)。未执行真实模型/语义/完整P-B、Windows/native、PG、远端CI或部署；不关闭这些原方案门。
