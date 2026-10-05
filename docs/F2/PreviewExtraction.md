# P-B 最小可信预览回执提取

本切片对应V5 P-B输入输出/工具轨迹/检查、新材料及冷会话的工程子集；没有完成完整F2-T03/AT-10。来源是本地合成PREVIEW任务回执，绝不是F1 Run成功签收。F1历史PARTIAL/LIVE和AT02不修改。模型请求0，PREVIEW_ONLY，不能发布或外发。

`POST /api/previews/{preview_id}/extract`接受`expected_source_fingerprint`、同项目新CSV的`resource_id`、`name`及`request_key`。从应用成功预览历史进入独立表单，人工选择源成功回执及新材料，显式授予新应用只读24小时权限。不接受Run ID、失败/未知/部分成功回执、任意执行器/模型参数或递归提取。

源模板必须完整匹配已审查的单节点CSV求和声明，不能仅凭SUCCEEDED标签或可信工具名称。源用户/项目/应用授权与目标卡历史重新核查，实际材料hash、回执输入指纹、可信工具回读输出一致；另以独立csv.reader解析和整数缩放精确求和oracle验证count/sum。源求和因Decimal上下文舍入而不精确时拒绝提取。oracle额外限制每个数值的digits及exponent绝对值最多1000；原工具1000行/材料32768字节上限仍生效。

候选使用`manifest.origin=task_run`和`source_run_ref=preview_*`，来源`namespace=PREVIEW`明确消除歧义；不是现F1 runs表ID。提取的是源稳定可信工具版本、输入输出schema和单节点逻辑，创建时显式重绑定新CSV，column成为每次运行的参数。源goal与generation全量留存，人工条件始终NOT_RUN；新材料必须hash不同，不能重放原资料/原结果。

preview_extractions由显式migrate建立并需应用角色业务CRUD，无API隐式DDL。事务锁源app，request_key绑定来源指纹/完整回执hash/新材料hash/名称；重复同输入返回同候选，冲突不增加应用身份或Grant。源回执完整快照、来源候选指纹、工具版本、oracle版本、参数化范围、目标材料hash存储；候选每次回读和预览均对照该独立来源记录并重新核查，候选重算指纹也不能移除/修改来源或接线。失败创建整个事务回滚。

当前限制：一层固定求和，非模型归纳/判断；新CSV创建时绑定而非运行时任意材料；仍需源资料与源应用权限有效以便可信审计，源撤权保守拒绝整个候选。这不满足完整P-B移除原资料依赖/发布要求。真实浏览器在本执行环境无可用Chromium沙箱而BLOCKED，Node/jsdom不是浏览器；Win11、完整AT10、F1签收和正式发布未验收。
