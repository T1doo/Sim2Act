# 普通已保存Goal明确交付单份MD：有限工程验收

产品及测试源码 `1bacf0bb015fedafa57d6ea27b8eb2b51292859e`，基于已接受 `28506343f7513b2f97476f38dca6bd7b71e08b6f`；普通分支 `dev/ordinary-goal-md-delivery-20261017`。其后仅补使用说明及本证据，交付提交以Git/推送核对为准。

[使用说明](../../ordinary-goal-md-delivery.md)：已保存完整Goal及标准 → 明确选择要求保存本项目一份MD → 再勾选冻结启动 → 原Worker/原保存工具实际写入 → 同Run查看下载 → 原标准和精确文件另行人工逐项声明。新typed `artifact_delivery` 与human v2、Run请求指纹、ACCEPTED事件共同绑定；`required=true`、MD格式、1次保存、8000字符和工具定义指纹事前冻结。旧v1工具暴露及真实派发拒写门保留。JSON/CSV文件不在本片。

正常文件会沿用原工具政策产生 **1个Resource和2条派生resource.read Grant**。没有新增Principal、角色、Grant类型或executor，不是零新增Grant。项目保存权限仍须本人及原项目运行身份当前均可用；不恢复已撤销权限。`DELIVERED`仅证明这一份文件同Run/同项目/格式/hash/原字节通过独立回读，不等于语义正确。技术仍 `PARTIAL`，自动目标验收 `NOT_RUN`，语义 `UNKNOWN`，正式发布关闭；人工接受也不成为技术成功或应用化资格。

## 实际执行

| 批次 | 精确输入 | 节点 | 结果 | JUnit秒 |
| --- | --- | ---: | --- | ---: |
| 作者正式 | 587个src/tests/schema/pyproject文件，前后SHA256一致，测试前后工作区干净 | 26 | 26PASS，0失败/错误/跳过 | 79.397 |
| 独立Git快照 | 同SHA588输入（多1个明确导出的既有goldfixture），逐项Gitblob/SHA256核对，前后不变 | 同26，新增unique0 | 26PASS，0失败/错误/跳过 | 79.184 |

26 = 14新API/真实网关 + 4新完整页面 + 8必要回归。[精确收集节点](raw/author-meta/final-collected.json)、[作者命令/RC](raw/author-meta/final-execution.json)、[JUnit](raw/author-meta/final-junit.xml)、[原日志](raw/author-meta/final-pytest.log)；[独审结论](raw/independent-final/review.json)、[独立命令](raw/independent-final/commands.json)、[独立JUnit](raw/independent-final/junit.xml)。没有自动重跑或额外PA/PB长矩阵。

新后端覆盖真实保存/回读/同Run人工声明、缺文件和同批/后续第二次保存的诚实失败、失败保留第一文件、项目save授权在受理前/模型读取后撤销、源读取与成果读取撤销、typed policy剥离/工具定义指纹改变/原始bool及float整数损坏、同call取原回执/新call写上界，以及最终提交前成果格式改变。原始合同指纹重验防止Literal把True/1.0规范为1后掩盖类型改变：[实际探针](raw/author-meta/literal-normalization-probe.json)。网关同call用例直接操作未完成的合成Run，不冒称完成Worker或进程恢复。

4新页为实际服务整页HTML/CSS/JS、authenticated ASGI和当前Store上的新Worker对象：正常交付、导航晚回调、无文件失败、后续重复保存失败但首文件保留。合计 **74可见断言、180页面API（172GET/8POST）、92资产响应**。页面请求统计不包括Python夹具建立和Worker控制命令。实际捕获4份下载Blob原件，每份115字节、SHA256 `2fb58d113d8ad78962f5a35722689585dc2b64bf10edd5d7af01f847cc60a865`；不是从DB重建，记录Run/filename/url/hash/size、URL释放及临时anchor清理。独审独立捕获同样4份。这是相同4节点复跑，不计8个unique。[页面计数及原件路径](raw/author-meta/final-scope-summary.json)，原Blob文件见author-final/independent-final各页 `download-*.md`。

新4页11次计数ScriptedMd响应；作者全部新API/页计数32次（包含上述11，不能相加），不含8回归的其他Mock/MockTransport，不称全部模型总量或独立总计32。所有响应都是合成Mock，真实模型0。[计数原件](raw/author-meta/final-scripted-models.json)。真人签收和语义评价NOT_RUN，模拟点击不代真人。

8必要回归：旧保存Goal未公告写入真实拒绝；旧v1接受/拒绝2节点；旧人工页面accept；普通freeGoal的交付及工作区返回2节点；原完整CSV报告API；原CSV未确认合同工作区返回。精确节点以收集清单为准，不将未选历史矩阵或旧不同源码的通过结论并入。共享owner追加协议未修改，不重复旧PA/PB长矩阵。

## 原件与边界

本目录 **260份原始输出**：开发红轮/失败、正式批次及独立封存结果、命令/输入指纹/SQLite/实际页面请求/资产hash/Blob。独立84项manifest逐项hash/size自核，另manifest与sums共86输出：[独立原清单](raw/independent-final/raw-manifest.json)、[封存核对](raw/author-meta/independent-seal-verified.json)。源snapshot/node_modules为可重建输入，未冒称执行输出。

[artifact-map.json](artifact-map.json)列原路径/长度/SHA/编码。DB及>1MB输出mtime0 gzip；解压与原字节相等，其他输出不改变CRLF、尾空格或换行。SHA256SUMS列所有归档文件。首红真实HTTP404：[原日志](raw/author-meta/initial-red.log)、[与285源码相同的测试提交来源](raw/author-meta/red-provenance.json)。开发页面夹具误用创建回执的content、损坏格式测试错误预期409（实际既有VERIFICATION_FAILED映射400）、辅助系统Python导入失败原记录保留；不作为最终产品失败/通过次数。[开工checkout/容量/默认网络/20保护引用](raw/author-meta/preflight.json)。没有使用旧满盘实例或旧bundle，没有补回旧未落盘独审报告。

当前未执行：真实模型、真人签收、真实语义/业务场景、PG、原生浏览器、Windows、独立worker进程重启、远端CI、部署、未选历史矩阵。原文`fresh/cold Worker`只可按实际对象/Store范围理解，不能称process restart。前片285的5页UNKNOWN仅实际覆盖已受理丢响应后原key GET恢复，无多POST；原body/key重试按钮、重新授权后重开完整矩阵未验，不以本片补签：[归因限定](raw/author-meta/previous-scope-qualification.json)。

原方案依据：产品§1.2、F05/F08/§5.5/§11及F2-T01/F2-T06。下一候选“人工拒绝理由带入明确新修正Run”尚未实施，不混入本提交。
