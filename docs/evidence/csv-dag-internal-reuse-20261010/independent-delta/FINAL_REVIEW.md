# 独立增量复核：LIMITED_PASS

最终总冻结 `d716feda486fd6f0322c11b2e1b5112f718a94fa`，产品增量实际复核源 `039b74cf03ea5926b0b02b1b81dc684fa639a46d`。357文件d716独立before/after实际工作树与Git blob SHA256全部匹配。807→039仅csv_dag_instances.py和作者test_csv_dag_instances.py两文件改变：355/357文件不变，68/69产品不变；039→d716仅作者测试注入条件增加compiled非空guard：356/357文件不变，69/69产品完全相同。

## 修复与实际证据

instance_run_ids新增接受事件集合，限定principal/project/app/instance，拒绝同Run接受事件重复，并要求receipt marker、binding/AppRun joins、独立CSV_DAG_ACCEPTED事件三个Run集合严格相等。随后原逐Run真实证明继续核授权、scope、source、fence、typed数据与结果指针。原型DAG事件无internal_instance，不参与实例集合。测试注入以compiled Update.table/status识别最终SUCCEEDED，不依赖数据库schema文本前缀；新compiled非空guard使原BEGIN IMMEDIATE不会引发夹具错误。只静态核作者该测试增量，未当独立动态证据。

自己编写的必要增量：4通过用例、12具名检查。

- 039实际新建业务实例，剥两accepted marker并共同重签、删除binding/AppRun/typed数据与归零版本，但保留原Run/events/两operations：实例409 Accepted instance Run history is incomplete，零写（2检查）。
- 039实际新建实例复制同Run接受事件：实例409，零写（2检查）。
- d716正常新建实例真实运行other列，独立Decimal期望1.5；全新Store/client冷读正确typed v1与实际关联Run，business_writes1；同源原型Run仍200/SUCCEEDED，同源独立空兄弟实例正常data_version0/runs[]；全程冷GET零持久写（5检查）。
- d716冷读039精确联合攻击数据库：409触发新事件集合硬门，同源未受攻击原型Run正常，全部GET零写（3检查）。

原始响应与DB JSON在joint-new、duplicate-event、d716-normal-cold、d716-039-joint-cold目录。所有创建fixture、攻击、Oracle和检查均自编，没有重跑作者测试断言作为独立证明。没有写共享源、作者测试、Git refs，没有触碰作者PG或真实模型。

## 归属与限制

第一次尝试直接读取807旧正常/攻击DB，被既有graph registry_versions整目录源码hash硬门拒绝：csv_dag_instances.py源字节变化使原锚点漂移，prototype/instance均409 Current graph baseline changed。保留incremental.log、results.json和cold-original-*；该拒绝不算新正例或旧源码升级通过。最终正常正例来自当前相同产品源的新fixture；联合攻击冷读来自039生成且与d716产品字节完全相同的DB。

807的原BLOCK和14API47checks/5HTTPUI6pages140checks完整保留在`/tmp/sim2act-dag-reuse-independent-20261010/FINAL_REVIEW.md`，不重标为最终全矩阵。68个产品部件和全部Web资产相同字节仅提供来源桥接。此次只签新增事件完整性门及必要正常冷scope/Run验证。

不签PG、实际旧源码DB升级、此次新HTTP/jsdom矩阵、native Windows/Edge/Node、任意DAG发布或整体项目通过。历史PG resources-history Future超时OPEN及其他HTTP200提示限制保留；PROJECT PENDING/BLOCKED_PARTIAL、semantic UNKNOWN、owner PENDING、overall NOT_ACCEPTED、LIVE=0。

证据根`/tmp/sim2act-dag-reuse-independent-039-20261010`，可复制文件以COPY_WHITELIST.json为准。旧807证据根与白名单须同时保留。SQLite二进制数据库和pycache不在白名单。
