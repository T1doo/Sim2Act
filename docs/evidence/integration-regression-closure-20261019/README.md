# 原两项集成修复：原始证据

当前源码对应 `08a966cf5413295d49cdb942287e83d9f72ac6c7`，父提交 `aae3abd9c5c422b199f82e66570b4bd71be49621`，本轮对照基线 `96690a60591fc27c9c6aa35a6e10fd69f7f57539`。v11 的 14 个冻结文件对应 685 个运行输入（679 个提交 blob 与六个单独归档的生成 egg-info 元数据）；v10 的 12 个冻结文件对应 684 个运行输入（678 个提交 blob 加相同六项元数据）。执行冻结工作树随后保存为源码提交，逐文件核对一致；不称生成元数据为已提交内容。

## 最终实际结果

| 源码 | 实际执行 | 结果 |
| --- | --- | --- |
| aae3abd9 / v10 | 原七槽 V2 | 1 PASS / 650.4557 秒 outer；真实合成发送 3+2+2，7 accepted / KNOWN |
| aae3abd9 / v10 | 其余 21 项 | 20 PASS / 1 FAIL / 273.9606 秒；普通 Source 失败完整保留 |
| 08a966cf / v11 | 普通 Source 原节点 | 1 PASS / 111.7964 秒，685 输入稳定 |
| 08a966cf / v11 | 普通完整证明/写后/无写权限到期保护 | 1 PASS / 18.8969 秒，685 输入稳定 |
| 08a966cf / v11 | fresh Store / 新材料 Goal 的 P-A Cold | 1 PASS / 171.2187 秒，685 输入稳定；不是 P-B Source 血缘验收 |
| 08a966cf / v11 | mypy 全 113 源文件 | PASS / 121.6604 秒，114 源/config 输入稳定 |

没有将不同版本的结果拼成单一新 SHA 全用例 PASS。独审确认旧非 None 绑定和试用版本 allowlist 短路控制流不变，因此只补直接受影响普通路径，未重复 650 秒 V2 或既有恢复矩阵。V2 的实际 PASS 仅归属 aae3abd9，v11 未额外运行 P-B Source 血缘用例。


`raw-evidence.tar.gz` 保存作者原件，包括成功、失败、中断和原生 -11 的全部可用日志、JUnit（存在时）、observer、隔离 DB、输入清单、候选源码及运行脚本。完整 mypy cache、pytest cache 和 bytecode 不属于原始业务结果，未收入归档。69 个 pytest current 目录别名只以路径/目标元数据收入 manifest，对应实际文件各归档一次，不删除原别名。`RAW-MANIFEST.json` 和 `RAW-SEAL.json` 在归档根目录；package-receipt.json 给出归档字节数、SHA256 与逐成员校验结果。

主要路径：

- `qualified-v10-v2/`：完整 V2 七槽实际执行，proof 在 `tmp/*/ACTUAL_V2_SEVEN_SLOTS.json`；真实模型 0，显式 test-local software qualifier stand-in，不是软件真实资格或真实场景验收。
- `qualified-v10-rest/`：v10 其余 21 项（20P/1F，失败不抹去）；`remaining-launch.json` 证明 V2 已退出才启动，避免与墙钟租期用例竞争 CPU。
- `ordinary-source-v11/`、`ordinary-proof-v11/`、`ordinary-cold-v11/`：新源码的直接受影响运行和保护用例。
- `FINAL-AUDIT.json`、`candidate-v10/`、`candidate-v11/`、`generated-inputs/`：按版本归属的输入/源码身份和七槽记账校验。
- `mypy-v11/`：当前源码完整 113 源文件 PASS，114 输入前后稳定；旧 mypy 执行另保留。
- `static-v11/`：改动的干净范围 Ruff PASS，完整 Ruff 仍 110 条、对照基线 117 条无新增；不声称全量 Ruff 通过。
- `baseline-final/`、`baseline-ordinary-source/`：原代码真实失败复现与额外普通 Source 对照 PASS。
- `qualified-v7/`、`qualified-v8/`、`qualified-v8-v2-retry/`、`qualified-v9-v2/`：中间真实失败/崩溃/中断，均不覆盖、不冒充成功；其余中间执行同样保留。
- `independent-review/`：独立只读 source/runtime 报告及各自封印，不补签旧满盘环境缺失的报告。
- `checkpoint/`、`checkpoint-v10/`、`checkpoint-v11/`、`disconnection-readonly-check*.json`：正常源码 push、实际远端读取及同实例通知后核验。

## 限制

未执行 Windows、PG、浏览器新验收、真实账户/免费额度、人工语义/场景、全量 pytest、部署或发布。旧 -11 在定时栈转储附近发生，原因未知；后续显式取消定时栈转储不关闭 fatal handler、不改断言，成功新结果不擦除原崩溃。GitHub Actions 元数据 GET 返回 Forbidden 后未换通道/凭据绕过，也未手动触发 CI；自动 CI 状态未知。最后交付普通分支 SHA 和远端/工作区差异见交付回执，归档内 code checkpoint 不自称包含自身的最终文档提交。

归档 SHA256：`ca62ce03830be790a64e2abc40df0abe125b5c67d6ca6091cca21e4937c1dee9`，8931046 字节，1591 个成员全部逐项验证。作者 raw manifest SHA256：`ba13b91f3c9d3ccb632a6a3cbff2b1462c858faf2baae0648e7630895e6cb1cb`。

可直接阅读[源码独审](independent-source-review.md)和[最终运行补充](independent-final-review.md)。两份 standalone manifest 的完整输入目录保存在归档 `independent-review/candidate/v11-source/` 与 `independent-review/candidate/v11-cold-final/`，原封印字节不变。
