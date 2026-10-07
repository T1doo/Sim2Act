# 下一独立核心实现合同：DeliveryGraph / 影响判定

2026-10-07，父明确要求安装线接续核心实现。准确基线为远端dev/install-preflight `e700db211378e67ca99529f4a5270f0ea6162769`（含e828c066底座）；当前主线整合源码/入口/UI/CI由root保留，不等待本模块开工。本合同依据原V5产品§9（404–444）和分阶段计划F2局部修改，不能仅再写文档或宣称整个增量验收完成。

独占新增`src/sim2act/delivery_graph.py`、`tests/test_delivery_graph.py`及本线Plan/Log/evidence。不得改现有contracts/apps/preflight/api/UI/db/工具/迁移/权限/CI。先读原文/AGENTS；独立分支，普通fetch基线，保留旧树；不LIVE/models/新Grant/外发/任意代码/发布。

`derive_manifest_graph(manifest, actions, source_versions, stable_ids, context, platform_limits)`实际调用现有严格schema/preflight，基于canonical AppManifest/ActionSpec生成bounded闭合DeliveryGraph，而非接收模型自称可信。context由服务端适配器提供project/app scope、当前授权允许的resource refs及版本；不是新外部API，也不是客户可授予自己的权限。至少覆盖GOAL/SOURCE/ACTION/VIEW/CHECK/MANIFEST，未存在的ARTIFACT/RELEASE不制造已交付状态；扩展输入节点类型按V5九类闭合。稳定ID复用goal/app/action/resource IDs，views/check slots使用显式服务端stable_ids，不按内容hash每次发明新ID。每节点strict revision（bool非int）、content fingerprint、project/app、status/lock；每条上游→下游边记录DATA/RULE/PRESENTATION/SEMANTIC/VERIFIED_BY/PACKAGED_IN、来源compiler_declared/runtime_observed/human_confirmed/model_candidate。声明依赖不自动升级为实际读证据或完备语义；模型候选及不确定资源集合登记关联app/project uncertainty。

`plan_change(graph, expected_graph_fingerprint, change_request, current_context, previous_receipt=None)`再次校验scope/当前授权/基线指纹/节点版本/闭合图。change_request闭合request_key、changed_node_ids、expected_node_revisions、由可信adapter确认的变更类型/范围；不得凭客户端一句presentation_only减小重验。返回确定影响、影响不确定、validation_scope/checks、preserved IDs/revisions/fingerprints、锁冲突、request_fingerprint和不可执行的plan状态；不写对象、回执、Run、Release。previous_receipt仅服务端持久记录传入：同key同fingerprint可确定返回原plan但仍重验当前权限/版本，同key异参冲突；无持久记录时不声称跨重启幂等已完成。由main后续适配持久保存与版本比较。

错project/current resource权限缺失PERMISSION_DENIED；旧scope/graph/node版本或协调重hash与可信当前版本不匹配VERSION_CONFLICT；影响命中人工锁定LOCK_CONFLICT且保留所有input bytes；重复node/edge、dangling/cycle/未知字段/超界INVALID_MANIFEST或INVALID_INPUT（各类型固定并测试）。未知依赖扩大关联应用/项目重验，不意味着重写所有对象；presentation已证仅展示可保留计算对象，checks/packaging仍正确失效。历史成功不删除，不触发真实检查或发布，也不因此记verified。

独立验收：使用本基线现有真实CSV/agent canonical清单（后续Report类型由root兼容整合），另手绘至少多source/action/view/check的独立答案。六边类型分别覆盖影响传播、CHECK失效、PACKAGED候选失效；确定无关对象保留ID/content/revision；unknown/model边/资源集合增减保守扩验，跨app/projectscope严格；锁命中/同key异参/旧版本/撤权/协调rehash/duplicate/cycle/非法bool/规模限额零修改；input深快照不变，输出稳定排序/指纹、同参确定性，模型/DB/network calls0。不把生成器自行全部影响当oracle，分母0记N/A。必须实际实现/测试/Ruff及独审，按阶段Plan/Log记录源SHA/失败/未测，再交精确commit；主入口消费、实际补丁/检查执行/发布后续由root处理。
