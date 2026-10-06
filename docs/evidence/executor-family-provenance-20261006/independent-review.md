# 执行器家族来源独立审查

最终独立复验：新增来源家族负例 **23 PASS**，12.56 秒；相关 goal/preview/local-task/bounded-agent 回归 **135 PASS / 4 SKIP**，77.38 秒。两次进程均 exit 0，完整日志及 SHA256 记录在 independent-review.json。

中央 validate_source_family 在候选指纹/所属项目检查后、compile_preview 与执行器分派前运行。它读取三来源表全部记录，拒绝重复/跨家族、错误 owner、未知 task snapshot kind、来源顶层字段集合不匹配及执行器家族替换；原各家族当前授权、接受请求、来源和证明详细校验仍保留。本轮实测未发现新的具体阻塞。没有新增 Grant、principal 或工具能力。

原独立 baseline **2 FAIL**、1.22 秒事实保留：goal 与 preview 原 CSV 撤权后，协调候选+fp 改为 initial bounded_agent，均 GET200、Replay2 轮、批准/Release/Instance/排队 Run 创建成功。没有运行 Worker 或声称 Run 最终成功。MD 合法授权在篡改前已建立；未改旧候选 GET403。仅合成 SQL 损坏复现，非公开 API 注入/跨 owner 漏洞。

最终 apps.py SHA256：8416b6f5281137ca45218b89cafd36f437a40fec7bea3fcb0a3fb2d1094004ae；新测试 SHA256：c24ee19f8223d31efd4d2804c6e34a2b71c42faa017a314bf69899f7ee80ccdc。原 baseline 文件哈希及修复前根因未删除。

本轮未独立执行 PostgreSQL、全量 aggregate、CI、浏览器或 LIVE；无接受来源锚点的直接初始模板草案，不在此 guard 的任意 SQL 替换防护结论内。开发者保留的 fixture-lock-failure 属于测试 fixture 嵌套事务问题，本审查未运行该故障版。0 外部请求，不改产品源码，不 push/CI。
