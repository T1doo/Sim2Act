# Cold settlement fact graph：完整验收未通过

本提交保全 `dc34ce4b1311810e27cd33a0cd156b6f84333666` 之后的开发候选及失败证据，不代表完整 P-B、Stage、性能或真实场景接受。没有部署，没有修改 main，没有调用真实模型。

候选接入固定的 G0 事实读取图、原五写事务，以及同一原子事务内、写后全新读取 epoch 的 G1；复用原 per-use、审批、权限、Run/version/fence/stop/deadline 和 ModelRead 检查。13 个生产文件在授权的 14 文件范围内，`text_apps.py` 未改。`natural_specs.py` 仅提取两处共享事实 core。没有新 executor、Grant 或持久化 ALLOW。类型与完整 raw pin、受控存储的 schema 桥、严格读取的原异常身份和最终实际时间门均有定向证据。

完整代码独审 `v14-full-graph-code-final` 给出 `FULL_CODE_REVIEW_ACK`，131 个选定文件匹配最终冻结。它是代码范围结论，不是完整运行接受。启动前收到即时 ACK；正式 seal 在运行期间完成，未倒填为启动前已封存。

唯一完整用例是 `tests/test_pb_spec_production_controller.py::test_pb_production_original_source_extraction_explicit_use_and_cold`。全新 SQLite、Store/client/Worker，有限显式 MockTransport；原合同 TTL 1800 秒、Run 300 秒、lease 30 秒、请求间隔 60 秒未变。外层上限 1200 秒、堆栈快照 300 秒。实际 pytest 621.90 秒，外层 634.128503 秒，exit 1，非 timeout，所有捕获的源码和测试字节前后相同。

实际 Mock 为 Generate 3、Source 2、Cold 1，共 6 次；预期 Cold 第 2 次未发生。真实模型 0。数据库的 `mode=LIVE` 是该合成控制器夹具的形状，不能计作真实调用。6 条原始 request/response 记录与 observer 的外层发送计数一致，没有重复 aid，observer secondary error 为零。

该完整用例已通过 Source 成功、原始正文归档、提取重放不新增发送、目录 `NATURAL_PB` 分类、重新打开 Store、显式 per-use review/提交及同 request-key 去重等前置断言。Cold 在首次提交前的 `lock_live → Store.guard` 被 `VERSION_CONFLICT: Stale worker lease` 拒绝，最终成功断言失败。不能据此前置断言声称 Cold 结果或人工验收流程通过。

| 实际阶段 | 结果 |
| --- | --- |
| G0 | 37.521112 秒 wall / 37.481985 秒 thread CPU，随后租约拒绝 |
| W5 | NOT_REACHED；没有执行本次 Cold 模型的五写成功事务 |
| G1 | NOT_REACHED；不是一次通过的写后重建 |
| finalguard | NOT_REACHED |

G0 内首个完整 binding 读取本身为 37.279449 秒；所有观测的公开祖先 verifier 在 G0 中调用次数均为零。CGR 完整检查 2048 次，input_key 2183 次，该 input_key 类别的实际完整 SHA 构造输入为 581,208,365 字节；G0 所有观测 SHA 构造类别合计 598,682,854 字节。codec 返回 585,174,551 字节，CPU 17.871195 秒；input_bytes 的直接 instrumented-child-exclusive CPU 7.207091 秒，validator CPU 4.495972 秒，SHA 构造 CPU 1.460127 秒。指标包含探针开销；inclusive 指标有嵌套，codec 和 input_bytes 字节也重叠，不能相加当作唯一数据量。没有无探针对照运行。

终态 Cold Run 与 AppRun 均仍为 `RUNNING`、结果为空；本次 Attempt 和模型 Operation 为 `REJECTED_KNOWN`，保留已知 usage 100/900/1000 及 RECEIVED/归档/REJECTED 事件。只有原 read 步骤 VERIFIED；没有本次模型的 NS_SETTLED 或模型 STEP 成功事件，Instance data_version 为 0、没有结果数据。未做续跑、恢复或第二次完整重试。

短门按各自 receipt 的实际源码 footprint 解释：完整新 G3/Source2 + queued Cold 的两独立读取事务与公开 oracle 比较 1P；typed cohort 30P；codec 78P；默认/受控边界 17P。最后一组 69 项是 68P/1F（旧 observer 漏记严格 collector），后续 21 项是 20P/1F（新行形状夹具先被真实资源权限拒绝），原失败均保留。修正仅涉及探针和合成夹具；终态定向 9P 包含完整 Run 行 join、goal 漂移拒绝、strict TypeError 后 sticky/IO0、真实 pair/权限计数及六个默认参数绑定反例。最终 mypy 检查 113 个源文件通过，全部本次修改的生产与测试文件 Ruff 通过。没有把各阶段门冒称为当前全测试套件一次联跑。

关键原始证据在同目录的 `raw-evidence.tar.gz`，逐文件索引为 `ARCHIVE-MANIFEST.json`：

- `pb-full-gate-final-20261020/`：实际 invocation、receipt、stdout/stderr、JUnit、完整 observer 和整个 pytest-tmp（含原 SQLite、原始 Mock 正文、租约及失败记录）。
- `pb-cold-graph-integration-20261019/`：全部短门原始结果、失败及超时、最终 131 文件冻结、启动记录、完整成本提取和只读数据库 hash。
- `pb-cold-graph-integration-review-20261019/`：独立代码审查、版本桥、原失败及完整运行结果独审。
- 其余外部 patch、静检、观察器源码/stdlib 自测和执行器静审均保留，未以静检冒称运行。

最终冻结 manifest SHA256：`c6d0dccd07670533fcdd3ab5110d9af8b6b2bae990723a4c0891d1c65853b866`。
v14 REPORT SHA256：`b5b37b350466f935c492e32ef423383b7e62104300e6ea7fc68dd4e549e36d0f`；MANIFEST：`676209eb362d101f76c7b54e6f1cca8c64448480c4410b471d95263ecf1c157f`。
v15 完整运行独审结论 `FAIL_NOT_ACCEPTED`；REPORT SHA256：`d3e97f54667fec83d58af6fdedfc775fa4df57d4dd63a1ad284f494b3bfee7ef`；MANIFEST：`63d5a2454e35eaacf2bfebb0619f99572e9ae632373457ac47aa83b70c4e234a`。
实际完整 observer JSON SHA256：`03ec1d92db7e736d2aae10c308386f8bc230741cb45b123f2777e454c65a7e12`；JUnit：`324ceca8e42e35b8b01ed8a560a3aef52c3a030afb07e8cf1bb845c2c44c7db8`。

剩余阻塞是完整 G0 读取成本已经超过原租约，尚未到达 W5/G1。需要继续降低完整校验的计算成本并保留全部边界，不能以延长租约、减少完整字段或复用旧授权解决。当前候选没有完整接受结论。

Windows、PostgreSQL、远端 CI、真实模型/语义/场景、真人验收均未执行。旧环境满盘导致的最后独审报告未落盘仍是已知证据缺口，本提交没有补回或声称恢复它；没有返回旧实例写入或删除文件。
