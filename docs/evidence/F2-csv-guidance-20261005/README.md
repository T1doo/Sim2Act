# CSV数值列输入提示工程证据

2026-10-05；按F2/Plan实施前选择，固定CSV只读PREVIEW切片。打开草案通过已有项目/应用授权及候选/资源版本验证后，由可信resource.read核对实际内容hash，再计算有界列提示；仅返回列名/是否有限十进制/行数/结构错误，不返回单元格或执行结果，不新增preview/F1业务记录。实际运行重新校验权限与材料，不以提示缓存授权。

UI使用Option/textContent安全DOM，下拉保留已选数值列；文本/缺值/NaN/Infinity列禁用，重复/空表头、多余行字段、超过1000行明确提示；header-only文件计数0，与汇总空集0一致。缺尾部字段仅禁用缺值列，保留原可信工具对完整数值列的语义。畸形材料提示不改API原有FAILED历史路径。

10项新增参数化工程检查覆盖列/内容不泄露、读无执行写入、不同列新结果、8类边界、实际内容hash篡改拒绝；原跨用户及三种撤权回读检查继续覆盖新元数据入口。LinuxSQLite133PASS/3平台专项SKIP/1旧Starlette警告（7.86秒），ruff/mypy14模块/JS语法/diff通过。sqlite.xml及source-hashes.json保留。

实际LinuxChromium（agent-browser、已安装系统Chromium、临时SQLite test_only/合成身份）6检查点PASS：重复表头提示/禁用、文本与非有限列禁用、行数、amount=4.00、quantity新结果15、第一历史回读。browser-results.json与已人工查看的合成页面columns.png保留，不含用户材料或真实凭据；本地fixture/browser已停止。非Win11或其他浏览器引擎通过证明。

正常阶段push已成功；精确源码07969cd3f2add1c446e2e0ef2e7775805bbf1854的[WindowsServerCI37318927260](https://github.com/T1doo/Sim2Act/actions/runs/37318927260)/job111792702059终态SUCCESS（2m12s）。PG136PASS/0FAIL/0SKIP/1旧警告43.50秒，原生smoke、完整依赖锁/pip check、ruff/mypy14模块、Report/Cleanup成功，server stopped。实际Server2025Datacenter/build26100/镜像20260925.250.1/PS7.6.6/Python3.12.10/PG17.11/admin=true/EnableLUA1。windows-run.json及windows-results.json为开发方以现有身份读取真实run/job/log归档，非独立复跑。文档收尾不重复CI。模型请求0，无新依赖/表/迁移、任意代码、外部写入/发布、Release/实例身份。F1签收/F2正式准入仍未通过。
