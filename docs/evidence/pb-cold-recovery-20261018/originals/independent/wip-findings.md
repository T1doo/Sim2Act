# 完整未冻结WIP：非作者静态发现

对象：`complete-wip-d5df36076a6770f5.js`，SHA256 `d5df36076a6770f5599100fe475821826f2923f6e8d779ca7e644079d884a9a7`，2026-10-18T05:18:15Z实际仓库只读副本。root唯一作者，本审查未执行任何产品/协议函数、HTTP、Worker或测试。以下是静态控制流推演，不能称为已动态复现。

## P2：另一合作文档成功清记录后，本页有原metadata却不再允许GET

位置：`naturalTaskRecoveryRefresh`约89–97行，`naturalTaskRecoveryForget`约110–116行，`naturalTaskButtons`约733–742行。

推演：A、B两个新协议文档已恢复同一scope/同一durable raw；B已有RAM placeholder及WeakMap metadata。A持同scope锁，严格GET+fresh app后成功删除durable record。B收到storage remove事件（或下一次手动action获取锁后刷新），saved为null、pending存在，进入RECOVERY_RECORD_CONFLICT。recoveryError同时禁用recover和所有写操作。关闭重开面板仍取同scope Map，因此在不整页重载的情况下无法再GET自己的原key核对已保存app。

这没有造成第二POST或误删新记录，但形成正常合作文档成功后的可见死路。普通spec helper对已知metadata且saved缺失仍保留原pending并允许GET，forget时只清该RAM。

最小安全修复候选：只对已有完整WeakMap metadata的RAM原pending允许missing-record只读GET；绝不因此POST，也不把无record的新cold页面当有原意图。成功后仍持同锁、同current/pending，重新读取raw：若原raw仍在则比较删除；若仍缺失则只清该pending RAM；若任意新raw出现则冲突并保留新raw。缺锁/坏读取/篡改raw都不走缺失分支。父级可选择明确不支持这条正常B恢复路径，但不能把跨页锁和第一方成功竞争通过扩大成另一方可读恢复通过。

## P2低：source-options拒绝未按作者声明清pending正文RAM

位置：`openNaturalTaskExtraction` source-options catch约799行，对比action catch约900行。

推演：本页提取真实201丢回执，Map保留body/review及durable metadata；关闭面板后当前源撤权，再开相同来源的options返回403。代码清s.source并invalidateInternalContent，私有DOM确已清，但没有删该scope Map pending.body/review；action catch才有删除语句。未发现该RAM残留可越权绘制的后续路径，因此不是已证P1；它与作者“source-options及recovery拒绝都清RAM正文”的合同声明不符。

最小修复：在options权限/版本拒绝invalidate前，仅对该scope中已知naturalTaskRecoveryMetadata的pending删除body/review，保留metadata/key/raw及durable未知锁。不要读取/清除别的scope。

## 尚未发现确定P1的部分

17字段、token-free稳定durable scope、来源完整options验证后restore、bounded/闭字段读取、首次POST前锁内save/readback、冷完整ExtractInput/review/candidate/source proof独立hash比较后才RAM重建、原recover和fresh app、每个API/hash后的operationCurrent、runGeneration以及showInternalRun关闭extraction方向正确。forget前最近一次current检查与同步compare/delete之间没有正常事件循环await；尚未发现同名ID导航ABA可越过这些fence。

这是未冻结有限源码审查，不是最终结论；原件和字节修复桥待父级修改后另核，实际资格仍未执行。
