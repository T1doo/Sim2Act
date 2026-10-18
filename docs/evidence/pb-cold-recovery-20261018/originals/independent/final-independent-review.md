# P-B 冷页原 key 恢复：最终有限独立审查

结论：**有限独审通过，未发现尚未修复的确定 P1/P2；既授权普通开发分支推送无阻塞。** 非作者审查包含生产合同/源码、冻结字节、纯原件独立复算和 immutable SQLite 元数据读取。实际产品执行由 root/作者资格完成；独审者没有执行产品函数、HTTP、Worker、模型或完整页面。

审查对象为 `737e80d2304509149fef3161226f92580724d43a`，基线 `1f725e8318a9f3993e782335203d5b2e76085c0f`。132 个生产文件仅 `src/sim2act/web/internal.js` 改动，SHA256 为 `5de00b3a3fc682b825293ef7688732a22631b46b0e7ceeb67c8af01f9d338105`。首次冻结 `7c6c79faa1de7a184dca7db468c0e784d5cc0cd6` 到737仅新测试 fixture 修正，生产字节相同；51个 Assert AST 保持。执行前后681项输入映射逐字相同。现在执行结束后两份交付文档 WIP 不改变当时冻结或输入。

## 安全及合同结论

新增能力复用现有 P-B extraction GET/by-key、完整 reviewed/request/candidate 及双 seal 验证；后端、executor、Grant 权限合同没有扩展。17字段白名单持久记录仅保存 ID、版本、请求 key 和独立指纹，不保存 token、其派生指纹、Goal、材料、完整请求或模型正文。独立完整 ExtractInput 指纹不能用 reviewed.request 的指纹代替。

首次 POST 前在同 scope 的 ifAvailable Web Lock 内完成保存、回读；冷页先验证新鲜 source options，再读取 metadata，仅显式 GET 原 key。原件证明完整请求/审核/candidate/source 指纹与保存记录独立比对后才重建 RAM，再执行原合同核验和 fresh app 内容验证。未知 key、污染、新 raw、撤权和导航迟到响应保持 fail closed；不会自动发新 key/POST。source、target 当前授权仍由既有 API 校验在私有正文前执行。target 撤权屏障实际仍评估34个其它已授权 context/source 单元，不能扩大成“所有私有数据均零读取”。

原两项 WIP P2 为**静态发现**，未冒称独立动态复现，原文件见 `wip-findings.md`。两页 A/B 中一页成功删除记录后，另一页已知 metadata 的显式原 GET 恢复现允许只清自身 RAM、不删除任何新 raw；实际平台场景覆盖。source-options 403/版本拒绝路径现清对应 pending body/review RAM并保留 metadata；这一专门分支为源码复核，实际边界场景主要覆盖 action GET 拒绝。修复证据见 `wip-fix-review.md`、`postfix-source-review.json`。

## 实际通过范围

五个唯一 actual HTTP/JSDOM case 来自主批已完成四例，加并行完整平台单例，原始断言没有减少：

| 场景 | checks | actions | 页面API | assets | 实际HTTP | 新DOM |
|---|---:|---:|---:|---:|---:|---:|
| 丢201→闭页→显式原key GET | 36 | 22 | 49 | 54 | 103 | 2 |
| 导航及真实摘要投递 ABA | 160 | 87 | 192 | 54 | 246 | 2 |
| source 撤权/unknown key/污染 | 79 | 42 | 88 | 54 | 144 | 2 |
| target 撤权 | 35 | 21 | 44 | 54 | 100 | 2 |
| storage/lock/两页协作 | 74 | 49 | 109 | 135 | 244 | 5 |
| 合计 | 384 | 221 | 482 | 351 | 837 | 13 |

837实际HTTP=页面833（482API+351assets）+4正常授权控制请求。另两份独立 fresh source seed 各25HTTP、3次生成 Mock+1次成功 source Worker Mock；合计 **8 Mock、2 source Worker claim、0真实模型**。资格页面 Worker 调用0。原导航回归另1 PASS、38checks、8 staged vectors、7源文件，为 synthesized API/staged view，不能计入 actual HTTP 数或 native browser 验收。

独立脚本 `audit_qualified_artifacts.py` 对 main四例及 parallel平台原件分别复核：完整HTTP exact body/hash、17字段metadata、独立请求/review/candidate/source锚、单提取POST、实际摘要投递、撤权屏障、DB delta/双seal与只读回读。每个克隆DB仅原提取的1 app、1 runtime principal、2现有工具Grants、4双seal journal和1 extraction marker；除明确正常撤权外旧完整行保持。**原提取会按既有合同创建2个工具Grants；GET恢复不新增，不能把全阶段说成0Grant写入。** 每份seed另有 generation PARTIAL、source SUCCEEDED、导航 CANCELLED 三Run；不是三个成功来源。

导航包含 workspace/project/instance/Run/app/账号/连接变化，以及真实 WebCrypto 完成后结果投递期间 workspace ABA；不跨范围污染旧DOM、不忘记新记录、无额外提取 POST。它不是另一 actor prepare 的旧/新 installation candidate 摘要窗口。

## 保留失败及未完成原件

- 首次7c批为共享 fixture 的5 setup ERROR/2.11s：测试把共享 httpx.MockTransport 类替换成函数，Worker原 isinstance 守卫 TypeError。模型/Worker尚未执行，但已接受一个 QUEUED generation Run。737仅把 fixture 模块 httpx 引用隔离为 SimpleNamespace，返回原 MockTransport 实例，原 Worker 检查和 test_only 边界保留。原错误日志/测试和修后字节均保留。此问题不是独审在执行前发现。
- 主批737在900秒总预算 exit124；JUnit **4个有name PASS+1无name占位**，最后平台 NOT_COMPLETED（76.526s/133HTTP，owned Node清理-9，watchdog_fired=false）。不称主批全绿。第五唯一通过使用同字节独立 fresh seed 的 parallel平台（213.015s，suite290.44s）。初错、超时、重复平台进场不计额外通过。
- root后置XML读取曾对无name占位触发 KeyError。`root-readback-parser-note.md`明确为当时工具可见stderr转录，非当时重定向原文件；只是纯observer解析修正，没有重跑产品或修改XML。
- 独审曾把5de字节出现时序推断错，已撤回，见 `prequalification-review.json`；最终使用精确字节桥，不借时序猜测证明修改。

## 交付与局限

已回读 root 的 `source-push-receipt.json`：source737普通 push 成功，仅 `dev/pb-cold-key-recovery-20261018` 新分支，远端155→156，其它HEAD保持；此结论不替尚未完成的最终docs push背书。归档/最终文档提交及远端终态由root继续核验。

支持同浏览器 storage 范围的新文档恢复，不声称原生浏览器重启/设备或跨设备保障；用户清 storage、旧JS、不同浏览器并无新增服务器全局 exactly-once fence。不存在可凭403/404/超时安全遗忘的 CLOSED/tombstone 合同；保存后未POST的未知意图继续保持未知。恢复得到的是原 candidate/PENDING，不是新的 Release、运行结果或人工验收提交。

Windows/native browser、真实模型/语义/场景人工验收、PG、远端CI和部署均未执行。永久取消的 `Old/new precise candidate installation digest concurrency comparison` 旧安装窗口完全排除，不得换名重试。旧独立满盘报告未落盘证据缺口仍存在；此前只读 profiler exit139根因仍Unknown。无相邻恢复矩阵扩展。

本目录封存后停止写入。原始作者目录只读引用，未改仓库、原DB或旧证据。
