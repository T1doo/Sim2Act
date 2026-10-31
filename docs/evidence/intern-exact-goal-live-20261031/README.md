# 有明确完成条件的真实 Intern 文本目标

应用冻结源码 **fc978d312bc2aa1e2871aea1f2b38e5d415736c3**，分支 `dev/cloud-g0-live-20261028`。本记录是 Linux 原 CLI／真实回环 HTTP／文件 SQLite／真实固定 Intern 的有限读取目标验收，未运行用户电脑、Windows CI 或正式 PostgreSQL。实际开始于 2026-10-31 18:04:58 UTC，前后 HEAD 相同、工作树为空。

原 F1 的 `PARTIAL / NOT_RUN` 不是连接失败：原 Worker 即使完成授权读取，也固定只声明工具执行完成，没有任意自然语言目标的验收器。此前两次真实 F1 请求仍保持原状态，不改签。新增入口要求用户**事先**选择明确的 `exact-resource-read.v1` 合同；仅此合同有可完整判定的读取目标，不把任意目标升级为成功。

## 本次实际完成

在普通工程页面可选择“完整读取所选文本”，保存唯一一份不超过4096 UTF-8字节的 TXT／MD，再提交任务。本次从正常 CLI 启动真实后端，经普通 API 提交相同表单语义：

```text
Save the exact synthetic text.
Preserve every original newline.
```

末尾包含换行。固定目标要求模型先调用唯一授权的 `resource.read`，然后返回仅有 `content` 字符串的严格 JSON。两次均由原 Intern sender 真实发送；未注入模型结果，没有 MockTransport、补造回执或修复重试。独立检查器核完整原文、精确响应、原操作和回执、请求身份／用量／完整预算／权限以及提交前后的原身份边界，原子保存结果。

| 项目 | 实测 |
| --- | --- |
| Run | `run_cd00aadf514e47358fc77526e7369486` |
| 最终状态 | `SUCCEEDED / PASS_EXACT_READ_CONTRACT` |
| 新真实请求 | 2，均 `RECEIVED`，返回 `Intern-S2`，经原别名策略验证 |
| 请求1 | 3.236083秒；558输入＋59输出＝617 tokens |
| 请求2 | 1.338456秒；878输入＋18输出＝896 tokens |
| 总已知用量 | 1513 tokens，仅上述两次新请求 |
| HTTP轮询目标时长 | 5.692054秒，包含排队和保存；不是大型 Cold 性能数字 |
| 工具／修复 | 1次原授权只读，0次修复、0次写工具 |
| 首次新服务重开 | 同稳定 origin、同 Run 完整结果、同原键，没有再次发送模型请求 |
| 两次退出 | exit0，原同worker STOPPED clean，stdout／stderr 均 EOF |

Run `version=2` 是控制版本，不冒称成果版本。合同有限范围 `whole_task_accepted=true`；通用语义仍 `NOT_RUN`、人工验收仍 `PENDING`，正式发布关闭。

`accepted/runner.py` 是实际执行脚本，`accepted/report.json`、`saved-run.json`、`received-attempts.json` 和两次服务原输出保存完整路径。重开前只对旧失败 Run 做保全行的 SQL 只读比较，**没有提前用 SQL 读取新结果**；新结果先经首次新进程 HTTP 回读，再读取账本。源码路径和 SHA256 见 `frozen-source.json`。

## 保留的真实失败及修复

初始应用 **9d74a3a175204cd6afb74f068a755f4a1fb4f216** 已完成有限合同生产接线，但首个真实请求在新加的8秒网络截止处失败（8.100822秒）。1个预约保留，未收到可验证响应身份，用量 **UNKNOWN**；这不能写成0次发送、0用量或成功。原失败数据库 SHA256 为 `0f96f4f1a4872c18207493d9c1fc75fc0de119f7acc99c2f0bf681b20b364b60`，原件及输出在 `failed-original/`，未改写。

