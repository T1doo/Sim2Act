# 新连续修订页面用例只读复核

只读检查 `tests/csv_column_revision.cjs` 与 `tests/test_csv_column_revisions.py` 的WIP页面夹具，没有运行测试或修改共享仓库。

三个用例能合并覆盖主要义务：same-navigation串三阶段完整JSON/冻结quantity→amount/确认重置/新GET与0导航POST，next-unknown通过真实Goal编辑保存v3并串实际CHECK202、Release200、CAS200丢交付后的原键GET恢复，navigation覆盖项目/实例/账号离开后的迟到隔离。Python proof使用新queue Run id、typed appRun行、result_version3、新Release和原instance/runtime/Goal contract，并保留旧30/5，能够防止仅借旧v1数值30假通过。

未发现明显产品阻断项；以下证据口径需准确，已发root：

1. 当前Python proof使用原data[0] Store的inspect_job+持久表读取，并没有新建Store/API重开。应称服务端持久proof；若称cold proof，应实际新Store读取。
2. 当前Python proof没有GET新Run csv-owner-review并断言owner_acceptance，PENDING来自CJS页面文本。可以在现有case直接核精确新Run的owner-review GET200和PENDING，或在Python proof补该GET；不必新增case。
3. navigation测离开后迟到，未测ABA返回原scope后再释放响应。报告不能把它称ABA实测；现有controller代数的静态检查不等于该路径运行。
4. 成功链仅检查下一轮按钮visible，未点next读取v3父context/newkey。如报告要包含继续新轮，可在现有next-unknown末尾只点next+baseline，验证新key、parent spec3/current Release/current dataVersion3，0新Run/GoalPUT/derive；无需执行v4或增加case。不补则限定实际范围至v2→v3和next入口显示。
5. 采用阶段以GET完整批准作oracle已正确；建议同时显式绑定该GET id/fingerprint与POST最小提示，避免重犯前次最小POST对象与完整GET对象比较错误。现有lost CAS路径也用POST id构造预期路径，能提供间接绑定。

以上均为WIP静态发现/覆盖边界，不是实测FAIL。阶段返回片段已经改用requests.slice(begin)，比全trace some强；后续冻结独审仍会对原始序列做精确endpoint/status/body校验并列出背景HTTP错误。NoModel/合成API/JSDOM不应被称作原生浏览器、PG或真实语义通过。
