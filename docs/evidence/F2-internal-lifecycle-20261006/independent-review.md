# E16 同工作区独立只读复验

2026-10-06，独立代理 e16_readonly_review；事前范围基线 eaeb73164213ed7e2724c4d0f8dc5ffdd86f1e9b，审核其后未提交实现；不编辑仓库、不运行真实模型或业务外发。

修复后实际复验文件 SHA256：

- src/sim2act/lifecycle.py：198e04ee9fd30f17257b18f9853f5b0267f039db39b98d80eaf6b1fa9be2b816
- src/sim2act/apps.py：4d08e583c476fb8944c56f1a89ce7e0a5d9f473c2eb154e9d3b2c21b95347569
- src/sim2act/db.py：0e1f7dfcc60a2db768d82d7fd45ed6a5b43bfde82ec45939e501bf0d0eb406b5

初版 lifecycle SHA256 d9394d714f9bcb4219b38ff5b2d5aeedf4bf128535c4b9cf9268478bf564a0a1，独立 /tmp/e16_review.py 合成复现缺 properties/required 的 schema 导致 KeyError、顶层 enum 将 result.sum 限为99仍批准 PASS但同sample运行FAILED。修复后两项均在批准前 DomainError 拒绝。属于检查覆盖/错误契约缺口，未发现授权泄露。临时脚本使用独立合成SQLite，本地无外发。

独立发现 tests/test_lifecycle.py 文件名撞名覆盖原 AT05_real_process_stop_accept_restart_reopen；主开发从HEAD逐字恢复，新增用例另存 test_internal_lifecycle.py。独立执行 git diff --exit-code HEAD -- tests/test_lifecycle.py 通过。

修复后独立执行新用例：32PASS、1PG专用SKIP、1Starlette warning，5.41秒。另行合成 smoke 通过双instance同request_key各自产生独立run/version1，另实例数据不可见；坏列FAILED不增结果version；跨owner读取拒绝；app runtime撤权后同缓存请求也拒绝。静态未见新增/恢复grant、preview复制或正式发布入口；冻结快照/current gateway/lineage/project→entity→grant锁序符合本轮边界。当前未发现具体阻塞缺陷。

未独立执行PG并发、WindowsServerCI、真实浏览器、正式部署；该复验只覆盖内部合成切片，不签收整个F2。主开发随后aggregate/精确CI另外记录，不能归为独立执行。
