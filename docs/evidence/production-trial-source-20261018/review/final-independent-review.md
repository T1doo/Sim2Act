# 未安装服务端来源 loader/verifier 有限独审

结论：冻结 `ab838215af13c04281bbad441fd75b9a97839890` 的本片有限审查通过，未发现剩余确定P1/P2。可交付的是固定 test_only SQLite 的四角色证据合同及原sender接线；没有真实provider producer、费用权威或LIVE安装。独审只执行文件/Git/AST/JSON解析，没有运行产品、pytest、Worker、HTTP/网络、SQL或打开数据库；不背书未来推送。

## 源码与静态修复

相对基线 `9df8a2ecca3e2e9905200398aa7c7a4d53b891a0`，仅新source模块、新测试、旧sender私有接线三路径改变。其余136生产Git blob一致，旧policy/journal/resolver未改。新入口无source对象、selector或callback参数，只调用固定loader；source唯一生产importer为未安装sender，未接API/Worker。原9个sender函数AST一致，旧receive剔除唯一新增来源重读分支后原AST一致，原data入口签名保留；新节点内实际做1次旧入口compat，没有声称旧8节点资格重跑。

WIP P1：`_source_history` 曾把原 `_ledger` 三返回解包为四，任何原key历史可ValueError。root在冻结/第一次执行前改为三项；正常删源history与晚撤销history原节点本次都实际通过。最初未修行只保留原工具可见文本转录，不冒未修完整源码字节已落盘；实际保存fragment是修后。发现及修复记录均保留。单镜像负例在现inconsistent节点内独立补强：先恢复valid raw，再只破坏一侧fingerprint、保持requestFP锚，实际SOURCE_INTEGRITY/UNKNOWN并拒发送，没有增加节点。

## 原件闭合及资格

作者封存目录 `/workspace/production-trial-source-20261018` 清单SHA256为 `7a0d61b98fcaf4405be5e40df9e8b6f9c5a5f0cb97ca06b43015deb939d0fa65`。本独审逐字核验74非DB原件374306B；清单另12107B，总75路径386413B。9物理fixture DB仅stat，未打开或重算DB SHA。

JUnit、原stdout及execution一致：首轮9唯一节点、9执行、9PASS、0FAIL，JUnit38.319秒、外层43.323537305秒，原命令240秒有界且只选本新测试模块。旧19/12/8矩阵未重跑。本片没有子进程资格，不借用前片四个真实crash进程。

707输入/138生产before-after映射逐字相同，helpers同源；3冻结文件与Git blob及实际served源一致。704旧输入/136生产映射未变，仅旧sender变化。当前701非DB输入独立SHA匹配；6个旧 `.db.gz` 仅stat和基线/冻结Git blob标识比对，未解压、读内容或重哈希，不能说全部707都由独审重读字节。

## 实际支持的行为

- 正常1936B来源原bytes SHA独立重算，与Resolution及evidence_fingerprint一致；从实际JSON独立核四角色schema、固定synthetic issuer、原requirements指纹/account/channel、明确identity/entitlement/零收费及禁付费fallback/status。原requirements指纹从回执scope另算一致。观察时间早约600秒而仍在原有效期，不引入30秒provider续签规则。ALLOW只表示合成合同符合，不是可信真实来源。
- 正常原trace为load→reserve、load→marker、guard load、receive load→settle；四个不同事务连接中，前三种mutation各与相应load共享原caller连接。源码确认guard也用同c调用fresh。删源后替换loader为立即抛错哨兵，原key仍只读成功且lookup0、handler不增加。
- 缺源、错账号、同owner另项目绑定、过期、撤销、四角色不一致，实际均LIVE_BLOCKED、handler0、拒绝窗口55表严格相等。跨项目先有snapshot SQL正向校准，再缺自有锚时payload读0；拷foreign raw到本scope仍拒绝。这是合成同owner跨项目证据，不能扩大成真实跨账号授权验收。
- 7份已保存raw JSON（normal、5个非missing拒绝、mirror损坏前valid）独立解析和SHA核对；按封闭执行末时间重算有效期/绑定/事实判定，与原Resolution一致。mirror前raw独立可ALLOW，损坏后loaderUNKNOWN/不修复/不发送，故不是四角色冲突掩盖pair校验。
- guard后实际Mock handler修改服务端status为撤销：已收到body及usage8保存，原slot attempted=true、accepted=false、halted=true；重复只历史、不退款、不重发。数据库guard不能撤回已经可能开始的IO。
- 边界保留exact Store/SQLite/test_only/settings/MockTransport；真实权限类异常传出，默认production_preflight仍缺源LIVE_BLOCKED。实际adapter3次/Mock handler3次：新source路径2，旧data入口compat1；真实provider/model/凭据/env读取0，guard attempts为空。所有公开receipt/Resolution的LIVE、dispatch、real_source均false，业务验收false。

全55表拒绝/历史窗口和fixture其它54表严格保护来自实际执行断言及导出回执/镜像FP，不是独审重新读取全行。normal尾态故意删source，inconsistent尾态故意留下单侧损坏；不宣称所有最终source DB全valid，也不从seal/hash推出抗管理员整体改写或真实免费事实。

## 未验与工具来源

未安装真实source/issuer/sender或有效LIVE许可，生产resolve_account仍NoReturn；未验真实身份/权益/强制零费/撤销/费用/模型/语义、完整generation/source/cold/UI链、PG、Windows/native、远端CI及旧取消窗口。

本轮产品资格一次9PASS，无pytest失败。作者实际Ruff初始及中间失败stdout/stderr、最终修正通过均在74原件中；wrapper断言与patch上下文拒绝按pre-freeze-observations元数据明确为工具输出转录、非独立原stderr，不算产品失败。独审本轮纯文件audit首次完成即通过。详细可机器读证据见 `final-verification.json`、原脚本和stdout/stderr；静态桥见 `freeze-static-review.json`。本目录随后以manifest封存，停止全部写入，旧sealed目录未改。
