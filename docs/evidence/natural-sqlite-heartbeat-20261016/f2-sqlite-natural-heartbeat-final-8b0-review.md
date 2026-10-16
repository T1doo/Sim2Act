# 自然 SQLite 心跳锁恢复：最终有限独审

最终审查提交 `8b0f74d101a9fb8843304f346e5390694eaafeae`，产品冻结提交 `99f878a83387a7ef1b2e8734aef3e015dff3020e`，基线 `87c1f0d0726f95270255a311983181ae1241bd09`。2026-10-16。根线程为唯一仓库写入者；本审查者只读仓库，只写自己的 /tmp 文件。

有限结论：产品三文件静审及独立新增完整9项轻测通过，无剩余未修阻断。8b0 相对99f仅修正旧测试一个函数的提交回执观察/断言，未改产品字节；该修正不降低验证门。根线程最终自然双 Run 已1PASS210.07秒，本审查者已只读核原回执、一次claim及保留行。自然实测没有 recovered 事件，恢复分支的直接证明来自实际SQLite/控制器轻例；不把已通过基线叫修复成果，不声称重现旧f9时序。

## 产品与安全合同核对

- 仅 natural_spec_runtime.renew、自然 pa_spec_apps.process_job 的现有同步续租数值发布，及共用 text_workflows 调度器恢复判断改变；没有更改 Store.tx、driver busy timeout、claim/guard/CAS、lease30/run300、模型/工具/令牌预算、权限、executor、Grant、版本/幂等或 Worker 模型发送门。
- publish_sync_renewal 仅在原 Store.heartbeat 成功返回后发布 worker/Run/fence/实际 lease 和单调 sequence。同一次自然调用私有 state 才 opt-in；恢复判断进一步 SQLite-only + genuine BUSY/LOCKED。普通完整验证读到更大的数值不产生该提交回执。
- failure 的 sequence 与 exception/failed.set 在 state 锁内同一锁存点捕获；只认锁存后发布的更新 sequence、相同 worker/Run/fence、未过已验证原绝对 deadline/真实 lease、未 stop。早于故障的旧 marker、不同 scope、数值进展、没有新 marker 均不能认领。
- 恢复明确记录 heartbeat_contention_recovered。旧 beat 在 failed.set 后只有 return，无后续 DB/state 工作；主线程清旧故障后用原 cadence 启动新 beat，保持模型 I/O 期间的后台调度。没有在原失败批次增加尝试或延长 driver 等待；没有将失败 heartbeat 改记为成功。后续新故障需自己的更新 marker，非 busy 或过期仍原传播/结算。
- 主线程重新 advance 仍走原完整权限/材料/Goal/owner/fence/deadline/receipt/最终提交检查；marker 是调度状态，不是授权 proof。未跨事务缓存权限或复用连接给后台线程。
- 静态 AST 对比证实15个关键函数相对87c1未变：Store.tx/heartbeat/guard/_frozen_contract_after_scope/claim，natural enabled/advance_model/effective/counters/fail_owned，pa commit_guard/verify_job/_advance_local/bound/receipts。git diff --check 通过。

生产 SHA256（99f 与8b0相同）：

```
801e45ebfa67e834c19dee2ab3e6c02907e4028b5f3f61bffc58e007b7e693ee  src/sim2act/text_workflows.py
10c1b3d29240f56fe60714376eb19ccdb6c0440f281b99d09ed91337f0b9e00a  src/sim2act/natural_spec_runtime.py
18a93701a2902f5f4827bbf990cea1e995d8adc43b580bda28bcbe20cf639199  src/sim2act/pa_spec_apps.py
```

## 本审查者实际独立执行

```
/workspace/sim2act-venv/bin/python -m pytest -q tests/test_natural_heartbeat_recovery.py --basetemp=/tmp/f2-hb-independent-99f878 --junitxml=/tmp/f2-hb-independent-99f878.xml
```

实际 RC0，9 passed / 0 failures / 0 skipped，29.71秒。执行时 HEAD99f；8b0 的三产品文件及该新测试模块均字节相同，已复核。只有既有 Starlette/httpx 弃用 warning。

real-lock 使用真实基础 Run、原 claim/Store/SQLite/flow：原 driver busy_timeout5000ms、lease30/run300；仅测试 cadence Event.wait(10)→.001。后台真实 BEGIN code5（本次整个 heartbeat 调用观察6.178秒，含调度/连接开销，不说纯等待6.178或配置变长）；之后同 scope 同步 heartbeat 真实 commit，marker1发布；新后台线程又实际 heartbeat commit。advance两次、一次 recovered，Run保持 RUNNING 无 error。这是控制器成功恢复，不冒充自然业务任务终态 SUCCEEDED。

