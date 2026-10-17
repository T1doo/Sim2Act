# 保存字面文本应用目录：工程证据

F2-T05 / 产品§2的实际缺口：既有 `REGISTERED_LITERAL` 被目录标为OTHER后跳过；现在从统一目录显式打开，复用原内部实例、term表单、Run/Worker和历史，未新增executor/Grant。用法已更新 [FirstUse](../../FirstUse.md)。本目录仅保存本次功能的必要执行证据。

产品源 `a051ba2379140bdf4f93830312e0bb9094e8d1d3`；最终执行源 `113a799a6217fb7e523e393ec0d509d42b3277bf`，3个产品文件字节相同。作者新增2节点PASS/53.83秒，关联4节点PASS/16.54秒，分轮共6个唯一节点；独审重复新增2节点PASS/47.20秒，另计重复次数。精确分母/源码/命令在summary.json、source文件、commands.json和原JUnit，不混称一次6节点全绿。

首轮2节点1PASS/1FAIL/50.90秒：guards驱动点击隐藏connect而未重连；仅改为可见identity-switch→connect。原失败log/XML以gzip保留原字节（解压SHA见summary.json），原始未压缩文件也保留于执行输出目录。未改产品安全边界或测试断言。

use/guards各保存完整ASGI HTTP/JSDOM回执、HTTP加载源码哈希和48表只读阶段核对。use通过两个独立冷NoModel Worker保存v1/v2完整引文并冷页面重开；guards覆盖迟到链/误导类型/实际撤权403。仅生成夹具每例2次既有MockTransport；真实模型0。关联回归为CSV使用、CSV目录、自然入口导航及默认模型拒绝。静态检查范围和RC见commands.json。

PG、真实浏览器/落盘、Windows、真实语义、原CSV四步验收、远端CI及部署仍NOT_RUN；不重试已有沙箱拒绝。不扩CLOSED_TEXT_WORKFLOW/DAG目录，不修改持久合同或正式发布门。独审原件存independent/，SHA256SUMS校验本目录payload（不含本索引/自身）。
