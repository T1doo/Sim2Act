# 自然规范正式入口接线审计

基础包73826ba7；本文件及local_desktop_settings后续改动尚未冻结到新包。

已核对存在spec_production、原五字段production_selection、configured_entry与C# --spec-selection转交；不重写这些实现。production_evidence保留2026-10-28运营方免费声明及固定账户解析，不由测试构造账户证据。

旧普通本机配置固定使用default-intern-account，正式执行器要求canonical_quota_subject(ACCOUNT_ID)。本轮加入明确可选字段 `production_account: "intern-ai-configured-account"`。只有live和generation_enabled都明确开启时接受，配额主体由服务器原函数推导，不接受任意配额字符串。缺省仍维持原行为；读取账户选择不创建配额行、不批准、不选中试验、不调用模型。正式启动仍须原五字段选择、既有配额行及全部软件/权限/期限复核。

新首次初始化在填写模型凭据时，通过原Store.initialize创建固定账户的配额行，并保存明确账户选择。不填写模型凭据仍用默认账户。实际Windows DPAPI和隔离PG初始化已使用合成模型凭据验证，确认配额行存在、没有选中任何批准、数据库最终停止；没有网络或模型调用。见first-use-production-account.json。旧私有安装配置和既有数据库未自动升级。

`tests/local_desktop_selection_checks.py` 实际执行通过10项合成配置检查，包括错误账户和非LIVE拒绝、正确固定账户映射及无自动批准。没有实际DPAPI/PG/模型调用。此改动没有修改现有私有安装配置或数据库。

仍待处理：

- 旧安装固定账户配额的明确升级入口，以及原试验选择的产品接入。新安装初始化已实现，但还未进入新冻结包。
- 自然规范生成前端当前仅接受OFFLINE_TEST_ONLY；不能简单删除判断或把LIVE_ENABLED当作已批准。需查询并核对原精确试验选择与阶段，再接入提交。
- 完整P-A/P-B按原七槽/阶段同意及同版合同运行；有限字面链路不是替代证据。
- 原生窗口继续遵从用户暂停自动操作限制。
