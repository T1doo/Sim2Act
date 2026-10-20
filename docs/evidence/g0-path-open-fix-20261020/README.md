# Path.open 适配修复：仅本地接口回归

基线提交：`f2d21775ff1cd9119cd900b07217b4dc96b6484a`。用户本轮仅授权修复适配器、无业务本地接口回归、独立审查及正常开发分支提交推送；没有授权第二次 G0 窗口。

## 根因与最小修改

实际执行环境为仓库 `.venv` 的 CPython 3.12.14，UTF-8 locale，`utf8_mode=0`。标准 `Path.open("a")` 先将默认 encoding 解析为 `locale`，再向 `io.open` 位置转发 buffering=-1、encoding、errors=None、newline=None。旧 `fixture_open` 的 `if args` 拒绝所有额外位置参数，并且默认编码只接受显式 utf-8 字符串，导致首次模拟响应归档前退出。

修改仅涉及 `g0_guard.py:Files.fixture_open` 及其标准库导入：使用标准 open 参数绑定，按 `io.text_encoding` 与 `locale.getencoding` 解析编码并核实实际为 UTF-8；允许等价 UTF8 别名和 strict 错误处理；读取完整转交原始 io.open。文本 writer 遇 bytes 显式抛 TypeError，严格编码错误在字节预算消费前抛出。

写入仍限原两个日志文件、精确 a 模式、默认 buffering、UTF-8 严格编码和默认 newline；二进制写入、其他模式/路径/编码/换行/错误处理、自定义 opener 均拒绝。每次仍经过原 BoundedWriter 预留字节及真实写入/flush，不更改上限、预算或产品逻辑。

标准库依据：[Python 3.12 io.open/text_encoding](https://docs.python.org/3.12/library/io.html#io.text_encoding)、[open 参数语义](https://docs.python.org/3.12/library/functions.html#open)，并以本机 3.12.14 pathlib 实现和实际调用为验证依据。

## 实际回归及独立审查

新增 FixtureOpenInterfaces 使用真实标准 Path.open / io.open / builtin open、真实临时文件以及同原保护入口的 io.open/builtin open 替换，不导入产品 fixture、不调用任何 transport 或 Mock、不消耗业务窗口。

- [修复前原始日志](BEFORE.log)：默认接口测试预期失败，保留 Path.open:1013 → 旧 fixture_open:248 的同一 Boundary 及原始 traceback。
- [接口回归](INTERFACES.log)：8 项全部通过。两种原日志的默认/显式位置与关键字参数、Unicode 字符数/字节数和追加内容；文本与二进制读取；非默认写入与模式/路径拒绝；非 UTF-8 locale 拒绝；bytes/Unicode 编码异常；context 原异常、字节上限及底层 I/O 错误传播。
- [完整纯保护回归](PURE-UNITS.log)：31 项，27 passed、4 旧原生案例 skip；没有业务流程或真实 Mock 调用。
- [ruff](RUFF.log)：通过；[CHECKS.json](CHECKS.json)列出命令、返回码、冻结代码 SHA256 及原证据不变核验。
- [独立审查](REVIEW.md)：审查者仅运行上述 8 项新增接口回归，未执行产品、数据库、Mock、G0 或 launcher；独立测试原始日志随报告保留。

## 重试条件与原证据

本次已解决已知的 Path.open 接口阻断，独立接口验证通过，原相同上限未改变：最多 6 次合成交换 / 8 次方法入口、prefix 480 秒 / G0 120 秒 / 总工作 600 秒、自有组收尾 5+5 秒、64MiB 采样预算（非硬配额）。原 TTL1800 / run300 / lease30 / RPM60、deadline、auth 和全图校验均未改。

这具备再次申请相同上限窗口的已知接口修复条件，不能作为业务前缀或 G0 端到端成功保证。原唯一 grant 已消费；本轮没有创建新 grant、调用 --describe 或 --execute-grant、启动业务窗口或恢复旧 Run/DB。完整纯单元中的既有 CLI 拒绝测试调用了非法 --child 参数，结果 BLOCKED 且未分配输出目录；这不是业务窗口启动。若后续明确授权一次新窗口，须使用新提交及源码清单绑定的新 grant 和全新目录，不能复用旧授权。本轮不会自动执行。

上一轮 [UNKNOWN 原证据](../g0-monitored-once-20261020/README.md)全部 26 个文件逐字节对比基线提交保持一致；包括原失败 DB 压缩件、日志、消费标记及前后独审。没有更改原失败结论或补造响应。此次修复不会解释原 G0/PB 超时。
