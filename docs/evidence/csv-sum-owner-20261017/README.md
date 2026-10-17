# 单步 CSV 的本人适用范围声明：有限交付证据

基线为父审已准入的 `b8725ced5c963d26c74513c3eb10254623c47d18`。生产功能冻结于 `854e52b72d87710f18c39119ff4379f9afffc8b9`，测试精炼提交为 `d6255ee782ddd84aeabb31ffac782376defa5871`。后者仅改一个测试文件；122 份生产源码及其他 596 个作者输入与前者逐字相同。交付提交随后只加入本文、使用说明和证据，不宣称在最终交付 HEAD 重跑全部测试。

用户从应用目录打开单步 CSV 实例，运行前明确勾选“仅求和、不含 MD”后，原请求、不可变运行 binding 及独立冻结事件共同固定材料/hash、列、Release 与适用范围。新 Run 成功后在同一结果下逐项接受/拒绝、填写理由并另行确认；旧 Run 不能补签，新结果不继承声明。原普通完整 MD 合同、来源 PASS 和人工历史不进入新声明。技术 SUCCEEDED、独立求和 PASS、人工 ACCEPTED/REJECTED、目标语义 NOT_RUN/UNKNOWN 和发布关闭分别保留。

复用已有 `run_ledger/run_payload/run_append/scoped_run_submit`，新适配器使用两张独立 per-Run CSV 账本/seal 表。当前身份、项目、实例、实际 Run/AppRun、独立 ACCEPTED 锚及多个来源标量在正文前校验；材料读取和聚合由现有双主体权限网关鉴权。准备和提交末重复核对真实输出、typed record、operation intent/receipt、Release、版本、授权及有效期。没有新 executor、权限动作、Grant 类型或自授权路径。测试备用材料的额外两个 app-runtime Grant 属于合成夹具，不能将整个夹具创建过程描述为零 Grant。

普通应用预览只有可信聚合与类型校验；内部版本准备、Worker 及声明证据核查使用既有独立求和 oracle。排队撤权仍是 WAITING_RESOURCE/GRANT_REVOKED，本轮没有将其改称 FAILED，也未重复其恢复矩阵。

## 准入分母与精确执行版本

作者和独审最终均准入 **21 个唯一节点**：`854e52b7` 实际原 18 项 + `d6255ee7` 实际收紧 3 项。两轮冻结批每方实际执行 24 次节点，其中 3 次重复；不是 24 个唯一节点，也不是最终测试 HEAD 全 21 项重跑。

| 批次 | 作者实际 JUnit | 独审实际 JUnit | 最终取用 |
| --- | --- | --- | --- |
| 854 原 API 14 项 | 14 PASS，40.462s | 14 PASS，46.535s | 其中 11 项 |
| 854 新页面 3 + 既有回归 4 | 7 PASS，129.669s | 7 PASS，126.152s | 全部 7 项 |
| d625 收紧原 3 参数 | 3 PASS，6.200s | 3 PASS，7.238s | 全部 3 项 |

作者原两分片墙钟并行 132.943s，新 3 项墙钟 8.606s。作者每批 597 输入前后相同，独审每批 598=597+已有 gold fixture 前后相同且匹配 Git 对象；本轮没有重建/恢复旧满盘实例的缺失独审报告。

旧 854 全批动态绿色曾被独审标记 `SUPERSEDED_COVERAGE_BLOCK`：grant_redirect 当时没有给备用材料当前应用 runtime 授权，两个 receipt 类型参数当时在 PREPARE 后才损坏，不能区分对应旧缺陷。d625 只收紧这三个分支：备用材料在撤原材料前后都实际通过本人+runtime 的 read/aggregate 鉴权，只撤原材料；bool/float receipt 在首次 PREPARE 前损坏，GET 不给正文、PREPARE 409、无账本新增。独审核对 delta 后仅复验这三项，最终 `PASS_BOUNDED`。旧绿色原件和覆盖不足报告均保留。

新 API 14 项覆盖：运行前固定范围；逐项显式接受/拒绝、顺序/理由、并发同键唯一效果及异体冲突；精确 Run/Release/结果版本；旧 Run 不补签、另一 Run 不继承、错实例/账号；当前授权/重定向/typed record/有效期/seal；提交末撤权整笔回滚；首次准备前严格 JSON 类型；coherent 重算旧 binding/Run/AppRun 指纹仍不能补出独立冻结事件；ordinary 完整成功合同派生 SUM_ONLY 应用的独立人工声明不改原报告。

