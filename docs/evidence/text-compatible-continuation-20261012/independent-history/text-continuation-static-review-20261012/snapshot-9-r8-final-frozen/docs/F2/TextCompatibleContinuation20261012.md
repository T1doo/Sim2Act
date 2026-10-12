# F2-T08 已有独立文本应用的显式软件兼容接续

P2修复后基线df5f422174c4eeea96e5dd16c141dc0a4b36b3e6；root唯一仓库作者，dev/text-compatible-continuation-20261012。旧233实际软件65个Python（config除外）指纹7f464d1099210fe485bb08ef455267cadf9970d5d1a098b1d00253ee1ad0edee；a747/P2为66个Python指纹08334fd20f4b3187ca2d5350bff50ec8d24cff881c2f1abaad821bd692bf1d2a。原AUTH/BIND/task extraction/candidate/Goal及原data/history字节保持，不自动重签、不放松正常current软件指纹。

1. 只两已接纳精确旧软件锚的一个封闭literal文本家族，支持一次从原不可变Release接续到当前精确软件；不支持把已接续Release串接到另一软件或回退。固定operator/check/schema及声明式ABI不变；其它软件、字段/语义/数据迁移UNKNOWN拒绝。`text_run_checks`只加私有归档参数转交，原完整Worker证明/算子/oracle检查体复用，不重写执行器。正常AUTH读取仍严格current指纹。新源码须重新冻结自己的真实all-Python指纹，不用a747假充目标软件。
2. root用Git精确233源码的实际TestClient/正常Worker创建SQLite旧库，原source材料撤权/删除，旧独立instance已有typed v1。当前df5 API真实409软件不匹配且全旧DB行未变，见before-current-api.json。静态Git差异不能代替该运行或最终接续后冷Worker。
3. 只对本人/项目/目标当前user+fresh app runtime权限下所选一个现有instance显式预检。冻结appid/candidate/runtime/old logic software与双seal、精确旧Release、instance revision/data/history、当前Goal及owner ledger、当前软件/预算/权限、样例输入与精确oracle。单实例最多64typed/history及64预检；任一非终态或UNKNOWN任务须先正常停止处理，不代为取消。
4. 300秒精确批准、提交时全CAS重验；新compatibility软件许可双seal、完整新不可变Release与索引、当前instance revision/history追加同事务，失败0部分写。data/schema/record release_ref/旧AUTH/目标Grant/Goal/其它实例/人工锁不变。旧签收因新Release/revision失效；新签收须新输入实际Worker，不继承旧判断。
5. 归档读取不授予执行。preview、generic release/new instance/switch、resume、enqueue/dispatch/结果提交、owner当前声明均须明确执行门；只有获批新Release+精确instance/revision/current software可执行，其它旧实例/旧queuedRun不得借app读通复活。日常live依赖原AUTH TTL/撤销与当前target双主体Grant/预算，不把旧source私有内容或Grant重新纳为依赖。项目全Grant版本仅预检提交CAS。
6. 未知仅原key GET恢复；取消预检与撤回兼容执行许可为独立metadata停止，不把owner声明REVOKE冒充执行撤权。metadata-only项目索引提供精确commit key/record fingerprint，使冷页面在target已撤权时仍可另行明确撤回；不要求先读保护内容。停止后旧原key只历史回执；晚结果不提交。已提交后的CANCEL另存truthful STOP_RECEIPT，stopped=false，不能谎称停止。原key不能混入其它操作语义；重复明确取消保留各自回执，不覆盖原tombstone。页面明确预览完整版本/保留范围并手动确认，不自动批准/重试保存。
7. 最终实际SQLite旧233→当前冷API/NoModel Worker与离线页面、精确版本独审及相关回归。原红轮和拒绝/取消文件保持；不重试旧取消精确竞态或CI Forbidden，不模型/付费/凭据/权限扩大/部署/main/core/force。只可称合成旧SQLite有限接续已验；真实用户旧库/PG/Windows/native/人工语义/完整P-A/P-B单列NOT_RUN。

实际文件：`text_continuations.py`负责已知版本锚、原对象全证明预检、双seal许可、事务和metadata停止；`text_logic_reuse.py`的私有归档读取只用于上述明确合同；`apps.py`/`lifecycle.py`/`internal_api.py`/`app_jobs.py`在冷应用/Release/approval/运行保护正文前授权，在enqueue/resume/dispatch/结果提交重验。`owner_acceptance.py`以当前精确Release/revision执行资格核自有Goal，原owner记录不重签。页面在现有`text-logic.js`及项目区内，保留三个一级工作区与20个HTTP静态资源。

可复现旧库位于`tests/fixtures/text-legacy/{233,a747}.db.gz`及info/archive/create日志；`tests/build_text_legacy_fixture.py <完整旧SHA> <空目录>`按允许的Git源码和普通fixture/helper重新生成，不重签当前软件伪造旧库。a747旧库实际含自有Goal、原正常Worker结果和SIMULATED ACCEPTED；233旧库不存在该新owner家族。测试明确在这些合成库原TTL内固定fixture时钟，生产时钟/TTL/权限不改。

最终冻结为393个`src/tests`文件，map `14be76fa429605338b4fd0a818be0e7f9fa3a9c34750f75b454f8ff4c1f3e591`，67个Python（config除外）实际目标指纹 `316f8327b4e886365c850027ebcfd2634925f1d9a490073ceddcc9c487d9f9d3`。原候选f7e0275因实际冷读取红例失效，未签最终通过；所有原轮次及最终结果见[证据目录](../evidence/text-compatible-continuation-20261012/README.md)。
