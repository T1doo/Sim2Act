# 有限文本无旧内容逻辑复用：候选8独立 LIMITED PASS

2026-10-12，独审`/root/text_logic_review`。审查对象是`dev/pb-text-logic-reuse-20261012`上基于`e2b856bb453fc74452583fa10843148758e2d9b9`的未提交候选8；不是已提交/远端CI的SHA签核。冻结清单SHA256：`8df8bb8f4f3b4336495af514eb4760ef3ecc0d38de10e01e7000ba71ba50dc61`。

**LIMITED PASS：** 本轮授权的有限TXT/MD字面逻辑主线及普通API/SQLite/NoModel Worker/实际TestClient HTTP可见JSDOM链通过。41项全部PASS、0 FAIL、0 SKIP、exit0，另2个纯目录回归PASS。四条严格正常页面链都完整通过；没有放宽资产、可见性、原key恢复或私有单元屏障断言。不是完整F2/P-B/AT-10、真实模型或人工语义签收。

## 精确执行与源码完整性

| 独立测试组 | 实际结果 | 退出码 | 时间 |
| --- | --- | --- | --- |
| 32个新作者测试 + 原独立API9项 | 41 PASS / 0 FAIL / 0 SKIP | 0 | 165.57秒（pytest164.00秒） |
| 默认catalog API及无socket synthesized catalog DOM | 2 PASS / 0 FAIL / 0 SKIP | 0 | 5.06秒（pytest3.58秒） |

两个测试组各自执行前后均核对冻结清单全部378个src/tests文件，零缺失、零hash变化。还独立比较候选7实测after表与候选8冻结表：src逐文件相同，仅`tests/test_text_logic_ui.py`与`tests/text_logic_ui.cjs`变化。没有跨候选拼接成一次全绿；本签核的41+2均来自候选8。

完整命令、退出结果、原始stdout/stderr合并日志及逐项JUnit：`final41-command.json`、`final41-result.json`、`final41.log`、`final41.xml`；小回归对应`catalog2-*`。每组1个既有Starlette/httpx deprecation warning，不影响退出；未安装/改依赖消除它。每轮前后源码哈希见`*-before-freeze-check.json`/`*-after-freeze-check.json`，逐项和UI汇总见`results-summary.json`，交付文件digest见`artifact-sha256.json`。

全部独审pytest/Node/runner已经结束；四个Node退出码均0、stderr均0 bytes；已向root明确解除src/tests编辑等待。不再启动额外测试或写产品/作者tests。root后续提交如改src/tests，必须重新对应验证，不能沿用此freeze。

## 四个正常可见页面链的实际证据

| 场景 | DOM检查 | 可见动作 | 实际HTTP资产 | CSS | SQL语句 | 原私有单元求值 |
| --- | --- | --- | --- | --- | --- | --- |
| valid | 13 | 29 | 40（2 boot ×20） | 2次真实取回并注入 | 2755 | 0 |
| authorization-lost | 14 | 30 | 40 | 2次 | 2755 | 0 |
| binding-lost | 15 | 30 | 40 | 2次 | 2755 | 0 |
| revoked-retained | 13 | 29 | 40 | 2次 | 2761 | 0 |

每页都由真实`/`、`/app.css`和18个产品JS的TestClient HTTP响应构建JSDOM，逐资产SHA256与冻结磁盘字节核对。所有交互前核可见、可用并真实触发按钮/输入/确认；没有调用DOM中隐藏入口或手写清单。每场景原source一次撤权/删除或撤权保留，新fresh Store的普通NoModel Worker恰执行一次，结果来自新Gamma输入和新材料的完整引用，不回放原Beta答案。

`authorization-lost`与`binding-lost`均证明接受后丢响应使用原key GET恢复，恢复期间不增加POST；每个明确授权/绑定命令仅一个POST效果。`revoked-retained`保留原content/hash单元但撤销权限，冷目录到新运行全段仍未求值这些私有单元。所有场景owner PENDING、semantic UNKNOWN、模型0，正式发布false。

