# AppManifest/AppRun R0 bounded agent 离线切片 / 2026-10-06

基线 `6cbf47f56a8b75e3527aac3922441f26dd9344c3`，工作副本 `/workspace/Sim2Act-pb`、`dev/f1-foundation`。本轮父线程授权仅本地实现/提交/验证；没有 push、CI、模型请求、V5原文外发、外部发布或额外导出包。原 work 树保持 `6f688e4dd80b5c81d41aecde90e360d3629f9c21` 干净。

## 实际范围

原 V5 §4 的源任务→输入输出/工具/验证记录→新输入应用、§5/6 同一编译与运行器、§12 引用与语义区分，见 [事前接口与验收](../../F2/BoundedAgentOfflinePlan.md)。没有新增孤立转换器 API/任务表；沿 `compile_preview`、内部 Release/Instance、持久 Worker AppRun prepare/compute/commit、既有 Operation 和 typed internal results 实现单 `intern.agent@1` 分支。已有 `task_extractions` 保存独立提取标记，不新增DDL。

最小应用目标是字面证据检索：自由 MD/TXT + 非空明确检索词→命中行引用/定位/source revision/hash。可信 `source.literal_evidence.v1` 只证明这一明确的非语义目标，所有结果 `semantic_status=UNKNOWN`；语义义务推断目标拒绝，不称自由Markdown规范理解/模型自主生成/完整P-B或AT10成功。

实际零 provider 请求；离线 Replay 两轮，一次真实 `resource.read`，下一轮收到真实读回执，再返回严格JSON。使用现有 F1 `intern.system.v1`原提示及 `parse_response`，仅提供 `resource.read` schema。拒真实adapter/subclass/fallback、未知/写工具、跨材料读、未读就final、额外round、截断/非法JSON、输出与预算越界。provider请求0与Replay轮数分开记录。限制：source≤4096UTF8、≤64行，term≤80字符、≤16命中；2轮/1工具/0repair，完整请求≤16000UTF8，保守完整body+输出byte envelope≤32000，输出≤4096UTF8（1024×4，**不是实际tokenizer用量**），30秒。合法资料也可能因输出envelope不足而拒绝，未保证所有边界输入均能完成。

权限只核 owner+已有独立 app runtime 的现有read交集，项目runtime不兜底；既有同项目app_draft锚定该runtime。多个候选复用同一runtime属于同授权域，不能称逐app身份隔离。产品创建/提取/执行不新增 Principal/Grant；测试准备显式合成资源/read授权后才计数。结果仅现有内部typed ledger，没有artifact.save_text/project writer。

来源锚点：独立accepted Run fingerprint→queue binding/input→AppRun→instance record→精确VERIFIED Operation/intent/receipt→冻结Release/批准记录→当前source字节/hash/授权。协议消息重新严格执行/验证，数值类型以canonical fingerprint区分；整个receipt身份/状态/shape重建。提取marker固定原请求指纹及accepted_name，不能仅改候选/provenance/hash、把另一真实成功source替进来或剥离来源。旧来源撤权/退休后仍拒绝，尚无来源退休后独立运行政策。

## 实际验收与未测

`source-a.md`/`source-b.md`及手工 `independent-gold.json` 在产品实现前冻结；独立审查已核对全部原行引用。gold仅在tests，产品运行时不加载gold。实际正链为 source app的AppRun→已验proof→提取新材料manifest→新内部Release/Instance→冷Store+既有Worker运行→不同引用结果/版本/幂等冷读；不是旧结果回放。

最终精确结果见 [results.json](results.json)。历史阶段日志全部保留：最初SQLite全回归438PASS24SKIP是pre-hardening；SQLite `*-final` 449PASS24SKIP也早于最后来源请求锚点闭合，不冒充最后源码。PG初专项33PASS、后专项44PASS也为中间版本。最后源码SQLite全450PASS24SKIP2warnings180.43秒、PG全473PASS1WindowsSKIP2warnings537.72秒；专项SQLite44PASS1PGSKIP、PG45PASS（包含最低CRUD角色/禁止DDL），独立44PASS1PGSKIP20.18秒。ruff/mypy23通过，全部独立hash匹配。

独立审查实际复现并修复：receipt状态/op/instance/release/输出FP/artifact refs篡改被接受；protocol计数字段float/bool等值被接受；独立提取请求FP未检查及协调替换真实source被接受。补强中出现冻结Release无name导致KeyError，修为独立marker accepted_name，保留失败日志。中间空protocol问题只有静态发现，复现时已修，不能称曾实际接受。复现脚本/独立报告保存于本目录。

无新UI/HTTP入口，本轮未作新增浏览器验收；既有Edge38不是本功能证据。Replay不是模型自主规划、语义理解或LIVE成功；目前provider预算仍0。Win11/F1正式签收、自由规范语义提取、P-A/完整P-B/AT10、正式发布及真实模型能力仍未完成。只本地commit，等待父检查决定push/CI。

精确产品源码本地 commit：`3e27ad9b55b3493da2dc403461916589427d4a2d`。最后源码SQLite全450PASS24SKIP2warnings180.43秒、PG专项45PASS77.10秒、独立44PASS1PGSKIP20.18秒；三个独立断言脚本exit0，源码/fixture/gold hash全部与最后文件匹配。最后PG全回归473PASS1WindowsSKIP2warnings537.72秒已完成；两警告分别为既有Starlette/httpx与旧local_task_retirement的Pydantic alias提示。

候选和Replay回复由离线调用者显式提供；不是模型自动生成manifest。源只接受明确字面目标的初始INTERNAL_APPRUN，不能泛称F1已完成任务提取均支持。默认Worker拒绝agent的非Replay adapter；跨进程自动恢复Replay/中途回复持久化未实现，冷Store验收不代表这些恢复场景。没有新增浏览器入口。

专用PG容器sim2act-agent-offline-pg-20261006已移除，127.0.0.1:32771实查关闭，pytest合成临时目录按托管保留。source-hashes.json最终只列106个受版本控制的源码/测试/配置文件，排除初步工作目录索引中的安装/临时产物；所有产品文件与精确本地源码commit一致。证据仅留本repo，未上传额外目的地。

归档失败的原pytest日志含3行尾空白，保持原始字节；证据专属.gitAttributes规则冻结.log字节并禁其空白风格检查，代码/文档仍正常检查。此收尾仅证据配置，执行源码/测试/fixture与3e27ad9零差异。
