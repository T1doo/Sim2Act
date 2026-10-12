# 最终独审：LIMITED PASS

当前冻结候选的有限显式文本软件接续验证完成：**80 个唯一 JUnit 节点，80 PASS / 0 FAIL / 0 ERROR / 0 SKIP**。源码与作者测试均只读，只有 root 写仓库；所有独审脚本、克隆数据库、报告和原始结果在 /tmp。

| 实际本轮集合 | PASS | FAIL | SKIP |
|---|---:|---:|---:|
| 指定后端，包括真实旧 FAILED Worker 夹具 | 58 | 0 | 0 |
| 正常／丢提交回包离线页面 | 4 | 0 | 0 |
| 独立后端／SQL 负例与屏障校准 | 10 | 0 | 0 |
| 独立页面晚身份／错误原 key／错误旧 Release | 6 | 0 | 0 |
| 独立损坏 FAILED 历史拒绝探针 | 2 | 0 | 0 |

以上只统计本轮新候选，不累加旧轮72或其它 root 回归。详细命令、进程退出码、JUnit 节点、耗时和分类在 final-summary.json / final-nodes.json，以及各集合 .log/.xml/-exit.json。

**实际版本**：401 个 src/tests 文件在全部测试前后 SHA256 零差异；完整映射指纹 **3bb07485d301ea8b01bd4e2b408e71b4789650934ebf8b1734dafc66ff08a32f**。当前67个Python（config除外）实现指纹 **c0cdc4e98de6a043bb43f1b1d5b27d4b57f525164922fb65cf70173f3b1d2a93**。pyproject SHA256 **49f68cb7901e719cd014141c69e5fa9ea562f51e9b9c40acd122ace6f2085d81** 不变。Git base HEAD 为 df5f422174c4eeea96e5dd16c141dc0a4b36b3e6、branch dev/text-compatible-continuation-20261012；本独审不作提交或推送，不能把 base 当成最终候选 commit SHA。完整冻结映射见 candidate-freeze.json / freeze-before.json / freeze-after.json；实际审阅21个文件的完整原字节在 source-snapshot，先前九份静态快照原字节仍在原静态目录。

**合同和实现审查**：有限来源只有批准233和a747的严格旧Python锚；正常logic.load仍 current-software strict。显式私有archival codec核原AUTH/BIND/candidate/旧Release，不重签旧authority、logicfp、原Goal anchor或数据。新审批将两软件、项目/身份/runtime、所选iid/旧Release/revision、typed/data/history/全部terminal jobs、Goal/owner ledger、target hash/GrantBudget、输入/oracle绑定；提交时重算并CAS，同事务新Release+双seal+精确实例history/revision。普通app/Release/approval/Run路径先scope和当前target门，再私有payload；新commit末尾独立fail-closed execution、expiry、GrantCAS，不用历史current_permission=false吞异常。只有精确获批Release+iid+revision能enqueue/resume/dispatch/commit或供owner新声明，app archival可读不复活其它instance/old queuedRun。取消和执行REVOKE是独立metadata，旧owner声明不会自动继承。

**R8红→绿**：原14be/316f候选中，追加明确损坏的合成FAILED queue（保留真实旧SUCCEEDED/typedv1与所有原data/history，坏binding、无新typed）实际preflight201/commit201后cold instance+job409，两锚均FAIL。该合成行不是合法旧Worker。新实现 text_continuations.py:293–314 对全部terminal job先核本人/项目/runtime、所选app的精确ReleaseIndex双seal、原archive load_binding/frozen contract/historical Goal和iid/Release，按ID排序；:351把完整job/accepted/AppRun写入批准CAS。typed-success继续用原oracle/Operation+Intent+receipt。当前独立R8两个探针均preflight409且数据库全部表零新增／修改，cold坏历史不再被接续；实际JSON见 terminal-history/{233,a747}.json。根另用精确已接纳旧Git生产API+正常NoModel Worker创建独立233-failed/a747-failed库，真实SUCCEEDED typedv1+INVALID_INPUT padded FAILED/no typed，新夹具正例也在58后端集合通过；不能把故障注入假行当成这两个真实旧Worker夹具。

**独立SQL探针**：旧origin discriminator剥除且当前target撤权时，app/release/approval/原键GET/release-list都403，完整private projection为0、受保护AUTH/approval cell为0、全DB零写。foreign identity访问Release/approval/原键亦拒绝且0 protected cell。未知old implementation真实UNSUPPORTED_CAPABILITY/HTTP400且0写；kernel差异为明确Path.read_bytes受控hash故障，未修改源码，known拒绝。另有实际SQLite cell屏障校准证明无WHERE完整AUTH payload读会被拦截；校准的故意blocked命中不能混成产品隐私FAIL。单marker组合已覆盖，全部恶意marker/同时重签组合不是本有限集合的完整证明。

**页面证据**：4例实际TestClient HTTP↔IPC↔离线JSDOM载入当前完整页面，两个锚×正常／丢提交回包。每例3boots×20assets=60，合计240asset hash核对、60页面断言；真实cold NoModel Worker新输入追加v2、保留v1、旧owner声明不继承，原key恢复仅GET，冷撤权后metadata明确REVOKE不读取旧source/native Goal body，原source和初始native Goal的屏障命中0。独立页面6例另有26断言、每例1boot×20assets，错误key与错误旧Release均为valid SHA重签200仍拒绝；晚POST之后新身份／connection边界不发旧GET、不重发POST、不画旧scope。身份变化通过明确本地fault injection完成，未称为可见身份切换或native操作；正常接续按钮使用真实可见控件。全部原始requests/actions/assets/sql/proofs在ui和ui-adversarial目录。

**失败历史保留**：初f7候选backend48P2真实F、custom6P4F（2真实private projection F＋2独审误断言409而合同400的夹具F），及UI4P完整原字节在 /tmp/text-continuation-independent-final-20261012/round1-original。14be候选72P原结果、R8真实2F、terminal第一轮克隆request_key唯一约束夹具2F在 /tmp/text-continuation-independent-final-v2-20261012；optional UI首轮6夹具F（在加goal barrier规则前先checkout，TEMP view缺失；隐藏login不能当可见身份切换）在 optional-ui-first-original，修/tmp后6P。此轮80不覆写或相加旧轮。完整文件散列与路径见 history-manifest.json。

原执行工具故障原文保留：`exec_command failed: CreateProcess { message: "Rejected(\"Failed to create unified exec process: exec-server transport disconnected\")" }`。该次/tmp准备命令和后续patch未执行，后以同原工具只读pwd确认通道恢复；这是transport故障，不是自动审批拒绝，没有更换环境/工具绕权限。

**边界**：只可称这些合成、精确已接纳旧SQLite的有限cold接续/NoModel实际Worker与离线页面通过。真实客户旧库迁移、PG、Windows、native browser、真实／付费模型、人工语义、完整P-A/P-B、远端CI、其它源实现／schema／operator变化均NOT RUN或不支持。没有重试旧取消精确candidate-install竞态、CI Forbidden或已知浏览器拒绝路径；没有部署、凭据配置、权限扩大、main/core/强推或向外部人员发消息。本审阅有限范围无未解决实际FAIL；root独立广回归／最终普通开发分支push仍由root完成。
