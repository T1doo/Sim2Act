# 旧短测及 mypy 基线补充只读复核

本补充接续 `4aaea50d4ea40b7d2425f3c1561bc99b5e3def53` 的独立17项报告，仅核原件，不重跑测试、mypy、HTTP、Worker或模型。核验时HEAD仍4aa，工作区干净，11份关键源/资格文件before/after hash一致且与commit相同。

**旧短测回执成立；mypy仍未通过，和463基线为同样7个错误。没有本次投影文件新增诊断的证据，但不得描述mypy通过。**

## 测试批次与去重

- 作者新模块：17 PASS / 0 FAIL / 0 SKIP，26.649秒。
- 作者显式旧短节点：17 PASS / 0 FAIL / 0 SKIP，27.651秒，原件 `author-regression.xml` / `.log`。分类为8个primitive、5个API/严格资格拒绝、3个真实admission、1个实际Worker顺序组合。
- 上述两个JUnit的完整classname+参数化name集合互不相交，合计 **34 unique**。本独审先前17 PASS /24.195秒与作者新模块集合完全一致，属于重复证明，增加0个unique；不是51个unique，也不是一批34项运行。
- 旧STRICT_REFUSAL.json真实保留VERSION_CONFLICT、database_unchanged=true、actual_model_requests=0；未放松当前软件资格。
- Worker组合实际先Worker.reserve后budget.reserve，仍是两个事务；旧短测通过不改签为同事务完整Worker链。

## mypy 未通过及基线比较

根实际当前src和基线各自mypy均RC1（退出码据root实际工具观察，本独审未重新执行）；两份原始输出 `mypy.log`、`mypy-baseline.log` **逐字相同**，SHA256均 `98ae0e8ed7f208e78eb516e2a3f2180e5c317256f585683c0f6590898cdfe012`。均报告 **7 errors / 4 files / checked 90 source files**，不是5个错误：

- status_report.py：3个类型错误（line72两项、line107一项）。
- tools.py：2个缺类型注解（line210、264）。
- natural_live_admission.py：1个v2 namespace Literal覆写错误（line144）。
- natural_trial_runs.py：1个namespace赋值类型错误（line36）。

没有错误定位到本次修改的natural_trial_budget.py。独审在内存生成Git463的`src + pyproject.toml` archive，hash `bd1d8f0cc4ec388e6041fa1e14b497d2fca5bcc39df931fb88c3b2e92645ccbe`与根基线声明相同；逐字核实际基线snapshot的114份archive文件，含90个Python源。上述4份报错文件在463、snapshot及当前4aa三方逐字一致。故可以陈述“本环境同命令基线已有且诊断未增加”，不能陈述仓库静态检查全绿，也不替代其他环境检查。

作者较早`author-test-and-source-proof.json`仍写baseline comparison pending，保留其时点；本补充由后续原日志与snapshot完成比较，不重写旧记录。初次lint的3个F811也在source-before原声明中保留，修后才进入实际pytest；不是pytest失败或最终lint通过前的绿色结果。

原有未知事项及Windows/PG/真实模型/费用资格/语义/远端CI/部署NOT_RUN边界不变。有限交付结论仍为固定七槽自然离线门的可见预算投影与合成拒绝证明，不是普通无限逐次使用批准或LIVE能力。

机器证明 `/tmp/f2-natural-budget-4aa-independent/independent-regression-mypy-supplement.json`，SHA256 `58ad04c93375fa286814d0e4c5f2b971ff908bad2b2513ef4b7f2065a2076b2a`，包括34用例列表、各原件hash、11源hash、完整7错误及snapshot比对。
