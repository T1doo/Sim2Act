# 共享预算与安全状态恢复：本地工程证据

2026-10-06，起点 `fd259942b85cc2d67bef184d7afb10fb682974fd`，既有 dev/f1-foundation 工作副本。范围事前记录于 [计划](../../F2/ProtocolSharedBudgetRecoveryPlan.md)，实施与失败另记 [Log](../../F2/Log.md)。本轮仅本地提交；无 push、CI、LIVE、业务外发、产品 Principal/Grant 或部署。完整 P-B/真实模型语义不在验收范围。

## 实现

source/extract/cold 在同一数据库按固定 mode 共享预算；不是每 Run、owner、project 或文件独立14。显式 controller 初始化 offline/live 默认0，只有 test_only 合成夹具可给 offline14；LIVE始终0且拒绝。新增 pools/slots 通过原显式迁移创建，API不建表。Attempt STARTED、slot和计数短事务原子预占，实际回执/usage和双方账目短事务结算。未知、不完整、超额或双账不一致保留占额且停止；新阶段、新 Run、新 sidecar、冷进程不能退款或重置。预算审计结合 genesis/reserve/settle/halt 事件和当前实际 Attempt。此有限防篡改不承诺抵抗可改写全部数据库与所有历史事件的管理者。

恢复 HTTP 接口只核查当前权限、源依赖、版本/fence和持久证据，返回状态元数据且 provider_requests=0。完整结果保持等待原 review；严格无发送证据可 PAUSED；STARTED/未知停止，收到响应但没有原子 completion 明确续跑未实现。不重发、不补答案、不造证明。协议 expired Run 与旧 F1 自动 recovery 分开，每 Run 独立 project→Run→pool 事务，释放 pool 后才处理下一 Run/常规 claim。

单 in-flight 为保守安全取舍：另一调用观察到 STARTED 会 sticky halt，即便原调用后来提交实际响应也不清旧 halt。本轮证明上限和未知停止，不证明并行吞吐或自动恢复可用性。

## 测量和独立审查

最终合并全量回归结果另存 result.json；仅最终锁修复和永久测试冻结后的结果用于本次签收。

- [预算独立报告](independent-budget-review.md)：九个真实复现的预算/篡改缺口及修后拒绝证据。预算五文件冻结认可；其旧 recovery/db 哈希明确是被锁修复替代的历史快照。
- [恢复独立报告](independent-recovery-review.json)：真实PG先复现40P01，拆分事务后同 schedule0死锁/0重试/0provider；永久恢复+并发15PASS23.58s，SQLite14PASS1项PG-onlySKIP9.52s。修前缺陷及随机项目顺序导致的测试夹具首FAIL保留。
- 跨进程末槽+五崩溃点：真实PG6PASS26.70s；两 owner/project 在13已消费后争末槽只再发送1次。DB占额后、sidecar后、发送中、返回但未DB记录、双账结算但未completion分别保留真实崩溃出口；冷 Store/进程、新 Run和新 sidecar无额外发送。
- 两表显式迁移、API无DDL、既有角色CRUD/DDL拒绝3PASS1.50s：其中API构造项显式SQLite、两角色检查真实PG。
- [DOM同序及父版本对照](dom-summary.md)：旧完整704PASS26SKIP1FAIL保留，确切原 interleaving UNKNOWN。父完整599PASS25SKIP；旧helper窗口两版本受控实际回执可复现。两测试文件仅等待同 IID/RID实际终态/表单/非busy，保留poll和12秒timeout；隔离修后完整706PASS26SKIP。孤立PASS不顶替旧失败；合并结果另列。
- 最终静态 Ruff src/tests PASS、18修改Python文件format PASS、mypy31源文件 PASS。冻结源/测试哈希见 final-source-hashes.json。

上一阶段131项“PG专项”实际91PG、40SQLite；旧报告保留，本轮 jobs fixture 已接真实PG。PG配置全量仍包含显式SQLite/纯单元测试，不能把总PASS数全部叫真实PostgreSQL；跨进程/并发/权限专项独立标明后端。

## 保留失败与边界

原DOM完整失败、预算缺口、PG40P01、root恢复夹具错误（material字段/返回tuple解包）及独立并发夹具随机排序首FAIL都保留安全日志/hash。修前完整结果使用 pre-lock-correction-hashes.json，不冒充最终冻结版。日志归档移除DSN与行末空白，原始和归档SHA另记。

固定 MockTransport响应、有限四包 exactJSON oracle只证明工程边界；书生/Intern真实模型语义未验，真实请求0/LIVE预算0。完整 continuation、正式AppManifest/Release、原生/视觉、本轮Windows及完整P-B/F1/Win11/AT02未签收。此恢复入口无外部网络/答案写入。

## 清理与交付

最终回归完成后核对owned PG test schemas/roles并删除仅本轮容器和含凭据临时状态；清理实测记录在 result.json。不会更改旧工作树或推送远端；本地交付精确commit见父线程回执。


