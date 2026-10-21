# 已授权单次验证：prefix 前启动拒绝，UNKNOWN

本次用户委托明确纠正先前父侧阶段限制，授权在常规合成测试范围执行一次
完整输入资格＋首G0验证。候选冻结为
`b4bac26b5ecbb98c864407170a94c202deee427a`，未修改冻结代码；源码／依赖摘要
`39190dfc45d353346bf41c1c12786e02e94d652c603331bf8bc9569c348efedd`，
profile摘要 `f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f`。
运行前实际只读 describe、clean HEAD、远端同SHA、无运行中launcher及必需保护
capability核验通过；旧日志和已消费窗口没有恢复。

## 实际结果

使用全新目录／SQLite目标和唯一grant
`native-g0-f530f82674b34cea90ef0d1bcace9d81`，launcher实际仅调用一次，退出码2。
**原始receipt终态UNKNOWN，business_acceptance=INTERRUPTED**；child原输出：

```json
{"classification": "BLOCKED", "boundary": "direct child entry prohibited"}
```

| 项目 | 实际证据／结论 |
| --- | --- |
| launcher work_wall_seconds | 0.1406026889999339秒；不是G0耗时或CPU测量 |
| prefix／G0／OWNED或LEGACY | 均NOT_REACHED；没有资格或性能结论 |
| Mock／真实模型／commit | 0次业务调用；原counter未初始化，依据拒绝位置在产品／prefix导入前；两commit和最终deadline均未到达 |
| SQLite与业务归档 | 无fixture.db、diagnostic、prefix-proof或mocklog；control.jsonl为0字节，run仅4个父文件 |
| grant | 原`.consumed`存在；没有重试、复制授权续跑或新grant |
| 清理 | 原receipt `OWNED_GROUP_EMPTY`、finalization_errors=[]；另只读复核PID39573不存在、原PGID无成员 |
| 磁盘监测 | 3次采样；峰logical633411／allocated638976字节，未触及64MiB预算；不是硬配额 |
| 实测采样完成间隔 | 最小0.0234896610／最大0.1148875130／均值0.0691885870秒；配置0.1秒不声称固定调度 |
| 源码新鲜性 | parent清理后digest等于原冻结摘要；未改代码或保护门 |

不是原G0业务拒绝、不是租约超时、不是逻辑额度或内存不足，也不是完整验证成功。
本次已消费，不因尚未进入业务而自动再开一次。

## 确定的调用错误与保留的防线

执行者启动命令的script token是相对路径 `scripts/diagnostics/g0_bounded.py`。
`validate_child_parent`读取父`/proc/<ppid>/cmdline`，要求绝对
`str(Path(__file__).resolve())`是argv中的完整token，并要求原execute/output参数。
实际相对token不等于该绝对token，所以在 child 会话／pipe检查后，产品导入前拒绝。
这次调用方式错误由执行者负责；不删除／绕过父身份保护，不改变已审代码。

`outcome-analysis.json`的启动参数来自执行工具命令记录；原程序没有保存父argv，
不能声称它是事后独立读取到的完整`/proc`原件。独审分别核源码、拒绝输出、控制流、
原receipt、manifest、文件缺失和现进程组，未执行产品／测试／数据库／Mock。

后续若另行允许新单次窗口，应使用**绝对解释器和脚本路径**，仍需全新description
匹配的grant和目录，绝不能复用这里的已消费grant。以下只是静态调用格式，不执行：

```text
/workspace/Sim2Act/.venv/bin/python -B /workspace/Sim2Act/scripts/diagnostics/g0_bounded.py --candidate --execute-grant <NEW_APPROVED_GRANT> --output-parent <NEW_EMPTY_PARENT>
```

本片不申请／生成第二grant，不重跑。上次冻结合同仍是6Mock／8入口、prefix480／
G0120／总600＋清理10秒、原lease30／Run300／TTL1800／reservation60秒不变，
64MiB采样监测、0真实模型／费用／外网业务／新权限，禁Cold2/W5、无自动重试。
逻辑work allowance不是CPU/RSS上界。未达到child保护安装位置，所以本次不能
声称实际安装保护通过；前置capability与之前必需单测通过也不能替代此运行证据。

## 原件与封存

原目录保留在
`/tmp/sim2act-authorized-native-g0-f530f82674b34cea90ef0d1bcace9d81/`。
`raw/`保留原授权来源记录、grant与消费标记、launcher输出、receipt、空control，
description和run source-manifest使用gzip逐字节封存；`raw-map.json`给原路径、
原始大小／SHA及封存路径，`original-manifest.json`封存全体原件哈希。
没有数据库可复制，旧窗口原件未改。`reviews/`是两名既有只读reviewer的结果核验，
不是重新运行或下一窗口授权。后续Git只提交本证据，不改变冻结执行源。
