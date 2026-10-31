# 30 秒诊断已修；PB 单候选切片无净收益，未启用

应用仍为 **2ad3227621b48793a4d03747463b33207139147e**，本轮起始已推送 HEAD **a9ab4d26f0ab0c82a445f1b89df54471047c8709**。`src` 五份实验改动已逐文件精确还原，不回退既有提交，不变更 main。新增的正式工具只有 [原 30 秒手动诊断](../../../scripts/diagnose_ordinary_thirty.py)及其必要反例；本目录的候选补丁为拒绝启用的实验原件，不被应用导入。

**原普通 30 秒大型保存仍未完成。此次没有新的大型 Cold、保存/重开/持锁取消或 live 验收，不把组件或负例审计通过当成目标成功。** 已验 Linux 限制候选及上一轮签署 120 秒的两笔保存证据保持原范围。

## 修复诊断的真实错误

上一轮原 30 秒控制器在首次 Cold 未完成目标，随后新诊断错误地只允许 Attempt 为 RECEIVED。实际原协议记录了 REJECTED_KNOWN、已知用量和预算错误。原 [失败及独立负例审计](../cold-earliest-deadline-boundary-20261031/README.md) 完整保留，未改写其退出码或数据库。

新脚本明确分开两种结论：原完整控制器全部成功断言成立、两笔真实 COMMITTED 才输出目标完成；否则仅允许原首次 Cold 成功断言这一处偏离，并检查完整预算负例。普通 caps 的精确类型、lease=30、无 settlement120 字段在成功和失败分支前共同检查，合同仍由原 `gate.approve` 审核保存。所有 tracked `src/sim2act` 文件从显式冻结 Git commit 导出，与实际导入目录逐字节比对；原 native 源码/构建资格仍由原产品核验，并未替换成脚本免检。

负例读取原模型 Attempt metadata 的 operation_id，而非先前合法 VERIFIED 的 READ 操作；规范化真实 SQL JSON null。必须按该 Run 匹配唯一原 failure-observations，错误精确为 `BUDGET_EXHAUSTED / Finite model settlement interval ended`，不能把其他权限/版本/未知错误归为预算负例。允许原两种边界 RECEIVED/DISPATCHED 或 REJECTED_KNOWN/REJECTED_KNOWN，但都要求保留完整 response、匹配 NS_RECEIVED 指纹、known usage、无模型成功 receipt/NS_SETTLED/typed result/app output/result_version，且无更长租约 booking。

[同一原数据库只读回读](corrected-thirty-diagnostic-final-readback-20261031.json)已实际调用新断言：REJECTED_KNOWN、known Mock tokens=1000、无成果，主 DB SHA256 **92159fbcc5dcc130d7b6a561e70d916fcbaf87c30183a7dfe376fde11b00bc33** 不变；**未重跑控制器、0 新 Mock/real 调用**。13 项诊断反例检查了两种原状态及错误 Run/错误原因、丢失或变化响应、unknown usage、错操作、伪成功、实际结果/提交，零失败/错误/跳过。另在恢复原运行时后再跑同 13 项，见 raw 原件，范围重叠不相加。

独审曾要求修共同 caps 校验、错误原因校验和全应用身份覆盖，现均闭合；不是修改产品状态让原失败变绿。新脚本的完整大型控制器入口尚未重新运行，不能称新一轮 30 秒 pytest 或业务成功。

## 实做并拒绝的最小所有权切片

先复核 [8c794/e9c08 的完整 SQLite 端点否定证据](../expected-post-shadow-20261031/README.md)及 [2936eda 的回调反例](../g1-pure-slice-refusal-20261031/README.md)。本次没有复用 SQLite 端点、五写计数、旧 Graph 或 PASS 来省掉 G1。

[candidate-not-enabled.patch](candidate-not-enabled.patch)完整保留本次实际实现和测试。其切片为默认 Cold 私有审核路径中，`candidate()` 完成完整 expand 与 manifest/spec_task 字段之后、首次返回给消费者之前，将完整 PB extraction 候选 JSON 交给已有 `own_fact`。同一 View 贯穿原 compile、preview、candidate/review fingerprint、ExtractionReview.checked、facts.fields 与完整绑定。每次独立 expand、role/facet、事务仍有独立 owner；Goal、Limits、请求、来源、文件、SQL读取、权限撤权、owner/epoch、期限和取消仍留原动态路径，未缓存授权或计算 PASS。公开无 Graph 的 review 不变；缺可选 native、已发 continuation 或早期容量拒绝走原完整 raw 路径，晚期失败不重跑生产者。

实际原完整 G3/Source2 前缀创建 5 次 FixedMock 后，将 Cold 排队但**不执行 Cold**；两个相互独立事务的 pre/post-shaped binding 都与完整公开 ancestry oracle 比对。这里的 post-shaped 读取不是 W5 后 G1。首次消费者观察测试误导入了禁止所有 Worker 的 autouse 夹具，在 Worker 构造前失败（0 调用），已拆开夹具并保留原失败日志；修正观察测试真实验证完整消费者与退休旧别名。后续完整同条件组件直接使用既有测试，不替换业务函数或时钟。

