# P-B 冷页原提取意图恢复：有限工程交付

实现：`7c6c79faa1de7a184dca7db468c0e784d5cc0cd6`；最终资格冻结及首次正常远端推送：`737e80d2304509149fef3161226f92580724d43a`，分支 `dev/pb-cold-key-recovery-20261018`。父级已接受基线1f725及原8fc均为祖先；root为唯一仓库写入者。首次推送155→156 heads只新增本分支，其它不变。后续文档/证据提交不改变资格源码。

用户明确提取前，同scope Web Lock内先保存并逐字读回17字段无token/正文原意图票据，再调用原POST一次。丢回执并关闭页面后，从统一目录回到原成功来源，核对当前来源后发现原票据；只读原key及显式GET入口可见，编辑/预览/再次提交保持锁定。只有原完整ExtractInput、审阅、candidate、source各独立SHA和fresh app全部核对成功，才清票据并允许明确打开。没有可靠NOT_ACCEPTED/CLOSED合同，未知仍锁定，无自动POST/换key/清锁按钮。

[功能及合同](../../F2/PBNaturalExtractionColdRecovery20261018.md)、[权威计划](../../F2/Plan.md)、[全部可直接阅读原件](READABLE.md)、[原件字节清单](raw-manifest.json)、[完整原件归档](raw-evidence.tar.gz)、[打包摘要及SHA](package-summary.json)、[纯字节/归档复核](artifact-verification.json)。原件保留原始bytes，大UTF-8文件另有按offset无损分段；SQLite为合成夹具，不是用户数据库。

归档含4358件原件、75,539,542 bytes，gzip12,283,260 bytes，SHA256 `f12b6007b95650c51b903c12f8cb2563a8b8beabfe97c04d59973a89fc9469ed`；4346份UTF-8原件、12份二进制，238个UTF-8无损分段。[全目录校验和](SHA256SUMS)排除自身，[复核脚本](verify-evidence.py)仅检查原件/归档/字节/已完成记录，不运行产品或增加用例。

## 实际验收范围

五个唯一实际HTTP/JSDOM场景通过；下表秒数是页面observer时长，首例的JUnit另包含模块种子时间。另一个原synthetic API/staged view控制器回归1PASS/38检查，不能并入actual HTTP。

| 场景 | 页秒数 | 检查 | 页面API | 资产 | 实际HTTP |
| --- | ---: | ---: | ---: | ---: | ---: |
| 201回执丢失→完整闭页→冷页原key显式GET→fresh app→明确打开 | 88.53 | 36 | 49 | 54 | 103 |
| 八类选择/导航边界＋实际SHA结果投递迟到；跨账号/项目实际403 | 384.87 | 160 | 192 | 54 | 246 |
| 只换本地key的实际OUTCOME_UNKNOWN、request/candidate污染、源READ撤销 | 200.93 | 79 | 88 | 54 | 144 |
| 目标READ撤销 | 77.93 | 35 | 44 | 54 | 100 |
| 缺锁/存储失败/坏JSON；两页BUSY；B清票据后A仅原GET恢复 | 213.02 | 74 | 109 | 135 | 244 |
| 合计（5个用例） | — | 384 | 482 | 351 | 837 |

837为482页面API＋351资产＋4次正常合成Grant控制API；13个真实加载源码的JSDOM。221次可见/可用交互；每例最多1个原提取201，只新增原合同1app/1runtime/2既有工具Grant/4双seal/1marker，无Release/实例/Run自动创建，随后恢复仅GET。原行逐行保留，撤权例只额外修改选中Grant的revoke/revision。实际撤权SQL屏障blocked均空；source evaluated=0，target有34次其它仍获权context评估，不表示零所有私有或JSON标量读取。来源options403清RAM分支只静态复核，实际动态覆盖为by-key403动作分支。

681项执行输入前后逐字相同，132生产项相对1f725仅internal.js改变。两个独立正常fresh来源种子各生成3次Mock＋来源Worker1次Mock，实际共8次Mock、来源Worker2次、页面Worker0、真实模型0。每个封闭种子逐字复制隔离case，不改数据库行、clock、lease、deadline或重签。模型wire与HTTP原bytes、source claim、copy provenance、最终rows和finally均留原件。

## 失败与未完成记录

初跑1个共享种子因测试观测器替换共享httpx.MockTransport类为函数，触发Worker构造类型检查，pytest报告5参数setup ERROR/2.11秒。普通API已产生QUEUED生成Run，模型和Worker执行未开始；不算5个业务失败。修后只替换fixture模块httpx引用，原共享类、Worker guard及原生成oracle保持，原错误及修复全留存。

修后main批次outer900秒到期exit124，4个named PASS，最后重复platform为NOT_COMPLETED；JUnit无name占位不计PASS，owned Node由finally清理exit -9，单Node900 watchdog未触发。相同冻结字节下并行platform完整1PASS，pytest290.44秒/页面213.02秒，以第二个独立正常seed完成。五个唯一资格来自明确的两个batch，不能称原main整批全绿。原synthetic导航1PASS单列，未因唯一改变的未使用新测试fixture文件而重复运行。root读取无name占位曾KeyError，工具可见转录与修复口径单列；无产品重跑来修复解析器。

[作者执行总结](originals/author/qualification-summary.json)、[精确命令/进程scope](originals/author/commands.json)、[初始错误原log](originals/author/cold-suite.log)、[main预算中断原log](originals/author/cold-suite-retry.log)、[完整并行单例原log](originals/author/platform-parallel.log)、[原synthetic导航log](originals/author/original-navigation.log)、[完整输入before](originals/author/inputs-before-retry.json)、[after](originals/author/inputs-after.json)、[fixture修复字节桥](originals/author/fixture-fix-input-bridge.json)、[首次远端推送回执](originals/author/source-push-receipt.json)、[root读取占位错误说明](originals/author/root-readback-parser-note.md)。独立源码/原件报告及其封存manifest均列在READABLE的independent部分；独立纯原件断言数不增加产品用例数，独审未再次跑产品。

[非作者最终有限独审](originals/independent/final-independent-review.md)与[封存清单](originals/independent/sealed-manifest.json)，清单SHA256为 `cc79b093c31e559d7492298b601de82a6ad87a944d8a04cd2b1506c74ae36568`。36份被清单明确覆盖的原件连同惰性缓存字节均保留；通用打包首次漏掉该缓存，修正记录与首次打包log另存，不改变产品资格。

Windows/native browser、PG、真实模型/语义/场景、远端CI、部署未执行。旧精确安装digest并发对照窗口永久NOT_VERIFIED且未重试，本片GET-only SHA迟到没有第二actor prepare或旧新实现同predicate对照。旧额外性能探针exit139故障因果/产品关系仍Unknown，不再探测；旧满盘独审未落盘缺证没有补回。用户清浏览器storage、跨设备、旧JS/升级前无票据的未知意图，以及server未受理/close fence均未新增保证。
