# 限制候选：安装、启动和保存重开

此包包含当前精确Git源码、应用wheel和构建／使用脚本，不包含数据库、模型令牌、虚拟环境或依赖wheelhouse。应用版本0.1.0仅表示开发版本，准确候选身份以 `candidate-manifest.json` 的完整 `source_commit`、wheel tag及文件SHA256为准。默认模型关闭；不是正式Release或完整自然语言产品验收。

## 已支持的环境和安装

本轮目标为 Linux x86_64、CPython 3.12，已有与 `requirements.lock` 一致的依赖环境。Linux原生wheel不能装到Windows。没有验证干净机器下载依赖；本包不会自动联网安装依赖、创建凭据或改变系统权限。当前Windows宿主源码可供后续构建，但这里没有新版已验EXE。

在解压根目录，使用上述已有依赖环境的 Python：

```sh
python -m pip install --no-index --no-deps wheels/sim2act-0.1.0-cp312-cp312-linux_x86_64.whl
```

这是有依赖环境上的应用安装，不是免安装运行时。缺依赖应先核已有 `requirements.lock` 环境，不要把缺项当模型失败。安装后可离开源码目录，以同一个 Python 启动；`python -m sim2act.cli`与已安装的`sim2act`命令是同一入口。

## 一次启动、停止、重开

默认本地入口不读取模型令牌，提供合成CSV固定工具及持久工作区：

```sh
python -m sim2act.cli synthetic-workspace --new --data-dir "/绝对路径/新的合成工程"
```

必须使用尚不存在的新目录，父目录须已存在；不会覆盖既有目录。看到 `SYNTHETIC_WORKSPACE_READY` 后，在页面打开其中的回环 `url`，用公开测试登录 `public-synthetic-blank-workspace` 连接。Linux这里是服务页面入口，不冒充Windows独立桌面窗口。

需要本次已验的有限真实文本目标时，先正常退出默认服务，沿同一个目录加显式参数：

```sh
python -m sim2act.cli synthetic-workspace --data-dir "/同一个绝对路径/合成工程" --exact-read-live
```

它只复用进程已配置的非空 `SIM2ACT_INTERN_TOKEN`，为空时用 `INTERN_API_TOKEN`，不会自动读.env。不要把令牌放进包、命令行或网页公开登录栏。缺已有令牌会在创建／打开工作区之前明确失败；默认入口依然可用。endpoint与model固定为原免费Intern及`intern-s2`，没有付费fallback。

1. 普通“项目”工作区创建项目；材料保存一份TXT／MD，例如两行 `Keep every line.`、`Save the exact text.`，保留最后换行。
2. “任务”表单选择“完整读取所选文本”的逐字合同，只选这一份材料，提交。固定目标由页面明确显示；不能把自由目标偷偷改成该合同。
3. 模型执行一次原授权`resource.read`，再返回仅含`content`的严格JSON。新请求的direct.v2协议明确要求不加解释／Markdown围栏并正确转义换行；旧协议仍使用原提示和原键。独立核对全部原文和保存证据后，才显示`SUCCEEDED / PASS_EXACT_READ_CONTRACT`。模型格式错误明确报`MODEL_OUTPUT_INVALID`，原响应／回执保留；不剥围栏、补造结果或自动重试。超时或未知用量也保留失败。
4. 在终端按Ctrl+C，等待`SYNTHETIC_WORKSPACE_STOPPED`、`clean:true`及进程退出。数据目录保留。页面关闭本身不等于取消；取消要使用任务的原取消入口，未知结果先读状态。
5. 用同一路径、同一启动模式重开，**不要再加--new**。普通CLI使用本次新READY URL进入，从历史选择同一Run查看结果；原任务和数据库请求键保留，但默认随机端口不保证浏览器中的原键记录仍同源。未知提交先读服务器历史，不要直接创建新任务。需要复用同一浏览器origin时，首次及后续启动可显式使用同一个自己选择的未占用 `--port`；不能据此找回旧随机端口中的浏览器记录。已验的桌面owned-stdin入口才有保存端口、独占重绑／拒绝占用保证。目录链接或身份／schema不符会停止，不初始化既有数据。

自由目标并无通用语义完成器：默认工作区会明确拒绝不支持的模型任务；普通F1工具链的`PARTIAL / NOT_RUN`不代表任意目标完成。只有事先选择的单文本合同能按上述确切范围判定，通用语义仍NOT_RUN、人工确认仍PENDING，正式发布关闭。

## 仍有边界

本包不开放正式PG、不代创建principal／project／trial／approval／account，也不自动启用自然应用生成。大型Cold原30秒目标尚未稳定达到；不能用小文本耗时替代大型Cold验收。旧8秒真实超时与UNKNOWN账本仍保留，新的25秒单请求上限只属于新有限协议且不能越过原租约／任务截止。当前源码真实调用与独审证据另保全于开发仓库的`docs/evidence/intern-exact-goal-live-20261031/`，不随此包带入数据库。
