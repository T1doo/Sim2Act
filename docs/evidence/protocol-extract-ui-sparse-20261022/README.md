# 受保护 UI 窗口的稀疏检出闭包

保留[上次 checkout 超时原件](../protocol-extract-ui-workspace-20261022/native-one-shot/README.md)：冻结 `3d4313cba1daf716d19ef2b3a7ed39ad0231982f` 的单次窗口没有进入 Python/API/Edge。日志显示全量 fetch 约41.4秒，随后展开48,479文件至48%时达到checkout自身60秒上限；不是鉴权拒绝，Node弃用警告不是该错误。此次不放宽原工作/清理/请求/保护上限，只修正准备层的确定性无关工作。

配置候选 `7085b94560c840d4f80b59ba6609f3ba5bcc8e89`，与 `b608895a09781bf15b13f8fe1beaca55c2446f5c` 相比只改窄job的19个非cone稀疏模式及新一次显式标记。foundation全量job、固定checkout/setup actions、public/ref/attempt1/只读权限、180秒从setup前开始＋共享10秒清理、完成POST≤3/业务GET≤30/静态GET≤40/截图≤4、无重跑及原保护均不变。`runtime-manifest.json` 绑定准备脚本、SDK锁和workflow；全部产品/控制器/清理代码未变。

固定 [checkout 实现](https://raw.githubusercontent.com/actions/checkout/11d5960a326750d5838078e36cf38b85af677262/src/git-source-provider.ts) 在 sparseCheckout 时自动设置 `blob:none` 并在 checkout 前设置非cone模式，减少无关blob和文件展开。当前完整树48,486文件的未压缩唯一blob合计3,798,989,558字节；清单实际选175文件，唯一blob4,815,366字节。它们是Git对象字节统计，不能当作网络传输或Windows时间。修正直接消除已见无关负担，支持再做一次有界验证，不保证60秒或后续SDK/Edge一定成功。

闭包包括全部src（Python导入、web及服务端固定JSON）、4个现有监督/audit脚本、实际driver、npm包与完整性锁、原Windows锁、workflow/.gitattributes/pyproject；仅封存process事实3件，以及 `protocol_reviews.ASSETS` 的 a-source/a-cold/b-source/b-cold 四份原始JSON。`windows_browser_ci.py --audit` 在任何fixture初始化前返回，不进入其全量 Source/Worker/agent脚本。没有把整tests、整browser harness或整docs/evidence纳入。

`probe.py` 在同一指定环境创建无网络、detached的Git测试树，使用本仓库明确的只读对象目录为alternate，实际运行非cone sparse-checkout；不切原分支、不创建第二写入者，不使用其他环境。175个选入文件逐件与冻结Git对象逐字节比较，无symlink回原树。然后使用 `-I -S -B`，只显式加入既有venv依赖及导出src/scripts，不运行site/.pth/editable；启动前无sim2act缓存、无editable finder，94个实际导入的sim2act模块来源全部位于导出src。audit拒绝原仓库业务源码/资产/DB读取及全部socket.connect，只允许原既有venv工具链依赖。导入实际API和launcher/audit模块，Windows WinDLL/token函数未执行。

最终真实ASGI验证 **PASS**：43个in-process请求＝15业务GET＋1完成POST＋27静态GET，复用原SQLite/sidecar；不初始化/迁移、不发送/保留/接受新候选、不创建Worker/Source/extract/Grant。读取真实项目、能力、材料、目标卡、应用、全部合同、历史、授权、两条原extract详情、正常静态页面及全部26个CSS/JS。移走固定b-cold资产后，合同读取按原HTTP400/RESOURCE_UNAVAILABLE拒绝，未借原树或前一响应缓存；恢复后通过。原普通提取接受事实完成后，严格按递归exact type比较原计划/原业务回执（含bool/int及list/tuple反例），仅runs/protocol_jobs/events改变、事件增4、其他账表及sidecar字节不变。原显式合成业务时钟及期限门不改。TestClient上下文退出、Store.dispose完成、child正常exit0。

本地先有一条闭包初验，随后对最终harness收紧strict输出和禁写bytecode；共两次隔离ASGI调用（各15业务GET/1完成POST/27静态GET），合计2次完成POST、30业务GET，0真实HTTP/socket、0Mock/模型/Worker。未重跑恢复37/20或任何G0前缀。初验原件留在 `/workspace/sim2act-ui-sparse-20261022`；最终原件 `/workspace/sim2act-ui-sparse-strict-20261022`，本目录 `checkout.json/result.json/probe.log/launch.log/postcheck.json` 为最终归档，选中源码在ASGI结束后再次逐件核字节相同。`opened`记录包括解释器尝试不存在的pycache路径，不能当作成功读取次数。

此结果只证明冻结候选的Linux离线运行依赖及语义路径；不证明Windows/.NET、已安装Edge/sandbox、真实DOM、网络速度、生产账户、G0/Cold2/W5或真实模型。独审通过前不启动新CI。新窗口与上次失败原件分开，新run目录，失败保全且不自动重试。

后续授权的唯一新CI已[完整归档](native-one-shot/README.md)：同60秒上限下稀疏checkout约7秒success，Python设置/Edge签名检查通过；实际Python进程启动前因多条PATH结果拼接失败，原生UI仍NOT_RUN，0业务/截图/模型。已独审最小精确解释器路径修复，但修复仅静态，未重开CI。本文 `runtime-manifest.json` 保持原7085/ba3候选事实绑定，新的PS源码hash和未验边界独立记于 `native-one-shot/repair.json`，不混充测试版本。
