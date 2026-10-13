# 自然规范：人工要求修正到有限新 Run（2026-10-13）

从已接受的 `5f943df9c17a39241feab647781456ae7871ca79` 创建 `dev/natural-spec-correction-20261013`。root 是唯一产品写入者，既有独审实例仅审查和生成外部证据。依据 F2 原计划及 V5 的人工量表要求，接通人工 REQUEST CORRECTION 后的明确预览、确认、新执行与新成果复审。上一切片的 44 unique PASS / 46 次 PASS 执行、3 条页面路径 / 95 项检查与另 3 控制器探针仍只属于上一交付。

## 实际合同

仅支持已保存且被当前人工声明 REJECTED 的自然规范 P-A / P-B 成果。用户选择原 Run，预览原 Goal、全部原标准、被拒声明、逐项原因、实际有效候选及有界预算；勾选新的明确同意后创建一个不同 ID 的普通 Worker Run。新结果使用新 typed 版本，页面逐项展示旧原因与新精确版本的关系，所有新的人工判断从空选项开始。

有限边界是每个原始被拒 Run 最多一个 correction；correction 的子 Run 不能再次成为 correction 父节点。每实例至多 32 个预览，预览有效 15 分钟。新计划保留原材料、Goal、标准和候选编译合同；P-B 使用原实际有效候选，不自动回退到默认 B，不自动 approve 候选或新增 grant。新预算取当前配置、原冻结 Run 和候选运行预算的最小值，预览区分已消耗 0 与 proposed_limits、模型节点及最多一次成果写入，真实模型 allowance 为 0。

实现文件是 `natural_spec_corrections.py`，并接入既有 `app_jobs.py`、`pa_spec_apps.py`、`natural_spec_runtime.py` 与 `owner_acceptance.py`；没有重写执行器或另加数据库表。现有 `delivery_graph_requests` 按独立 kind 记录 review、accepted 及各自 seal；新 Run 的 binding、snapshot 和 HUMAN_CORRECTION_ACCEPTED 事件同时冻结原声明、原因及证明摘要。模型输入仅在 correction 模式增加人工原因，普通自然规范的 messages 原文字节不变。

API 是选定实例/原 Run 下的 `correction-reviews`、`correction-runs` 与 `correction-requests/{key}`。同意常量为 `RUN_NEW_BOUNDED_CORRECTION_KEEP_ORIGINAL_GOAL_AND_CRITERIA`。未知预览或提交结果只能按原 key GET 恢复；已有受理 key 不产生否定回执或重启 Run。明确拒绝只有在本人精确请求不存在、事务完全回滚且完整 scope/intent hash 相符时返回 CORRECTION_TX_ROLLED_BACK 未受理证明。

原 Goal、旧成果资源、typed 行、旧人工声明与历史不改写；不会继承接受、降低标准或开放发布。新机器成果仍是 owner PENDING、semantic UNKNOWN / NOT_RUN。测试中合成选择 ACCEPT 仅验证新的独立声明机制，不证明语义问题已解决。

## 提交、权限与来源门

确认前完整核验原正常 Worker 的确定性、引用与保存证明。每次 Worker scope gate 重新核项目/身份、当前材料与成果权限、实例/Release 版本、Goal 版本、原精确人工声明序号和指纹、原 typed/output 指纹及封印证明摘要。原声明撤销、来源撤权、过期、版本竞争或证明污染阻止新的结果提交；取消使用既有本人元数据控制，不需要撤权后的来源正文。

成果 READ 授权前只提取既有四处成果指针：SPEC_COMMITTED、已验证 SAVE effect、AppRun.output.resource_id、typed.data.result.resource_id。摘要读取只使用封印的 material/artifact/Goal/version/project；先核原 Run.resource_refs、effect ID 和 Goal 的标量关联，再按封印 ID 读取内容，不能跟随被污染指针读额外项目资源。

自身最后保存阶段仅允许精确 child AppRun SUCCEEDED、result_version=base+1，且精确 typed 行的 aid/版本一致；其他 Run 抢先产生新版本被拒绝。本次实际正例覆盖自身保存阶段，未另跑真实 sibling 版本竞争场景，不扩大该项验收声明。

页面使用实际 owner-review.js，冻结原 scope、请求 key、Run、连接和读写代次。恢复检查预览全文、内层原声明 payload、候选指纹及原 pending 的上下文/声明锚。失败 GET 保留原 pending；A 的迟到拒绝仅清 A 的精确意图，不画入 B。预览 hash 等待期间切换 workspace 不发送旧 POST。

## 验证与保留失败

功能 core `537b3adef0715838ebe547399927725f59df64ce`；产品冻结 `2e21d0fbfa810f5f117523e6e74412df6bd033a7`。76 个 Python 文件资格 pin 为 `dd070bfd15d334b1c9e30e4eebe16d44fa3037a838d848bcbfd00f3e40bbb81e`，原 anchor、CHANGED 与 config 排除不变。`357264c2` 仅清理两个新增测试的 import/格式；函数 AST（忽略内部 import 排序）与全部 src 字节相同。各执行闭包有 456 个 src/tests/pyproject 文件的前后 SHA256 映射。

