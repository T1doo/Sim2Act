# 独立只读核验：a05 证据可读补充与材料 WIP

本次只读仓库；未修改仓库、运行回归、Worker、模型、CI或推送。根代理同时实现，以下材料实现意见属于移动WIP设计审查，非最终冻结签署。

## a05证据

核对提交 `db2228a4522a2838fdfdf4156b2148e627e4bc96`，对a05差异135路径均为指定证据目录。未发现可读补充的缺失链接或原件字节差异。详细机器结果：`a05-readable-audit.json`。

- tar SHA256 `b41dd981c0b6ab72ca554e0605a5a7d5a5ca501f2df72dc9d1501ff33fec8668`；155原件/24,083,110解压字节逐件匹配原raw-inventory。
- 129 UTF8副本/7,194,103字节逐字节匹配tar；26二进制记录/哈希/字节存在于原tar。
- README与READABLE共36相对链接均存在；readable-supplement-checksums全同。
- 610源/测试冻结输入按db2228 Git blob对cc858清单零差异。源WIP不用于此历史冻结判断。
- final-delivery-verification.json与原工作区历史保存件逐字节同。内容明确为a05历史远端与0/0核验，不冒充本补充新推送回执。
- 4份真实JUnit保留最终page 1/0F、原qualified4/1F、独后端2/0F、独页面2/0F；未改写失败或伪造17项单批全绿。没有重跑。
- 旧满盘环境缺失独审报告仍缺失；本核验未声称补回。

## 已即时通知根的WIP风险

1. `csv_material_revisions.replacement_graph`替换source key后调用`column.definition_graph`，后者从canonical authority复制`resource_ids=[A]`；新manifest refs B在core严格资源并集检查处会拒绝。应在真实B授权后构造用于有效图的精确resource_ids，保留canonical图原件及authority核验，不能放宽core gate。后续B父图重建同理。
2. 首次material PREVIEW无journal时，先operation.context读A Goal/Release正文，calculate才授权请求B。若本轮A/B并集先于私有正文为硬合同，须对owned iid/project/runtime标量先授权body.resource_id；已有键双anchor的B授权不覆盖首次请求。
3. owner prospective/context若只按effective rid是否不同root rid决定冻结effective draft，未来B→原A会错误退回root fp/schema。建议依已验证material谱系识别，或明确拒绝该后继；不要只比较rid。纯旧v1/v2 policy字节须保持。

其余正在补充的app_jobs/lifecycle/parent/owner接线不作为最终缺陷报告。最终严格namespace、合同重建、防篡改、授权先读、同iid CHECK→批准→CAS→Run→独立oracle、旧历史、B人工PENDING，需要最终冻结和实际合成NoModel测试后再签。
