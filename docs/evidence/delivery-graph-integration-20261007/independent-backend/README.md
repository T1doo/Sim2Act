# 独立真实后台验证：保留失败与限定闭合

旧冻结 `5b6b44de` 的 peer 图锚及仍有效授权版本变化在同键缓存/历史中漏验，原实际 HTTP 失败保留于 `final-review.json`、`actual-http-report-v2.json`、`actual-http-v2.log`。

新冻结 `3f07b751a45cab522e754ab3f31b22034dafc26c`：9 项独立 HTTP/SQLite oracle 限定通过，包括上述缺口、真实内部 owner 锁加公开 derive、项目成员集合、严格 graph 类型、双回执/封印协调重算、错误 owner、同键并发。检查完整表内容与原候选/权限，不以行数代替内容。坏 peer 的新键可产生明确 BLOCKED_PARTIAL 规划及合法 peer 等待项，未宣称完整 PROJECT 成功；旧键和历史拒绝且零写。

`fixed-http.log` 保留独审脚本误用不存在 requests.id 的失败；随后仅按真实复合主键修正该项，`fixed-outer.log` 记录补验通过。新源码共 30 固定 Mock（27 个成功 fixture 加该脚本失败 fixture 的 3 个），图增量模型 0、LIVE 0；临时客户、引擎与 SQLite 清理记录见最终报告。

纯核心回执 bool/int 篡改已拒绝，但原始 source_versions 的 True/1.0 仍被接受，因此整体仍 BLOCK_UPSTREAM_RAW_SOURCE_VERSION，待上游独立修复。并发结论仅 SQLite；未执行 PG、全量、原生、CI、调度、补丁或发布。字节一致复制的文件由 artifact-hashes.json 固定。
