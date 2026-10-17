# SQL observer 修订判断

本轮三份权限失败是空 PA family-discovery SELECT 被 observer 计成正文泄漏。仅对这些独立 SQLite fixture 作此判断，不将其扩为 PA gate 的一般保证。

证据：`raw-analysis.json` 逐条保留原证据路径及 SHA256、原 SQL/参数和独立 `mode=ro; query_only=ON` 的精确 row count。每例4条均为 `(known ordinary Run id, owner, pa_spec_run_scope|pa_spec_run_scope_seal, accepted)`，实际匹配行均0；delivery/approval/run/original-key/confirm全为403且前后DB指纹一致。

源码路径是 `pa_spec_apps._job_scope_gate` 的现成 family discovery：无 AppDraft family 时探测两个独立 scope 行，均为空则returnFalse；使用 `delivery_graph_apps.lookup` 因而发出全列 SELECT，但这些查询没有返回任何正文行。

候选只改变测试 observer：

- positive 前，对当前新 Run 和原 source Run、精确owner、两固定kind与accepted key先独立COUNT并要求0；末尾再次COUNT并记录。
- 只允许完全一致的7列SELECT结构、精确四参数、非executemany且预先count0的查询归为empty discovery。
- 对任何非空身份、未知Run/owner、其他kind/key、其他SQL形状或executemany均不排除；所有其余journal/Run/recipe/approval正文仍严格拦截。
- 正向control必须在排除空probe后仍看到真正正文；被排除SQL完整单独保存。

`existing-raw-classification.json` 是对原raw的离线分类，不是测试重跑或PASS：每例剩余positive真实正文SELECT80、被拒阶段精确空probe4、剩余正文SELECT0；同时检查分类器对非空/未知identity/其他kind-key/不同SQL/executemany均拒绝豁免。

交付：`test_csv_full_report_instances_negative_sqlbarrier.py` 是可替换原negative模块的完整候选；`observer-only.patch` 是最小diff。不要作为新模块同时收集，以免重复旧3PASS。

原FAIL文件、DB及仓库均未修改。没有新fixture、Worker、模型、PG或CI运行。新oracle的3个权限case仍待root实际重跑。