其余 case 为明确合成反例或发布边界：

- numeric-only、old-marker、wrong-scope、deadline：各只 advance一次、0 recovered、原 WAITING_RESOURCE。
- non-busy：原异常传播，0 recovered，未虚构终态。
- repeat-failure：第一次已恢复后，第二个非BUSY IO错误仍传播，不能吞新错误。
- repeat-busy：只在合成缓存 scheduler lease置0、实际DB lease/clock和真实marker不改，迫使原规则锁存第二个BUSY；旧 marker sequence不能认领它，实际 WAITING_RESOURCE。
- 发布失败：实际另一 worker 的 sync renewal被原 guard拒绝，不产生 marker，不改 state lease。

除 real-lock 的真实 code5、真实同步续租/重启后台成功外，其余故障明确 synthetic；所有 case 基础 Run、natural business fixture NOT_RUN、0真实模型。8份每case proof JSON，最后的发布失败仅 pytest 断言/JUnit，无单独 proof JSON。

独立原始证据：

- `/tmp/f2-hb-independent-99f878.xml`，SHA256 `32b6d2085acb760ec5fad3e6eaf8135889a116c894d9484730a7b8fd663c8805`
- `/tmp/f2-hb-independent-99f878.log`，SHA256 `5a9ed363c8bf9c6a3a8496605d1de9468022a7ff0252e08889881fcff6a72894`
- `/tmp/f2-hb-independent-99f878-manifest.json`，SHA256 `718c7fc4d680e94b6c50e598202521493a908014c326fe1496b20ad32ad7035a`，含8份 proof路径/哈希、源文件哈希与15函数AST证明。
- 新模块 SHA256 `f00b5c87761cd7ef41255aaaad995def7f232b407898d7b548fead56cd258553`。

## 因果证据及旧身份边界

原 f9 额外多历史第二旧 Run 的 WAITING_RESOURCE 与错误原件未改；该旧原件没有事务时序，不能追认其确定持锁者/具体竞态。根线程87c1自然时序基线1PASS110.18秒，两Run各一claim成功，本轮没有自然重现旧WAITING。

对根原始trace的独立配对发现7次真实code5全在BEGIN且从未acquire；与前台已acquired→committed-return窗口几乎全重叠。第二Run两次错误分别完整落在 settle900的9.232秒和advance691的13.170秒同一前台窗口中。它定位当前真实自竞争，不是纯CPU/精确解锁/旧f9身份归因证明。

独立基础Run受控基线探针一次稳定复现：前台真实持writer→后台默认5秒BEGIN code5→故障锁存线程退出→前台commit→同owner/fence真实sync heartbeat commit并发布→原循环仍不继续advance、变WAITING_RESOURCE。该探针只加速测试调度、不改预算/异常/clock，证明了可修sticky竞态，但不是自然业务身份的完整复现。

完整基线因果报告 `/tmp/f2-sqlite-natural-heartbeat-causal-87c1-review.md`，SHA256 `de693b542c7a782aebc1ba201101d4dfcaf839ecfe71bc6dd31e437b19626ce9`；原件均保留：

- `/tmp/f2-sticky-owned-87c1-g4nku3x2/proof.json`，SHA256 `5fcb6d4303d8d75213f1b3eedaaa5214a4df3fbc8f0daf94312d41093469d57e`
- `/tmp/f2-sqlite-sticky-probe-87c1.py`，SHA256 `d9762a647a2f17b5e3014597821f9ebdf9d9d1e3b656da6e6405174b38258352`；同名.log。
- `/tmp/f2-hb-baseline-overlap-independent-87c1.json`，SHA256 `957480d84cf1f0190a93151d9e1f119bdce9cd03a6f776babe19b17c90420353`
- `/tmp/f2-hb-own-store-87c1-nlmsoa_d/proof.json`，SHA256 `749237fd22308fc581d5207ad2bf6ae965d1bc616b090c10ab9e745c35067b79`，先前真实公开Store纯读持锁机制probe，非Run/Worker。

## WIP 与分阶段安全回归如实保留

首次WIP曾按失败attempt开始sequence判新进展，独审建议后已收窄为严格halt锁存sequence；该项关闭。首次light7P1F中 repeat-failure要求第二sender3秒内halt，但原已有 guarded defer允许有效既有同步进展继续等待，是夹具期望错误，未归产品。根原 `/workspace/heartbeat-lock-wip-light.xml`（SHA256 `9440bea940577f33b45df34c1e49fdf0980a1612d67a5b2bda379259a4cf2edc`）、`.log` 和 `-test.py` 原字节保留；改为第二非BUSY传播，另加独立repeat-busy，当前9项均过。