最终签收：SQLite **741 PASS / 34 SKIP / 0 FAIL**（637.12s）；PG配置全量 **774 PASS / 1 SKIP / 0 FAIL**（1475.06s），均775 collected。两次最终退出0；PG全量不是每项实际PG的宣称，后端专项另列。最终源码哈希不变；owned test schemas/roles清理前均0，owned容器及私有凭据状态已删。见 [结构化结果](result.json) 和 root-log-hashes.json。只本地提交，无 push/CI/LIVE；旧失败及未验边界保留。


归档格式检查收尾：两份原失败日志含行末空白，提交版本仅移除行末空白。独立报告保持原始审查SHA不改；`archive-whitespace-normalization.json` 映射其原归档SHA到当前提交日志SHA，失败内容/数量不变。产品、测试及源码冻结hash未变。


2026-10-06 唯一授权 Windows CI 实际终态 **FAIL**，source `c3b0f3c37ed53207d59535dc187f95ca89f80f77`，run [37499515105](https://github.com/T1doo/Sim2Act/actions/runs/37499515105)/job112392601026。原Setup显式PG迁移和应用role smoke SUCCESS；Ruff PASS，Windows mypy在model_budget fcntl给5个attr-defined错，pytest/JUnit未运行，不能声称新表CRUD/共享并发Windows通过或列pytest平台SKIP。浏览器step因失败跳过，此次无Edge38/agent33/registered29复验；新protocol/recover无原生UI验收。Report/Cleanup SUCCESS，owned API/worker已停、temporary PG server stopped、原JobRoot清理完成。原runner/权限/helper/超时/上传范围未变，真实请求0/LIVE0。

本地Windows-target mypy复现同5错，最小修复model_budget两处锁平台判断为sys.platform=='win32'（保留msvcrt/fcntl原锁API）。修后Windows目标mypy31PASS、Ruff/format PASS、SQLite预算/恢复54PASS10.85秒；这是本地静态目标+POSIX实际运行，不伪称Windows runtime。源码变更待独立只读审查，修前/修后安全日志及CI终态见windows-ci-result.json。用户本次只授权一次CI，下一次普通push修复会触发第二CI，因此修复仅本地保存，待父额外授权；不自动rerun，不改失败历史。


追加唯一原CI37500554573/source18fbae4175477d85eb2fd620905e9d4adcf5096b终态FAIL：645PASS127FAIL3SKIP，775 collected，315.83秒。真实WindowsRuff/mypy31成功；同源775收集顺序映射原-q进度且匹配JUnit总量（非下载JUnit逐case明细）：预算锁19PASS含native锁竞争；schema3PASS，其中2真实PG应用role新表CRUD/DDL拒绝，1显式SQLite API无DDL。6跨进程/崩溃及1三Run并发在oracle加载前FAIL，不能签Windows并发成功。公共/jobs PG fixture路由661项为533PASS127FAIL1SKIP，另114项为112PASS2SKIP；这是fixture路由，不将全部645称真实PG。3SKIP为registered-generation可选jsdom两个模式、旧生成HTTP DOM jsdom项；浏览器step因工程失败跳过，当前两CI均无旧Edge38/agent33/registered29复验，更无新protocol/recover原生UI验收。Report/Cleanup成功，owned API/worker及PG server已停，原jobroot清理完成；Windows残schema/role未独立计数。两次失败保留，LIVE0。

127FAIL均同Registered evaluation asset changed。真实隔离Git core.autocrlf=true checkout4个固定evaluation JSON，四个CRLF/PIN失配，loader拒绝，匹配CI错误；CI未导出四原文件字节，换行归因来自此Git复现。最小.gitattributes仅两行使该四资产-text保持原bytes，原PINS/gold/hash校验未改；同checkout四原SHA/loader通过，独立四单字节篡改均拒绝。独立补丁审通过，attrs SHA76c84a011a591088588f448560f3442283d044aa8b98d8cd9c416c842acb3bad。SQLite相关79PASS2个PG-only角色SKIP46.14秒，非Win签收。追加一次额度已用完；byte修复仅本地提交，第三push/CI待父授权，不改runner/权限/上传范围。结果见windows-ci-second-result.json。


口径定点更正：WindowsCIPlan此前把所有registered HTTP DOM宽泛称SQLite，现按实际fixture细分。scripts/windows_browser_ci.py与scripts/agent-ui/fixture.py都固定SQLite，因此原Edge/agent/registered native fixture及两个direct generation DOM为SQLite；旧test_registered_run_generation_http::test_real_http_dom_generation_entry_and_lost_receipt依赖公共PG env，此次1项SKIP也归PG-selecting fixture列。因此实际路由为533PASS127FAIL1SKIP（661 PG-selecting），112PASS2SKIP（114其他），非534/111。三个skip属于可选Node/jsdom前置，未单独导出JUnit具体skip reason，不伪称已实测Node缺失或jsdom缺失。原-q定位的127个FAILED nodeid与CI完整failure summary逐一完全一致，定位证据自洽；仍明确不是独立JUnit逐case下载。新表2真实PG角色检查通过不等于预算6process/1concurrency已过，后者本轮均停于oracle PIN拒绝。
