# Typed cohort 完整严格流式比较：运行代码候选

本片实际修改 `_trial_typed_values` 的公共内部实现，所有既有 prepare、两次 commit、
stage、独立入口及 scope/post 中调用此函数的位置统一使用新比较；不只改变 `_recheck`
或显式 native 模式。新私有模块为 `src/sim2act/_cold_typed_stream.py`，原调用方仅增加
6 行接入。没有新增 owned 能力、迁移任何根、删除 typed 门或修改事务/期限。

基线：`6f2a848f701673c3c26a24b93eee9a15fbeb5d7d`。
最终 stream SHA-256：`38eb83139b6aaf70f0e624075951fb0f5caf5537c306c2fb9a1356275107868f`；
admission：`1d9f85ab98a71ba00715b6a2c64037a22878280eb43965515762f7b7b9914749`；
新测试：`fdc35cde14d40a58b0a364e9d8a71fe8de9cf6b8d2f8fd0edd6c1fe4543bff5e`。

## 保持原门的实现

1. 每次完整遍历实际 model 存储：exact 根/嵌套固定类型、完整字段集合、fields_set、
   extra/private、全部容器与键；保留两种既有 None omission。迭代器替代 actual 的
   递归容器副本。只复用本次已完成 DAG 节点；active 先于 done，cycle 仍拒绝。
2. 完整遍历 raw，并同时与实际存储的虚拟投影严格比较，避免深复制 saved raw。
   值、键、形状、长度不等只置 mismatch，**全 raw 门完成前不因 mismatch 提前返回或
   抛错**，因此后部 unknown/cycle/非法键/行索引仍按原 DFS 顺序拒绝。缺失/被省略的
   actual 字段使用哨兵，不提前索引、不让 None 顶替另一个缺失字段。
   raw 完成集合与比较 pair 完成集合分开，pair 包括两个对象及 omission 模式。
3. 全 raw 门完成后才执行原 storage mismatch 拒绝。资格检查对本次访问到的每个
   固定模型类型新鲜读取，包括 Any 中的嵌套模型；不缓存跨调用/跨 pin PASS。
4. 保留原 `expected.model_dump(model, warnings=False)` 一次，再做完整严格流式比较。
   类型仍区分 bool/int、int/float、list/tuple；NaN、Inf、±0 行为与旧比较一致。
   RowMapping/quoted_name 保留原受控可见投影，不扩大此纯比较的隐藏数据边界；
   完整隐藏域的原 CGR 校验没有减少。原 bytes、业务 fingerprint 和输出不改。

原 `_trial_typed_guard`、hold/produced、parent/CGR、每个 SQL/授权返回检查及所有
Run/version/fence/stop/时钟调用点均未改变。原单个 BEGIN IMMEDIATE、连接、scope、
renew、heartbeat 和所有期限保持。CGR `input_bytes` 直接调用的 `_trial_typed_storage`
仍为原实现，不在本片优化内。临时遍历 metadata 不逃出调用，无新产品输入上限。

## 固定序列化边界与兼容

只有固定标准序列化器可使用上述无 raw 深副本桥：静态取 `model_dump`，不提前触发
descriptor；exact C SchemaSerializer 的构造 schema 必须是该固定类的 core schema。
资格覆盖每个已访问模型类型，防止 Any 中嵌套序列化器改变外部 raw。
不符合者走**原 snapshot 算法**，保留序列化前 saved raw 的含义，不能把它改成
“序列化回调修改 raw 后与新 raw 相等即可”。fallback 会多做纯预检查，不能声称所有
底层遍历次数不变。此兼容不是 owned 发行后的降级，也不创建权限或预算资格。

固定源 catalog 无自定义 model/field serializer，只有两个 `is None` exclusion hook。
这里不声称对任意同时替换类 schema/serializer、任意进程代码或协调并发改 model/raw
的行为具有快照等价；它也不取代任何原可变前沿或外部返回边界。
被替换的 method、descriptor、同 C 类型 serializer 以及嵌套 Any serializer 均有旧新
差分拒绝测试，原异常/回调次数由相应反例检查。

