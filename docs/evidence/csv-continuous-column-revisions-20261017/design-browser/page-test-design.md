# 连续CSV列修订：最小实际页面测试设计

只读审查WIP csv-goal-revision.js、csv_column_revisions.py及接入点；root为唯一产品写入者。本轮未运行产品、测试、PG、原生浏览器或模型。以下是待冻结后的合成API/完整产品DOM JSDOM工程门设计，不是已经完成的验证。

## 已核合同与首要风险

连续修订复用同一csv-goal-revisions API和原CHECK/Release/原实例CAS控制器，新namespace为csv-column-revision.v2。context绑定当前已采用父Release、effective fingerprint、spec revision、Goal、column、graph、权限与实例revision/data_version；只允许保持当前Goal或显式保存其下一版本，资源材料不可替换。新effective spec从父n到n+1，保留root candidate generation。隔离CHECK可读父SOURCE，普通新business instance仍不能从该SOURCE创建；递归父链有循环/有限深度边界。

UI对已采用版本新增“基于当前版本再次修订列”，新cycleRelease和原key history保留；未决sending/UNKNOWN/accepted-read-error不得被next覆盖。父列由ctx.parent.column冻结，KEEP不应重新derive graph；可选Goal编辑仍需真正打开原卡、明确保存。后续复用现有完整JSON重鉴权恢复，三确认框重置和unknown原键GET。

最容易假通过的地方：夹具v1 amount=30、v2 quantity=5，v3回amount又等于30。不能仅断言页面含30；必须证明新queue Run/typed AppRun、原实例结果版本3、v3 Release和本次contract绑定，且新人工状态PENDING，没有借用v1结果或人工接受。

## 最小五个完整API/JSDOM用例

用adopted(env)直接准备真实v2+旧Run，加载实际产品HTML/CSS/所有脚本，用既有TestClient/RPC和NoModel Worker；不另造假的entry或API业务数据。

| case | 用户操作与核心断言 |
|---|---|
| keep-three-returns | 目录打开当前quantity/v2实例→明确next→只读context→quantity固定、选择amount→preview、CHECK、version、Release、adoption、CAS逐步显式确认。分别在preview受理未CHECK、version批准未commit、adoption批准未CAS时离返，同一case串三阶段；每次完整GET JSON、冻结列和新确认均严格核对。完成新spec3/instance revision3/result_version3 amount30/PENDING，冷页面从目录只读找回旧/新结果。 |
| explicit-next-goal | 明确next后点击真正Goal编辑入口，保存同卡Goal v3，再回原实例进行完整重验/保存/采用/新Run。证明Goal v3和spec v3分别冻结，原Goal v1/v2及旧Release/Run保留。KEEP case必须零Goal PUT且版本仍2；不能由程序伪造保存或自动升级Goal。 |
| lost-check | CHECK POST实际202后hold/丢交付，离返后原key锁定；next/reset和再次CHECK不能建立新意图。显式GET原checks/key恢复，然后实际Worker到PASS，继续完成同一链。preview/CHECK/commit等双击只一个接受POST；不凭Worker.once返回值断言完成。 |
| lost-cas | 原CAS实际200后丢交付，目录回读已见新父v3而原intent仍UNKNOWN，不能由已采用摘要替换未决恢复入口。仅GET原实例精确history证明原approval/previous/target/revision/data/runtime，0第二次commit POST；恢复后新Run正确。再点next只读取下一轮context，证明新key绑定当前v3父而非重用v2 key，不必扩展执行v4。 |
| late-scope | 在一个有界case分三段hold实际响应，分别跨项目、实例和账号ABA再返回；旧proof/列/批准不能填入新选择，旧回调不能发原项目的下一GET/POST。返回原scope显式按原key GET恢复；另一个实例用root原Release创建真实业务实例，不能绕SOURCE禁止随意创建v2 business instance的合同。 |

不必把所有相邻故障组合成矩阵；既有三阶段测试工具可复用，但oracle必须来自完整GET，不可再把adoption POST最小提示与GET完整批准比较。

## 必需的原始证据oracle

- 三阶段导航：保存离返前完整GET回执，并绑定POST hint的id/fingerprint；新proof中的当前stage对象深等它，preview/context父信息同时正确。确认框原来可先勾选再离返，返回后必须未勾、提交禁用；字段选中值quantity→amount且已冻结。
- freshGET顺序：以preview接受后的第二次GET/context为起点，到下一显式POST为止，每条均为成功GET；包含原preview/key，后阶段包含CHECK、version批准、live批准、Release与adoption完整GET。该段0POST；下一POST的原key或批准fingerprint及路径精确正确。不要用全trace some(GET)作离返证据。
- 连续父版：context.parent.release_id/fingerprint/effective_fingerprint/spec_revision/column须等实际v2保存回执；新preview spec_revision3，manifest/action/action_binding revisions都3；ctx.goal_mode明确KEEP_ADOPTED_GOAL或EXPLICIT_NEXT_GOAL。父列必须quantity，不可回退到root amount。
- 新结果：GET新Run与typed ledger相互绑定，column amount、sum字符串30、result_version3、新Release、原instance/runtime/app身份，实际operation receipt也指向该Run。旧v1/2数据、合同、owner seal和Release按原JSON保持，新Run owner PENDING。不要把数值相同当作来源相同。
- 写入边界：next、导航和cold reopen不发POST/Goal PUT；continuation context不得发graph/derive，原canonical graph不被覆盖；只有明确步骤才能写各原批准/运行。对原行集合逐字节保留以及Grant/principal数量不增可复用现有API断言。
- UNKNOWN：请求body/key逐字段冻结，回切后GET恢复，最多一个POST；失效、403/409或错误parent/Goal/版本不能清原键后重发。仅确证NOT_ACCEPTED/TX_ROLLED_BACK或既有terminalCHECK规则才可明确新意图。
- 报告全部后台HTTP>=400；为了完整页面加载将同SHA protocol evaluation assets和import gold明确列为依赖，或如实保留缺资源400，不能称所有HTTP通过。根node_modules链接指向现有只读安装，避免旧jsdom probe再SKIP。

## 静态注意与后续独审

当前新API测试有result[run_id]使用点，需按实际jobs.inspect_job返回id合同核对；这是测试源码提示，本审查未运行，不能作为产品失败。MAX_SPEC_REVISION=8等上限可由API层少量负例证明，不必在页面把v3一路跑到v8。父链权限/版本/材料/封印保持现有门，不因页面便利而放宽。

冻结后独立审查应新建对应SHA源码快照、标记实际src/tests/schemas与额外资产哈希前后、保存API/DOM/SQLite/log/JUnit原件；精确区分unique case与重复执行、FAIL/SKIP和修正后的targeted rerun。原生browser、PG、真实语义/模型/CI不在本设计通过范围。
