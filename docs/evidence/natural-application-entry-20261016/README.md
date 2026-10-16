# 保存自然规范应用统一入口：实际交付证据

开发分支 `dev/f2-t05-natural-app-entry-20261016`，接续远端 `8fc70cc43a6ac81cd522249e8a3d367cd66c9238`；`2b290038` 是祖先。最终源码/测试冻结 `bfb3c6c3c1ef8f45fb8cce8cc53dc53c44b86169`。本目录随后仅保存说明与证据，不修改 src/tests/pyproject。

应用页顶部现在能发现自然 P-A/P-B 和 CSV。自然目录仅显示当前所属项目的家族、定义版本、逐次材料/Goal范围与受限声明；后台刷新零自然详情/私有历史展开。用户明确打开应用并选择已有实例后读取 Release、实例修订和结果版本，再进入原 per-use 精确预览、确认、提交与结果/同 Run 人工入口。没有新 executor、Principal、Grant 策略或正式发布。详见[功能合同](../../F2/NaturalApplicationEntry20261016.md)。

## 分阶段执行，不能合成单次全绿批

| 冻结 | 实际范围与结果 | 原始证据 |
| --- | --- | --- |
| `f9adaae3b34ef498854e2ac57f955679ee7c1ef8` | 6节点，**1 FAIL / 5 PASS / 0 SKIP**，退出1，919.16秒。P-B完整链及目录/CSV四节点通过；P-A尚未进入Node，在额外预置第二旧历史Run时失败。 | [XML](f9-final.xml)、[日志](f9-final.log) |
| `b788949cffbac4ee48403e7d65091335324ceda1` | 仅把新P-A夹具收窄至一份真实旧结果，其他断言全保留；**1 PASS / 0 SKIP**，退出0，352.42秒。 | [XML](pa-minimal.xml)、[日志](pa-minimal.log)、[两行差异](test-only-delta.patch) |
| `bfb3c6c3c1ef8f45fb8cce8cc53dc53c44b86169` | 最终薄UI守卫：首次await前固定Run导航上下文；主线程 **1 PASS / 36检查**，退出0，9.64秒。 | [XML](final-ui-fence.xml)、[日志](final-ui-fence.log) |
| 相同 `bfb3c6c3` | 独立执行轻导航 **1 PASS / 36检查**，退出0，4.88秒；独立静审和原始回执复核通过。 | [XML](independent-final.xml)、[独审](independent-final-review.md)、[导航原始JSON](independent-final-navigation.json) |

P-B 新 `run_3308b2beed824df7ba70baad48f1584e`：66检查、62可见DOM动作，单次提交POST，旧v1保留/新v2保存。P-A 新 `run_d62f170178134e94b1f6d823a8a43401`：72检查、64动作，同样单POST与v1→v2；另通过精确正常API撤权后旧目录重新GET403、旧成果/人工正文清空。两例各加载两次冷页，共42项实际HTTP资产并与当时Git字节匹配；逐次材料/Goal先预览、空确认、防双击、同Run人工合同、成果实际读取和冷页只GET均有原始回执。人工ACCEPT是合成测试声明，不代表真实语义或真实用户签收。

两条新per-use Run各导出1条实际MockTransport线报；这不是夹具生成/旧任务的全局mock调用总数。真实模型未调用。实际为SQLite、TestClient HTTP/JSDOM与正常Worker；CSV回归另使用真实loopback HTTP/正常Worker和拒绝模型的NoProvider。间隔调度在JSDOM禁用，靠显式点击/刷新验证；不称原生浏览器或自然墙钟自动轮询证明。

[关键请求/响应、页面动作、成果持久核对和线报原件](case-receipts.tar.gz)保存三个执行阶段的JSON/log/stderr；[唯一案例摘要](case-summary.json)。归档不含源码树或数据库副本，不按别名重复计用例。

最终UI差异仅收紧首次await前的选择、连接和工作区守卫；后端与正常HTTP请求参数未变。没有对最终薄UI守卫再跑Worker，因此P-A/P-B实际执行分别严格归属上述冻结；独审已逐个匹配42项资产与对应Git blobs，并复核最终差异。PA-lost新测试保留但**本轮未执行**；底层重启/取消恢复矩阵没有重复运行。

## 失败、字节与限制

原P-A失败的第二旧Run为 `WAITING_RESOURCE`，错误为 `RESOURCE_UNAVAILABLE: Heartbeat renewal could not acquire the database lock`；[只读状态原件](f9-pa-extra-history-failure-state.json)。这项额外多历史v3准备未完成，未修运行器/租约，不将其归因成已证实仅属环境，也不把此FAIL覆盖成PASS。最小补测仍有真实旧v1、真实新v2和原行不变断言。

[开发与中断原始历史](f9-development-history.tar.gz)保留缺jsdom时的1FAIL/1SKIP、测试夹具/导航错误，以及bd23、0a3两次主动中断（均0已完成节点，退出2；85.91/484.39秒）。初版自动展开自然历史的设计已撤回；只有最终元数据发现方案被签收。原始日志/XML中的空白按原字节保留，源码空白检查与这些原始输出分开，不清洗失败证据。

f9阶段和b788阶段各自475项Python/Web/Node/pyproject文件执行前后均一致：[f9前](f9-source-before.json)/[后](f9-source-after.json)、[b788前](source-before.json)/[后](source-after-b788.json)。最终[源码清单](final-source-manifest.json)、[受影响静态检查](final-static-checks.json)均可核查。API的mypy检查通过；全仓mypy实际有未修改4文件的7错误，保留[原始输出](whole-mypy-unmodified-findings.log)，不能称全仓静态全通过。

[环境/初始checkout](f9-environment.json)、[祖先/范围/磁盘/远端记录](final-preflight-and-scope.json)保留新环境证据。初始实际checkout是6f688e4，随后从远端可见8fc创建新普通分支；可用空间约30GiB，后续仍约27GiB。root是唯一仓库写入者，代理仅只读仓库和自己的/tmp；未访问/清理旧实例，未知锁未删除。

Windows、PG、原生浏览器、真实模型/材料场景/人工语义、远端CI和部署均 **NOT_RUN**；不关闭整体F1/F2/F3/R0验收。旧环境最终独审未落盘、历史作者1P原XML独立核实不足仍未补回。没有改main、强推或扩大凭据/安全权限。最终远端与无未提交/未推送差异的核验由最终交付回执给出；本目录内source-remote是当时f9保存点，不冒充最终证据提交。
