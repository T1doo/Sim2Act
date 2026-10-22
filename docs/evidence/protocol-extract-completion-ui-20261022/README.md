# 窄完成入口的控制器及实际 HTTP 证据

基线 `be3e4c434f79f97d3d68cbcd69b59c197088dc7f`，对应[原方案和最小产品边界](../../F2/ProtocolExtractCompletionUI20261022.md)。只改现有 `protocol.js/index.html`；后端及先前553个 source/test/config 原文件哈希全部保持。没有新模型/Worker/Grant，未重跑恢复37/20或进程窗口。

实际最终候选：`pytest-initial.log/xml` **2 PASS / 0.95秒**；90秒外限＋10秒清理宽限。`logic-result.json` 为实际 protocol.js 通过 Node stdlib VM 的64项断言（属于一个 pytest 用例，不是64个测试），`http-result.json` 为另一个实际 HTTP 用例的3项控制器断言。模型0、源前缀0；复用已提交的完整持久接受事实，不重新发送 Source/extract。

第一项使用真实 HTML ID 集和最小元素适配器，核明确确认、普通/不支持状态、9键完整回执、bool/int、坏200、UNKNOWN原键黏性、已确认后GET-only、同页Run/项目/身份ABA及迟到读取、旧状态核对接口独立性。不是完整 DOM 或浏览器。

第二项将已封存 before.sqlite 和原 sidecar 复制到新隔离测试目录，只创建该测试自己的空同步 lock 文件，未重写见证/Run/Attempt/slot/Grant，未初始化或迁移数据库。启动真实 loopback API，实际控制器发一次完成 POST 和一次成果 GET；另有初始化详情 GET，共3次本地 HTTP。设置 call/reserve/accept/model tripwire，实际0调用，严格规范化 JSON 原计划及 V2 回执相同。全表指纹仅 runs/protocol_jobs/events 改变，原事件保留并增4；非完成账表和 sidecar 字节不变。原显式合成业务时钟只作语义验证，不是实时G0、PG或模型资格。

原件在 `/workspace/sim2act-extract-ui-20261022`；候选静态审查绑定 `source-manifest.json` 中4个文件。独审者 `/root/independent_gap_review` 只读源码限定 ACK，未执行/开库/写入。最终测试控制器与HTML源 hash 和已审版本完全一致。mypy三项既存 native loader错误未改，本片不称其通过。

开发阶段首个纯VM检查失败，原因是测试把合法空对象输出 `{}` 当作迟到成果；修正 oracle 为原结果仍 null 且没有 compiled_plan 后通过。失败日志/JSON保留，随后针对新增HTTP驱动完成两项候选测试；没有为得到通过运行任何模型。测试中没有放宽产品门。

能力探测确认当前 Node 无 jsdom，未安装新依赖，采用 stdlib VM；一次 `/tmp` 文件搜索遇到 `/tmp/codex-daemon-1000` 拒读后停止该搜索，未进入或绕过该目录。没有原生浏览器、视觉/窄屏、Windows、PG、远端 CI、真实模型、G0、Cold2、W5 或真实语义签收。页面原命令只在内存，刷新不保证原键恢复；未知状态不自动生成新键或触发模型。
