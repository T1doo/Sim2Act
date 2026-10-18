# 已封存 key 回执与当前来源证明：准确性补充

支持仅收窄README/F2表述，不改已授权实现、不新增关闭测试；未运行产品，未改旧sealed目录。

`pb_extraction_terminals.close`在事务_source前后重算完整proof并匹配原identity17；`read`只当前source_gate→canonical2 header/pair→identity_scope→absence→封存receipt一致性，不调用_source，也不重算原source_proof_fingerprint。因而“来源权限/版本一切变化时均保持锁定”把两种证明混在一起：source_gate拒绝时无法取得closed；而已成功封存的原key，其历史永久停用证明不因所有来源内容版本变化自动失效。

closed GET/forget并不使用旧来源执行、打开app或授予新提取；独立本地metadata/hash匹配、同raw/lock/current仍须满足。允许忘记永久关闭意图不等于重新验证当前来源或授权新提取；后续必须重新显式review/fullsource。UI当前source证明来自打开面板时取得，GET处校对缓存，不能说每GET复验fullsource。源码仍可能让某些Goal/结果变化触发source_gate拒绝，不能泛化为所有漂移都允许返回。关闭后Goal/结果漂移的具体实际分支尚未执行，不补签。

此前独审最终报告的“来源fullproof漂移……仍UNKNOWN”也应限定为**新CLOSE事务的完整来源匹配要求**，不可当作已关闭GET的全版本重验承诺。原sealed文件保持原件，本补充纠正其可被过宽解读的范围；不是新增产品缺陷或已复现安全绕过。
