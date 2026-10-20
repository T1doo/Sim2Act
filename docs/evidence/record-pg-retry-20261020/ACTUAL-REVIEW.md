第二次 CI 的原 10 个 PG 节点实际全部通过，JUnit 为 10P/0F/0E/0S、80.318 秒；测试步骤与清理步骤均成功。重启 hook 的执行与恰好一次成功由冻结源代码控制流及测试步骤退出 0 交叉支持。整份 job 仍为 failure，原因是报告在部分输出后超出固定 2MB 压缩上限，不能称 CI 全绿。

run 39369709238，attempt 1，source `7f47c74487e794f95ca362b3396b5e0d33a6cd72`。实际 job 213 秒；加前次 238 秒共 451 秒。原日志 2,440,155 字节，SHA256 `4daa32568eeae1b8f34b770de31e19649a7db099103e25ac650d455054163c03`。

独立恢复 34 份完整 gzip，33 份非 cleanup 附件的原始字节均与完整 cleanup.sanitized_files 哈希吻合。无尾 manifest。19 份未输出，完整列表在 decoded-index.json/final-review.json；其中 setup.json、restart.json、test-summary.json、test-process-cleanup.json、run-budget.json、startup-diagnostics.json 均缺失。不能宣称恢复了完整 SQL server version、重启前后时间/投影原件或原始测试后代进程回执。PGBIN/runner 声明不能替代 SQL 实测字符串。

完整 cleanup 回执为 PASS：最终 pg_ctl status 3，owned root/cluster/private config/pwfile 删除；共享命令预算45秒内实际0.484秒。回执列出 initial_status、stop、final_status；结合冻结代码，stop 分支只在初始 status 0 后执行，且必须成功，再核最终3才删除根并确认不存在。因此此次可有限支持曾运行及实际 stop 成功的控制流结论，但没有原始 pg_ctl 输出。十份 schema 回执均五项运行角色提升 flag 为 false、schema_dropped 为 true。

未发现 P1。P2：report 的字母序/逐文件流式输出导致可选大文件挤掉核心证据，超限后失去尾 manifest。建议只做本地修复：保留前置 cleanup/redaction/hash 门，预先压缩计量，核心回执/JUnit/fixture 优先，完整文件原子选入，保持2MB，显式列 OMITTED 与所有摘要，不再触发 CI。

原日志及34份恢复文件的有界秘密形状扫描无未决命中；12个 Bearer 候选均为捕获网页源码中的 ${token}/${ctx.token} 模板字面量，真实头仅合成 fixture token。删除的随机密码不可用于精确比对，不能将有限扫描表述为绝对无秘密。

本独审仅解码、哈希、读取原件与源码，未改仓库、未测试、未运行数据库或 CI。不得第三次；缺失原件不可通过本地修复补造。
