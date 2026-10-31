# 图fixture闭合与安装、卸载实测

最终源码 **2d41ad38b84630cb817d87374122bce31e357d0d**，分支`dev/cloud-g0-live-20261028`，源码已正常推送并通过官方GitHub ref读回。上版应用1a23c032fdc5ac83b4caf3ba07ed06f8a9d7669e及证据dd462e6907293c4b7ca1184bcd887f39059d9840／原ZIP完整保留。未改main、未发Release、未新增Windows CI或电脑操作。

## 原12项逐项对照

未改动原22项测试时，当前dd462工作区和实际已安装1a23包**相同12失败、10通过**；两者首先都在真实`_cold_source_packet.current()`拒绝被fixture替换的生产函数。不能声称原12条日志已直接观察到后续产品异常。

图测试借用了原origin调用顺序测试的`local_origin`：它替换`sim2act.apps.compile_preview`、`validate_source_family`等函数；图测试只需要合成pin数据，并不需要这些stubs。将纯数据构造独立出来，图fixture要求真实Source.current且不替换生产者，**原11项直接通过，余1项才暴露真实AttributeError**。不替换资格函数／current／完整图核验，也不为测试造执行许可。

| 原测试（参数逐项保留） | dd462／安装1a23原fixture | 仅改fixture后 | 最终2d41 |
| --- | --- | --- | --- |
| `test_complete_graph_match_drops_encoding_but_dynamic_is_live` | 失败／失败 | 通过 | 通过 |
| `test_current_dynamic_or_content_changes_still_reject[stop]` | 失败／失败 | 通过 | 通过 |
| `test_current_dynamic_or_content_changes_still_reject[epoch]` | 失败／失败 | 通过 | 通过 |
| `test_current_dynamic_or_content_changes_still_reject[scope]` | 失败／失败 | 通过 | 通过 |
| `test_current_dynamic_or_content_changes_still_reject[role]` | 失败／失败 | 通过 | 通过 |
| `test_current_dynamic_or_content_changes_still_reject[contract]` | 失败／失败 | 通过 | 通过 |
| `test_add_rebuilds_and_unknown_configuration_uses_original_sha` | 失败／失败 | 通过 | 通过 |
| `test_native_original_reducer_error_is_not_replayed` | 失败／失败 | 通过 | 通过 |
| `test_unknown_graph_binding_and_row_lookup_getters_deopt_before_callbacks` | 失败／失败 | 通过 | 通过 |
| `test_pre_scope_fresh_complete_walk_and_original_frontier_selection` | 失败／失败 | 通过 | 通过 |
| `test_pre_scope_content_change_still_invalidates` | 失败／失败 | 通过 | 通过 |
| `test_frontier_branch_clears_snapshot_and_keeps_original_rejection` | 失败／失败 | AttributeError，真实缺陷 | 通过 |

[逐项机器记录](per-case-matrix.json)和raw目录保留原日志/XML、去替换后的21通过1失败、首个修复WIP的25通过。所有原22项仍执行；本轮最终图29项为原22＋非法mode三例＋外来storage两例＋替换真实生产者仍拒绝两例，没有删除或跳过原断言。

真实缺陷在`_receipt_for_frontier`原条件先读取`frontier.mode._native`，未发行／外来mode会抛AttributeError或调用外来descriptor。现在先核exact frontier、exact普通dict存储和str字段，再核exact mode及candidate，错误统一受控VERSION_CONFLICT；后续原完整receipt元数据、reader、回调替换、身份及动态校验均保留。`vars()`可能返回dict子类，必须在任何迭代/get前拒绝，新增两条零回调反例已覆盖。非法mode在完整receipt门先拒绝，所以原监测断言从调用Frontier.check一次改为零次；仍要求DomainError、graph失效及结构状态清除，有效发行链另由receipt／second-receipt／frontier原套件覆盖。

旧trace fixture同时保持原对象语义：compile_preview每次返回新tuple外壳，三个元素仍是原对象；verify_origin固定捕获原局部origin，不随namespace重绑改变。两条新身份／重绑反例通过。独审查出的差异已实修，不以同值替代原alias。

## 冻结验证及期限反例

* 最终2d41的15套件：**293通过、0失败／错误／跳过**，实际216.75秒，完整命令和分组见[validation-scope](validation-scope.json)、[suite groups](final-suite-groups.json)及raw XML。是明确的定向范围，不宣称全仓绿。
* 新wheel实际安装到全新隔离venv，复用已有运行依赖，不下载。`python -I -B`，源码外cwd，原src不在sys.path；10个关键模块逐Git blob核路径／字节，包含实际receipt修复。四原生扩展实导入，完整C/header/Python输入的内嵌source hash均匹配。新安装包图29＋旧租约29＋正常页面/ASGI目标1＝**59通过、零失败／错误／跳过**；该59与源码293有重叠，不相加冒称独立数量。
* 最终293使用已有jsdom26.1.0兼容环境。另用仓库lock对应的已有jsdom30.1.2执行实际正常页面/ASGI流程，源码与安装包各1通过。旧已安装1a23同页面案例用26.1.0也通过。jsdom是DOM工程回归，**不是原生窗口截图或Windows验收**。

