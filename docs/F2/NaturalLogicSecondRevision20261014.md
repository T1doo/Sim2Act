# 第二次自然规范局部修改：R0 → R1 → R2

接续父级已审 `bc5da99d6c7449900a89b75b6fb8ae957d43ecec`；root 为唯一产品源码写入者。依据原 V5 产品 §9.3 与 F2-T07，本轮只实现 requirements → qualifiers 的 prior_items/prior_feedback 和对应 depends_on 开关，最多两次明确修改。R3 预检拒绝；反向 R2 即使 recipe 与 R0 相同，也必须新 CHECK、隔离实例、独立明确批准和新内部 Release。

冻结两层合同：原生成 draft/来源标记、Goal/材料和当前授权原图锚保持不可变；另外冻结已完整验证的父 Release/来源指针、R1 有效候选指纹与 R1 有效图。R1 图由已授权原图的同一组稳定 ID、外部版本与当前人工锁只读重建，不替换持久原图。应变集按该父有效图及 qualifiers 的实际 revision/content fingerprint 计算；APP UNKNOWN 保守整应用重验，PROJECT UNKNOWN 仍拒绝。五个其他 action 定义逐字节保留，不把它们误称为图 retained_objects（整应用扩验下该集合可以为空）。

新 revision 3 明确绑定第二层 logic_revision 标记；旧 R1 双字段标记和 revision 2 格式保留。入队器要求 CHECK 的 Release ID/指纹精确等于预览父 Release，且检查实例与来源实例不同；使用既有普通 Worker 和完整六步 readback。版本确认再次完整检查。旧原始 draft、稳定 app/action/step ID、Goal、材料、历史和原限额保持；无新的执行器、权限、模型或预算。

两层来源/祖先 CHECK/current CHECK seal、完整执行摘要、权限和来源批准继续逐事务重验。反向 recipe 相等不取消版本来源证明；无来源版本仍须匹配原 recipe。来源及 CHECK 实例的原切换 pin、循环与版本/CAS 检查不变。原 deadline、取消/撤权、reservation/settlement/SAVE 和迟到回调守卫保持。

页面从原 candidate 有界重建一/两次有效候选，独立核原锚与有效图的完整节点身份、definition、revision、拓扑边及上游版本指纹。R1 可预览第二次调整，R2 不显示第三次修改；新材料使用仍要求自己的精确 Goal/材料/权限确认。未知回执只按原 key GET，不重发 POST。

失败历史保留：旧 bc5 的第二预览被 UNSUPPORTED_CAPABILITY 拒绝；首候选第二 CHECK 被旧入队器限制拒绝；第二候选的反向 R2 新材料入队被旧 recipe 不等式来源判断拒绝。独审发现的页面节点哈希与身份校验问题已修。漏表导入被 Ruff F821 发现后受控中止 r2-third，return2，验收 0 PASS；该不完整 JUnit 条目未带 failure 属性使原 runner raw pass 字段为1，原输出和显式更正分类均保留，不能算完成通过。纯合同测试两次夹具错误（缺 Goal、错误 project ID 前缀）各7FAIL，修正后7PASS，不改写旧记录。

首页面业务链的32断言已完成，但 pytest FAIL：关闭 JSDOM 后仍有完整异步读回继续访问文档。该轮不算页面 PASS；测试收尾改用既有 owned-page lifecycle drain，不改产品代码。曾提出的定时器无限排队推测未获因果证据，独审指出 showInternalRun 的同步 view.run=null 会抑制后续 ticks；已保留否定结论，未扩大轮询修复。

源码冻结 `847576d1933c12b63d9d40bcf59a5aba8f92fb1b`，core `19d6470fa68ce8f2c9fdf7c91eaf1862ef5e97b3`，77项资格 pin `9bef1d9f7bc31a75d4681af8d745f1250b6acc1a25652a753a151859ac894661`。原 baseline/anchor、config 排除及 pin-only 规范化不扩大；所有完成套件的467源码/测试/pyproject闭包前后零变化。实际终态见下列唯一身份索引；历史候选数不累计。

真实/付费模型0；人工验收PENDING、语义UNKNOWN、正式发布false。PG缺现成授权服务/连接仍NOT RUN，Windows/native/真实模型/人工语义/完整产品验收/实际旧源码升级/远端CI/部署不提升。/opt/containerd与既有私有UDF/诊断拒绝保持停止，不重试/提权/换工具环境。原 main/core 与旧 owner WIP 不改。既有 old cutoff/new lease 活性边界仍为未复现假设，本轮不修、不称漏洞。

