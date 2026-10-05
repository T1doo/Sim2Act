# 返回模型标识兼容修复实测

记录 2026-10-05T04:32:56.377335+00:00；基线 04335528cdce3febec03273fe9446695aa7b11d5；dev/f1-foundation。工程提交 SHA 在后续日志追记。

触发：独立真实接入验证报告发现模型 ID intern-s2，但成功文本/工具响应为 Intern-S2；旧 Worker 小写严格比较拒绝。使用既有证据建立 [明确兼容规则](../F1/ModelIdentity.md)，本次只作零网络修复和验证，不消耗独立验证任务保留的3次真实预算。

| 实际检查 | 结果 |
| --- | --- |
| pytest -q tests/test_model_identity.py | 14 PASS，1 warning，1.04s |
| pytest --junitxml=docs/evidence/F1-model-identity-sqlite.xml | 110 PASS、1 SKIPPED（实际PG独立进程），1 warning，6.15s |
| SIM2ACT_TEST_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55432/postgres pytest --junitxml=docs/evidence/F1-model-identity-postgres.xml | 111 PASS，1 warning，17.47s；各夹具独立schema并清理 |
| ruff check src scripts tests / mypy src | PASS，12源码模块 |
| python -m sim2act.cli probe --output docs/evidence/F1-model-identity-offline-probe.json | PASS，固定MockTransport，原始Intern-S2/规范化intern-s2/策略版本均保留 |
| git diff --check / 源码指纹 | PASS |

14项新增断言：lower/官方同名返回都通过真实项目HTTP API → InternModel适配器 → Worker → resource.read VERIFIED → 工具反馈 → 回填42。响应MODE配置分支设live仅用于覆盖严格校验代码，传输固定MockTransport、身份token合成，无网络/账号调用；不能将该Mode值当LIVE证据。结果PARTIAL/goal_acceptance NOT_RUN未降低。

异型号intern-s1/Intern-S1、开发模型gpt-6.1-sol、未确认INTERN-S2、带空格、缺失与非字符串7种响应继续FAILED/MODEL_OUTPUT_INVALID；数据库无Operation。已确认别名也不能读取未列入本Run的其他项目资源，仍PERMISSION_DENIED且无Operation。人工恢复使用相同规则：已确认别名可记录并保持PAUSED/零工具派发/用量unknown，异型号和缺失不修改STARTED Attempt。请求端不把大写请求名视为canonical模型。

成功/失败Attempt断言保留request_model、response_model原值、normalized_returned_model、版本、执行/合成标签；不把身份校验通过当整个响应或业务通过。adapter原始返回不改写；probe合成模型列表仍标SYNTHETIC，不推导正式可见性或权重版本。

[离线运行引用](F1-model-identity-offline-probe.json)与[源码指纹](F1-model-identity-source-hashes.json)可复核。111项包括前90项回归、7项token别名兼容和14项本轮；保留1条已有Starlette/httpx客户端弃用警告。本轮没有测试失败、删除用例或隐藏警告。没有新增服务/页面/依赖，没有读取真实.env或凭据、没有更改监听/防火墙；Windows及跨设备未在本轮实测。修复后交独立验证者在批准预算内重新验收，当前不预写真实复测PASS。