官方实现核对：[Python 静态属性读取](https://docs.python.org/3.12/library/inspect.html#inspect.getattr_static)
说明它避免 descriptor 动态查找；安装的 pydantic-core 为 2.41.5，其
[SchemaSerializer 源码](https://github.com/pydantic/pydantic-core/blob/v2.41.5/src/serializers/mod.rs#L174)
保存并返回构造 schema 引用，元数据读取不调用序列化；
[Any 序列化源码](https://github.com/pydantic/pydantic-core/blob/v2.41.5/src/serializers/infer.rs#L589)
解释了为何资格必须覆盖嵌套模型。依赖升级须复核此固定实现合同。

## 实际验证与有限成本观察

- 冻结广回归 **111 passed / 71.06s**，9 个测试文件：差分、两项真实 SQLite model/raw
  别名反例、pure cohort、fixed-key、guard delta、typed callback、extract parse、
  `_base`、真实 `_cold_receipts`。冻结前后 4 项源码/测试 SHA 完全一致。
  该批 stream 为 `6660067b…`，新测试为 `b9d50805…`。
- 此后 stream 仅增加 7 条无赋值局部集合类型声明以通过 mypy，递归核对编译后的
  co_code/co_consts/co_names/co_varnames 完全相同。另补反向 DAG 差分一项。
  **最终版本定向 37 passed / 11.87s**，前后 manifest 一致；mypy 两个源码文件及 Ruff
  通过。两批有重叠，不相加为 148 项独立测试。
- 差分基准为旧四阶段函数本身。覆盖全部 header、未知键/值无回调、混合错误优先、
  missing/extra、None omission、双向 DAG、cycle、数值类型/非有限值、RowMapping、
  固定序列化替换、原 parent 异常，以及 128 棵确定性原生树。新 SourceResult 用 UNKNOWN，
  不伪造 ALLOW 或替换账户 resolver；RunCheck 只验证内容比较。
- 最终观察仅为同一真实 SQLite 下级 producer 得到的 **11 个 typed 值、25,387 JSON
  字节**。旧算法两批 40 次 CPU 为 53,223,655 / 53,279,458 ns；流式为
  48,865,494 / 49,261,534 ns（该小样均值约低 7.9%）。单次 tracemalloc 峰值旧为
  67,912 / 62,168 B，新为 14,720 / 14,720 B。此为本样本 traced allocation，非 RSS、
  全进程界、完整 G0 归因或 30 秒期限通过预测。

开发失败原件均保全：新增测试首跑 28P2F 是测试字典构造时碰撞回调及错误的
BranchCondition 字段，修夹具后 30P；后续 omission 反例 1F 确认候选曾在第二比较才
拒绝而原算法在第一比较拒绝，已修正并纳入最终批。初两批 mypy 类型声明错误也
单列保存。早期 14P/31P/32P/34P 均为开发阶段，不冒称最终源码验收。

## 尚缺完整成功尾段：固定账户门，不以 stub 越过

完整 `_prepare → first commit → receipt → second commit → 正常原 scope/final clock`
本轮 **NOT RUN / NOT PROVEN**。现有精确 Cold/CGR 要求 ProductionTrialBinding，
而 `_journal_source:1188 → spec_production.source:52 → resolve_account:188` 在原 approval
后无条件 SOURCE_MISSING，之后还有原 software qualification。SQL 种事实不能解除
代码级拒绝；改为 offline binding 不再是该 Cold 路径，制造 SourceResult/替换 resolver
不构成安全阳性。只读夹具审查逐项列明现有 seed 缺失，不能将 `_base`、receipt 或
有显式 stub 的 synthetic commit 改名冒充此成功路径。

本片交付真实统一比较代码和必要安全差分，不以此限制停留在重复缺口文档，也不
把它说成完整 owned 迁移或 G0 修复。仍无新 grant/Mock/G0/W5/真实模型、外网业务、
付费、凭据/权限变化。没有新 launcher/后台进程；测试使用原隔离夹具关闭连接。
原未知 G0 状态及全部原期限保持。完整尾段资格需原账户来源与完整当前结算事实
先合法具备；本片没有另开账户实现或为性能测试添加假证据。

原始日志、冻结清单、初审/修复/最终独审和 fixture 审查在 `raw/manifest.json` 逐项
绑定压缩前后 SHA-256，gzip 可逐字节恢复。最终提交及 remote/dirty/ahead 回执另实核。
