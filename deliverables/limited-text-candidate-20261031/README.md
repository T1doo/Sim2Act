# 单文本真实目标限制候选

[候选ZIP](Sim2Act-local-candidate-6424cc040bc8.zip)，3,184,682字节，SHA256 `ee5c85fa70a33cb3f823c0ed91f56c2fb8e7d2726f4f24a694e58da85264baf0`。

准确构建源码 `6424cc040bc8da7fd7f1c86130e30b0f95598594`，应用版本0.1.0，Linux x86_64／CPython3.12原生wheel，四扩展。源码／wheel库存和hash见 `candidate-manifest.json`，实际包审计见 `package-verification.json`。

解压后先读 `docs/LimitedTextCandidate.md`，使用已有锁定运行依赖环境安装。包内不含依赖wheelhouse或Python运行时，不能当Windows安装包、通用Linux免安装包或正式Release。默认模型关闭；显式 `--exact-read-live` 仅用已有令牌执行单文本逐字合同，不是任意自然语言产品验收。

已实际从wheel新安装，在源码目录外用 `python -I` 启动。默认入口自由目标明确拒绝、Ctrl+C退出／首次重开同结果；显式有限入口2次真实Intern、1477 tokens、5.161秒，全文独立核对保存为SUCCEEDED，同origin首次新服务重开／原键不重放，双EOF且exit0。已有超时UNKNOWN和上一成功结果均未改变。[完整验收与仍失败的额外测试](../../docs/evidence/limited-text-installed-20261031/README.md)。

尚未验新版Windows、正式PG或大型Cold真实模型整链。额外Cold图fixture有源目录和安装包相同的12项拒绝，不能称所有回归通过；原30秒目标仍未稳定达成。此候选仅承诺上述有限支持范围。
