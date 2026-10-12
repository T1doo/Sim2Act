# 两个旧锚到精确新 P-A 软件：执行证据

本轮基线6088dcfc93ecf9de48f10ab6a72b89ec4759fd91，新分支dev/pa-text-compatibility-20261012。
合同见[本轮有限兼容合同](../../F2/PATextSoftwareCompatibility20261012.md)。旧P-A交付与全部旧失败证据位于相邻pa-intern-provider-20261012目录，原字节不改。本片只有单节点字面检索及其当前模型图新材料复用，没有自主业务规划资格。

## 根因、原失败及对照

旧82项：70预检409、12未进原断言要求的完整历史verifier。新2模块首先阻断完整文件集合；五个非CHANGED核心文件摘要也变化。不能解释为82独立语义缺陷。
当前6088两代表实际2FAIL、1.05秒：[red](red.xml)/[log](red.log)。同时保存合成原SQLite。
已接受a4fd完整src/tests独立只读快照运行原两份测试：100PASS、84.80秒；416原文件post零变，[原map](baseline-a4fd-map.json)/[终态](baseline.xml)。不是从当前candidate重新签旧fixture。
修复后仍是原两份tests/旧fixture原字节：100PASS、213.95秒。原82逐全名匹配PASS，[映射](old-failures-to-current-passes.json)；36份[边界原JSON](author-boundary-proofs)包含full-verifier调用、实际SQLite私有cell校准、scope过滤与DB不变。原失败不覆盖、不改标SKIP。

## 完整精确目标

70个实现PY全部逐文件核：[review](file-review.json)。资格JSON SHA f247ef81b9ed40725cab07b89e0fe1f2b22caee88454bae663c13a9978f186c2，原anchor SHA24f26f3621b8fc49a24fa3566484b568148d9317f2d279d79f264416b994193a及CHANGED集合不变。只规范唯一顶层简单QUALIFICATION_HASH赋值的64值为零；其它字节不规范。重复JSON、非简单/嵌套/多写pin闭拒。规范目标不是实际运行/批准fingerprint；完整原字节70PY当前FP f3ae7559431c110462fa43aa433e7e16a81750f1c90a4b756b9c1964c0bbf95d。
两个既有源锚通过原完整性后，才核新固定完整target；不增加文件名豁免、未知软件不接受、不自动产生实例permission。原完整Goal/Grant/TTL/版本/历史/instance/key/原软件与当前软件精确consent继续在preflight/commit/Worker重验。原seal、原候选、历史与其它实例不改签。

424src/tests+pyproject=425条冻结map SHA a5ee13eff81d6226af7a9ce8dda7074ef9c4b459cf061db58a91e8a853923057。[before](candidate-before.json)/[after](candidate-after.json)0diff。src修改及实际测试结束后才commit/push。

## 作者实际终态

四范围307唯一=300PASS/0FAIL/0ERROR/7SKIP，互不重叠：

| 精确范围 | 实际终态 |
| --- | --- |
| 原test_text_continuations+test_text_continuation_boundaries完整两文件 | 100PASS，213.95秒 |
| 新资格/篡改文件 | 22PASS，0.85秒 |
| P-A provider25+typed binding12+页面4+rejected raw14+确切CSV来源撤权1 | 56PASS，287.86秒 |
| text_logic_reuse/persistent_app_runs/internal_lifecycle/internal_api/internal_switch_api完整5文件 | 122PASS/7SKIP，290.64秒 |

[逐节点结果与7个PG跳过原因](author-result.json)。原两文件58续用+42边界，不把36raw证明计额外PASS。22项测试覆盖旧2锚、七门外文件与原CHANGED变动、增删文件、manifest/anchor/pin/表达式/嵌套/dup JSON/未知源。22先独立执行，之后src/tests无编辑；100/56/129在425freeze上独立DB并行实际运行。没有把旧a4fd100、旧P-A68或原r4大回归通过数混入当前资格。
主线4UI为实际TestClient/IPC/JSDOM及cold NoModel，原生浏览器/人工点击未跑。改动ruff PASS；实际src全mypy仅既有status_report/tools5错误、71源文件，无新增。此前全ruff10错误原证据未改，本轮未重报全ruff绿。

## 归档及限制

387份已终态合成SQLite无损gzip，逐个解压校验，14,767,643压缩字节；[archive map](synthetic-databases/archive-map.json)保留原SHA/压缩SHA/大小。无真实账号凭据或真实模型数据。更早675扩验原587PASS/84FAIL/4PGSKIP保持历史，本轮不声称全部675在新版本重跑；共享129单列。
pyproject package-data增加资格JSON。实际setuptools build_wheel尝试退出1，ModuleNotFoundError(setuptools)，[全文](package-build.log)保留；没有安装依赖、网络下载或真实wheel构建/冷安装通过声明。
真实模型请求0、费用0、真实预算0。PG/角色与真实并发/RPM、Windows、原生浏览器、真实模型/费用、完整P-A/P-B业务及人工语义、正式发布/部署、远端CI均NOT_RUN。旧明确禁止的浏览器/CI/取消install路径未重试；本轮普通代码与Git动作无权限审批拒绝。

## 最终独审

独审[完整报告](independent/final/FINAL_REVIEW.md) SHA d7cd236d94c93141c93555a5d105e6ce14c69815b2ba378fc5d2ebf03c321641：190唯一PASS/0FAIL/ERROR/SKIP；122(旧100+资格22)204.07秒，56主线255.33秒，12独立fault45.80秒，全部进程明确退出。178与作者重叠，12为独立额外节点，不相加为497。为原始JSON落盘补跑的36旧节点全部PASS、39.54秒，是既计节点子集，不加入分母。

独审自己的[82逐名映射](independent/final/old82-to-independent-current.json)82/82 PASS；独立[36raw汇总](independent/final/boundary-raw-summary.json)12foreign真实SQLite context/result校准后产品privatecells0+DB0，4success-missing-typed与20failed-residue实际调用目标完整verifier+DB0，bad0。这些是独审自己的实际新run，不借作者36raw或静态SQL猜测。

425map独审pre/post零差异，资格JSON/pyproject与真正全字节软件FP一致。完整1924件独审原产物及原manifest封为[无损完整归档](independent/complete-evidence.tar.gz)，每件解档SHA逐项复核；[原manifest](independent/manifest.json) SHA8378ecc74e0a09c88dfae7c6204bfbe1bdf68f221b076eb92aba067b584f6d53保持原字节，115件报告/log/XML/map/probes/raw/UI另外可直接读取。[复制集合及归档SHA](independent/copied-set.json)区分完整压缩归档与原始可读子集，不能把未单独复制的source-tamper fixture当成丢失。

[结构化最终限定](final-qualification.json)记录测试重叠、旧失败、原锚/白名单不变、原seal和明确实例批准边界。当前新软件也不自动继承6088时期或其它源版本的审批/执行permission，不能把两个旧锚的有限资格当成任意软件升级。原589件6088证据与原owner WIP摘要均实际核为不变。
完整最终Git SHA/远端一致性、clean/ahead/behind及最后原环境成功执行UTC在提交推送后的交付回执另行记录。
