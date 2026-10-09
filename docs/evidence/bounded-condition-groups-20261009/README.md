# 有限 all/any 条件组合：限定候选证据

独立分支 `dev/bounded-condition-groups-20261009`，开发基线
`8c572154ff72ac61a506fb9313cb631996e76df7`。原功能冻结
`eeb368ccb338429637f271bf57bdb2781245b976`，最终产品/测试冻结
`79b119b616a20d9347b5677c0d58fbbbe18127c8`。后续仅文档证据提交；未合并 dev/main。

依据 [V5 产品 §5.3](../../平台产品设计.md) 与 F2-T04 的“有限逻辑组合”。
原单 eq/in/exists 谓词无法表达同一步的输入开关与已核前驱 count/sum 同时成立、
或任一成立。本轮在已有三步与四节点 CSV 执行链补充二至四项平面 all/any；
不是重复已有展示、工具或外围检查。详细范围见
[实施说明](../../F2/BoundedConditionGroupsPlan.md)。

## 行为和约束

保留单谓词 v1 字段及回执，组合计划标记 typed-conditions.v2。所有叶子先经过
原 schema 类型、直接前驱、常量与来源预检，运行全量求值后归约；不会短路掩盖
缺失 eq/in，exists 缺失仍为 false。前驱跳过优先，缺失输出不读取、不伪造报告。
每叶观察与判断进入持久决策指纹，冷恢复重建和篡改拒绝；既有权限、Grant、版本、
锁、租约、fencing、预算不扩大。未新增表、API、工具、模型请求或业务写入。

原页面可选单个/全部/任一与有界增删；编辑清空已保存证明与精确确认，未决原键
恢复锁住控制。独审发现 legacy 四叶按钮禁用被通用锁循环覆盖，原第五叶守卫
仍有效；f4bf463 调整赋值顺序，并增严格上限/删除恢复检查。79b119b 仅同步新
测试检查总数22→24。最终与 eeb 的336个冻结文件只有这三个文件变化，后端与
schema 字节全部不变；见 `source-freeze.json`、`final-source-freeze.json`。

## 验证与精确归属

日志、JUnit、退出码、页面逐例结果及实际加载 HTML/JS 哈希均在本目录。
`test-summary.json` 和各 `*-source-verification.json` 核对真实加载字节。
SQLite → PostgreSQL 串行运行，未修改原等待/超时、未全量、未CI、未真实模型。

| 范围 | 精确冻结 | SQLite | PostgreSQL |
| --- | --- | --- | --- |
| 新29后端 + 新3页面 + 必要旧DAG/分支/组合/契约/升级，共180 | eeb368c | 176通过，4既有PG角色例跳过 | 180通过，零失败零跳过 |
| 最终受影响11个HTTP页面，199项driver检查 | 79b119b | 11通过，零失败零跳过 | 11通过，零失败零跳过 |

两份实际旧源码升级（5a5543c902fbb78dd91c28c98386af51fb24dd67 与
1b65e94ebd81c1e31091b3078b8223328b726294）在双后端均通过：旧历史和原始JSON
存储字节保留，旧证明拒绝，新执行须新精确确认。逐例 `upgrade-proof.json`
保留原断言结果。本轮没有宣称最近8c源码数据库升级或完整数据库迁移验收。

新后端病例包括八项真值实际Worker路径、非法组合先拒绝无写入、缺失叶子不短路、
四叶/exists/in、aggregate组合冷租约接管及旧worker拒绝、执行/跳过决策篡改、
撤权优先及独立末端输出保持。最终页面实际 loopback HTTP、产品JS、jsdom 和
持久Worker，检查同键丢失接受响应恢复、修改清除确认、实际执行/跳过与冷页面读回。
Node24.19.0、jsdom30.1.2、Python3.12.14；模型适配器调用即失败，LIVE=0。

独立复核在 `independent/`，另写21个SQLite/API/Worker病例与实际旧8c源码四个
组输入负对照（均预期HTTP422失败）。最终另写16项DOM/JS上限、删除恢复及未决
原键锁定检查通过；同driver在eeb按钮缺陷处预期失败。独审结果 LIMITED_PASS，
不代签作者PG、真实HTTP、升级或整体F2。number叶子仅预检/纯决策检查；实际CSV
注册输出无浮点number端口，独审没有宣称这一实际路径。

Ruff、53文件Mypy、JS语法及手写产品/测试/说明diff检查通过。保留原始证据的
空白诊断另记 `raw-evidence-whitespace-check.json`，不改写失败日志/JUnit。
FastAPI/Starlette已有httpx弃用警告原样保留。

## 开发失败与保全

`development-history/` 保留早期完整日志/XML和失败JSON：先前两个新测试预期
错误（400/409与Grant字段名），随后group编辑器改变旧driver第一按钮选择导致
两例失败（调整产品按钮顺序，旧断言不改），随后新driver未更新重计划指纹导致
三例失败（修正新driver）。按钮修正首轮最终UI为8通过/3失败，三例页面driver
各24项已全部PASS，Python旧总数22断言失败；更新新测试为24后最终重跑。
这些结果不计入最终通过，也不隐藏为成功。原负对照失败是预期敏感性证据。

自有PG17.9容器仅network-none、空listen_addresses、无映射端口、专用Unix socket
与合成库；创建/删除随机test schema，结束后按所有者label和完整ID核对并只移除
本轮容器/匿名卷。清理与远端检查记录另列；不修改凭据或安全网络配置。

复现按本仓库 `tests/test_csv_dag_upgrade.py` 准备两份实际旧源码archive，设置
SIM2ACT_UPGRADE_OLD_ARCHIVE / SIM2ACT_UPGRADE_CORE_ARCHIVE；私有jsdom置于NODE_PATH。
`commands.txt` 给出限定命令，PG只指向自有隔离测试库。保留临时完整数据库/日志，
不把数据库或临时身份令牌上传Git。

## 保留未验收

PG resources-history / 全量与探索超时继续OPEN，HTTP200损坏响应提示限制继续保留。
Windows900 / Edge240 / Node150 未验收；本轮HTTP/jsdom不是原生浏览器验收。
真实材料、真实模型授权、人工签收、通用运行器与完整F2仍未完成。本切片不签收
完整F2-T04/P-A/P-B，不部署、不强推、不改main，发布关闭。
PROJECT PENDING/BLOCKED_PARTIAL、semantic UNKNOWN、owner PENDING、整体NOT_ACCEPTED、LIVE=0。