作者冻结矩阵 17 PASS / 0 FAIL / ERROR / SKIP，544.28 秒：P-A/P-B 实际新 Worker 成功及独立新人工声明；确认前材料撤权、Goal 改变、预览过期、错误指纹、原声明撤销；重复 key/同意与取消；排队后撤销；binding/attempt/receipt 污染；模型回包期间撤销；实际取消；两条页面路径；被污染 foreign source 指针的私有内容屏障。最后格式清理后的矩阵结果见终态证据段。

各例逐字节复制此前正常 Worker 生成的 fa14 P-A/P-B 成功历史；当前代码重新验证原历史，再实际运行新 correction Worker。保留种子来源、SHA、claim 和完整数据库。没有改时钟、预算或 Worker claim 上限；模型为 httpx.MockTransport，运行测试不冒称真实模型。

独立资格检查及旧文字 owner 回归 23 PASS（22+1），19.92 秒，456 文件零变化，静态审查无阻塞。独立页面故障三个不同节点全部 PASS：自签名双污染恢复被拒；丢失提交后连续两次失败 GET 只保留原 key；A 的明确迟到回滚不污染 B，且 hash 等待切换不 POST。它们是当前资产的 JSDOM 控制器探针，不是额外完整用户路径，也没有重跑 Worker。

保留首轮 collection ERROR（误用不存在的 request.id，改为 app_id）、自身保存版本门的真实 FAIL、撤销后 Worker.once 返回 False 的夹具 FAIL、中断轮次、foreign pointer 私有读取真实红例、恢复双污染真实页面红例。独立最终探针首轮 lost GET 另有一个夹具 FAIL：直接赋 correctionReview 绕过 production correctionRender，key 空；保留 raw/XML 后恢复实际 Renderer 初始化，只有该节点重验通过。中断 XML 的 unnamed 节点不算 PASS。不能声称全部历史执行从未失败。

private-source 屏障实际观察 foreign resources.content 的私有 cell：旧源红例尝试读取并被 SQLite UDF 阻挡，修后没有评价 foreign cell。它不是全 SQL/JSON 零读取的声明，也不是工具授权拒绝。

源码与新增测试 Ruff PASS；全仓 tests Ruff 仍有 29 个既有格式错误，原样保留；mypy 仍有 status_report.py 三个和 tools.py 两个既有错误（77 文件）。owner-review.js 的 node --check PASS。全项目类型检查和全仓 Ruff 不称绿。

NOT RUN：PG、Windows、原生浏览器及身份重连、真实/付费模型、真实人工语义验收、完整通用 P-A/P-B、旧源码升级、来源退休、真实 sibling 版本竞争、远端 CI、部署。原已知浏览器拒绝路径未重试。main、core dev、旧 owner WIP 不变。本切片没有当前工具批准阻塞。

## 终态证据与交付

终态计数、两条可见页面路径的检查/手势/实际静态资源、完整历史执行表及逐项归档核验见本任务证据包的 SUMMARY.json、MANIFEST.json 与交付 JSON。只归档 regular 文件，排除 pytest symlink，保留所有失败与准确源快照；不含真实凭据。

证据包：`docs/evidence/natural-spec-correction-20261013/natural-spec-correction-evidence-20261013.tar.gz`。交付提交只增加本文与证据；完整远端 SHA、归档 SHA256、clean/ahead/behind、保护引用及旧 WIP 哈希见 `/workspace/natural-spec-correction-delivery-final-20261013.json`。

最终测试闭包 `357264c20c42fa5bc3ddf6afc1d8d4f4a2c70fe7` 的作者矩阵再次 17 PASS / 0 FAIL / ERROR / SKIP，531.00 秒，456 文件零差异。当前合计 **43 unique PASS / 60 次 PASS 执行 / 0 未解决 FAIL / ERROR / SKIP**：作者 17 unique、两轮 34 次；独立资格及旧 owner 23 次；独立控制器 3 次。最终两条实际 HTTP/JSDOM 可见路径共 64 项检查、109 次可见有效手势，每路径加载 20 个当前源码静态资源；三个控制器探针另列。

测试格式桥独审确认 99 个 src 文件字节全同、76 文件资格摘要全同，以及全部函数 AST 等价；未重复资格矩阵。移除未使用顶层 import 导致其首个额外“整模块 AST 也应相同”断言失败，完整脚本/错误保留；并非产品或测试执行 FAIL。归档汇总首轮因 pytest 的 current 别名链接被重复计数而断言失败，修为排除链接；同样保留准确错误，归档重新生成。

最终归档 SHA256：`7e78f4d9573d96ef6157b1715bd54d88713b417f775d651ec1107b13fbcb3490`；6106 个 regular 成员、208322285 字节，逐项回读 size/SHA256 验证通过。
