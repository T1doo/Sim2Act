# Cold admission 诊断：最终精确字节独审

**ACK。原 P2 已闭合；当前无未解决 P1/P2。** 本审仅只读源码、Git diff、作者 JUnit 与保存的局部 JSON；产品/测试执行 0、DB 打开 0，未编辑仓库。

| 文件 | SHA256 |
| --- | --- |
| src/sim2act/natural_spec_runtime.py | dd2eaff6dcb362fce4c1408f8df6dc76dc31a4c427e2ec7c8d34328bbf73c934 |
| tests/test_spec_production_controller.py | 4a9d6856b05304f3d16614db7f8b4ed92d58481c8d344aadb763bd2216dd53c3 |
| tests/test_cold_admission_diagnostics.py | 2f872ba5d782c7965b84261e28e0f62e7a2d528f3e6619e79b4cbbb77a806d1e |

两处计数自增均以窄 Exception 保护，不再让坏诊断状态抢先替换原业务异常；原 check try/invalidate、全图 bytes、无缓存路径保留。新增坏 check/key 计数两参数用例要求有效输入仍完整序列化，原输入漂移仍 DomainError+sticky invalid，覆盖了本审 P2。

原拒绝点的 end=time.time→pin→单次 stop 读取顺序保留；stop=true 仍短路 min。finite 原表达式与追加顺序保留，仅平行加入固定标签；实际 Run lease/version/fence 在原 RunCheck 位置复制标量，后续 row 变动不覆盖这份快照。五个固定外层阶段各做两次 monotonic 快照，计算已有 check/input_key 计数差；不新增 SQL、全图调用、序列化、哈希、回调或产品 I/O。其计数和诊断不进入完整图输入、权限或成功 output。

拒绝仅附私有 DomainError 属性，code/message/public 保持原样；阶段采样普通故障不覆盖原异常。提纯 failure_observation 仅供既有测试 JSONL，不进入产品公开输出。已独立读取作者保存的 `synthetic-admission-rejection.json`：原公有 error 不含诊断；私有诊断不含 SENSITIVE_ 身份哨兵，11 个命名 finite 值、原 end/stop、RunCheck 快照与五阶段均保存。

作者最终 JUnit 原件 `/tmp/sim2act-cold-admission-diagnostic-final-v2-20261020.xml`：**34 passed / 0 failure / 0 error / 0 skipped，5.568 秒**；9 个诊断局部用例、22 个既有 guard delta 用例、3 个 fixed-key 用例。该结果包含实际局部 CGR 原语，但首次 admission coordinator 用显式 stand-ins 替换语义/SQL producers，不代表完整 PB/Worker/模型/PG/CI 已验证。本审未执行任何用例。原件 bytes/SHA256 与分组列于 FINAL-REVIEW.json。

开销是每个既有 check/input_key 入口一次浅计数及五阶段有限对象/单调时钟采样，属于非零且未基准测试的观测成本；不可称耗时完全不变、性能修复或租约验收通过。诊断对普通 Exception 尽力保全，不承诺进程终止、取消或资源耗尽时仍可产出记录。历史唯一 full 失败的 actual finite/end/stop 仍未知，本补丁不能补造它们，也不新增重跑授权。

证据版本说明：首版 REVIEW-v1 先读到未保护自增的 diff，随后采 SHA 时 writer 已落最小修复，因此其 source_sha256 实际恰为当前修复后文件，不可当缺陷版冻结 hash。首读工具原件保有旧 diff；v1 文件不改。本次重新读取当前修复后完整 diff/测试，并核对上述冻结 SHA；最终 ACK 仅针对本表精确字节，取代 v1 的 hash 归属歧义。
