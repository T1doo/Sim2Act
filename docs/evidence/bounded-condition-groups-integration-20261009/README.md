# 有限 all/any 条件组合：开发分支限定集成

经父任务核验及明确授权，在 `dev/f1-foundation` 从
`8c572154ff72ac61a506fb9313cb631996e76df7` 正常 fast-forward 集成候选
`f540194b334f6ccce06b7548e7a0d36636d6fbc1`，未操作 main。
实际 merge-base 为开发基线。本轮执行时 HEAD=f540194，之后仅提交本轮说明与证据。

最终源码/测试冻结 `79b119b616a20d9347b5677c0d58fbbbe18127c8` 与产品冻结
`f4bf46355e009617775c056540fc45fcc4512a77` 的 src/Schema 字节完全一致；两者唯一
差异是新Python页面测试检查总数22→24。相对原功能 eeb368ccb338429637f271bf57bdb2781245b976，
后端和Schema完全不变，产品仅四叶按钮通用锁/上限赋值顺序修正。
`baseline-verification.json` 及页面加载哈希核对336个源码/测试/工作流/依赖文件。

## 前置核验与独审归因

初始实际 HEAD=f540194、候选分支、工作树干净；正常 fetch dev 与候选并核对远端。
无merge/rebase/cherry-pick/revert状态或事务锁；空 `.git/codex-index-refresh.lock`
原样保留。没有活动Git、pytest、Node或PG进程；已有僵尸进程未触碰。团队只有root
活动，先前独审agent已完成，本轮唯一写入者。workspace未提供AGENTS.md或本地skills；
读取运行说明、候选范围、实际测试及原独审，不假定旧环境资源共享。

[原独审 FINAL_REVIEW](../bounded-condition-groups-20261009/independent/FINAL_REVIEW.md)
结论LIMITED_PASS：另写21个SQLite/API/Worker病例在eeb通过，实际旧8c源码四个组
输入负对照预期HTTP422失败；最终产品另写16个磁盘加载DOM/JS检查通过，旧eeb按钮
负对照预期失败。73个src/Schema匹配最终冻结。独审没有执行PG、实际HTTP、旧源码
升级或原生浏览器；本轮作者回归不改变这一归因，不写作独立PG/HTTP验收。

## 必要集成回归

SQLite → PostgreSQL 串行，只运行11个受影响实际页面与两份实际旧源码升级，共13例。
两后端均13 PASS、0 FAIL、0 ERROR、0 SKIP；日志、退出码、JUnit与逐例证据保留，
精确耗时及来源见 `test-summary.json`。没有无目的全量重跑或新测试放宽。

每后端页面共199项driver检查：新3个条件组合页面、原6个单条件页面与原2个有限
节点组合页面，实际loopback HTTP、产品HTML/JS、jsdom及持久Worker。新3页各24项
明确检查四叶时添加禁用、删除恢复启用、编辑清除证明/确认、未决原键接受丢失后
同键恢复、实际执行/跳过与冷页面读回。加载HTML/JS逐字匹配冻结源码，见两个
`*-page-source-verification.json`。这不是Windows/Edge原生验收。

每后端两实际旧源码升级分别从5a5543c902fbb78dd91c28c98386af51fb24dd67与
1b65e94ebd81c1e31091b3078b8223328b726294运行原驱动创建旧计划/实际执行，当前源码
拒绝旧图锚/执行证明与旧确认，保留旧历史、原始JSON存储字节和停止控制元数据；
新派生/新计划必须新精确确认并实际执行。逐例 `upgrade-proof.json` 保存所有原断言。
没有宣称最近8c源码数据库升级、自动迁移或完整迁移验收。

Ruff、53源文件Mypy、两份JS语法和产品/测试/手写说明diff检查通过。已有
FastAPI/Starlette httpx弃用警告原样保留。本轮无失败；原候选的开发失败/测试计数
修正/负对照记录仍在原证据目录，未修改、删除或计入本轮通过。

Python3.12.14、Node24.19.0、私有jsdom30.1.2。模型适配器调用即失败，LIVE=0 /
SIM2ACT_LIVE_ENABLED=false。复用前先实际核对旧archive与依赖路径存在；未安装新依赖。
新建自有PG17.9 network-none容器、空listen_addresses、无映射端口、专用Unix socket
及合成库。结束后核对所有者label/完整ID与测试对象归零，仅移除本轮容器/匿名卷，
保留原日志、数据库夹具、archive、依赖及镜像；见 `pg-container.json`、`cleanup.json`。
`commands.txt` 保留限定复现命令，PG仅指向自有测试库，未更改真实凭据/网络安全设置。

## 保留未验收

PG resources-history / 全量及探索超时仍OPEN，HTTP200损坏响应提示限制保留。
Windows900 / Edge240 / Node150 未验收，所有原断言/等待上限不变。
语义UNKNOWN、owner PENDING、真实材料和真实模型授权待定、整体NOT_ACCEPTED；
PROJECT PENDING/BLOCKED_PARTIAL、LIVE=0、发布关闭。
限定集成不签收完整F2-T04/P-A/P-B或项目，不强推、不改main、不部署。
