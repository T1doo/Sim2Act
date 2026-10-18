# 首版直接换已有授权材料 — 独立有限终验

**LIMITED PASS。未发现本片剩余 P1/P2。** 仅签原 spec1/Goal1 直接 A→B 的已授权合成 CSV 正向切片，不签整体F2、真实语义、LIVE或后续归档/提交/推送。

本轮不是“同一CSV换列”的重复。实际起点是API准备的原Release1/Goal1，尚无Run、先行列改版或采纳。夹具在初Release、测量及derive之前**明确预置两项App/B权限**；普通App给B追加授权的UI仍NOT_IMPLEMENTED。产品操作没有新增Grant、executor、Store/Worker、DDL或权限，所有阶段原Grant逐字不变。

## 最终源码和原件

作者seal文件SHA256：`7f858795b1b9ffdc54776b7d177aca13f22a6e4c74053c53677f831cc15c43e9`。2413普通路径/81228636B准确列举：独立哈希 **2397个非DB文件/67396444B**，16个物理SQLite文件仅stat，24个symlink仅readlink；树成员精确匹配。不宣称独立读取或重算DB内容/哈希。

九份当前交付文件与`final-source-hashes.json`全部吻合，完整九SHA在`final-verification.json`。作者没有`final-source/`九文件副本，不能补称存在；143份实际运行副本位于`qualified-installed/execution-source`，已独立哈希并核执行前后143项和fixture/runner相同。执行后仅FirstMaterial说明文档追加实绩，post-execution-doc-bridge与当前实读吻合，包/runtime/tests不变。

最终wheel942732B，SHA256 `f034a382ffd4860c775d7f953238a3f61336e8b2e922426c5a3a696510c476e7`；139个包文件在wheel、安装venv和当前源码逐字相同。相对上一片仅三产品路径变化：material revision、共同修订UI、synthetic launcher，其余136包文件保持；没有运行作者venv或导入产品。

## 实际通过范围

最终专用API **3 PASS / pytest17.77s / 外22.379571s**。执行M源码与当前一致；测试后仅两条import排序，独立精确重构匹配原执行SHA并核非import AST/绑定相同，重构文件不是原runtime副本。闭合JSON独立重算完整55表、精确preview/seal scope/key/body/全部指纹、原Goal完整快照、SOURCE+ACTION/APP、B权限前提、锁拒绝零写。第三节点的同事务深拷贝/写失效/跨事务重建来自实际通过断言及导出flags；撤权拒绝窗55表独立全等，不冒称独审运行缓存。

安装后真实loopback/JSDOM原页面 **21检查/84HTTP（75GET+9POST）**；新进程冷页 **9检查/56GET**。分别观测242.336609s、107.751435s；本窗口整页观察上限900s按三个原300s Run说明，原terminal18s、产品Run/lease不变，旧300s失败不改签。两个进程均exit0/STOPPED cleantrue。两页各有一个项目绑定`/protocol/contracts`400 RESOURCE_UNAVAILABLE（Evaluation asset unavailable），不称所有HTTP成功；原生/视觉浏览器未跑。

独立重构全部**140响应SHA**，包括86个原JSON响应及安装包JS/CSS/静态HTML；两页各25脚本和CSS匹配wheel。实际路径：原A30/v1→首版材料入口显式选B/amount→SOURCE+ACTION和APP独立CHECK B350/check实例v1→单独Release2批准保存→原业务iid采纳→显式新Run B350/v2→同Run owner sequence0/PENDING。没有Goal PUT、先行列修订、自动采纳或DECIDE。

精确业务iid `iinstance_01ba1607d3ea7fd596f6c60f3f541665`。旧Run `run_e02a6c32943c46eaaad2319c49416470`，CHECK `run_2e204270d3c64b15ac4ae92a32be9f48`，新Run `run_ecf2df76c088464f92d56e4c3fcabeef`；三个原Worker CLAIMED均SUCCEEDED/fence1，模型Attempt/Reservation0。纯CSV/Decimal独立算A30/B350，核真实材料hash、原Goal1完整provenance、原/新Release、bindings、typed数据/指纹、同iid修订1→2/业务数据1→2及旧历史行保留。预览仅双锚和心跳可变，其他53表保持；冷页54个非心跳表逐字相同。原Goal资源A仍是来源记录，新有效绑定与Run明确用B，语义UNKNOWN、无真人签收。

## 必须保留的失败和限制

- 两个混合API批次分别180/240s FAIL_TIMEOUT；旧adopted完整兼容第三节点两次NOT_COMPLETED，不能算PASS或推定唯一原因。独立锁诊断因误期望409而FAIL，实际正确LOCK_CONFLICT400，只有断言更正。
- 首安装runner在第一个fixture HTTP之前Headers.update关键字TypeError而FAIL；workspace初始化已发生。第二安装窗口terminal18s观察FAIL，后停机新Run PAUSED且无业务Btyped。fair窗口整页300s FAIL；增量page原样RUNNING/18检查，末POST202受理，停机PAUSED/无业务Btyped。原A/CHECK通过与这些尾部未完成分开；等待gate的ASGI取消原stderr保留。不能据此唯一断言饥饿/竞态。最终PASS是新软件新fixture/新ID，未续发旧键、重签或放宽软件门。
- 首Ruff I001导入排序失败、只读剖析Settings.limits错误及汇总SyntaxError等保留为工具/观察器事件，不改成产品通过。自身六类纯查看器字段/路径假设错误和修正亦全部保留；原stderr或明确工具文本转录来源见各observer文件，修后只纯文件审计，无新产品运行。
- 同进程调度和同事务证明复用已静审，不认证通用公平性、取消后sync线程已完成、外部进程/renewal线程、PG并发或跨事务缓存权限。未跑Windows/native、真实语义/人工签收、PG、远端CI、LIVE或正式发布；真实账户来源仍SOURCE_MISSING。旧满盘最后独审缺证仍NOT_RECOVERED。

方法和机器结果：`final-file-verification.json`、`final-installed-json-verification.json`、`cache-api-qualification-bridge.json`、`cache-api-json-verification.json`。独审只读源/封存文件/JSON/CSV/zip/hash/stat/readlink，无产品测试、Worker/model、SQL/DB内容或哈希、Git/auth/network、私有holdout访问。归档/raw副本和后续commit由作者单独核验，不在本独审背书内。
