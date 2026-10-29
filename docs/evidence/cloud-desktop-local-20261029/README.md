# 桌面本地工作流核验与错误反馈修补

冻结补丁源码 `a3e0ca65833e74d92142117aad4b4415bfbf06d2`。原包 `a140d37ab71b4923e8478555a594a4ed13abbbfc` 的ZIP SHA256为 `21ef7b478bf56ccfde52358c5370fd56490350e7f617ee236a1ccff9f6bf7988`，204个清单文件逐字节核验一致，另含清单本身。桌面宿主、构建脚本、manifest、父目录检查脚本、setup.py、Windows依赖锁、四份C源码都在。它是源码/纯Python预览构建输入，不是Windows EXE；现有.NET/WebView2 Runtime和固定SDK仍是构建前置。

本次唯一程序改动是 `web/app.js`：全局错误区的操作捕获、资源预览捕获及后台轮询捕获，使用纯展示函数同时显示原错误码与服务端已有的字符串原因。保持Error.message、detail、HTTP状态、原提交拒绝证据完全不变，撤权、版本冲突及恢复分支仍按原码工作。只用textContent，非字符串detail不展示；不新增请求、重试、模型调用或权限。不声称所有局部状态区都已改造。独立只读审查通过。

`PreviewRelease.md`补入现有空白合成桌面的实际首次操作：创建项目/CSV→预览→精确确认Release→实例→两次持久Run→关闭/重开。该文件原已进入候选清单并受`checked_desktop_inputs`约束，portable装配时直接复制为`使用说明.md`，不是只存在于源码仓库的外链。同步纠正根README和候选说明中“没有真实模型证据”“最新整链失败”等陈旧结论，保留历史失败和验收边界。

## 已实际运行的本地业务

使用真实产品CLI `sim2act.cli synthetic-workspace`、真实loopback HTTP、SQLite与原Worker，从全新合成目录开始。创建CSV `amount=10/20, quantity=7/8`、草案、样例批准、内部Release及独立实例；分别提交两个原Run，结果SUCCEEDED，typed行30/v1、15/v2。关闭通过私有stdin STOP进入原停止路径；另一进程重新打开原目录，只读GET两个完整detail，逐项完全相同。两个真实READY与两个同worker的clean STOPPED，0真实模型、0 Mock模型交换。最后只读SQLite核验两SUCCEEDED、0模型attempt、两typed版本；检查前后DB SHA256同为 `5babe18df74de67cfe7f5f4412de6152456594cdb1bfd00c19550dab341bc4ba`。见`local-csv-flow.json`、`local-backend.log`及`sqlite-readonly-check.json`。

这是源码checkout中的产品CLI，不是已安装新wheel、原生Windows窗口、PG或真实模型整链。首次驱动误读上一子进程队列里的EOF，在第二进程真实READY前报告失败；原后端正常停止，原目录仍保留。更正为每进程独立队列后，在另一个全新目录完成上述闭环。归档驱动只将不准确的“installed”分类标签修为实际覆盖范围，未修改业务控制；未通过更改产品状态、重试模型或改期限获得成功。此流程证明已有无PG/无密钥的合成本地能力可用，不是新增正式用户SQLite资格。

## 错误与恢复验证

最终4项定向检查通过：真实本机API/产品JS消费、未读到结构化回执时保留原键、协议错误语义，以及完整HTTP/DOM的任务只读恢复/跨身份/撤权隔离。新断言核具体配置原因可见、HTML文本不执行、非字符串原因不序列化；原Error字段、请求数量和未知结果恢复语义保持。JS执行环境是JSDOM，不是原生浏览器像素。早先7项正式连接选择检查也通过，未启动正式Worker或模型。

初次UI检查因重启环境缺jsdom而失败，依赖按仓库锁、禁脚本/审计/自动更新恢复到私有scratch目录；默认npm缓存不可写时改用私有缓存目录，没有系统安装或权限修改。中间组合结果10PASS/1FAIL，失败是旧任务测试仍等待metadata-only目录中已经不公开的Goal明文；没有放宽生产目录。测试改等真实展示的Run ID，并新增Goal不泄漏断言；捕获实际首个2500ms主后台轮询，修正原来误捕内部500ms定时器。未延长等待时限，完整持久行快照、跨身份和GET-only断言保留。中间失败与最终日志分别保全，不能混称一次整批全绿。旧15个Cold continuation fixture债未在本轮修正或算通过。

## 仍缺的输入与交接

原Python、C与桌面宿主字节未改，正式软件pin仍是 `d612b5c0b6332d07ac8139b4d6932be1570beeb27950d13f7cbfe8aa896efce2`，`_qualified()`正常返回；完整源码差异与文件SHA见`freeze-proof.json`。没有重跑自然Mock整链，也没有将旧72c52360的103.844/98.383秒回执改签为新UI字节的整体验收。

当前云端原Intern令牌注入已ready，仅核非空布尔，不打印值。没有PG应用连接，也未选定其principal/project/trial/approval；连接后还需实际核原schema/权限及固定quota行。已有免费授权无需再问；缺具体连接与业务选择时不造凭据、不发正式live请求。合成公开身份只用于非敏感练习，不能处理正式私人项目。

Windows只由原协调任务执行，云writer未操作用户电脑。继续a140的实际窗口验收时保留原包身份；本补丁新包须按新manifest绑定，不能修改旧包或把旧EXE改标签。源码包、EXE编译、窗口可见、页面业务操作、关闭与重开分别记录。main未改，无强推、部署、新费用或新安全权限。
