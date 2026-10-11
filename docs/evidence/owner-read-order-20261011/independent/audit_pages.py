import hashlib,json,sys
from pathlib import Path
repo=Path('/workspace/Sim2Act');root=Path('/tmp/owner-read-order-review-20261011');folder=root/sys.argv[1];out=root/sys.argv[2]
results=[]
for p in sorted(folder.glob('*.json')):
    o=json.loads(p.read_text())
    if 'static_resource_loads' not in o:continue
    loads=o['static_resource_loads'];boots=sorted({r['boot'] for r in loads});errors=[]
    for r in loads:
        name='index.html' if r['path']=='/' else r['path'].removeprefix('/')
        expected=(repo/'src/sim2act/web'/name).read_bytes();ctype=r['content_type'].split(';')[0]
        validtype=ctype=='text/html' if name=='index.html' else ctype=='text/css' if name=='app.css' else ctype in {'text/javascript','application/javascript'}
        if r['status']!=200 or r['bytes']!=len(expected) or r['sha256']!=hashlib.sha256(expected).hexdigest() or not validtype:errors.append(r)
    for b in boots:
        paths=[r['path'] for r in loads if r['boot']==b]
        if len(paths)!=19 or len(set(paths))!=19:errors.append({'boot':b,'paths':paths})
    gestures=[a for a in o['user_actions'] if a.get('event')=='native DOM dispatch'];diagnostics=[a for a in o['user_actions'] if a.get('event')!='native DOM dispatch']
    assert all(a.get('visible') and a.get('enabled') for a in gestures)
    assert not errors,errors
    results.append({'file':str(p.relative_to(root)),'status':o['status'],'checks':len(o['checks']),'gestures':len(gestures),'diagnostic_summaries':len(diagnostics),'boots':len(boots),'actual_asset_http_gets':len(loads),'asset_mismatches':errors,'loaded_source_sha256':o['loaded_source_sha256'],'has_read_order_evidence':o.get('read_order_evidence') is not None})
value={'classification':'ACTUAL_IPC_IN_PROCESS_HTTP_ASSET_AND_JSDOM_VISIBLE_GESTURE_AUDIT','page_count':len(results),'assertion_count':sum(r['checks'] for r in results),'visible_enabled_dom_gesture_count':sum(r['gestures'] for r in results),'diagnostic_summaries':sum(r['diagnostic_summaries'] for r in results),'boot_count':sum(r['boots'] for r in results),'actual_asset_gets':sum(r['actual_asset_http_gets'] for r in results),'all_assets_status_type_utf8_bytes_sha256_match':True,'pages':results,'native_browser':'NOT_RUN','real_owner_semantic_signoff':'NOT_RUN','live_models':0}
out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in value.items() if k!='pages'}))