3 个新页面均加载实际 HTML、CSS 和全部脚本，通过可见 DOM 手势与实际 ASGI/SQLite/Worker 运行：deliver 16 检查/46 页面 API 回复；lost 16/45；navigation 18/56。合计 **50 检查、147 实际页面 API 回复、72 资产回复**。Worker RPC 与夹具操作不计入页面 API。覆盖默认不勾选、连续两次改列清确认、运行前显式提交、同 Run 结果与声明、实际接受 201 丢失后的原 key GET 恢复且只一次 DECIDE POST、工作区 preflight 迟到不提交、账号切换后实际接受迟到不接管、撤权清成果/历史数值/证明正文并显式撤回声明。

4 个既有回归仅为：普通 Goal 人工接受；自然规范 P-A 人工接受；旧四脚本 CSV 使用组件；b872 的普通成功 CSV→SUM_ONLY→内部版本/实例/目录/新输入 deliver 页面。准确命令、JUnit 和逐次请求见原件。新的主路径均为 NoModel；旧普通 Goal 使用 MockModel，自然规范回归使用合成 MockTransport。本组不宣称整个批次无合成模型响应；真实模型调用未执行。

## 原件与校验

[artifact-map.json](artifact-map.json) 记录 **318 份原始材料**的原路径、原长度/hash、存储路径及编码；[summary.json](summary.json) 提供计数与版本摘要。SQLite 和超过 1MB 的原件用 gzip(mtime=0) 保存，其余原字节保存，解码均与原件一致。94 份 SQLite 归档包含开发失败史、两方及两轮副本，**不是 94 个测试**。

- [作者 854 证明](raw/author/author-final/proof.json)、[API JUnit](raw/author/author-final/api.xml)、[页面及回归 JUnit](raw/author/author-final/pages-related.xml)。
- [作者 d625 证明](raw/author/refined-final/proof.json)、[收紧 3 项 JUnit](raw/author/refined-final/result.xml)、[测试 delta](raw/author/oracle-refinement.diff)。
- [最终独审](raw/csv-owner-independent-d6255ee7-20261017/review.json)、[独审证明](raw/csv-owner-independent-d6255ee7-20261017/proof.json)、[新轮原清单](raw/csv-owner-independent-d6255ee7-20261017/raw-manifest.json)、[旧轮原清单](raw/csv-owner-independent-854e52b7-20261017/raw-manifest.json)。独审两轮分别原 79/27 文件已封存停止写入，清单与各自 SHA256SUMS 原字节保留。
- [静态检查](raw/author/static-final/proof.json)：Ruff 6 个 Python 文件、mypy 仅新模块、node --check 5 个 JS 文件。
- [额外作者 SQLite 加法初始化探针](raw/author/additive-sqlite-probe/proof.json)：只在本任务红轮自己产生的旧合成库副本上运行既有 initialize，原 51 表全部行不变，只新增两个空 CSV 表，第二次初始化相同。它不属于 21 pytest 节点，也未由独审重复；没有执行 Run/Worker。第一次误用默认 Python 因无 sqlalchemy 在导入时失败，未开始目录/库复制，改显式 venv 后成功。

红轮实际 HTTP 422（csv_review extra_forbidden）及 837b2178 红测试原件保留。开发历史保留：首个 API 批 9 绿/1 断言路径错，首页面批 3 失败（测试手势/等待），dev2 12 绿/1 丢回执恢复失败，dev3 17 绿。提交末证明原本位于 error.submission_rejection，初断言读错顶层，未冒充生产修复。首次打包递归多带独审可重建源码快照，初包完整移至 workspace 外部留存；最终严格按独审原清单保留运行输出，见 [打包说明](raw/author/packaging-note.json)。全局 SHA256SUMS 排除的只有它本身，包含嵌套独审 SHA256SUMS。

## 未执行边界

只在 Linux 合成 SQLite、实际本进程新 Store/TestClient/Worker 对象及 JSDOM 页面执行；不是独立操作系统进程重启或原生浏览器。真实用户语义签收、真实场景/模型、PG、Windows、真实旧用户库迁移、远端 CI、部署、正式发布和完整通用 P-A/P-B 未执行。未重试已拒绝的浏览器下载，未访问或清理旧满盘实例，未调用真实模型或修改凭据/安全权限。
