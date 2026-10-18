# 首版 CSV 保留原 Goal 修改列：有限交付证据

本地基线 `b58584d101261bccbb43dce56b77f49fc5da0567`。[功能依据与范围](../../F2/InitialColumnRevision20261018.md)、[实际可用上手步骤](../../F2/BlankSyntheticWorkspaceQuickstart.md)。首版同一CSV的列修改不再强迫创建下一Goal；仍须明确预览、独立CHECK、精确Release批准、同实例采纳和新Run。原Goal/材料/Grant/草案/历史保持，不添加executor或授权，不认证自然目标语义。

## 实际执行窗口

| 窗口 | 实际结果 | 原件 |
| --- | --- | --- |
| 有限API | **2 PASS / 6.64秒**，外层9.317秒；本片预览、两次精确拒绝及既有Goal+1换列兼容 | [命令与前后hash](raw/api-command.json)、[stdout](raw/api.stdout) |
| 第一完整流程 | **FAIL**：旧30与CHECK PASS，新版本批准已接受；后续读取中断、Worker非正常停止，原异常类型UNKNOWN | [完整FAIL](raw/first-full-FAIL.json)、[页面](raw/first-page-FAIL.json)、[服务日志](raw/first-process.stdout) |
| 第二完整流程 | **FAIL**：30秒连接等待仍不足；新Release/采纳已接受后，Worker心跳BEGIN IMMEDIATE报SQLITE_BUSY(5) | [完整FAIL](raw/second-full-FAIL.json)、[页面](raw/second-page-FAIL.json)、[安全异常栈](raw/second-process.stdout) |
| 同已采纳库接续 | **FAIL**：新启动器改变软件注册表，原安全门409明确未受理新Run；observer随后误读/runs/null403 | [完整FAIL](raw/software-drift-continuation-FAIL.json)、[页面](raw/software-drift-page-FAIL.json)、[原软件锚对比](raw/software-anchor-refusal.json) |
| 最终软件新空工程 | **PASS**：20页面检查/137HTTP，旧30/v1→保留Goal1的ACTION-only列修改→真实隔离CHECK→新Release/同iid采纳→新Run15/v2及同Run人工入口PENDING | [完整PASS](raw/final-full-PASS.json)、[新页全部请求/响应](raw/final-new-page-PASS.json) |
| 同最终安装包冷开 | **PASS**：9页面检查/53全GET，精确读旧30和新15及各自Release；55表仅心跳变，54非心跳表保持 | [冷页全部请求/响应](raw/final-cold-page-PASS.json)、[冷进程正常停止](raw/final-cold-process.stdout) |

最终整链2026-10-18 21:21:40—21:25:28 UTC；新页165.857秒，冷页43.512秒。新页137HTTP=120GET+17POST（119GET200、1GET400；10POST201、4POST200、3POST202）；冷页53GET=52个200、1个400。两个400均为可选`/protocol/contracts`的`RESOURCE_UNAVAILABLE / Evaluation asset unavailable`，不能把“全GET”写为“全部HTTP成功”。使用实际loopback加载已安装包原HTML、25JS、CSS及原事件；JSDOM hidden/display检查不代替原生浏览器或视觉验收。

最终wheel [可核验安装包](sim2act-0.1.0-py3-none-any.whl) 940967字节，SHA256 `7eb1c477f806a5f728201706e2951557afe74e6f10170e876f60f97088700cb4`。独立venv以`--no-index --no-deps`安装，显式引用已有锁定依赖目录；构建仅用公开PyPI准备锁定setuptools。最终新空工程复用该精确安装，不声称第二次安装或干净机器下载。[139包文件hash](raw/final-wheel-files.json)、[143输入前件](raw/final-execution-before.json)及[后件](raw/final-execution-after.json)核全等；执行后仅补交付文档，[9个最终交付源](raw/final-source-hashes.json)与[源桥/关闭记录](raw/author-closure.json)。

业务实例 `iinstance_49644b3918ae735ee8bd36d0a9d15cb3`。旧core Run `run_13f52ae561fe4f9bbeee0ac4293e22f5`、隔离CHECK `run_81ddd1805dd84825b94a9c38224bc75c`、新Run `run_7d57c7e380474fdba2b93fd092f318ef` 全部原Worker `worker_52ca4f38dbab42408f8980a89f98b78e` 执行，3次CLAIMED、SUCCEEDED/fence1、模型Attempt0。core与AppRun/typed由原binding关联；新人工状态PENDING、无DECIDE。冷Worker `worker_720d3aa32ad24e12822585b524705f78` 同主体、不同进程身份，两个服务均Ctrl+C cleantrue/worker_stopped/data_preserved。

