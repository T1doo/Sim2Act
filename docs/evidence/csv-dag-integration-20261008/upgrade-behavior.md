# 源码升级行为与保留范围

本次产品源码与DAG/P2候选3b3534ca相同，未新增字段修改或数据迁移。既有schema仍使用Run/Operation/operation_intents/events及DeliveryGraph账本。原应用定义、CSV资源、amount旧预览、quantity旧报告结果保留；不删除、改签或自动迁移旧证明。

交付图trusted registry hash覆盖除config.py外的全部服务端Python模块，依据DeliveryGraphIntegrationContract §2/§4/§6及原V5 §9.2–9.3：源码也是对象版本，缓存/历史/重放重验当前版本。新增csv_dag/csv_reports及P2更新改变该依赖集合，可能使其他CSV/Report/agent的图锚过期，不能把变化范围误说成仅新DAG。资源内容未变也不能绕过源码版本核验；本次不缩小原依赖集合掩盖409。

| 状态/操作 | 升级后的实际行为 |
| --- | --- |
| 已完成旧DAG运行 | DB原状态和结果不删除；当前证明GET返回409，不能当新版已验证 |
| 本人运行控制状态 | NOT_VALIDATED，result=null，steps=[]；SUCCEEDED状态本身不是新版证明 |
| 旧计划读取/接受重放、旧列补丁历史入口 | 当前图锚过期时409；失败读/重放零写入 |
| 另一应用的旧图锚 | 同一源码依赖集合变化也会409；本病例实际验证第二个CSV应用 |
| 显式重派生当前锚 | 新锚/来源版本另存，旧锚和旧请求/回执保持；旧DAG计划列为INVALIDATED |
| 新计划、新接受键 | 要求新plan_fingerprint精确确认；旧确认被拒；正确确认后另存运行与回执 |

用户应先重新派生当前图锚，再新键保存计划、新指纹明确确认、新接受键运行。旧键不能用于不同内容，不能用修改标签恢复旧证明。升级前的暂停/未完成计划也不能承诺继续执行；它们仍受当前binding/来源/授权/lease/fence检查。该整合验证的是实际完成记录跨版本升级，不声称跨版本混合worker、热部署或不中断升级经过测试。本人停止控制继续可用；任何撤权、人工锁、未知结果或不确定依赖都保留原拒绝规则。

实际病例用git archive精确5a旧源码，在独立子进程导入旧模块生成两个应用图、已检查列补丁、amount=30预览、quantity=15完成DAG记录。新源码读取同一自有SQLite/PG隔离schema：旧计划/结果/历史/其他图409，状态NOT_VALIDATED；拒绝前后全表相同。新锚、新键、精确确认完成quantity=15，同时Run/Operation/intent/events/请求/锚/来源版本/应用/预览/资源原有行全部保持。额外将历史JSON列CAST为TEXT，哈希其原始存储字符串及主键，核对历史字节表示保持，不只比较解析后的字典。

升级夹具两个早期失败独立保留：先生成第一图再创建第二应用改变了授权快照，old driver正确被PERMISSION_DENIED拒绝；调整为创建所有自有资源/应用后冻结两图。随后作者错误使用不存在的单列补丁GET路由，404；改用原历史GET接口。未改变产品源码或旧断言来掩盖失败。SQLite和PG阶段用例各1PASS，最终冻结双后端范围另见README/summary。

父线程报告同一独立审查者已限定闭合两项P2，每端26PASS3FAIL的三项是原源码完整依赖记录跨升级409，符合失效合同；原reviewer文件本环境不持有。该信息不冒作全功能、人工签收或无缝升级证据。接线966a25d仍冻结在独立分支，未混入dev；semantic UNKNOWN、owner PENDING、publishable=false，LIVE=0。
