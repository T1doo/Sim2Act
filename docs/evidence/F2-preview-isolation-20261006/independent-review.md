# E18 独立只读复验

同工作区 `/root/e16_readonly_review`，实际 SQLite 定向测试，非主开发自验；未独立执行 PostgreSQL、全量聚合、WindowsServerCI 或浏览器。

初版13PASS/1warning/3.57s，审查发现故障发生在 receipt INSERT 前：record/preview 已写后回滚有证据，但 receipt 为空不能证明已写 receipt 回滚。主开发将故障移至两者真实 INSERT + 同连接 SELECT 后，增加 receipts_executed/inside_transaction_receipt；不是生产权限漏洞或产品事故。

最终独立13PASS/1warning/4.57s。确认两次实际写后的故障，从新 engine 独立读回 record/receipt/preview history 均回滚；成功/重试/并发/身份及namespace负例、test_only/path/schema guard、finally listener卸载通过。全部生产meta表仅排除app_previews，原存储文本字节相等。无新具体阻塞。

复验SHA256：

| 文件 | SHA256 |
| --- | --- |
| tests/preview_write_fixture.py | 1658fd5cab3b7ee58a2b60d5d6bb4ee486b2821d15d0aec0dcb61a4d78274c1e |
| tests/test_preview_write_isolation.py | 92696def7dc0b7cbf36f2aeabf5361effaab81f2d56c2a5b772286718a95f841 |
| src/sim2act/db.py | fe5dfd49947d9f1dc5a10d42f315cabaf63d183f2dc7172d403ea5aa26e02760 |

结论仅AT17_SYNTHETIC_FIXTURE；test adapter guards不等于生产writer gateway，原正式AT17/发布仍OPEN。

源码925e560后另做阶段门文档只读核对：AT17合成/正式、AT20在途外部链、Server/Win11/浏览器、预算0与后续接入等级准确；指出F2-T07“局部修改工程子项”没有实际验收证据，主开发收窄为“既有固定对象/指纹；未提供原V5局部修改验收证据”。文档修正不改变已独立复验的三文件hash。
