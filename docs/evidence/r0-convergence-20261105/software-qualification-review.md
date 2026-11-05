# 当前软件清单候选审阅

审阅候选为3ec03e255c2e146a26f29a7b04912b21e28b0ec1；本次资格校验器版本变更作为其后续差异单独纳入完整文件哈希。不是第三方独立审计，也不将旧审阅身份搬到新代码。

变更审阅与已有证据：

- private_postgres/local_setup/windows_credentials：自有实例身份校验、当前用户DPAPI、新目录拒绝覆盖、应用角色无DDL、按需启动停止；first-use-production-account.json及历史首次配置实际PG记录。新代码不接管未知数据库。
- local_desktop_settings/process_env：严格字段、清除继承的批准选择，固定账户映射必须明确配置；合成选择与环境回归记录保留。账户选择不等于批准。
- desktop_protocol/desktop_service：数据库cleanup在API/Worker及预检排空后执行，共享原关闭期限，未知退出保留claim；配置选择传给两个角色，API只读核对。原双进程测试10项、依赖cleanup测试及真实PG停止记录。
- api/natural_generation_readiness：启动选择来自进程参数，HTTP不提供更换入口；主体/项目和Goal绑定复核，原check_selection、批准、软件和期限检查保留；前端35项、接口投影2项，正式选择正例仍待新资格后验证。
- contracts/generation_approvals/goal_applications/worker：版本化4096候选预算、逐Run明确批准、原键恢复、v1-v6原字节分支；预留使用与发送相同的serializer。旧scope不得借新选择权限；实际85b8失败保留、73826有限成功保留，不能当自然P-A/P-B验收。

资格文件候选：production v3增加review_candidate明确身份，保留原baseline；literal v2使用新baseline与candidate。原v2/v1文件按原字节保存为previous-*。两枚唯一模块级字面量继续只在各自规定位置归零，所有其他PY/C/H和SQL目录字节仍完整绑定；不扩大豁免表，不删除_qualified，不新增可替换判决回调。

计划验证：资格双清单/唯一pin/篡改/重复字段、production admission/evidence、SPEC与P-B controller。最终结果以JUnit为准；未完或失败不签通过。新软件资格变化后必须新建试验，禁止修改旧scope的软件指纹。

此清单与回归即使通过，也只允许继续原正式门；不代表R0或全产品验收通过。
