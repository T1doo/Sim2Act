import hashlib,json,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path('/tmp/pa-text-edit-generation-review-20261011')
before=json.loads((out/'source-before.json').read_text())
after={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in before}
assert before==after
(out/'source-after.json').write_text(json.dumps(after,indent=2))
parent_path=root/'docs/evidence/pa-text-edit-generation-20261011/source-manifest.json'
parent=json.loads(parent_path.read_text())
full_before=parent['files'];full_after={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in full_before}
assert full_before==full_after
(out/'complete-source-verification.json').write_text(json.dumps({'scope':'Parent freeze manifest independently verified; own 16 before/after paths separately recorded','parent_manifest':str(parent_path.relative_to(root)),'tracked_paths':len(full_before),'unchanged':True,'files':full_after},indent=2))
counts={}
for name in ['backend','http']:
    cases=ET.parse(out/(name+'-final.xml')).findall('.//testcase')
    count={'tests':len(cases),'failures':sum(c.find('failure') is not None for c in cases),'errors':sum(c.find('error') is not None for c in cases),'skips':sum(c.find('skipped') is not None for c in cases)}
    assert count['failures']==count['errors']==count['skips']==0
    counts[name]=count
ui=[]
for p in sorted((out/'http-final').glob('*.json')):
    d=json.loads(p.read_text())
    assert d['status']=='PASS' and d['api']=='IPC_IN_PROCESS_HTTP'
    assert all(full_after['src/sim2act/web/'+name]==value for name,value in d['loaded_source_sha256'].items())
    gestures=[a for a in d['user_actions'] if a['event']=='native DOM dispatch']
    summaries=[a for a in d['user_actions'] if a['event']!='native DOM dispatch']
    assert all(a['visible'] and a['enabled'] for a in gestures)
    posts=[r for r in d['requests'] if r['method']=='POST']
    generation=sum(r['path'].endswith('/application-runs') for r in posts)
    confirmation=sum(r['path'].endswith('/confirm-application-candidate') for r in posts)
    assert generation==confirmation==1
    ui.append({'scenario':d['scenario'],'checks':len(d['checks']),'gesture_count':len(gestures),'diagnostic_summaries':len(summaries),'summary_event_types':[a['event'] for a in summaries],'generation_posts':generation,'confirmation_posts':confirmation})
assert len(ui)==15
assert sum(i['checks'] for i in ui)==572
assert sum(i['gesture_count'] for i in ui)==494
assert sum(i['diagnostic_summaries'] for i in ui)==2
controlled=json.loads((out/'controlled-final.json').read_text())
assert controlled['status']=='PASS' and controlled['passed']==26 and controlled['failed']==0
assert len(controlled['event_evidence'])==24
assert all(i['draftGenerationAfter']>i['draftGenerationBefore'] for i in controlled['event_evidence'])
assert all(i['loaded_source_sha256']['goal-application.js']==after['src/sim2act/web/goal-application.js'] for i in controlled['results'])
assert all(full_after['src/sim2act/web/'+name]==value for name,value in controlled['loaded_source_sha256'].items())
result={'status':'PASS','baseline_commit':'7e86ec78201e7d0fcce5b43d6157c318f9ba8296','scope':'Only monotonic draft-edit generation fixes confirm/recovery handoff after same-card edit then undo or material selection ABA; no semantic acceptance','pytest':counts,'pytest_total':sum(i['tests'] for i in counts.values()),'controlled_not_http':{'tests':26,'pass':26,'fail':0,'scope':'7 fields + materials select × confirm POST/keyed confirm GET/app GET delay =24 ABA probes; 2 unchanged selection controls','event_evidence_count':24,'responses':'Controlled responses derived from an actual previous SQLite/Worker candidate; no HTTP/backend-proof claim'},'actual_http_ui_scenarios':ui,'http_ui_checks':572,'http_ui_native_dom_gestures':494,'http_ui_diagnostic_summaries':2,'own_before_after_paths':len(after),'own_source_unchanged':True,'parent_freeze_paths_independently_verified':len(full_after),'parent_freeze_unchanged':True,'source_sha256':after,'red_history':'red-history.json','red_counts_not_summed':True,'live_requests':0,'not_run':['Real provider/paid calls','Semantic goal acceptance','Native OS/browser history undo or visual/layout acceptance','PostgreSQL/Windows','Old source full upgrade','Deployment/push/full P-A/P-B'],'unresolved_product_defects':[],'blockers':[],'repository_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()}
assert result['pytest_total']==68
(out/'final-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
report=f'''独立终审 PASS；未解决产品缺陷0，阻塞0。只审同卡编辑/撤销和材料选择ABA导致迟到确认/原key恢复接管的P2修复。

冻结源实际 pytest 68 PASS / 0 FAIL / ERROR / SKIP：backend53（author13、raw14、adversarial26）与实际IPC/进程内HTTP15。15实际页共572断言、494个 event=native DOM dispatch 的可见启用gesture；另2条undo input_events诊断summary分列，不计作gesture（user_actions总长度496）。每场景只有1次generationPOST和1次confirmPOST，恢复为原keyGET。

另独立CONTROLLED_NOT_HTTP 26 PASS：7字段＋材料select在confirm POST、keyed confirm GET、app GET等待点各ABA共24；2无编辑对照仍正常可见打开exact app。最终值回A、旧workspace/app/goal代次不变、InputEvent insertText/historyUndo或select input/change使新编辑代次增加；旧交接不导航、不抢焦点，保留草稿。材料0→4、各文字字段0→2，24份事件证据保存。

旧7e86ec7页面四文件经git show只读保存；红轮补夹具后2PASS/24产品FAIL。首次2PASS/24FAIL中21产品、3材料options缺失的fixture FAIL原样保留，原driver保留；补入实际frozen material option后3项都复现产品FAIL。重复红轮节点不叠加。准确历史见red-history.json、controlled-red*.json/log和两个原driver。

唯一产品改动给8编辑控件input/change添加单调goalApplicationDraftGeneration，handoff保存并复核edit；不回退counter，保持完整draft值guard、身份/项目/目标/workspace/app guard。现有事件处理不被覆盖，确认意图/授权/持久候选及模型预算不变，fresh显式原key恢复可重新交接。

16相关src/test路径前后SHA一致；独立核父358源/测试/pyproject冻结路径全部一致，HTTP和controlled每份加载SHA匹配。
goal-application.js SHA256 {after['src/sim2act/web/goal-application.js']}
完整SHA见source-before.json/source-after.json、complete-source-verification.json、final-review.json。

LIVE0。JSDOM合成InputEvent insertText/historyUndo与selection事件不是原生OS/browser undo、layout或视觉验收；真实provider/付费、语义/owner、PG/Windows、旧源码完整升级、部署/远端CI及完整P-A/P-B仍NOT_RUN。独审不写repo产品/测试/docs/.git，不改任何旧证据。
'''
(out/'FINAL_REVIEW.txt').write_text(report)
print(json.dumps({'status':'PASS','pytest':68,'controlled':26,'http_ui_checks':572,'http_ui_gestures':494,'http_ui_summary':2,'own_source_paths_unchanged':16,'parent_freeze_paths_match':len(full_after),'edit_source_sha256':after['src/sim2act/web/goal-application.js']},ensure_ascii=False,indent=2))