原finite期限实现本轮未改变。29条legacy interval检查保留真实SQLite：过期0状态拒续租且DB不变；heartbeat在原owner过期后不得提交；原lease／node／Run／更早state截止取最小，snapshot开关均需有效；提交callback跨尾窗、取消stop、外来token替换都回滚；wall回退不能绕过monotonic。另19条commit boundary、13条120秒settlement及25条取消恢复全部通过，有效提交与回滚／重启无重放均有原断言。fake非SQLite调用接口不冒充PG执行。没有扩大任何期限或用短时钟样例称大型30秒达标。

前置失败原件也保留：pre-freeze dirty阶段286通过／1失败，因为测试进程未找到已有jsdom，未进入UI动作；它没有可绑定的冻结SHA，不改签最终验收。首个冻结f960新增poison测试误导入pa_spec_apps而非apps，已知两条测试准备错误后中止**自有**pytest；其SIGINT/teardown输出保留，不当完成结果。2d41仅修这条测试导入，应用字节与f960相同。最终上述293及59均在2d41固定字节下重新取得，未跳过失败。

## 实际新安装包的可用流程

[准确ZIP、wheel及完整清单](../../../deliverables/limited-text-candidate-graph-fixed-20261031/README.md)。223项库存、全部SHA、ZIP内wheel及四个原生输入全部核对，未混入数据库／私有配置／虚拟环境；当前注入秘密比对无命中，不输出秘密值。构建沿原打包器、现有CC=cc和setuptools82.0.1，pip离线/no-deps/no-build-isolation。Linux x86_64、CPython3.12，本次系统glibc2.41；无运行时／依赖wheelhouse，不代表干净机器或其他Linux ABI已验。

`installed-graph-fixed-cli-20261031`是新wheel的正常CLI入口＋真实回环HTTP＋实际SQLite/worker，默认模型关闭，非预先写入结果。实际创建项目、合成CSV `item,amount / A,10 / B,20`、草案、内部审批/实例，运行结果SUCCEEDED、sum=30、result_version=1；相同键未新建Run。首次新进程重开，完整CSV结果及自由目标原失败都一致；自由目标仍明确FAILED/UNSUPPORTED_CAPABILITY，不能偷改为成功。两次SIGINT均原STOPPED、clean/data_preserved、exit0及双EOF。普通CLI随机origin42529→34399，按本次READY URL进入，未称桌面稳定origin。结果JSON和实际runner、stdout/stderr保留；0真实模型调用。

`installed-graph-fixed-live-history-20261031`仅使用已闭合的原工作区**私有副本**，原DB字节hash不变、原WAL为空。新包显式exact-read模式连续两次实际启动／STOP，正常API回读1a23原真实成功Run_e090…完整结果，相同请求键仍指同Run，全部五表逐字段不变，Attempt/Reservation均9→9。验证进程增加只允许回环socket的测试audit hook，禁止本次回读意外发送模型请求；未替换模型响应或业务核验。这是**旧真实结果兼容／重开**，不是新源码新做真实模型执行。其真实2次Intern请求、1739 tokens、6.391秒目标成功属于[原1a23证据](../finite-lease-and-installed-v2-20261031/README.md)，不重签到2d41；本轮新增真实调用0。旧UNKNOWN／格式失败历史没有删除或改写。

## 实际卸载与数据保留

完成所有安装回归、四次服务正常退出后，只对**本次专用新scratch venv**执行显式target Python的`pip uninstall --yes sim2act`，实际exit0。卸载前核distribution路径确属该venv；卸载后该prefix包、dist-info及命令入口消失，新解释器find_spec为None。两个自有合成工作区6个文件逐字hash不变，原共用环境30个发行METADATA hash不变；不卸载共享依赖、不删除venv或任何工作区，也未操作用户电脑。详见[uninstall实测](graph-fixed-uninstall-20261031.json)及原日志／driver。不能将metadata核对表述为共用环境全部文件逐字扫描。

用户操作见包内[限制候选说明](../../LimitedTextCandidate.md)：已有依赖环境安装，默认合成入口；显式参数才开放已有免费Intern的单文本逐字合同；Ctrl+C等clean停止、同data-dir重开不加--new；同环境卸载仅应用，工程／导出／日志默认保留。手工清理专用venv/解压目录前须确认无混入文件且服务已退出，工程需另行备份和明确删除决定，无自动危险清理命令。

独立只读复核及已实修意见见[independent-review](independent-review.md)；最终文件身份见[artifact-manifest](artifact-manifest.json)，隐私范围见[privacy-check](privacy-check.json)，扫描器仅内部比对当前秘密值，不输出值。

## 仍未完成的范围

这份候选已声明的原图失败及上述支持流程没有剩余已知回归；不代表完整产品／全仓／正式发布验收。**新版Windows、正式PG及大型Cold live未验**；既定Windows runner预算不再消耗，未关闭sandbox绕过旧浏览器拒绝。PG缺现有应用角色连接和明确principal/project/trial/approval/account来源选择，未创建凭据，不阻断已验合成SQLite。

大型Cold性能未重测、未冒称修复：上次真实时钟Mock+SQLite G0为29.4065／31.3387秒，writer44.2858／45.9703秒，total73.69／77.31秒，原30秒仍不稳定。30秒writer admission/首次DML租约与签署120秒SQLite结算预算有不同边界；本轮受控错误修复、短反例、CSV与历史回读均不替代大图性能。正式发布与通用自然目标语义仍保持原安全门。