独审另发现原 helper 新增 fallback 的 builtin 角色未完全收口。实验已对新 helper 使用 Source code 见证的 keyword 默认角色并先拒绝非 exact dict，14 项边界（与早期 7 项重叠）通过：完整字段/顺序/别名、不变 owner/独立 owner、外部可变共享依赖、早期拒绝原路径、晚期/根变化原异常、dict 子类零回调、callee/keyword 角色变更拒绝、缺 native。**这不证明整个原 review/checkpoint 的所有 module builtin 查找已闭合**；独审仍指出 `pb.type` 等外层 lookup 需在整段入口资格之前固定。候选未获“全部行为等价/可启用”的签字，也没有把未覆盖的外来回调当允许。因净收益亦不足，未继续增加资格复杂度或启用实验后端。

## 同环境、同输入、无并行的组件对照

[顺序两臂原记录](extraction-component-pair-20261031.json)、原 profiler/runner 与两份逐状态 profile 已保存。基线使用此前完整冻结 2ad export；候选运行当前 dirty 原型，所有 tracked 改动 hash 记录于 [prototype-files.json](prototype-files.json)。同 CPython/SQLite/四扩展、原 fixture/recipe、hashseed0、同被动 observer，基线结束后才启动候选；UUID/时钟自然不同。不替换 clock、数据、业务 callee、授权、SQL 或 Graph 判断。对照时未并行编译/测试。单对样本不作因果或稳定速度保证。

| 两个 binding 组件 | 基线 2ad | PB 候选原型 |
| --- | ---: | ---: |
| 完整测试 wall，含观察开销，不含 pytest 启动 | 34.915240 s | 34.076228 s |
| 该 owner 线程 CPU，非所有线程 CPU | 23.621600 s | 23.703039 s |
| pre 编码次数 / 字节 | 477 / 271,431,279 | 477 / 272,722,263 |
| post-shaped 编码次数 / 字节 | 486 / 409,670,970 | 486 / 410,866,989 |
| pre 完整结构比较调用 | 2,214 | 2,217 |
| post-shaped 完整结构比较调用 | 3,754 | 3,757 |
| pre 每次比较节点数加权和 | 9,049,323 | 8,890,481 |
| post-shaped 每次比较节点数加权和 | 27,289,670 | 27,252,214 |

每个 owner 620 个节点、无外部 boundary anchors；raw 候选退出了消费者，确实是真接线而非只加未调用工具。但全图扫描加权体积只降低约 **1.75% / 0.14%**；这是每次比较节点数之和，不是独占对象数，也不能当 CPU 下降。原完整编码次数不降，字节量增加；新增每图 3 次完整比较。wall 少 0.839 秒而 owner CPU 多 0.081 秒，**没有证明 material 净收益**。因此拒绝启用，不重复耗时相同的大型 Cold。两臂各 5 FixedMock、0 real；本轮其它烟测/消费者测试共 10 FixedMock，因此当前阶段总计 **20 FixedMock、0 real，0 Cold 模型请求**。所有 DB 为新建 test_only SQLite；不作正式 PG、真实来源权益或 Windows 验收。

## 下一结构边界与现有产品范围

不能继续按单个 620 节点候选添加 owner 来声称解决 G0/G1。上轮真正大型两笔仍为 G0 31.088/30.963 秒、writer-window 45.450/49.599 秒、总计 76.539/80.563 秒；这是原签署 120 秒测试的功能证据，不是原 30 秒合同。本轮没改这些值。

仍需处理的是完整依赖计划与动态执行的分界：在首次完整生产口持有 Source/Generate/提取事实的全部不可变值及别名，不带 Graph/授权结论；后续必须保留原每次文件/SQL/身份/回调执行。只有纯值变换具有 exact code/default/global-role 来源、完整输入和明确变异边界时，才可替换该纯值计算；原事务和 G1 的实际写集、rowcount、完整 postconditions、版本/fence/撤权/双时钟仍完整执行。前轮端点相同但外部回调/文件/查询顺序/原生事务生命周期未闭合的事实未被解决，本轮无复用资格。若不能在此边界消除真正大头，应改变事实生产和消费者的数据所有权/依赖接口，而非再增加末端包装或强指定快速路径。

已验 Linux ZIP仍为 `Sim2Act-local-candidate-2ad3227621b4.zip`，3,188,692 字节，SHA256 **6b6e42d909089ad001a6ff889976b7eff0e65ab7e4229fd95f15377b57efe81d**。该候选及历史小目标真实成功范围不变；本轮 0 新真实模型请求，不声称新二进制、Windows 目标机、大型 live、正式 PG 或全产品完成。没有更改预算/取消/撤权/原子性；无 main、Release、部署、Windows CI、用户电脑、新费用/凭据/权限或训练。
