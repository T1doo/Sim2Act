# 独立审查：BLOCK

精确候选 `807090cf0b9e6f6306f86ed79a64be065a68279c`，基线 `67c6ccc8ad7d6f132205c2ac4f33b10defca5da7`。357 个冻结文件的 Git blob、实际工作树及独立 before/after SHA256 完全一致；其中69个产品文件。审查未写仓库、原测试、Git refs，未使用作者PG或真实模型。

## 阻断发现

`src/sim2act/csv_dag_instances.py:329` 只比较接受回执 marker 与 binding/AppRun 两个集合。对一个已成功实例 Run，将 csv_dag_run 和 csv_dag_run_seal 的 response.internal_instance 同时剥除并重新计算 snapshot fingerprint，同时删除对应 internal_run_bindings、internal_app_runs、internal_instance_data 并归零实例 data_version。真实 runs、CSV_DAG_ACCEPTED event 的 internal_instance marker、两步 operations/operation_intents 仍存在。

独立冷 HTTP 读回：实例 GET 返回 **200 / data_version=0 / data=[] / runs=[]**；直接 GET 实际 Run 返回 **409 / DAG accepted request link changed**。接口隐藏已完成的真实结果并把受损历史显示成空实例。应将当前 iid 的独立接受事件 Run 集合与回执/seal marker 集合和实际 joins 三者严格核对，再逐Run重构真实证明；任一存活来源矛盾应拒绝零写。

精确原件：`api-joint-marker-join-omission/readback.json`、`database-evidence.json`、`joint-omission-readback.log`。最初联合攻击脚本的辅助直接Run断言错误预期200，实际409；冷readback独立保全了真正产品阻断。

## 实际限定范围

自编SQLite/API：14通过用例，47个具名检查（不包含创建fixture的assert）。使用自己的不同CSV，CRLF/中文/负小数，源码列amount，两新列quantity和other；Decimal独立期望4和1.5。验证真实新Run、前驱回执、单次typed append、同键缓存、冷Store零写、输出+typed同改、跨owner/project、孤立origin/seal/全缺失、接受pair整删/共同strip、joins+data删除、未知列、同key改输入、最后typed append后deadline全事务回滚、旧fence零写及新fence只写一次。另联合marker+join遗漏攻击实际FAIL，结论不被通过数量覆盖。

自编真实HTTP/jsdom：5通过场景、6实际页面、140具名检查（包括每次实际HTTP加载HTML及12脚本SHA256）。业务两新列实际typed结果、冷重开零POST；真实accepted丢回复后retry403保原UNKNOWN/key/body；accepted晚到app ABA保存validated receipt、恢复零POST；commit-history ABA无旧paint、原accepted receipt GET恢复；损坏200坏ID不缓存/不做坏ID GET、原key恢复只有一个Run。独立driver保持6秒idle/90秒进程预算。页面与后端均零模型。

首轮自编接受pair夹具误读顶层response造成NoSuchColumnError，保全backend.log/backend-initial.py；只纠正该case，另加同pair marker共同strip。首轮业务driver以字符串1.5比较实际合法1.500造成FAIL，保全ui.log/independent-initial.cjs/ui-initial.py及原结果；只纠正业务格式预期，独立Python Decimal oracle前已通过，正式cold页通过。没有把作者断言或作者PG通过当作独立证据。

不签PG、旧源码数据库升级、native Windows/Edge/Node、任意DAG发布、整体项目验收。PG resources-history历史Future超时OPEN、其他HTTP200提示限制保留；PROJECT PENDING/BLOCKED_PARTIAL、semantic UNKNOWN、owner PENDING、overall NOT_ACCEPTED、LIVE=0。

原始证据根为 `/tmp/sim2act-dag-reuse-independent-20261010`。可复制文件以 `COPY_WHITELIST.json` 为准，包含全部自编harness、freeze、原始成功/失败日志和合成数据库导出；排除SQLite数据库、pycache及二进制。
