# 修改后的固定 CSV 内部版本：另一份材料与无内容逻辑

实现前合同：基线 d96e20e0f82793c5fe460d408ca48ff69fc0e01f，同一普通开发分支。对应原 F2-T03 / AT10 的有限纯 CSV 子项；遵循 CsvDataFreeLogicSafety20261010.md，未签通用语义提取或完整 P-B。

1. 仅接纳完整实时核过的 internal.project-csv-read-sum-report.v1 来源。保留精确项目批准、overlay、实际源 Run 和双来源 seal；不放宽旧 Release/CSV 权限或允许双求和、条件分支、递归材料转移。
2. 直接新材料复用保留已批准 default_column：目标必须是同 owner/project 当前授权且已 derive 的另一份注册 CSV，不同 resource ID 和真实 hash，同名列必须是有限数值列。缺列、坏数不能静默换列。请求明确绑定目标版本、图、授权、hash、列、冻结 cap 和原键。
3. 服务端将已证实的固定三步结构规范化为既有 read→sum→report composition，仅目标绑定进入新计划。使用原实际 Worker、新 Run、独立实读数值 oracle；不复制旧输出。成功后仍须分别确认新 Release/Instance。
4. 新目标版本默认列从其实际计划输入与成功 aggregate receipt 重建，并随不可变 snapshot 冻结；冷实例按此默认。旧 overlay/default、Release、Instance、typed 数据和人工锁不改。
5. 无内容逻辑须在旧来源仍可完整核验时另行明确授权。公共对象只含规范化三步结构、家族 tag、cap、身份/expiry、软件承诺；不得含旧列名、overlay、原 CSV bytes/hash、goal、输入、输出或结果。私有审计仍只保存原 opaque ID 与指纹；复用时不 SELECT 旧资源、Operation input/output、Run result/context。原数据撤权/删除后仍可在当前授权目标显式选择新列，形成目标自己的默认。
6. 沿用独立逻辑 24h expiry/不可逆撤销、reserved prefix、双 origin、project 锁、worker 每步与最终提交权限/预算/版本/fence 门。取消、撤权、预算收紧、版本竞争及迟到不得生成 typed 成功记录或伪通过。失败历史完整保留。
7. 页面只开放已证明固定三步家族，校验规范化目标计划与完整目标定义，显示精确默认与批准来源。固定来源授权/新计划接受不明时只 GET 计算出的原逻辑 ID/原 plan key，不能重发 POST；已核迟到回执存储后仍守当前 identity/project/selection 门。
8. 实测至少覆盖直接材料、无内容授权后删除旧源、不同目标数值与冷未见列、缺列/坏数、预算/权限/取消/迟到、原键幂等/换 body 拒绝、完整源及旧数据保留。使用 SQLite、进程内 HTTP 和离线 JSDOM；PG、Windows、原生浏览器、旧源码升级、真实模型及完整 P-A/P-B 明确 NOT_RUN。

原始失败、最终源码冻结、独立审查与回归报告在本轮证据目录保存；结果只在实际完成后追加。

独审后的默认列门补充：新的既有 material/logic 两/三步版本统一从本目标已核计划和实际 aggregate receipt 保存 default_column；页面从 reserved 原 plan key 识别此门，删除/null 默认字段也拒绝，不能用字段是否 truthy 决定是否验证。旧封存 JSON 不迁移或覆盖，旧源码升级仍 NOT_RUN。

真实独审发现并修复：恶意 200 同时更换 default_column 与 execution_source.plan_key、重签 Release/Instance 公开指纹时，旧页面分类可被绕过。最终页面先读实际来源 Run、核其版本及 plan fingerprint，再核完整所指计划与实际 worker 回执；从已核计划判断新材料来源。不存在或另一个有效的普通计划键不能替代原 Run 的精确计划。原两失败病例保留，修后实际重验另记，不能将旧轮累计为最终 PASS。
