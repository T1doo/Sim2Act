# Linux 本地限制候选

源码 `5db5a71fe3cf73efe9a0201545a5427835ba09bb`。保留旧 5af 包；此包不是 Windows EXE 或完整 Release。

| 文件 | 字节 | SHA256 |
| --- | ---: | --- |
| Sim2Act-local-candidate-5db5a71fe3cf.zip | 3562876 | a029c25a8e60e65a94e245e5031f5b2fefe10a1f972e2d49d7362f45f55d4104 |

Linux x86_64、CPython3.12、已有 requirements.lock 依赖。包不含 Python/依赖；本轮离线复用已有依赖，未新下载。

解压后，在该已有依赖环境执行：

```sh
python -m pip install --no-index --no-deps wheels/sim2act-0.1.0-cp312-cp312-linux_x86_64.whl
python -m sim2act.cli synthetic-workspace --new --data-dir "/绝对路径/新工程"
```

父目录已存在，目标必须新目录。用 READY 的回环 URL，公开合成登录 `public-synthetic-blank-workspace`。创建项目 → 保存 CSV `item,amount`／`A,10`／`B,20` → CSV 预览建草案 → 批准内部发布 → 创建实例 → 选择 amount 执行，得到30/v1。已验证同键不重复。SIGINT/Ctrl+C 等 STOPPED/clean/exit0；同目录不加 --new 重开，结果相同。普通 CLI 每次使用当次 READY URL；桌面稳定 origin 协议另行验证。

默认模型关闭，任意自由目标明确拒绝。已有 `--exact-read-live` 仅开放显式单文本逐字合同，使用已有 token、固定免费 Intern、0 付费 fallback；真实2次调用证据绑定31源码，不能冒称本包新 live 验收。原30秒 worker 租约现在可独立有界续租，完整提交屏障保持；大型保存与本包源码/二进制的具体版本边界、长锁和绝对预算风险见[证据](../../docs/evidence/lease-control-final-fence-20261101/README.md)。正式 PG、Windows、整体语义未验。

四个原生扩展实际加载且字节匹配 wheel，安装后32项相关回归、CLI/HTTP保存/去重/关闭/首次重开通过。包只含允许的源码、文档、模板和 wheel；不含数据库或实际凭据。manifest 的 BUILT_NOT_ACCEPTED 保持原构建记录，安装后证据单列。

停止服务后，在安装它的同一环境运行 `python -m pip uninstall sim2act`，只移除应用；数据目录、导出、日志和共用依赖保留。已在自有隔离环境实际验证卸载及工程文件不变，没有清理用户工程。
