# CSV Run JSON 下载工程证据

功能与范围见 [报告](../../F2/CsvRunResultDownload20261016.md)。产品冻结 `897558064a9bf759b609e22edd7cbe4f6d589d42`；最终执行源 `a0730fab025af68c10ae2706c7b9125d91ac2241`，产品JS字节相同。PG/真实浏览器/四步验收仍NOT_RUN。

| 原件轮次 | 源码 | 实际结果 |
| --- | --- | --- |
| author-attempt-1 | 897558064a9bf759b609e22edd7cbe4f6d589d42 | 3节点：2 PASS、1 FAIL；撤权控制夹具缺JSON体HTTP400 |
| author-final | eff5309989b468fc255c1a5ebeaed42c1d573630 | 7节点：6 PASS、1 FAIL；初始化实例GET8秒等待超时，原因未定 |
| author-observed | a0730fab025af68c10ae2706c7b9125d91ac2241 | 7唯一节点全PASS，85.56秒；未扩等待或断言 |
| independent | a0730fab025af68c10ae2706c7b9125d91ac2241 | 独立重复其中3新增节点全PASS，45.54秒，不加到7唯一节点 |

各轮 `.log/.xml` 是原始 pytest 输出和JUnit。轮次目录内 `results.json` / `driver.log` / `database-proof.json` / `captured-blob-*.json` 字节复制自对应原始输出，保留存在的文件；失败未走到的证明不会补造。不归档测试库、完整夹具info/合同、venv或私有配置。

`captured-blob-*.json` 是 **JSDOM + Node Blob字节捕获**，并非真实浏览器download/saveAs；失败anchor也可能已创建Blob，但必须撤销URL且无anchor点击记录。数据库证明是合成SQLite全48表行比对；撤权夹具的显式Grant更新单独列出，下载GET自身不写。

`source-before.json` / `source-final-before.json` 是前两次执行源记录；`author-source-and-results.json` 记录最终源哈希、全部作者轮次/JUnit身份、失败边界及去重计数。`COMMANDS.json` 明确转录实际执行命令和工具结束状态，不作为独立OS argv捕获。`ruff.log` 是新增Python范围静态检查原件。

`design-review.md` / `design-proof.json` 是实现前独立设计审查；`independent-review.md` / `independent-proof.json` 和 `independent/` 是最终独审与独立复跑原件。`SHA256SUMS` 对本目录全部payload逐字节校验，排除自身及此索引。独审复跑不能代替PG、真实浏览器、完整用户闭环或未知的旧超时原因。

`archive-whitespace-check.json` / `archive-whitespace-proof.json` 保留完整归档diff检查RC2（stdout按JSON字符串完整保留空格）：旧失败日志/XML的原始缩进空行自带尾随空格，4个原件不改字节。源码/测试/使用说明及归档其余内容检查RC0。`independent-archive-supplement.md` 是独审对此归档边界及最后报告文字的补充，不改变原独审或测试原件。