每场景的完整DOM/动作/请求/资产/结果proof、Node原stderr/exit、原SQL及经过屏障的实际SQL均保留在`ui-artifacts/<scenario>.json`、`<scenario>-node-stderr.log`、`<scenario>-exit.json`、`<scenario>-sql.json`。SQL屏障同时附着API与fresh Worker；保护原resource内容/hash、原AppRun及生成Run私有字段/contract、原candidate、Release/approval快照、操作/intent、typed结果等真实SQLite单元，不是只查SQL参数有没有旧ID。

## 静态审查与实际保护范围

来源签发前沿用真实成功初始literal AppRun完整来源/授权/步骤/typed检查；签发后只核独立authority/seals、最小opaque source身份与盐化材料身份承诺，不重开原私有来源。新候选从固定canonical结构构造，标准goal、fresh app/action/runtime、单目标read Grant；没有复制原goal/term/引用/结果/自定义标签或原runtime权限。目标现有授权在绑定前核验，后续运行用当前user+fresh runtime交集。

新authority、binding及候选JSON的规范指纹比较实际挡住原三个单边bool/float污染；原独立坏proof/wrong Release/consent/key、任一binding seal缺失等9项均通过。新marker改写/删除、额外runtime Grant或token、logic不可逆撤销、当前目标/logic撤权、预算与expiry、同key冲突/原GET恢复、绑定事务回滚、最终typed写中expiry全回滚以及真实第64次写/第65次拒绝/原key仍读均在本轮对应测试通过。

冷目录使用无旧candidate/goal/contract读取的metadata模式；resource hash仅在当前授权门通过后读取。初始literal独立marker先排除CSV发现hint，发现hint只用于路由，显式打开仍严格核验。

新Release索引为闭集metadata对象；在commit_release同项目锁事务内双seal保存，和新Release/approval consumed一起提交。列表先load_draft及独立家族门，不能由损坏marker降级；仅检本app索引ID并先核公开Release身份/fingerprint metadata，再读取指定新snapshot，避免原全项目snapshot扫描。read_release对新家族严格核索引；任一seal缺失与索引插入失败回滚均已实测。普通执行/最终提交继续重验独立logic、当前目标bytes/hash及权限/预算，typed提交后且事务commit前再核，expiry失败不留下typed成功记录。

## 历史和本轮边界

候选3/4/5的独立红日志、XML和报告保留；候选7保持真实37PASS4FAIL，两项CSS资产缺失、两项BrokenPipe无完整DOM/new Run证明，根因UNKNOWN（当时Node原stderr未采集）不改写。候选8通过只能证明新harness完整链成功，不能倒推候选7的BrokenPipe原因。作者候选6中断记录由root保留，不计本独立通过数。

候选4误选的两个socket旧UI保留其真实P/F与`OUT_OF_SCOPE_EXECUTED_NO_ACCEPTANCE`分类；没有改写成NOT_RUN或累计为此轮通过。本轮没有socket绑定、native browser、PG/Windows、真实模型/付费、凭据/网络权限变更、旧源码升级、push或部署。仅本次/tmp隔离SQLite、现有MockTransport准备来源、TestClient/IPC JSDOM及普通NoModel Worker。

用户取消的精确旧/新候选安装竞态对照单独永久NOT_VERIFIED：本轮不执行、实现、变通或代签，不能用本轮冷Worker/权限成功关闭它。完整P-A/P-B/AT-10、人工语义/owner、PG/应用角色、Windows/native、真实设备崩溃、全旧源码升级、正式发布/部署和远端CI保持NOT_RUN。owner PENDING、semantic UNKNOWN、LIVE0、正式发布false。

在此有限scope及冻结源码内，没有剩余产品阻断；部署/发布/全平台或业务签收未授权、未验证，不属于本报告通过范围。
