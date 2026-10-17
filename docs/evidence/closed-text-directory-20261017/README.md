# 已保存四步文本应用的统一使用入口

对照原产品 `docs/平台产品设计.md` §2 和 `docs/分阶段开发计划.md` F2-T05：当前应用工作区应能发现已支持应用、输入新参数、触发原动作、查看同次运行和历史。基线 `251b1722871fde91a93265f0c33160781ed34398` 的 `closed-text-four-step.v1` 已有严格 canonical 四步合同、内部 Release/实例/Worker 和结果历史，但 metadata 将其归为 OTHER/csvfalse，统一使用目录直接跳过。这是实际入口缺口。

本片只将该类型接入原 `openSavedInternalUse → showApp → openTextWorkflowApp → openInternal`。新增路由 hint 使用既有 namespace/首工具/check 标量，不读取 candidate/Goal 正文，不授予任何权限。选择后原 API 重新鉴权并检查完整 canonical 合同、来源、Goal 和版本；页面核对当前模式、版本、检查引用及四个 registered_tool/version1，再由原控制器显选已有实例。`selectionCurrent` 贯通整个打开链，继续复用账号连接、工作区、项目、实例和 Run 围栏。没有新增 executor、Grant、Principal 策略、endpoint、Worker、模型调用或恢复矩阵。

目录与草案列表一致标为“四步文本流程”，区别于逐次材料 + Goal 的自然应用：固定 TXT/MD ≤1536字节、32行；两个检索词各≤80码点；报告开关明确提交。选中报告才保存成果；关闭报告保留 PARTIAL 和报告跳过回执，没有新结果，原成功历史保留。人工状态为 PENDING，此类型原控制器暂不提交人工声明，语义 UNKNOWN、正式发布关闭。其他未知文本图、未来版本或 CSV DAG 不经此四步入口打开；未增加相邻类型支持。用法见 `docs/FirstUse.md`。

## 执行源码和失败记录

初次实现冻结在 `3ba041fd945223e27b789f2260c1b16a40937b30`。作者首轮 **1 FAIL(use)/1 PASS(guards)，26.98秒，RC1**；独立同两节点 **1 FAIL(use)/1 PASS(guards)，25.616秒，RC1**。use 驱动沿用了字面应用的“历史结果 v1”，而原四步控制器实际展示“结果 v1”。失败发生在实际 SUCCEEDED/v1 后，尚未完成第二次 PARTIAL 或冷重开，不能认领通过。原失败 log/XML/result/DB 均保留，失败 use 没有生成的 `database-proof.json` 未补造；`author-and-related/failure-analysis-3ba041fd.json` 只解释既有响应与源码标签差异，不代替通过证据。

修正冻结在 `75cfd9b10b0e099cb11c00441120446d5057d170`。3ba→75 **只有** `tests/closed_text_directory.cjs` 变化：修正三处结果标签，增加唯一成果条数及当前 Run 的渲染绑定断言。产品代码和三个相关现有用例逐字节不变。后续证据提交不改变执行代码。

## 已完成的新冻结验证

作者新冻结75：**2 PASS，50.81秒，RC0**；独立同两节点：**2 PASS，47.042秒（JUnit），RC0，0 FAIL/ERROR/SKIP**。use 29项检查、guards 15项；48表只读检查点分别6/7。两个冷 NoModel Worker 产生 SUCCEEDED/PARTIAL，仅成果v1；生成和运行的真实模型请求均0。独立报告见 `independent-passed-75cfd9b1/independent-review.md`。独立重复不增加唯一节点，旧轮 guards 也不另加分母。

相关批次3ba：**3 PASS，382.07秒，RC0**（字面目录52.562s、CSV19.953s、P-A normal308.993s）；新源75与该批产品及相关用例文件字节一致。合计 **5 个不同工程节点**。首轮失败及独立重复不增加唯一分母。精确命令与节点结果见 `author-and-related/commands.json`、`author-and-related/commands-fixed.json`、`author-and-related/batch-results.json` 及原 XML/log。初次冻结六条 Ruff/JS/diff 检查和修正后两条 driver语法/diff 检查均 RC0，原始输出保留；无全仓/PG/原生通过声明。pytest保留原Starlette/httpx弃用提示。

## 最小验收的实际范围

新增 `use` 通过实际 ASGI HTTP、完整 served JS/JSDOM、SQLite 和两个冷 NoModel Worker：目录不自动打开/写入，显选原实例；两个词与 bool 原样提交，逐次双击各仅一条原 Run POST；第一 Run 四步 VERIFIED、完整引用并保存 v1；第二 Run 三步 VERIFIED/报告 SKIPPED、PARTIAL、result/version null，原 v1 保留；重开冷页面零 POST 找回同两个 Run 与 v1，再明确打开原 PARTIAL。当前 Run 的状态和详情 ID 一致，人工 PENDING 且不暴露不支持的声明表单。

新增 `guards`：后续 app GET 的工作区 ABA、实例列表同账号重新连接、初次 app GET 的项目 ABA；旧实例 GET 晚于明确选择第二实例；伪造 CSV 的目录 family；合成未知 namespace/check 标量不被展示或打开；已有授权显式撤回后旧按钮重新鉴权得到真实 403，并清空受保护内容。全部通过原服务端与控制器，不新造执行权限。48表只读检查和 principals/Grant 不变断言保留；guards 中仅有一个明确合成撤权，原授权/其他表差异受控。没有扩展其他故障恢复验证。

相关回归只选已保存字面目录 use、CSV 应用使用、自然 P-A 入口 normal。该批次执行源为 3ba，最终源75与其产品/用例字节相同，不能改写批次执行源为75，也未因纯驱动标签修正重复这三个无改动用例。

## 原始证据边界

原目录未删除或改写；归档 map 逐件记录绝对原路径、原始 SHA-256/大小、归档路径/编码。DB和大JSON采用 gzip 无损压缩，解压后逐字节核对。独立原始 manifest 与报告本身保留原字节。静态 HTTP 响应记录路径和 SHA；独立 `statics/` 是与已执行响应 SHA 匹配的冻结源码拷贝，明确 provenance，不冒充另一次请求或原始 HTTP 流。新驱动保存 POST 和逐 Run GET 的 JSON 响应。最终 `SHA256SUMS` 覆盖本目录其他全部文件。

PG、受保护真实浏览器、原生 IME/剪贴板、Windows、真实语义/场景、真实模型、远端 CI 验证与部署未运行。没有再次探测 PG/browser/cache、重试403下载、禁用 sandbox 或改变凭据/安全/网络设置；已有平台卡点仍需平台授权配置。原满盘实例缺失的最后独审报告仍是既有证据缺口。

归档验证：作者/相关原件 56 件；独立失败原目录全部39文件（原manifest35载荷）、独立通过原目录全部40文件（原manifest36载荷）均逐件保全。三个 archive-manifest 是完整映射，原 manifest 与报告未改字节。

原始失败log/XML带有pytest尾空格；首次归档diff检查RC2已原样记录于 `author-and-related/precommit-raw-evidence-format.json`。仅将四份归档改为无损gzip，没有清洗原日志或改变其解压SHA；随后重新进行归档diff检查。
