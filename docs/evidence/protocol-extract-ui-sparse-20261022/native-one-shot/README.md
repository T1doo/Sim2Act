# 单次稀疏窗口：checkout通过，Python启动前失败

经独审及父级明确授权，新一次 [run39740895401](https://github.com/T1doo/Sim2Act/actions/runs/39740895401)，attempt1，冻结 `ba3d91bba00b7e575e6cce50c3f08a17de07cdbe`。原60秒checkout上限不变，实际 **success / 约7秒（jobs API秒级）**；原log确认 `--filter=blob:none --depth=1` 和非cone稀疏配置。旧窗口60秒超时原件不变，此结果只说明本次修正后的检出通过，不是可推广的时延保证。

setup-python选定现有toolcache CPython3.12.10成功；已安装Edge154.0.4258.62签名Valid/Microsoft Corporation。接着外层监督器的 `Process.Start()` 失败：`Get-Command python -CommandType Application`返回toolcache与WindowsApps两条Source，赋给FileName时拼成带换行的不存在路径。原receipt `started=false/timed_out=false/forced_tree_stop=false`。**自有Python、pip/npm、API、Edge均未启动，业务GET/完成POST/截图/新Worker/Mock/模型均0，原生UI NOT_RUN，CI整体failure。** 未自动或手动重跑，不改保护/权限，不调用真实账户模型。

平台post checkout实际success并记录orphan cleanup；这不能冒充自有API/Edge进程退出或独立PID清单。自有窗口根/SQLite/sidecar尚未由Python创建，故该资源清理不适用。正常DOM、sandbox/token、回执丢失重试及真实清理逻辑仍未获Windows运行证据。

同片修正直接使用固定setup-python提供的单值 `$env:pythonLocation` 拼出 `python.exe`，校验非空/无CRLF、绝对路径和Literal Leaf，FileName只赋GetFullPath得到的一个字符串；缺失即失败，取消PATH/WindowsApps备选。固定[官方实现](https://raw.githubusercontent.com/actions/setup-python/a26af69be951a213d495a4c3e4e4022e16d87065/src/find-python.ts)将installDir赋给pythonLocation，并同样构造Windows python.exe。独审实核7增1删及 `repair.json` 中精确源码SHA，限定静态ACK；Start/Wait/finally及全部预算不变。此修复未在Windows/pwsh实跑，不复用原CI当修复通过证据。本轮无新SDK/本地pwsh安装，也不重新刷ASGI或另开CI。

`job.log/run.json/jobs.json`为原始下载证据，`result.json`记录实际终态，`repair.json`绑定后续源码与未验边界；无marker普通开发分支推送修复及证据，不触发下一实际窗口。
