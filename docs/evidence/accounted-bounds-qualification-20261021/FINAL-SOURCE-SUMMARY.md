# 最终源证据摘要与方案A设计附录

**源审结论可采纳；方案A仅有条件设计认可，不批准安装/启用分流。** 基线f51bbaae3f7f5bab64c79c4c135d0b0d3a2951c8；本独审产品/Worker/Mock/G0/DB/测试执行全0，未写仓库。

- Run18/Attempt13列定义在db.py95/178；String无length、JSON无字节/深度CHECK。实际写站65处，详见WRITER-INVENTORY：Run插入db.py1072、app_jobs.py369、csv_dag.py383、local_record_apps.py899、protocol_jobs.py733；Attempt插入worker.py258。其余Run42/Attempt17更新包含checkpoint351、finish438及generation/natural接收更新。
- 不能以有限平台限制代替产品bounds：SQLite/PostgreSQL单值大小/Integer位宽、CPython递归或整数字符串限制会受部署/构造路径影响。这里不主张物理无限，只说当前没有统一、已审合同覆盖完整接受域。Store.submit_tx的request_key没有HTTP100限制；checkpoint能保存额外JSON；普通mock接收可保存任意长raw.model；nativeRow可带任意额外_data/安全索引，这是明确的源码反例域。
- PB局部有限界是真实的：TrialCaps50-64的7槽/Generate3/Source2/wire与响应ASCII32768等、policy._ledger200-229已接受usage预留界、contracts.strict_json397-433的depth20与调用方字节界、generation68-82/594-605/1634-1655原archive及safe message界。accounted1591先.all后1592要求3/2；成功后事实形状有界，不等于查询/拒绝前全域有界。Source context927-954有exact keys；Generate counters1935没有相同exact key集合。
- 真实select(runs)/select(attempts)自然来源是18/13原始数据位置；但RowMapping类型没有来源封印。cyextension/resultproxy.pyx14-24、row.py171允许沿用任意parent/index/full tuple；runtime._cold_graph_row_storage1680-1710保留hidden_data与全部安全str索引；cold_accounted718-728只核可见列并存sidecar。不能用dict投影、可见列数或只有原键来消除额外存储。
- SQLAlchemy sqltypes2811-2820的JSON解码用json.loads，不经过本项目strict_json；后置meter不能承诺DB解码前峰值受限。row-storage helper完整lookup、capture names/set/visible dict也在现有freeze前分配，流式适配必须单独解决。

方案A不见原则性权限绕过，但必须明确：

1. Keep complete original Source and Generate producer outputs in unissued staging; each role producer once. Do not use an existing issue() helper that silently invokes the producer again.

2. Select one joint route only after both staged families are complete and current original guard/freshness/authority checks still hold; never issue Source before discovering Generate exceeds work budget.

3. Only typed new-meter capacity/domain incompatibility may choose legacy before issuance. Producer/authorization/drift/cycle/original DomainError failures are not fallback eligibility and must retain original rejection/sticky invalid semantics.

4. After any issued handle/registered owned family, any failure closes the relevant scope; no late fallback, thaw or proof-of-identity shortcut.

5. Native row sidecars preserve full _data, safe index, keys, aliases and relevant intra-call graph sharing. Visible-field projection or known SQL-column count is not a storage-origin attestation.

6. Do not claim peak closure: raw producer rows+old graph inputs+staging+meter/capture structures+both packets/encoded buffers+other snapshots may coexist. Whole-scope aggregate accounting remains unproved.

7. Post-read staging cannot bound DBAPI row fetch/JSON decode; raw→capture streaming adaptation and other snapshot/consumer migration remain installation prerequisites.

其中真正的反例是：Source先发行成功、Generate随后超界，如果此时再回legacy就是发行后fallback；或拿一般DomainError当容量不足重试producer，会吞原拒绝并破坏首次/单次语义。联合未发行staging后一次选route能避免这两类问题，前提是实现确实不提前注册handle、issue helper不重跑原producer、其它原guard也未被“已staged”替换。

因此当前适合交付文档与独立prepared meter证据；raw→capture适配、DB解码前边界、其它snapshot及scope联合峰值尚未闭合。不得把“某个packet在预算内”改写为完整G0产品内存/性能已界定，也不改变原PB失败或固定禁止启动状态。
