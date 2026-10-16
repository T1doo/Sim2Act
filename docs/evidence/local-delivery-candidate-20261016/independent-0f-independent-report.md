# 本地候选包独立核验

结论：本次有界范围 PASS，未发现阻断。精确源码提交 `0f0819a6a481841a0221cc69f75959326f264529`。

核验对象是 `/workspace/local-candidate-artifacts/Sim2Act-local-candidate-0f0819a6a481.zip`，SHA256：

`00315c17bfcdc91c28384a5675e32590a19ffd5047761de7fb962adc325fe216`

独立解包目录为 `/tmp/f2-local-candidate-independent/extracted/Sim2Act-local-candidate`。所有脚本和结果写入本代理自己的/tmp；没有修改原zip、wheel、解包内容或仓库。

## 归档与wheel

- 134个归档文件、133个manifest校验项，逐项size/SHA256通过；只多一份不自引用的manifest。外部manifest与包内字节一致。
- 包内131个tracked源码/脚本/文档与上述冻结Git blob逐字节一致；generated README、manifest、wheel按各自规则核验。
- wheel SHA256为 `23fcbd6fd1a49de28899fae40e99c879aa2bb54ca04e40d94da3855ea0194323`。wheel内113个程序文件含21个web资源，集合和字节均与包内src一致。wheel的117条RECORD完整校验通过。
- 路径集合没有.git、tests、docs/evidence、node_modules、venv、数据库、日志、pyc或私钥文件；没有重复、绝对路径、父目录跳转或符号链接条目。
- 对包与wheel展开内容扫描本机路径、常见API密钥格式及私钥头，无发现。人工核模板只含LOCAL_PASSWORD占位与空模型token；脚本中的公开synthetic身份是明确标注的演示值。此项是给定模式扫描与内容复核，未读取本机真实凭据进行比对。
- 运行前后重新核对134文件集合和manifest全部hash，不变；没有产生包内pycache或其它运行文件。

原始逐项结果：`package-audit.json`；运行后核验：`package-after-runtime.json`。独立审计驱动：`audit_package.py`。

## 实际CSV运行

使用已有 `/workspace/sim2act-venv/bin/python`，从独立解包目录的src导入产品，从包内原 `scripts/local_candidate_demo.py` 导入Demo、loopback、settings_for和NeverModel。实际导入路径保存在 `csv-prepare-proof.json`。没有从仓库导入产品或测试fixture，没有安装新依赖；wheel安装/导入由父级另外执行。

命令：

```text
PYTHONDONTWRITEBYTECODE=1 /workspace/sim2act-venv/bin/python /tmp/f2-local-candidate-independent/csv_probe.py prepare
PYTHONDONTWRITEBYTECODE=1 /workspace/sim2act-venv/bin/python /tmp/f2-local-candidate-independent/csv_probe.py cold
```

两个命令分别作为独立Python进程运行，退出码均0。第一条使用全新自有 `csv-data` 目录，实际loopback HTTP从空应用目录创建项目、CSV、应用，准备/确认Release、创建实例、明确提交AppRun，通过原Demo.once调用normal Worker及NeverModel：

- `result.sum='30'`，count=2，result_version=1。
- Run：`run_57e37e16af0b4e4cb1c6e04bc8223577`。
- AppRun：`iapprun_a439dbc2a47f43f4a51655ba3cbe0a62`。
- app：`app_9320079eb83741c5a13d45dd5a99ca6a`。
- Release：`irelease_befd88bcd2ec415f971087514b5b561f`。
- instance：`iinstance_2498250f860fa424396dda793e8f5568`。
- 恰好1次Worker.once、1条CLAIMED、fence=1，SUCCEEDED。模型attempt=0，mock transport调用=0，真实模型请求=0；没有任务重试。
- 第一进程12条实际HTTP请求含完整请求体、status和响应体，原件 `csv-prepare-http-raw.json`。关闭自己拥有的API线程/Store，进程正常退出。

第二条命令重新导入包内组件、新建Store和只读loopback API，仅发8条GET，重新读取页面、metadata目录、精确app/Release/instance/Run。读取到同sum、同v1、同执行Run与AppRun；typed.run_id精确关联AppRun id。比较关闭前、冷读前和冷读后全库持久行完全一致；不启动Worker，不发POST，model attempts仍0。

原始证据：`csv-prepare-proof.json`、`csv-cold-proof.json`、`csv-before-close-snapshot.json`、`csv-prepare-http-raw.json`、`csv-cold-http-raw.json`，以及两个 `.log`。合成数据库仅留在本代理/tmp，不进入交付包。独立驱动为 `csv_probe.py`，没有改变原Demo源码或调用完整Demo.run。

## 普通PG边界

同解包src的额外两条轻检查均通过：无test_only的普通Store拒绝SQLite；普通Settings.from_env明确SQLite配置也拒绝，仍要求PostgreSQL应用角色URL。只在独立进程内设置合成测试环境，没有读取或修改实际配置，也没有连接PG。原始错误回执在 `ordinary-pg-boundary.json`。

## 本轮范围限制

没有执行全量prepare、自然P-A/P-B、锁矩阵、全新venv安装、wheel运行导入、Windows、PostgreSQL、原生浏览器、真实模型或真实语义验收。父级的完整5mock自然链及fresh-venv安装应单独记录，不能合成本代理已执行范围。归档未修改、仓库无写入；无剩余阻断。
