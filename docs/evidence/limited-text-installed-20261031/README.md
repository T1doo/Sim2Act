# 从实际安装包启动的有限目标

候选源码 **6424cc040bc8da7fd7f1c86130e30b0f95598594**，Linux x86_64／CPython3.12.14，应用版本0.1.0。`src/`、`setup.py`、`pyproject.toml`与已验 `fc978d312bc2aa1e2871aea1f2b38e5d415736c3`逐字相同，原386项回归证据保留且没有重签为本轮重新跑过。此提交修的是打包闭包和使用入口：setup已有4扩展，旧候选白名单／数量门仍只认2，已完整列入并按4实编；缺一个也拒绝，Windows／Linux tag仍分开。

## 包和安装身份

[候选包与清单](../../../deliverables/limited-text-candidate-20261031/README.md)。ZIP 3,184,682 B，SHA256 `ee5c85fa70a33cb3f823c0ed91f56c2fb8e7d2726f4f24a694e58da85264baf0`；内含wheel `sim2act-0.1.0-cp312-cp312-linux_x86_64.whl`，SHA256 `c97358e079bd44bea547435f46bb9556689235fcf6680c507e56f130aa8f62c7`。

只从干净Git blob白名单构建。pip参数 `--no-index --no-build-isolation --no-deps`，零依赖下载。首次构建因Python配置`clang -pthread`但环境没有clang，optional扩展未产出；严格数量检查拒绝，没有生成合格ZIP。原失败wheel保留于scratch，日志和原SHA=e7b50d6ff6c624df8589a617279d5ad143fea47eba3ed90134d9825e6f0314b4在本证据；没有覆盖成通过。随后仅为该次命令指定已有`CC=cc`，未安装编译器或修改系统配置，四扩展全部构建。

wheel通过本机已有pip离线装入**全新venv**。测试通过显式一行.pth复用原有锁定运行依赖目录；没有下载／复制依赖wheel，不能称干净机器依赖安装。服务/probe使用新venv的 `python -I -B`，cwd在scratch，sys.path无原`src`，7个实际运行模块路径及SHA逐Git blob核对。4个`.so`均实际导入自新安装目录，内嵌源码SHA按各完整C/header/Python输入重算匹配。原包223项库存、wheel源字节及原生字节均核，不含数据库、.env秘密、虚拟环境或历史大证据。

## 实际正常入口

普通无`--control-stdin`、无live参数的新安装CLI正常启动。经真实回环HTTP创建项目和文本材料，提交自由目标，按默认能力返回`FAILED / UNSUPPORTED_CAPABILITY`，0真实模型调用。用实际SIGINT（模拟终端Ctrl+C）退出，两次服务均STOPPED clean／exit0／双EOF；首次新进程重开持久结果一致，相同键仍同Run、没有重放。普通CLI端口实际48961→52667，所以文档明确按每次READY URL进入，不混用桌面owned-stdin的稳定origin保证。完整原输出在 `default-cli/`。

显式有限目标仍走正常表单对应的API：唯一TXT／MD、事先声明逐字合同。运行的是已安装应用，不是repo中的可编辑源码。原固定Intern endpoint/model、已有注入令牌、零修复／无fallback。

| 项目 | 实测 |
| --- | --- |
| 新Run | `run_c4e3e59e864d4ea6aec4ddbc8f40e4b1` |
| 结果 | `SUCCEEDED / PASS_EXACT_READ_CONTRACT` |
| 本轮新真实请求 | 2，均LIVE／RECEIVED、返回Intern-S2且身份校验通过 |
| 已知用量 | 1477 tokens，仅这两次 |
| 目标轮询时长 | 5.161354秒，不是大型Cold耗时 |
| 工作执行 | 1次原授权resource.read，模型全文独立逐字核对、保存 |
| 首次新服务重开 | owned-stdin同origin、完整结果／原键一致，无重放 |
| 两次关闭 | 原STOP协议、同worker、exit0、双EOF、clean／数据保留 |

输入为两行合成英文 `Keep installed sources exact.`／`Preserve the final newline.`，末尾有换行。没有结果注入、MockTransport、补造回执或自动重试。仍用同一原工作区／quota subject，初始8秒UNKNOWN一笔及fc978成功两笔全部逐字段保全；加本次2笔，共5个Attempt／Reservation，4个RECEIVED与1个UNKNOWN，见closed-ledger-summary。首次新进程HTTP回读新结果之前，SQL只读过旧历史保全行。实际脚本、installed module SHA、启动命令和输出见 `installed-live/`。

## 检查结果与保留失败

打包／平台／清单／旧候选本地服务相关回归 **44 passed，0 skip**。额外从新安装运行原生测试得到 **17 passed、12 failed、28 skipped**，没有写成全部通过。12个失败都在完整Source代码门处拒绝：被复用的图fixture会替换受保护的`apps.compile_preview`等生产者。源目录同一图套件对照也是相同12失败／10通过；独立fresh import确认原生产者verify_code=True，临时替换compile_preview=False，恢复后=True。未放宽门、删除／跳过这些断言，也未据此宣称完成fixture重写。28个skip属于需要另行显式构建目录的旧实验`_cold_typed_native_impl`测试，本次未请求该实验，不能当当前4扩展或生产路径通过。原始失败、对照XML和边界探针均保留。

因此这里只验**声明的单文本目标和默认CLI生命周期**；大图Source／Cold的这些fixture仍是未闭合验证范围。4扩展导入／hash不等于全部原生业务通过。默认关闭的实验cohort没有启用。普通模型、自然应用生成和正式发布依然关闭；通用语义NOT_RUN、人工确认PENDING，原30秒目标仍不稳定，且旧30秒结算尾窗另有已复现待修安全边界，均不以这个小目标冒充解决。

没有Windows CI／用户电脑操作／系统runtime安装／新凭据／权限／费用或Release。新版Windows、正式PG、完整大型Cold live没有验收。支持环境安装和一次启动／停止／重开命令已经随ZIP封入 `docs/LimitedTextCandidate.md`。