后续新增前瞻性 `exact-read-direct.v1` 请求协议，仅为确定的单次读取关闭深度思考、第一轮指定 `resource.read`／末轮禁止额外工具；全 wire 字段纳入原指纹和保守字节预约。参数支持依据[书生官方文档](https://internlm.intern-ai.org.cn/doc/docs/Chat/)；该文档仍建议通用智能体开启深度思考，未改变通用配置或迁移 endpoint。

新协议单次网络上限25秒，同时取**原30秒租约、原 Run 截止、协议截止的最小值**；旧合同仍8秒，旧键仍恢复原policy，不延长旧请求。未改变 Cold admission／原120秒结算合同。新目标使用**同一个既有工作区、公开合成主体及原 quota subject**，新建一个不同的明确目标，至多2个新请求；加上旧UNKNOWN仅3个预约。旧 Run／Attempt／Reservation／Event／Contract 全字段前后相同，UNKNOWN没有退款、清除、重发或重置账户。

网络等待接入原 Worker stop Event，取消真正的 asyncio HTTP task并有界关闭；发送前和完整响应返回前同步查停止，封闭最后chunk竞态。停止后的完整响应仅据实记账，不执行工具或伪装成功；已收到模型调用而关闭时沿原 PAUSED 生命周期保留，停止时不再发送模型请求，后续恢复仍受原状态机和剩余预算约束。原动态撤权、owner／fence／租约及提交时钟检查保留。

## 验证与交付边界

最终精确源码组合 **302 passed**，原完整校验／快照／期限与所有权门 **84 passed**，均0失败／0错误／0跳过。原始日志、JUnit及 `validation-summary.json` 可核，不将子进程测试重复计数，也不宣称全仓测试全部通过。组合覆盖普通表单材料选择、请求恢复、有限目标及篡改反例、原连续版本资格、取消恢复／过期提交和原sender。模型停止测试仅使用显式合成HTTP transport，与上述2次真实请求分开。

初始9d源码的282＋84定向回归单列保存，不能冒充新源码验证。独审分别覆盖源码／权限／停止竞态及用户入口／UI证明／实际driver；发现的闭合窗口均在最终冻结前修复。旧失败数据库副本在新版上 GET／同键POST仍保持原失败、所有相关行不变，见 `old-failed-copy-compatibility.json`。

`development-original-output/`保留开发中失败和后续修复回归原文，包括测试准备、回调签名／类型、原用例状态码预期、JSDOM依赖／操作前置等失败；这些不是最终302＋84通过数量的一部分，也没有删除原失败。独立标准库只读检查两份压缩SQLite原件完整性，核旧失败行逐字段不变、共3个预约／同quota subject，并从保存的消息独立重算两次完整wire指纹／字节预约和最终原文，见 `archived-ledger-audit.json`；该审计0模型请求。

使用已有源码或新构建包，运行 `sim2act synthetic-workspace --data-dir "原合成工程绝对路径" --exact-read-live`（新目录才加 `--new`）。默认启动不读取模型凭据；显式入口只复用已配置的 `SIM2ACT_INTERN_TOKEN`／`INTERN_API_TOKEN`，固定 `intern-s2` 与 `https://chat.intern-ai.org.cn/api/v1/chat/completions`，不创建令牌、读取.env、切换服务或付费fallback。[用户步骤](../../F2/BlankSyntheticWorkspaceQuickstart.md#显式开启有限文本目标)。

本轮 UI 验证是实际ASGI＋所服务JS的JSDOM操作，未冒充浏览器像素。桌面独立宿主已接新增显式参数，但**新版 Windows EXE 尚未编译／运行**，旧安装包不能冒充本次功能。没有新增 Windows CI 或使用用户电脑。正式 PG 缺已有应用角色连接及明确 principal／project／trial／approval／account 来源选择，未创建；大型 Cold 的真实模型整链仍未验。既有大图G0为29.41／31.34秒，原30秒目标尚未稳定达成，本次有限目标5.69秒不替代该验收。

两个数据库都仅来自本任务创建的合成文本、公开本地测试身份及模型只读回执。gzip展开及原SQLite字节已核无当前注入模型凭据／私钥，不含用户导入私人文件；公开合成登录不属于秘密。见 `privacy-check.json` 与文件身份清单。数据库压缩原件仅用于只读审计，不作为可直接覆盖安装的数据包。
