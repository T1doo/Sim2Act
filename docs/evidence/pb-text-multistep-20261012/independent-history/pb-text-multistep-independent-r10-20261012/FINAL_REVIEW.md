# 有限四步非CSV提取独审：LIMITED PASS

r10当前精确候选完成 **54个唯一检查最终态54PASS / 0产品FAIL / 0ERROR / 0SKIP**：指定41后端、4实际HTTP/JSDOM页面、独立7后端负例、独立2受控页面负例。原始55次执行为54PASS＋1独审expiry错误码夹具FAIL；该FAIL/exit1/JUnit保持，修后只重跑同一节点1PASS，不能描述所有原进程均exit0。详细最终唯一节点、原全部执行、每套命令/exit/wall/log/XML见 `final-summary.json`、`final-nodes.json`、`all-executions.json` 和各 `.log/.xml/-exit.json`。

| 实际集合 | 原结果 | 最终资格 | wall秒 |
|---|---|---|---:|
| 本轮后端（作者定义、独立运行） | 41PASS、exit0 | 41PASS | 120.072 |
| 四种实际页面场景 | 4PASS、exit0 | 4PASS | 132.474 |
| 独立后端首轮 | 6PASS/1夹具FAIL、exit1 | 下行补齐后7PASS | 52.336 |
| 独立expiry校正单节点 | 1PASS、exit0 | 替代上行同一expiry节点 | 3.669 |
| 独立原key/真实app替代200页面 | 2PASS、exit0 | 2PASS | 10.393 |

41＋4与父root本轮45选集重叠，运行和证据独立；额外7＋2有自己的节点。功能场景也有重叠，不把独审54与作者45、旧291、CSV或旧轮成功数相加。父关联回归及推送不由本报告推断。

## 精确源码和只读范围

414个 `src/tests` 文件测试前后完全一致，map **8315e4f02df120c2b066c12e58dd2299e5dbbe52062d8b53fcfd4514512253fa**；68Python（config除外）implementation **ccf4ffd41ff45ccf5d46d12ebb659c1ea930b9f75dd45922ec84781806d0c70a**；pyproject **49f68cb7901e719cd014141c69e5fa9ea562f51e9b9c40acd122ace6f2085d81** 不变。实际base HEAD **1ab405fa5a413e9812744d39b7c0d51c9265ee3d**，branch `dev/pb-text-multistep-20261012`。这是未提交候选的资格，不能把base当新切片最终commit SHA。

完整前后映射与作者冻结原字节在 `source-before.json`、`source-after.json`、`author-freeze-original.json`；审查的原代码/测试快照在 `source-snapshot`，diff在 `source.diff`。所有仓库、作者测试、旧报告只读，root唯一writer；仅新/tmp目录写脚本/数据库/证据。文档允许root更新，不属于414代码资格。`no-active-processes.json`实际核本scope测试进程/Node均退出。没有安装、切换执行环境、网络权限扩大或任何push。

## 有限合同与桥审查

新 `text_workflows.py` 只接受规范 `closed-text-four-step.v1`：同一TXT/MD读取→两个独立字面lookup→显式bool条件引用报告。材料≤1536 UTF-8字节/32行，词≤80且非空单行，每侧≤8完整行引用。精确比较全部manifest/actions/接线/条件/schema/permission/dependency锁/limits；不开放自定义DAG或登记任意operator。报告oracle从实际source bytes独立重建两组完整引用与报告文本，步骤各自Operation＋Intent＋完整receipt，不由最终output反推完成来源。

`source_goal_card is None`属于既有普通GoalRun字段契约，没有把该字段冒充AppRun Goal锚。新入队保存原完整nativeGoal为 `accepted snapshot.text_goal`，冻结GoalSpec card ID/version/fingerprint marker、真实goal/constraints/unresolved及资源hash；`bound`与每步、末尾 `commit_guard`重核当前head与完整接受绑定。当前原样Goal修改、有效hash重签contract约束、权限/限额变化均会阻断执行。`app_jobs/lifecycle/apps/api/text_continuations`只增加闭合家族桥与durable Worker路径；同步实例run明确拒绝该家族。

实际false分支三份VERIFIED业务节点＋report SKIPPED构成PARTIAL，无typed/output/result_version成功记录，来源proof拒绝；前缀、未终态、FAILED、UNKNOWN、取消、缺步骤、错误引用/Intent、缺typed、实例data_version错均不能获得完成提取。真SUCCEEDED提取须4个真实VERIFIED节点与精确typed/accepted Release/contract/input/output链，当前source权限及材料hash；同项目不同材料仅一跳，第二跳拒绝。新应用独立runtime仅新所选材料Grant，owner PENDING、semantic UNKNOWN、formal publication false。owner后端的既有 `owner_acceptance.base` 因非generated literal Goal家族明确UNSUPPORTED，前端也明确该家族暂不提交人工声明；本审仅静态核这个拒绝门，动态验证的是页面PENDING，没有冒充人工签收验收。

## 三个实际红→绿完整性反例

r8原成功41之前的36后端＋4页面不覆盖三个独立负例，不能作为最终合格。独立原3真实FAIL完整保留在 `/tmp/pb-text-multistep-independent-r8-20261012`：

