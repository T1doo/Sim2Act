# 内部 CSV DAG 实例版本切换证据

基线 `db6b5dafe5d5ccc394465a666145c93dafa4a87b`，开发分支 `dev/csv-dag-version-switch-20261011`。需求与使用方法见 [本轮范围](../../F2/CsvDagVersionSwitch20261011.md)。

同应用的两步读取/求和或三步报告实例新增手动核查、确认兼容内部版本升级/回退入口。当前来源、owner/project/runtime、执行家族/端口/列范围/预算及数据 schema 仍须可核验；非终态 Run 阻止准备及提交。旧 typed 行及历史不迁移、不删除、不重签。新输入重新经过实际 worker，原版本30、新版本quantity15、回退后amount30，各自保存独立结果版本。模型调用0，Principal/Grant不增加，正式发布关闭。

## 验证与限制

- 作者最终关联集合的精确计数、运行秒数、产品文件 hash 与实际 UI 结果见 `validation.json`，原 pytest 日志和 JUnit 同目录封存。全部使用合成 SQLite；三个原 PostgreSQL 角色专项跳过。两项真实旧源码升级作业显式未运行，不复跑旧核心验收。
- 四个新实际 loopback HTTP/JSDOM 页面病例：两/三步 × 丢失提交回执/丢失后续读取。每例22检查、两次冷页面，实际worker计算新15；接受结果不确定时只GET恢复，提交POST恰好一次。原四个HTTP/JSDOM页面回归也纳入。JSDOM不是原生浏览器或视觉验收。
- 独立审查原冻结30个后端反例通过，8个产品JavaScript/JSDOM检查通过；后者API为stub，不计真实HTTP。原报告记录其精确产品SHA，最后控制状态修复另列 addendum，不把旧冻结审查直接算作新冻结通过。审查发现的5种畸形历史AttributeError已补闭合结构检查；原错误摘要、实际反例、修后日志保留。首轮审查完整trace未单独redirect，报告明确保留最小准确摘要而非声称完整原日志。
- 修改文件Ruff、两个JavaScript语法及diff检查通过。全仓Ruff10错误、mypy5错误与原db6源码独立归档对照报错逐字相同；未修改对应旧文件，不能宣称全仓静态绿。`*-base.log`与当前日志封存。
- PostgreSQL、Windows/Win11、原生/视觉、真实模型及正式P-A/P-B/semantic/owner验收 NOT_RUN。既有Chromium沙箱拒绝未重试；不提高原900/240/150预算、不改安全/网络/凭据、不改main、不强推或部署。

## 原失败保留

`sim2act-version-switch-first.log` 保留单条旧Run scope入口409；修复只读历史scope后，`second.log` 失败为作者误将DomainError.message匹配code的测试断言，改核 `.code`。`third.log` 是之后10作者专项通过的历史冻结。`sim2act-version-switch-final.log/.xml` 保留扩大关联集合后的111PASS/1FAIL/3SKIP/2DESELECT，唯一原ABA控制状态200被新revision门误拒409；最终将revision守卫留在authorize=True业务路径，保留authorize=False原控制状态/停止能力。随后同集合最终结果单独保存，旧失败不覆盖。

测试依赖安装在 `/tmp` 隔离 Python venv 与 Node目录；Python最终使用仓库requirements.lock。npm默认用户缓存目录不存在的ENOENT通过使用获准可写/tmp缓存解决，无权限升级；依赖日志未当作业务或认证成功证据。