API窗口在启动器修复之前，最终CSV实现与其hash相同；双拒绝55表不变，成功预览原journal增加独立双锚、另外54表不变。最终真实页面预览前后53表保持，例外仅原journal及运行中心跳。静态[Ruff/Node/mypy两Python源](raw/static-final.json)、[最终driver语法](raw/final-driver-static.json)、[diff检查](raw/final-diff-check.json)通过；不冒认旧大矩阵已在最终包重跑。

## 失败与边界

首轮后诊断**执行了**原Worker.once（可写心跳/恢复/领取），实际返回false；[delta](raw/diagnostic-once-delta.json)仅心跳变化，[原stdout](raw/diagnostic-once.stdout)保留。它没有复现首因。另一次无Worker的原API读取新Release200/2.032秒，见[原响应](raw/no-worker-release-read.json)；没有独立DB前后对比，不宣称零写或并发因果证明。

修复仅合成启动器的SQLite连接等待和同进程API/Worker协调，保留原Worker、Store、租约、审批和版本门。该协调不认证取消后的sync线程、独立进程或所有竞争。安全日志只有异常类、SQLite数值码和有限栈位置；无SQL、参数或私有正文。第三窗口软件锚拒绝正确，55表仅心跳变且仍为原2任务；未重derive/重签/放松旧修订，最终软件必须另建新空工程取得上述完整PASS。

本片三个FAIL原件原字节保留，最后完整PASS是独立新窗口。更早b585两个runner FAIL、分期PASS、提交前observer TypeError及修正后的提交核验均保持历史；参见[前片封存证据](../blank-synthetic-workspace-20261018/README.md)，不回写成先前全程绿。原满盘实例最后独审缺证仍NOT_RECOVERED。

## 原件封存

[作者全部原件](author-originals.tar.gz)26635188字节，SHA256 `433b7934d33d1d04e6e9e3574450e5b087914aaa81e99f32f6c50e26c3314266`。包含三次失败、所有页面请求响应、源码/脚本前后件、已停止DB及55表JSON、wheel/安装venv/进程日志；共享运行依赖本身不打包，绝对路径/symlink只供核证。安装请用wheel与锁定依赖，不直接执行归档venv。

[作者seal](raw/author-sealed-manifest.json) SHA256 `9995d7f297b6d55a2fbe5acc7c23f612e980f9fe0df3cea9e82053b43cc7dde1`：4088普通文件86735823字节、14symlink；files投影 `ae73cb11292aa0e7a10543c3fbc6fcaed9e08b7f24f3cc8f7fe96d75daca0f68`。作者目录只读封存，归档逐内容校验[4088文件/14链接及seal](raw/archive-closure.json)通过。[34份可读副本](raw-copies.json)均与原件逐字对应。

未执行真实模型、自然语义、用户人工签收、Windows/native、PG、远端CI或正式发布。真实账户材料仍SOURCE_MISSING。本轮Git远端/auth访问重试0、push0；当前实际远端HEAD未知，沿用最后acknowledged `a7403b379b1278fd1be533ca21d790f0311244af`。最终精确本地commit及未提交/未推送差异由提交后delivery记录固定。

有限独审 **LIMITED PASS，本片未见剩余P1/P2**：[最终报告](final-independent-review.md)、[机器核验](final-verification.json)。独立核对4082非DB文件81955791字节、6个DB仅stat、14symlink仅readlink，基于关闭后的JSON独立复算55表/结果/版本/请求，未执行产品或新测试。[独审全部原件](independent-originals.tar.gz)37535字节，SHA256 `0cf261d329b99d6a9ea617079712b60ef2b4c6e778aaa86786b34687a587b0be`；[独审seal](independent-sealed-manifest.json) SHA256 `357cd534a13fca2451302ad8ef44f69c6c9a19d91b1a0b6cc627e01e1e2e1bd0`，38普通文件105702字节。一次纯文件observer对UTF-8投影的ASCII假设错误及原stderr保留，纠正后仅重跑文件audit；[更正记录](raw/independent-observer-correction.json)。归档打包及后续commit/push不在该独审背书内，作者另作[独审归档内容校验](raw/review-archive-closure.json)及提交后核验。
