# 精确开发版本构建与便携装配修复

起点 `cd8ff1f51a86ea28ee8d0410f377718f5616bb8e`，工作树干净且实时远端相同。用户已澄清“不动仓库”只指 X 存档，四项目恢复开发；本轮不消费 G0/设备/浏览器窗口。

## 实际产品修改

原 `package_windows_portable.py` 固定旧 wheel 摘要；最新已审源码无法进入原便携装配。新增显式 `--candidate-manifest`：核精确 source_commit、整份 wheel hash、全部实际打包 Python/网页/数据资产字节及 ZIP 完整文件集合，拒绝额外、遗漏、重复或篡改项。只有原本省略的两份实验 C 源码仍省略，不扩大运行资格。校验在运行库装配前完成，输出存在拒绝覆盖。旧无清单路线继续只认旧 wheel，并补精确旧 commit，不能用旧 wheel 改贴新版本。清单只是构建一致性，不独立认证任意手写清单的 Git 来源。

源码提交 `c0cdb9a6`；随后 `12c83541c8d0cba82820531517bac8b96de8ca82` 仅把两份既有装配/启动源码加入开发包白名单，保证包内维护说明有实际工具。没有更改后端、UI、模型权限、lease/fence、SQL、时钟或回执协议。

## 实际执行与冻结

- `.venv/bin/python -m pytest -q tests/test_portable_revision_binding.py --junitxml=/tmp/portable-revision-binding-20261027.xml`：8 PASS，pytest显示0.05秒；原 JUnit 为 `binding-tests.xml`。这是合成归档测试，不运行 Windows。覆盖新旧版本绑定、wheel篡改、源码修改/缺失/新增/重复、完整小型装配、失败不产输出和已有输出保全。Ruff两文件与 git diff --check 通过。没有保存该次完整 stdout 文件，不伪造原终端日志或运行前时间戳；源码冻结由 assembly-before/after 及最终 Git 字节另证。
- `.venv/bin/python -m pytest -q tests/test_windows_portable_delivery.py::test_exact_assembled_archive_all_bytes_and_notices --junitxml=/tmp/portable-original-compat-20261027.xml`：1 PASS、0.22秒，单独核历史成品全部字节/许可证，不是重跑旧整套或新 Windows 运行。两个 pytest 均保留既有 Starlette/httpx 弃用警告，未改依赖迎合检查。
- `.venv/bin/python scripts/package_local_candidate.py --output /workspace/sim2act-delivery-final-20261027`：从干净 `12c83541…` 精确 Git blobs 构建开发包和 wheel。`build.log` 是原 stdout/stderr。原 venv 没有 setuptools；现有构建流程在临时隔离构建中取得 pyproject 已锁 `setuptools==82.0.1`，没有使用系统84替代、升级全局环境或改锁。pip缓存目录不可用，未修改所有权/权限，构建正常完成。
- `assembly-before.json` 在唯一装配前落盘，记录实际 argv、60秒本地子进程上限、UTC、源码/输入/候选摘要。以原已下载 Python 和21个 runtime wheels 装配，**未下载运行资产、未执行Windows代码**。`assembly.log` 原 stdout；`assembly-result.json` 终态 exit0、1.608184秒、sources_before==after，1723归档成员、159源资产一致，所有成员核manifest。不是性能基准、RSS界或G0。
- 独审 `catalog_native_review` 只读核：开发包183件、精确Git源码及三份打包工具；便携包完整清单和候选/wheel/commit/launcher绑定；1552原运行库成员逐字节与冻结输入一致。限定ACK，无写入/运行测试/联网/Windows。之前构建的cd8开发包仍在其独立目录保留，没有覆盖成最终版。

便携成品 18,997,744B，SHA256 `82e8bb87bc01148ad1c8e639f6b2aac9b154d40b75d651b9c8e554d47fccd13c`；开发包 2,410,449B，SHA256 `8371e0e5381cdc71f26866d32a2b3430e650a38cbeed13a1f430771e3a8630d9`。文件见 [开发候选](../../../deliverables/dev-candidate-20261027/README.md)。本地源构建临时 staging 正常删除；最终包、日志和清单按交付要求保留，没有启动服务/浏览器/Worker，不宣称全机进程扫描或删除所有 pip 临时目录。

## 最短剩余关键路径及时间风险

原V5/F2、P-B控制器与10月31日底线保持，不把此包或旧局部通过升级为整体F2/R0。

1. **G0工程结算**：最新受控窗口的UNKNOWN仍有效，不能重用已消费grant。源码独审再次确认 `_NativeModels.produced` 每producer独立memo、可变native模型返回、`_recheck` 的新requirements/Approval/StageAuthority/Source/FrozenContract/Limits/RunCheck、最终FrozenContract/output及独立 `_ModelSettlementRead` post graph 尚未形成七族消费者闭包。现有候选保留全扫描而且增加复制，不能声称净收益。下一代码工作须整批实际producer登记、跨根别名一致的不可变内容源和全部消费者迁移，再证明发行前总容量/LEGACY路由及同范围净收益；不能先删guard、缓存PASS或延lease求过。本轮没有新增半套组件、微基准或声称已完成该项。
2. **可信生产来源**：`production_evidence.resolve_account()` 仍明确 SOURCE_MISSING；用户免费确认不是伪造官方事实的许可。需要受审真实producer对固定账户身份、权益、不可收费/撤权及有效期的可信来源映射；不阻断独立工程代码，也不能由合成provider替代。此轮零真实模型请求。
3. **精确冻结候选验收**：这个新包仅Linux构建/字节审查。Windows启动/退出、最新组合PG应用角色/并发、真实材料/人工语义和owner签收各缺相应真实证据；已有历史PG及原生局部证据不作废，但不能签新包。旧Python3.12.10已superseded且原包明确短期隔离预览；长期运行库升级及最终成品原生验收尚未闭环。
4. **最终提交材料**：F3/R0/C0所需的官方提交范围、实际任务/基线、演示与可访问体验须按原方案冻结，不能把dev分支包当部署/发布许可。此时距原10月31日底线仅数天，G0完整尾段未通过且真实来源/正式验收未闭环，整体按期风险高；没有证据支持承诺必过或自行延后。