1. 真四步成功后插入一行合成Attempt（没有provider调用），proof仍200且model_requests0。r10 `bound`硬核实际Attempt表无任何该Run行；当前probe409、全数据库零写，不能以context计数0代替实表证明。
2. 删除RunScope双seal及ACCEPTED，再把binding的app_run_id改为坏指针并撤user材料授权；最终HTTP403，但SQLite观察器先实际求值Run的context/result/goal/resource_refs/error五个私有单元。r10使用独立fresh runtime及 `internal:+原AppRun.id`最小metadata找原app/material scope，当前授权先于Run/binding/result body，随后缺seal明确失败关闭。当前同一probe403、保护单元求值0、全数据库零写。它是本地合成持久错误下的先读后拒问题，不是响应内容泄露，也不是已证明真实攻击。
3. 保留真实成功Run、原binding、全部fp，将AppRun.input.emit_report从bool true改integer1；原Python宽等使inspect/proof200。r10 `load_binding`用规范fingerprint比较input，当前两路均409且全数据库零写；成功输出严格schema/fingerprint也保留。

原状态解释门还核当前fence `TEXT_WORKFLOW_STEP_VERIFIED`，不能在已经执行该fence步骤后把AppRun改QUEUED伪装最初CLAIMED；WORKER_LOST解释要求当前fence，真实cold前缀lease接管仍通过。作者41包含对应真实负例和冷接管，旧prefix Operation ID及完整bytes保持。

## 末尾提交与独立额外样本

7个独立后端样本额外实际确认：Attempt污染；双marker/accepted丢失＋坏binding的撤权先门；原create key撤权冷GET保护source/Run单元0；4真实节点之后typed INSERT与最后guard之间失效时事务回滚；真实一跳derived Run已有4个receipt却不能二跳；有效hash重签Frozen Goal constraints仍拒绝；AppRun input integer宽等仍拒绝。所有只读拒绝请求均比较全部数据库表无新写，实际JSON/SQL在 `independent-proofs` 和 `input-width.json`。

expiry首轮（r8+10000、r10+60.001）越过原30秒lease，先被 `Store.guard` 的VERSION_CONFLICT拒绝；typed插入hook1、全DB零写与四个prefix ID保持本已通过，但独审误要求只能BUDGET，原FAIL完整保留。这不是产品部分提交。校正只在新/tmp测试代码中按真实同worker heartbeat续lease120，保留运行预算60与原所有写入/前缀断言；时钟在typed INSERT后到created+60.001，实际 **BUDGET_EXHAUSTED**、INSERT hook1、全部表零差异、4份真实VERIFIED Operation ID原样。只重跑该同一JUnit节点1PASS，不重复或假造其它6个通过。

## 原key及页面证据

4个作者定义页面场景各1boot×20assets，实际TestClient HTTP↔IPC↔离线JSDOM，合计43断言/80当前asset SHA、4个真实冷NoModel Worker：正常、丢create回包、丢run回包、false分支。真实新材料、独立term_a/term_b、conditional report、精确引用新计算；原key未知只GET恢复，不自动重发；owner PENDING。结果/请求/可见动作/asset hash全部在 `ui`。

另原r8精确414快照、20assets的受控UI1真实FAIL：丢create回包后原key GET被同项目另一真实fourstep app的有效candidate hash替代，前端错误保存receipt并开启Open。原精确source复制/PYTHONPATH只/tmp，无安装/共享可变source，前后414原hash一致，完整证据在 `/tmp/pb-text-multistep-r8-ui-counterexample-20261012`；初次GoalCard create response错读title的KeyError属于夹具失败，原log/XML未覆写，正常Goal API设置唯一title后才得到真实反例。

r10回执携带双seal request/key/fp/runtime，实际App GET另给独立origin key/requestFP；页面对pending原body、实际app origin/Goal/material/source scope逐项核。当前额外2受控UI合计8断言/40assets：另一真实app完整valid回执（wrong key），以及保留正确原key/body/fp但替换另一真实app id/validcandidatefp/runtime。后者应用名称用正常可见输入对齐，因此不仅依赖名字不等；两例均receipt为空/Open禁用，不产生额外POST。它们是受控坏200/本地UI验证，不是实际攻击声明。

异步hash后可能发生只读GET，随后current fence在receipt赋值/Open/pending删除前，服务器身份/材料授权另行限制返回；不能把只读请求本身升级为迟到提交或scope写穿透。没有额外运行晚hash identity恶意场景，故不声称所有identity切换期间旧目标GET都为0。POST发生在该hash之前，已有第一层current门；本有限关键结论是无错误receipt/Open/新写，而不是完整网络请求抑制证明。

## 原历史与未验边界

306份既存独审证据在本轮前后原SHA一致，完整路径/hash见 `history-manifest.json`。r7两套exit2、partial backend30P/UI4P均INTERRUPTED，不计最终通过；ps substring自匹配停止核查脚本的AssertionError明确为bookkeeping夹具误判，原记录保持。r8共47节点43P4F，其中3真实core反例＋expiry错误码夹具F，以及单独r8真实wrongkey UI1F/其前KeyError夹具，全部保留；作者原4NameError、r7双barrier退出3错误属于其夹具日志，不将它们写成已经执行的真实产品红例。作者STATIC五项具体设计问题属于静态判断；本独审实际红→绿证据按以上3＋UI1明确列出。r9作者历史由root归档，不从其未解析状态推定通过。旧取消精确安装窗口永久NOT_VERIFIED，不是本受控GET负例。

只可称本SQLite、HTTP、离线页面和NoModel有限四步合同通过。本scope无未解决实际产品FAIL；PG、Windows、native browser/socket、真实/付费模型、真实客户旧库升级、人工语义与人工签收、完整P-A/P-B、CI均NOT RUN。没有凭据配置、扩权、部署、main/core修改、强推、外部通知或重试任何已知拒绝路径。父291/CSV关联回归、文档及普通dev分支commit/push仍由root完成，不提升为全产品或语义验收。
