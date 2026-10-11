# 有限项目 overlay → 可执行内部版本证据

基线：a6dd6f401edb3aef997447fb41bd3f39cefd1f58，开发分支
dev/project-column-revalidation-20261011。父回执仍是 CHECKED_PROJECT_CANDIDATE；
新增整组显式批准产生 EXECUTABLE_INTERNAL_VERSIONS，canonical 未修改，正式发布关闭。
合同：[ProjectColumnVersions20261011](../../F2/ProjectColumnVersions20261011.md)。

最终验证：[final-validation.json](final-validation.json)。650 个唯一用例的收集与两份
JUnit 完全一致：641 PASS / 9 PG 专用 SKIP / 0 FAIL / 0 ERROR，另 2 个旧源码升级
deselected。新增核心 33 PASS（1181.85 秒），关联集合 608 PASS / 9 SKIP
（1178.17 秒）；两套独立进程并行运行，时长不可相加。

新增四个真实 HTTP/JSDOM 场景 27/26/25/25，共 103 次检查，已包含在核心 33 例中；
各加载 16 个页面文件，其 SHA256 与当前冻结源码一致。原结果在 [ui-author](ui-author)。
独审当前源码 [LIMITED PASS](independent/FINAL_REVIEW.md)：14 项后端 + 2 项冷来源撤权
检查、41 次页面检查（38 个不同页面标签），0 FAIL / 0 SKIP。独审不是额外 pytest 例数，
旧 31/8/12 与中断结果不累计。

frozen-before.json 与 frozen-after.json 全部 294 个 Python、页面和测试文件逐字节哈希
一致；独审的 77 个产品文件运行前后同样一致。所选完整集合全部通过后才提交。
原日志/XML、收集清单、复现脚本与失败历史均随证据保留。
源码、测试与 F2 说明的 staged diff 检查通过；完整 staged diff 的空白告警仅来自
原始 pytest 输出日志/XML，不改写原记录，见 raw-evidence-whitespace.log。

实际执行范围：SQLite、现有 Worker、进程内 TestClient HTTP、离线 JSDOM IPC。
新实例默认新列 quantity 得 15；另一个新输入 amount 得 30，均重新派发三步 worker
并保存一条 typed 数据。旧 canonical 内部版本继续得 30；旧实例/结果保留。
整组批准、Release、实例、回执同一事务；第二应用失败、最后撤权/到期回滚。
原键幂等、取消、跨身份/项目保护、合法实例 A→B→A、UNKNOWN 仅原键 GET 恢复。
冷版本使用自己的来源证据，不要求无关应用仍保持原成员集合。

## 失败与中断历史

- first.xml/log：24 FAIL，旧父 FINISH 无 principal_id，新预览误读该字段，0 部分版本。
- probe.log 与 trace.log：分别定位 principal_id 与 column 的旧回执字段误读。
- second.xml/log：24 FAIL，column 误读；独审同时发现 check_instance_records 少 records。
- third.xml/log：22 PASS、2 FAIL。不可变 Settings 测试赋值错误；真实并发确认超出
  SQLite 默认 5 秒等待。修正夹具并在新整组事务中使用不超过 30 秒的等待，结束恢复
  原 busy_timeout，最终到期检查仍阻止迟到提交。
- ui-first/xml/log：4 FAIL；预览把非身份 metadata 当身份。修正为绑定已核父预览身份。
- ui-probe.log：失败诊断先关闭 DOM 的夹具错误；ui-second-probe.log 仍定位身份误读。
- ui-third-probe.log：产品实际 23 项检查 PASS，测试错误要求至少 25；补两项真实新 Run
  与完整 worker/typed-write 检查，不降低检查内容。
- fourth 与 ui-fourth：开发期运行记录，期间 Python 注册表/页面文件发生后续修改，
  分别 26 PASS/1 FAIL 与 1 PASS/3 FAIL，不能用于最终源码签收。原日志保留。
- mypy-full.log：新增 3 项 driver_connection Optional 错误，已加显式连接检查。
- interrupted-frozen-core/associated：为修类型错误主动 SIGINT，分别仅完成 12/42 PASS；
  原 XML/日志保留，不能计入最终完整范围。独审首轮中断也单独保留。
- interrupted-source-seal-frozen-core/associated：因独审复现来源 accepted_fingerprint
  自引用缺口主动中止，分别 24 PASS 与 370 PASS/3 SKIP/2 deselected；不是最终验收。
- 独审 ui-accepted-failure：合法 64hex 的错误来源值，同时重签 definition/base 双读和
  配套批准后确认按钮错误启用。已增加从实际 Run 重建的完整来源只读接口，页面逐项核对。
- source-probe.xml/log：新来源接口第一次 1 FAIL，撤权后 family 先读账本；已调整为
  当前授权/实际来源重建在前，完整 family 在后；保留该失败后重新冻结回归。
- 独审 peer-source-grant-probe：新冷来源接口第一次实际 1 FAIL，最终虽 403/零写，
  Release 的 family 验证仍先读三条来源账本。仅固定项目家族改为实际来源授权在前；
  普通家族的顺序保持。源批准、Release 本体及冷来源三路径快速回归 1 PASS，
  然后再冻结完整关联集合；不把此单例当整套完成。
- interrupted-peer-auth-frozen-core/associated：为上述冷来源授权顺序修复主动 SIGINT，
  仅完成 29 PASS 与 392 PASS/3 SKIP/2 deselected。前独审 14/41 通过与补查 1 FAIL
  全部保留，最终只计新冻结夹具结果。

[prior-run-history.json](prior-run-history.json) 区分实际 console 完成数与 JUnit 条目。
中断时 JUnit 可留一个未完成、却没有 failure 标签的条目；不能将其算作 PASS。

全仓 Ruff 10、mypy 5 项均与上一轮诊断逐字节/逐诊断一致；改动 Ruff PASS。
见 static-baseline.json、mypy-final.log 与 ruff-changed-final.log。不声称全仓静态检查绿。

PG、Windows、原生浏览器/视觉、真实模型/付费 API、旧源码升级、完整 P-A/P-B、
人工语义、远端 CI、部署：NOT RUN。没有重试已知拒绝的浏览器路径或扩大权限。
现有 CI push 仅匹配 dev/f1-foundation，本分支不触发该流程；不声称远端 CI 绿。
正常推送本开发分支；main/coredev/原双求和分支不改，不强推。
