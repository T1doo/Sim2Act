import pathlib,json,hashlib,subprocess
p=pathlib.Path('/tmp/sim2act-resource-file-independent-20261010');repo=pathlib.Path('/workspace/Sim2Act');sha='fdc91282b2107164ba33624246be6f50e007cd13';base='66709612d5acd2e4b0dc41f75ef5c9f769508b0c'
initial=json.loads((p/'initial-summary.json').read_text());second=json.loads((p/'second-summary.json').read_text());last=json.loads((p/'summary.json').read_text());outcomes={r['case']:r for group in [initial,second,last] for r in group if r['status']=='PASS'}
assert len(outcomes)==9
source=json.loads((p/'source-after.json').read_text());product={k:v for k,v in source['files'].items() if k.startswith('src/')};changed=subprocess.check_output(['git','diff','--name-only',base,sha,'--','src'],cwd=repo,text=True).splitlines();assert changed==['src/sim2act/web/app.js','src/sim2act/web/index.html']
bridge={k:{'final':v,'base':hashlib.sha256(subprocess.check_output(['git','show',base+':'+k],cwd=repo)).hexdigest()} for k,v in product.items()};assert all(v['base']==v['final'] for k,v in bridge.items() if k not in changed)
(p/'product-byte-bridge.json').write_text(json.dumps({'source_sha':sha,'base':base,'count':len(product),'changed':changed,'files':bridge},indent=2))
new=[r for name,r in outcomes.items() if name!='old-negative'];assert sum(r['pages'] for r in new)==9
report={'verdict':'LIMITED_PASS','sha':sha,'base':base,'frozen_files':source['manifest_count'],'product_files':len(product),'source_before_after_git_match':True,'new_scenarios':8,'new_http_jsdom_pages':9,'new_checks':sum(r['checks'] for r in new),'old667_negative_pages':1,'old667_checks':outcomes['old-negative']['checks'],'cases':list(outcomes.values()),'model_requests':0,'limitations':['SQLite only; own synthetic fixtures','No independent PostgreSQL/roles/performance/deadlock conclusion','No old-database upgrade conclusion: old667 is HTTP asset-only negative','No native browser/pixels/Windows/Edge/Node acceptance','No complete source-proof assertion for valid-shape forged HTTP200 resource IDs','UNKNOWN resource Save state remains page-local; reload loses the pending map; no backend idempotency added','No formal publication, whole F1/F2/P-A/P-B/semantic/owner acceptance'], 'retained_harness_failures':['initial-business: own worker POST had no JSON body; existing strict_json correctly returned HTTP400','initial-accepted-aba and initial-read-aba: own idle awaited deliberately held HTTP I/O before release','second-business: HTTP400 cause captured in worker-responses.log','second-read-aba: same own idle issue in selected(); corrected only private harness','initial/second/final harness and logs preserved; successful original cases not needlessly repeated'], 'global_status':{'PG_resources_history_historical_timeout':'OPEN','PROJECT':'PENDING/BLOCKED_PARTIAL','semantic':'UNKNOWN','owner':'PENDING','overall':'NOT_ACCEPTED','LIVE':0}}
(p/'FINAL_REVIEW.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
text=f'''# 本地 CSV 文件入口独立复核

结论 **LIMITED_PASS**，精确产品/测试冻结 `{sha}`，基线 `{base}`。独立只修改本目录自编 harness；未修改仓库、作者测试、Git refs 或使用作者 PG。352 文件与 Git/工作树前后逐文件 SHA256 一致；{len(product)} 个产品文件中只有 app.js/index.html 改动，其余后台、API、Schema、执行器与基线字节相同。source-before/source-after 与 product-byte-bridge 为原件。

独立 SQLite 实际 HTTP/jsdom **8 新场景、9 页面、201 检查 PASS**；数字包括每页真实 HTML/script 冻结字节校验。另精确原667 HTML/app.js 实際 HTTP 页面 **1 个负对照、17检查 PASS**：正断言 `actual local CSV selector exists` 在旧页预期失败，原失败stack已保存。旧负对照其余资产/后台为当前冻结版本，仅证明新入口敏感性，不是旧数据库升级。

business从磁盘独立文件（中文、CSV引用逗号、负小数、CRLF）经FileReader→显式Save→草案创建→preview→精确内部快照/人工确认Release→创建实例→应用使用页两个新列运行，全部实际页面处理器及真实HTTP。独立拒绝模型provider的worker两次执行成功；SQL原资源bytes/hash、独立csv/Decimal期望1.75与4、两个不同持久AppRun、版本1/2及两typed记录一致。冷页面重新认证并打开实例，零POST、两个旧结果保留。fixture预建项目因此本次Grant增量Save4+draft2=6，未混算API创建project的既有2条授权；项目创建/资源保存/草案既有授权范围不扩张。

其余独立范围：空/超限/精确32768字节/多文件/非法编码/BOM/NUL/名称/后缀；取消、新文件胜过旧读取、项目ABA、身份切换；接受回复丢失后原意图冻结、双击及只读核对零重复Save；实际已接受再替换408/425/429/无效ID/损坏JSON保持UNKNOWN；迟到accepted保存不自动refresh、显式GET核对；accepted后列表错误遇新文件/ABA不能覆盖；手工修改解除文件原字节绑定。SQL资源/授权计数及AppRun/结果零额外新增均独立核对。

初始及第二轮 harness 失败全部保留：自己的worker请求漏{{}}，被原strict_json真实HTTP400拒绝；自己的idle在故意持有响应时等待全局网络清空造成超时。仅修私有harness，再跑对应失败场景。6个首轮PASS保留原归属，accepted-ABA第二轮PASS，business/read-ABA最终PASS；没有以作者测试或重跑掩盖初始结果。正式 source freeze 在每轮前后均匹配。

本结论不签PG/角色/历史Future10根因、旧数据库升级、原生/视觉/Windows900/Edge240/Node150、有效形状伪造ID的完整来源验证、刷新后持久UNKNOWN恢复、完整F1/F2/P-A/P-B或正式发布。Save原无幂等键，UNKNOWN仅页内Map；页面重载前应核对材料历史，不能声称持久exactly-once。HTTP200其他入口限制保留。PROJECT PENDING/BLOCKED_PARTIAL，semantic UNKNOWN，owner PENDING，overall NOT_ACCEPTED，LIVE=0。

证据根：{p}。COPY_WHITELIST.json列出允许复制的有限原件及SHA256，排除所有临时SQLite数据库。复制需同时保留初始/第二轮失败，禁止只留PASS。独立源、harness、磁盘合成fixture、每页network/hash/checks、SQL写入审计及持久DB投影齐备。
'''
(p/'FINAL_REVIEW.md').write_text(text)
allowed=[]
for f in sorted(p.rglob('*')):
 if f.is_file() and f.suffix in ['.json','.log','.py','.cjs','.js','.html','.md','.CSV'] and f.name!='COPY_WHITELIST.json':allowed.append({'path':str(f.relative_to(p)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
(p/'COPY_WHITELIST.json').write_text(json.dumps({'root':str(p),'files':allowed,'file_count':len(allowed),'exclude':'all SQLite database/WAL/SHM files'},indent=2))
print(json.dumps({'verdict':report['verdict'],'new_checks':report['new_checks'],'product_files':len(product),'whitelist_files':len(allowed),'status':subprocess.check_output(['git','status','--short'],cwd=repo,text=True)}))
