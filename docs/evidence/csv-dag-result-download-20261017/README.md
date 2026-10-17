# 所选 CSV DAG 历史成果 JSON 下载

原方案依据：[平台产品§2](../../平台产品设计.md)的历史结果和以实际使用界面为主、§3 F05 的JSON/受控成果交付，以及[分阶段计划F2-T06](../../分阶段开发计划.md)真实成果可回读。基于有限独审接受的 `4451ff495fd7d87f12cf5e15e0bdaad2717adbc2`，四个原DAG家族不新增。此前只有单步CSV和字面文本提供逐次成果下载；DAG历史只显示摘要和技术证明，本轮补齐明确选择历史成果后取得文件的实际功能。

## 用户行为与合同

每条成功历史成果旁新增“下载此流程结果 JSON”。点击重新 GET 当前实例范围内的实际 Run，复用从原历史回读提取的完整 Run/原 canonical 计划/Release/typed记录校验，再与冻结选择比对；没有新增后端入口、executor、Grant、Schema或执行家族。当前撤权403清空受保护DAG，旧响应只在原选择仍有效时可产生Blob。原durable intent Map不删除、不改为新请求。

导出 `csv-dag-result.v1`：实际run_id与typed app_run_id分开、实例ID与当时修订、该历史Run自己的Release及指纹、执行家族、输入、结果版本和record指纹、来源app/Run/计划/哈希、本次计划指纹、完整typed result、原受控output及按稳定节点ID的完整聚合/报告node_outputs。普通报告可有formatted_*字段，不硬编码节点名；固定报告保留同Run文本；双求和两份五字段值及sum字符串精度完整保留。读取节点的原CSV、令牌和授权合同不导出。语义UNKNOWN、人工PENDING、正式发布关闭，不是应用包导出。

先按原key去重，再更新此次下载选择代次；下载另一成果、页面重读、身份/项目/工作区/实例变化使迟到响应失效。Blob链接在成功或anchor异常后移除，URL用零延时任务回收。详情见[使用指南](../../FirstUse.md)。

## 冻结与实际验证

源码冻结 `3be0300b306fac0cb6f5d9e0a1521ca16814c126`。产品修改仅csv-dag.js；页面历史和下载共享同一完整seal，并为摘要使用独立可见span，保持完整逐版本sid/column/count/sum断言。初次未提交版本把下载按钮文字追加到原整行，会破坏旧精确摘要比较；只读静态独审在任何动态执行前发现，此静态BLOCK原件保留，不声称动态错误UI复现或测试FAIL。

作者及独立同四节点均RC0、4PASS/0FAIL/0ERROR/0SKIP，各一次尝试。原目录两次真实提交、冷Worker和冷页回读嵌入新下载节点，不另增测试分母：本轮4个新增唯一节点，独立重复4项、额外唯一0。有限通过见[独审报告](independent-final/independent-review.md)及[终态汇总](author-originals/final-batch-results.json)。

| 下载节点 | 作者秒数 | 独立秒数 | 各侧JS检查 | 各侧产品HTTP/POST | 来源/目录冷Worker Run |
| --- | ---: | ---: | ---: | ---: | ---: |
| 双求和 | 385.209 | 351.101 | 62 | 266/2 | 1/2 |
| 普通报告 | 115.592 | 110.367 | 32 | 108/2 | 1/2 |
| 两步求和 | 96.424 | 116.692 | 29 | 104/2 | 1/2 |
| 项目固定报告 | 314.574 | 305.850 | 39 | 160/2 | 4/2 |
| XML批次总时间 | 912.055 | 884.170 | — | — | — |

表内POST均为原目录两次新Run，下载新增POST为0。固定报告夹具另有2次同步preview，不计Worker。各侧双求和有18个只读检查点及一次夹具IPC真实撤权，其后实际Run GET403清空保护视图；另外三例撤权0。两侧均0模型调用，各侧全部11个Blob URL回收、10次成功anchor和10份成功Blob.text()原始JSON文件；双求和anchor异常额外产生的第11个Blob只有metadata与清理断言，没有另存字节文件，不从其他payload重构。成功文件的UTF-8大小与实际Blob.size一致，MIME/精确格式/文件名/完整成果逐项核对。

双求和完成6个held-response下载门、身份/项目/工作区/实例ABA、另一历史成果下载按钮使旧响应失效、迟到403隔离、重复点击和anchor异常清理。两种报告删除绑定报告文本的合成响应均在Blob前拒绝。实际ASGI原响应/状态与合成返回体分别保留。下载另一条成果按钮是实际历史选择操作，没有新建历史行select handler。当前实例已跨Release切换后下载旧Release仅静态覆盖，不冒充动态通过。

[来源前后Git字节证明](independent-final/source-git-objects.json)固定19文件；产品src相对4451仅csv-dag.js变化，此冻结后只追加本轮证据。初版[静态BLOCK记录](author-originals/static-initial/finding.json)及两份未提交源快照保留，未执行动态红轮。

旧wait、waitHeld与原guards方法与4451逐字相同，12秒实际HTTP回复间隔/当前空闲及60秒总上限不变；不选择旧guards、条件/恢复或private矩阵。空intent Map不作未知请求恢复证据。

## 证据边界

仅归档此轮新生成原件，不重新签署旧188/377原件。[作者原件映射](author-originals-manifest.json)与[独立原件映射](independent-originals-manifest.json)列出原路径/大小/SHA、identity或gzip归档路径/大小/SHA；本轮共119份原件（作者50、独立69），原目录保留，逐项核对归档字节、解压字节及当前本轮原件。最终校验表122项，包括上述原件归档、2份映射和本说明。[SHA256SUMS](SHA256SUMS)覆盖本目录其余全部文件。

[独立64项payload manifest](independent-final/raw-manifest.json)声明的大小/SHA全部复核，完整独立目录同时归档，包括manifest范围外的报告、证明、原manifest与打包脚本。记录实际ASGI请求/响应、full served JavaScript的SHA、JSDOM点击/Blob/anchor适配器、合成SQLite与冷NoModel Worker。静态源码是与实际served响应SHA相同的冻结Git副本，非原始传输抓包。Blob捕获证明交付内容及清理合同，不代表原生浏览器文件落盘或Windows体验。

PG、原生浏览器/IME/剪贴板、Windows、真实模型/语义、Actions/远端CI、部署、应用包导出及额外恢复场景均不执行。不重试被拒下载、不降低浏览器隔离、不诊断PG环境或配置凭据。旧满盘独审报告缺口未补回。8f7静态缺陷、212可选脚本兼容缺陷、880迟到错误门原因未明等历史分类保持原意，未新增重验。
