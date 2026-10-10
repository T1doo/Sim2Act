from common import *
prefix=json.loads((ROOT/'results.json').read_text());passed039=[r for r in prefix if r['status']=='PASS'];final=json.loads((ROOT/'final-results.json').read_text());before=json.loads((ROOT/'source-d716-before.json').read_text());after=json.loads((ROOT/'source-d716-after.json').read_text());assert before['files']==after['files'] and after['git_match'] and after['worktree_match'];b1=json.loads((ROOT/'byte-bridge.json').read_text());b2=json.loads((ROOT/'039-d716-byte-bridge.json').read_text());product={p:h for p,h in after['files'].items() if p.startswith('src/')};(ROOT/'product-freeze.json').write_text(json.dumps({'source_sha':SHA,'product_count':len(product),'files':product},indent=2))
out={'result':'LIMITED_PASS','source_sha':SHA,'product_review_sha':'039b74cf03ea5926b0b02b1b81dc684fa639a46d','previous_blocked_sha':'807090cf0b9e6f6306f86ed79a64be065a68279c','scope':'Event acceptance-set increment and necessary cold Run/instance regression only; no new full matrix or UI/PG run','357_before_after_git_worktree_match':True,'byte_bridge_807_039':b1,'byte_bridge_039_d716':b2,'actual_independent_tests':{'039_cases':passed039,'d716_cases':final,'passed_cases':len(passed039)+len(final),'named_checks':sum(len(r['checks']) for r in passed039+final)},'initial_cross_version_probe_failures':'807 persisted anchors include every src/*.py registry hash; changed csv_dag_instances.py correctly yielded Current graph baseline changed on both prototype Run and instance. This does not prove upgrade acceptance or the new event gate. Logs preserved; final positives created under current identical product source. Exact fresh joint attack returns Accepted instance Run history is incomplete.','previous_evidence':'/tmp/sim2act-dag-reuse-independent-20261010/FINAL_REVIEW.md remains BLOCK at807 with14API47checks/5UI6pages140checks; retained original scope, never relabelled as d716 full matrix','boundaries':{'LIVE':0,'PROJECT':'PENDING/BLOCKED_PARTIAL','semantic':'UNKNOWN','owner':'PENDING','overall':'NOT_ACCEPTED'},'not_signed':['PostgreSQL','real old-source database upgrade acceptance','new HTTP/jsdom matrix','Windows/Edge/Node native','resources-history historical Future timeout closure','all HTTP200 corruption forms','arbitrary DAG publication','overall project acceptance']};assert all(r['status']=='PASS' for r in passed039+final);(ROOT/'FINAL_REVIEW.json').write_text(json.dumps(out,indent=2))
(ROOT/'FINAL_REVIEW.md').write_text('''# 独立增量复核：LIMITED_PASS

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
''')
files=[]
for p in sorted(ROOT.rglob('*')):
 if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.json','.md','.py','.log','.cjs'} and p.name!='COPY_WHITELIST.json':files.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(ROOT/'COPY_WHITELIST.json').write_text(json.dumps({'root':str(ROOT),'source_sha':SHA,'files':files},indent=2));print(json.dumps({'review':str(ROOT/'FINAL_REVIEW.md'),'result':out['result'],'passed_cases':4,'named_checks':12,'whitelist_files':len(files)}))