页面额外失败记录：page-drained 为1PASS/1FAIL，正常场景通过，lost 因测试 owned lifecycle 将未标记的合成网络丢失记为异步错误；只给指定 CHECK/version 合成丢失加 controlledAcceptanceLoss 标记。page-lost-corrected 又因继承的 dropCorrection 额外注入新材料响应丢失而 FAIL，32业务断言不等于整例通过；关闭该无关注入，保留全部旧记录，未修改产品源码。最终 page-lost-final 实际1PASS，36检查/37可见操作/3启动/60资源；正常场景32检查/28操作/2启动/40资源。独审逐一重算100资源的当前源码SHA和200状态，两个唯一页面身份合计68检查/65操作/5启动。恢复只读原key，不重复提交 CHECK、批准提交或新材料执行。

具体入口：`src/sim2act/natural_logic_patches.py` 的 context/effective/preview 合同；`natural_specs.py` 的有界 revision 标记；`lifecycle.py` 的完整来源读回；`app_jobs.py` 的 CHECK 精确父 Release 入队绑定；`pb_natural_uses.py` 的反向 recipe 来源发现后完整验真；`web/internal.js` 的有效父图预览、明确确认与冷恢复；新增 `tests/test_natural_logic_second_revision.py` 的两方向真实 Worker 与冷新材料用例。正常 Graph/Worker/事务执行链复用既有实现。

P-B 新完整用例实际1PASS，755.856秒：任务派生应用 R0→R1→R2、两次独立 CHECK、反向 R2 revision3/new Release、冷实例新材料，原 draft 保留；四次 Worker 完成回执与独立公开标量保留。逐 suite467闭包零变更。

原有局部修改 `tests/test_natural_logic_patches.py` 实际9PASS/0FAIL/0SKIP，取消/撤权/人工锁/精确key恢复和独立确认的既有合同继续通过，467闭包零变化。修改文件 Ruff PASS，`internal.js` node语法 PASS；mypy78源码仍5个既有错误（status_report.py3/tools.py2），不得称全项目静态检查全绿。

原有切换依赖 `tests/test_logic_switch_dependencies.py` 实际8PASS/0FAIL/0SKIP，374.26秒 pytest/375.816秒外层wall：多层/循环边界、外来身份、三种失败事务回滚、实际采用修改逻辑且保留历史、长链有界与无关实例仍可读。source467闭包零变更。

最终验收索引为 **64个唯一PASS / 0最终FAIL / 0SKIP**：资格合同29、P-A双方向2、边界11、页面2、任务派生P-B第二修改1、原局部修改9、切换依赖8、普通P-A/P-B新材料2。最后普通使用实际2PASS，226.841秒wall。每套467闭包的完整before/after映射及当前HEAD一致；没有为终态再改源码。page-drained原混合suite仍1PASS/1FAIL，只接受其normal身份；lost唯一验收来自page-lost-final。历史20个pytest失败身份（3产品候选、14夹具、3页面失败）及1次受控中止仍保留，不混入本轮64PASS。早先pure-contract-valid7PASS为旧HEAD重叠合同，不重复统计。

[机器索引](../evidence/natural-logic-r2-20261014/SUMMARY.json)列出精确用例身份、各套退出码/XML SHA、467闭包和页面计数；[独审终稿](../evidence/natural-logic-r2-20261014/REVIEW.md)与全部原始日志/失败/命令/夹具/公开标量封存于本轮专属归档，旧heartbeat与旧证据归档未改。

最终独审接受该有限工程切片，独立重算64唯一身份、每套467完整before/after/current映射、77资格指纹和100页面资源。终稿SHA `2737f5f50f02e2f2016fec418eee66508878e5620a9f131c81a430c09cdca5f1`；独审manifest SHA `da1f52b434fe3a0671f7da5e7b0767373f6c1c92a73d5da473e66f9ba76b3d6f`。独审未额外运行Worker/测试，未读DB、私有证明体或已拒诊断。

[完整归档](../evidence/natural-logic-r2-20261014/natural-logic-r2-evidence-20261014.tar.gz) SHA256 `8b3233b1e152beafbe942966bb807c4f0c85d97ef6f44e483fe00a74b2c71c56`，14419273字节；2051个普通文件成员逐一回读大小/SHA核对，解包原字节总量104470099。归档内MANIFEST包含每项大小/哈希，排除符号链接。归档只含本轮新证据；未替换旧被拒候选或旧归档。源码冻结后追加仅文档/本轮证据。