根99f最终安全批实际 **45PASS/1FAIL/0SKIP，46项，96.525秒**；原FAIL是旧 known/late恢复测试在.001加速cadence下多出第三次合法成功heartbeat（codes仍仅[5]），裸len(calls)==2失败，不是业务旧f9根因。原 `/workspace/heartbeat-lock-final-safety.xml` SHA256 `ace16e5ac72b063d3e5806d606de3938c75bd26e019ab26763431aa7e1540f0a` 与.log保留，不说46全绿。

8b0仅把该旧函数新增 renewals 记录；保留 codes==[SQLITE_BUSY]，要求每个额外call都对应原 heartbeat成功提交返回值，DB lease==state lease==max(renewals)>claim，且同owner/fence。该修正以实际提交合同替代加速调度下不成立的精确次数假设，不允许重复Run/模型、不增等待/循环，且没有弱化授权/lease验证。

根在99f+这一个test-only WIP精确字节上仅定向 known/late **2PASS/0SKIP**，stdout10.92秒（JUnit10.899），随后普通提交8b0；未冒称全部47或46在8b0单批通过。已只读核 `/workspace/heartbeat-lock-final-test-adjustment.xml` SHA256 `b35bd5c38e624c08e14620d6af82ff2667130be80d9f0517385a4f0537c5e8be`，.log SHA256 `eff54b3ff9083f29c814cf3027a33dccd3bdf5fce74dcf8b5007419b21b9705f`。旧函数完整文件 `/workspace/heartbeat-lock-safety-before-test-adjustment.py` SHA256 `34b2f877b8e6275f28fdb59cc497aef60a62733f3314195f66873e552f156dce`；修后文件SHA256 `95b4ebfec4973f9227af5a79c111d50c24562bb1d5bb1cd8bac7956b4bd5cb46`。

以上阶段不合并伪造成同一提交单批绿结果；独立9项是重复验证已列新模块，不另加覆盖分母。本审查者未重跑Worker。未执行Windows、PG、原生浏览器、远端CI、真实模型/场景或人工语义；未声称SQLite任意负载容量或所有旧随机失败已解决。

## 根线程最终自然1PASS的独立只读回执核对

`/workspace/heartbeat-lock-final-natural.xml`：1PASS/0FAIL/0SKIP，210.072秒，SHA256 `93f1207eb72d04725a9359a4ec772ea312835cbf51bde11d3413cfc31dc6b408`。这是根线程执行，不是本审查者重跑。

原件目录 `/workspace/heartbeat-lock-final-natural/test_sqlite_same_natural_insta0/` 已只读核：

- proof.json SHA256 `c826bf18db93d3564f6e74991bf8f7f368a955cf03dcc2c591b1f80da9b2c84e`，同 app/Release/instance、两次显式 Worker.once、版本[1,2]、lease30/run300、真实模型0。
- run-observations.json SHA256 `624da1d72cd55f3e1c8bd4b49b369909968073018ae2d7d9646d7a5fef5091bf`：原Run `run_de967df974b845eb9b54d58d6a48921c`、新Run `run_f2e079743bf14db9a9c515b7990b0e76` 均SUCCEEDED/fence1，各一个CLAIMED事件，created_at不变。
- retained-rows.json SHA256 `99b5bd385898d5b1b7619d2cfc668f9e3e6a499ac5f80fa4a5f1c055fe872e88`：本审查者实际比较原Run、AppRun、artifact资源、app、Release、typed_v1的before==after；原instance唯一变化为data_version1→2，其他字段完全相同。
- runtime-wires.json SHA256 `1f8ebc59c1296b139a470fb06165cc6cce9ae56a6e80df089ea1f74f22f46009`：两个Run各一条MockTransport wire。新结果材料独立，原制品字节仍由既有精确HTTP读取校验。
- heartbeat-logs.json SHA256 `97fb5d1ae5b0f507302dc700a06c3f39e9638bee98ad43c7bf882f35e50a120a`：5次既有deferred、1次halt、0次recovered。根报告halt为终态后stale，不把它当运行中恢复分支命中。另有完整http-receipts、run-ledgers、tx-heartbeat-trace原件。

最终证据必须保持分阶段：99f安全45P1F、8b0同产品test-only定向2P、根自然1P、独立新增轻模块9P。它们支持已证sticky竞态修复及有限自然双Run正常回归；旧f9具体时序依然缺证据，原FAIL身份/原始错误不得改写。
