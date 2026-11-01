# Linux 限制候选：可用范围独立交付

源码 `5af351804a33171ca06b8136c56047cb677265b3`；后续证据提交不会改变此包。保留旧35e候选，当前包不是完整产品Release或Windows EXE。

| 文件 | 字节 | SHA256 |
| --- | ---: | --- |
| Sim2Act-local-candidate-5af351804a33.zip | 3416609 | 7c80f29c1e107430dd29a43740048c3f4011e06e38444ef1d4743a88c7e94af4 |

Linux x86_64、CPython3.12、已有requirements.lock依赖环境。解压后使用该环境：

```sh
python -m pip install --no-index --no-deps wheels/sim2act-0.1.0-cp312-cp312-linux_x86_64.whl
python -m sim2act.cli synthetic-workspace --new --data-dir "/绝对路径/新工程"
```

父目录已存在，目标必须新目录。打开READY中的回环URL，以公开合成登录 `public-synthetic-blank-workspace` 连接。创建项目，保存CSV `item,amount`／`A,10`／`B,20`，CSV预览创建草案、批准发布、创建实例，选择amount执行，得到30/v1。已验证同键不重复、Ctrl+C等待STOPPED/clean/exit0、同路径不加--new重开结果不变。页面关闭不等于取消。

默认模型关闭；自由目标明确不支持。已有 `--exact-read-live` 仅支持显式单文本逐字合同，复用既有环境令牌，固定免费Intern、不付费fallback；本包安装验收0live，不能沿旧源码真实调用记录冒称本包已验live。

此包四原生扩展实际加载且比对wheel字节，安装后32项PB检查通过；大型完整链使用同源工作区构建通过，未在新wheel二进制上重跑。原30秒大型路径仍预算拒绝，不影响已验CSV范围；Windows、正式PG及任意目标未完成验收。包内manifest保留构建时BUILT_NOT_ACCEPTED，以上安装后证明另存仓库，不篡改已测试包字节。

停止后可在安装它的同一Python环境 `python -m pip uninstall sim2act`；仅移除该应用，数据目录、导出、日志及共用依赖保留。本轮只在自有隔离测试环境实际验证卸载，未清理任何用户工程。

完整边界、失败原件、保存／首开／取消证据见 [本轮验收](../../docs/evidence/pb-contract-owned-default-20261101/README.md)；更详细使用步骤在包内 `docs/LimitedTextCandidate.md`。
