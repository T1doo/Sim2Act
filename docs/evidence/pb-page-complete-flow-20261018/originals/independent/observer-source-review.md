# 冻结491的非作者观察补丁有限审查

审查对象：`491cd75b8600dc1794d6a153f68a9052af763bae`，基线`f5d6cedb26fe549ad274951892a219c0b34b32b9`。仅只读仓库、纯AST/字节及原件；本审查员零产品测试、HTTP、Worker或模型执行，零仓库写入。

未发现确定P1/P2阻断，可开始所选原连续P-B单例。`observer-oracle-review.json`记录独立复算：采用文件逐字等于草稿；38条Assert节点按词法顺序AST一致；`source_unchanged`完整AST及原setup/ready/enqueue/drive_to_success/transport/Store/TestClient/create_app调用序列一致；第二导航测试AST和字节一致；原CJS字节一致。`freeze-byte-bridge.json`独立回读679项执行输入与开跑前映射一致，相对phase-start仅该Python测试变化；132生产项逐字同f5和cac79410，HEAD clean。

具体边界：

- `tests/test_pb_natural_product_flow.py:22`在fixture setup前进入观察器，因此setup和原ready失败也会留阶段与最终错误。Node看门狗在`:86` own_node开始；覆盖前置fixture和Worker的外层900秒仍由实际执行命令提供，不能仅依赖Node timer。
- `:25–27`新增ObservedList保留list行为，只在原append后写观察副本；不替换全局HTTP/transport、不改变原Mock返回值或Worker调用。
- `:66–68,80–85`仍把原Node stderr写入`node.stderr`，不经PIPE等待；创建的`driver.log`空文件不能冒称Node错误原件。`nullcontext`不提前关闭该句柄；外层观察器最终关闭它。未调用硬编码读取driver.log的`stderr_text`。
- `:216–223`保持原本只清理本Popen的Node及本case创建的cold client/Store；观察器也只保存本Popen句柄，不触碰未知进程。
- `:225–237`在异常路径写出已收集wire/checkpoints；原ready未返回时，`fixture-generation-observation.json`明确记局部wire未导出，空数组不能推导没有生成尝试。未为取证新增生成调用。
- finally写盘失败可能使最外层显示异常类型变成写盘异常；Python原异常链及观察器test_error仍可保留原因。观察器`__exit__`返回False，不能把原异常吞成PASS；原Node退出码、proof、数据快照断言保留。
- 原source/new Worker辅助器仍最多3次有界真实claim，并核验原clock/deadline/fence；本轮实际claim次数必须回读原件，不按计划假定一次。

本审查不签实际产品资格。待本轮原JUnit、result/progress、HTTP原字节、Mock wire、claim、checkpoint、保存证明和输入after全部完成后，另写最终有限结论。

永久取消精确安装digest窗口保持`CANCELLED_PERMANENTLY_UNVERIFIED`；本次只有原正常丢201回执后的同页原keyGET，没有第二actor或修前/当前精确窗口对照。正常连续链不能替代取消目标。
