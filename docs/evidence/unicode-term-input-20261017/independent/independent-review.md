# 检索词80码点输入：独立有限审查

执行源 `51bc5f23210c20910d0545b642662efb5a368ae3`。静态审查未见阻断问题：3静态与4动态输入共享80码点pattern/计数，处理器不改value、不使用持久customValidity；composition状态保持到end，inactive字段disabled，程序化清空/模式切换刷新计数。新preview/sample/Run/preflight验证只阻新意图，既有pending/retry保留原冻结输入。服务端长度与权限合同未改。

独立实际只重复新增events/use两节点：**2 PASS / 0 FAIL / 0 ERROR / 0 SKIP**，RC0，JUnit 127.928秒，无失败或重跑。与作者同2节点，不能增加唯一分母。events在7字段验证BMP/nonBMP/mixed80/81、组合标记、paste默认插入适配与IME状态，原value不截断；use通过实际ASGI鉴权HTTP的80码点预览/批准，页面3个不同Run由cold NoModel Worker成功保存，UI81不发POST也不建intent，已接受请求的受控重复仍使用冻结输入且未新建Run。另一次Python直接送81并执行cold Worker后实际FAILED/INVALID_INPUT且无成果，持久成果版本仅v1–v3，81的失败历史保留。

页面cold Worker3次，直接81边界额外1次，总4；生成MockTransport仅use2次，runtime模型0。48表各只读/阶段checkpoint及principals/Grant边界已核对。源码/测试前后与冻结Git逐字节一致，root证据差异原样记录，本审查未写仓库。

完整原件manifest有36个文件（含2个合成fixture.db、info/result/数据库证明、stderr、XML/log/source前后与static来源说明），见raw-manifest.json及raw-SHA256SUMS。statics/是与实际HTTP响应记录SHA一致的冻结源码拷贝，非另一次请求、非原始transport流；明确来源见static-source-provenance.json。

这是完整served JSDOM + 明示clipboard默认插入适配 + 合成composition事件 + 实际ASGI/SQLite工程验证；不能证明原生IME、系统剪贴板或真实浏览器输入体验。PG、browser/root cache探针、真实浏览器、Windows、真实模型/语义、远端CI与CSV四步验收均未执行；未独立重复其他相关模块。
