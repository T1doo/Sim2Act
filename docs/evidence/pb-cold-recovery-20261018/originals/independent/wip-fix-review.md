# 两项WIP静态发现的修后复核

修前原件和静态推演保持wip-findings.md，不改签为已动态复现。本审查员仍零产品/协议函数执行、HTTP、Worker及仓库写入。

修后实际字节与132项生产映射见postfix-source-review.json及postfix-wip副本。相对1f725只改internal.js，另外131项生产文件原字节；后端by-key、授权、executor/Grant和共享表协议没有变化。此处仍是未冻结源码结论，不签未来资格。

1. 已知同scope WeakMap metadata但持久record缺失时，Refresh保留原pending，recover初始比较也只在saved存在时要求原raw；两者不会进入新POST分支。严格GET及fresh app成功后，Forget在同锁/current/pending下若record仍缺失，仅删同RAM pending，不调用removeItem；任意新raw/mismatch仍冲突。故静态推演的正常A成功后B永久死路已修；是否实际A/B通过待作者原件，不冒签。
2. source-options权限/版本拒绝与action catch均只对该scope、具有已知metadata的pending删body/review，再invalidate当前私有DOM；durable原key/hash不清。作者所述RAM正文清理与源码现已一致。

对修后有限控制流尚未发现新的确定P1/P2：冷返回完整ExtractInput SHA/review SHA/candidate SHA/source proof SHA先匹配冻结metadata才重建RAM；原精确pending比较及fresh app hash/身份/来源继续；每个新增API/hash await后复验operation/current/pending，runGeneration/instance/connection/workspace防ABA；首次POST在scope ifAvailable锁内save/readback之后；forget后同步安装已保存状态，没有普通事件循环await间隙。

仍保留范围：存储/锁不可用或坏record阻止新POST；未知/撤权/版本冲突保留原key；无PB CLOSED/未受理墓碑，不因时间清理未知锁；仅合作新文档互斥，不签旧JS、清空浏览器存储或跨设备的全局fence。取消的精确安装窗口未执行，exit139原因Unknown。

等待作者冻结及实际新DOM/HTTP资格、平台协议与输入前后字节原件；最终有限独审另写。
