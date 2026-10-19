# P-B Cold 结算共享谓词：第一批

只修改 production_trial_policy.py、goal_applications.py、text_apps.py，另加4项定向回归。此批把原谓词抽为共用私有事实叶：policy绑定尾部、候选history门/验证锚点、生成counter前后检查及文本候选确认。原公开入口仍执行原读取、权限、parse、完整Limits和错误顺序；独审以28项原基线AST对照核验。未接入新图、未做shadow双证明、未平直完整history，原结算五写/权限/租约未改。

基线为 `8f8a289a392321d240e73b279a61fb064ae78241`。被测四文件和patch精确SHA、命令、前后hash、独审报告及原始结果均在 [raw-evidence.tar.gz](raw-evidence.tar.gz)，完整性见 [RAW-SEAL.json](RAW-SEAL.json)。该包包括完整最终独审的49成员及其manifest；不包含测试SQLite DB或pytest符号别名，也不声称给全113个源文件做了输入封印。

正式结果：17 PASS、0 FAIL/ERROR/SKIP = 新增定向4 + 原policy7/普通生成复用1 + 原独立origin5。Ruff四文件通过，mypy检查113个源文件通过。环境为Linux、Python3.12.14、隔离SQLite、显式httpx.MockTransport；新增实际前缀完成三次mock修复生成并核完整候选、确认、9组完整Limits、counter和锚点，真实模型调用0。各pytest组均有1条既有Starlette弃用warning。

首次14项兼容命令在180.109秒驱动上限超时，仅8个输出标记、无完整JUnit，原件保留且不计通过。后续分别取得8项及5项正式终态；其中包含9次Cold输入运行的旧文本端到端用例本轮未完成，没有补签通过。初始新增测试的lint样式失败亦保留摘要，修正后Ruff通过。

独审结论仅 **BATCH1_FACT_LEAVES_ACK**，0开放P1/P2；报告SHA256 `44cce7166fb6842bf6949aaccb64f28907f863ce73b63187581647a15c26d874`，独审manifest SHA256 `310f032a50ae0fd7cab15b0f8e8f4a6472db9e85c5c31bf85f79d2f54b71acb2`。它绑定基线及被测内容hash，不代签未来Git提交/推送。

上一轮完整P-B仍 **FAIL_NOT_ACCEPTED**；完整指纹与祖先独占成本仍 **UNKNOWN**。本批未运行完整P-B、性能验收、Windows、PG、真实模型/语义/场景、人工验收或远端CI，不代表集成通过；旧满盘独审缺失证据没有补回。下一批尚未开始。
