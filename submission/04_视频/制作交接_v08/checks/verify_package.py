from pathlib import Path
import json,hashlib,csv,re,copy
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads((R/p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def causal(f):
 e={x['action']:x['time'] for x in f['events'] if x['action']!='editorial_time_jump_to_result'}
 for names in [('confirm_publish_scope','click_publish_v1','show_published_v1','click_run_a1'),('show_independent_task','click_extract_application','click_input_checks','show_check_report','confirm_pb_scope','publish_pb','show_pb_published','click_pb_run','editorial_time_jump_to_pb_result'),('confirm_change_and_publish_v2','show_published_v2','click_run_a2')]:
  vals=[e[n] for n in names];assert all(a<b for a,b in zip(vals,vals[1:])),names
 assert e['show_check_report']==167 and e['click_pb_run']-e['show_pb_published']==2
 assert e['click_run_a2']-e['show_published_v2']==2
 assert [r['budget_total'] for r in f['results']]==['90000.00','76000.00','90000.00']
 assert f['results'][0]['app_release']=='v1' and f['results'][2]['app_release']=='v2'
f=read('business_facts.json');causal(f)
bad=copy.deepcopy(f)
next(x for x in bad['events'] if x['action']=='publish_pb')['time']=171
try:causal(bad)
except AssertionError:negative=True
else:raise AssertionError('publish-before-confirm was accepted')
m=read('film_manifest.json');assert m['duration']==270 and m['fps']==24 and m['total_frames']==6480
assets=read('asset_manifest.json'); amap={Path(a['path']).name:a for a in assets}
for a in assets:assert sha(R/a['path'])==a['sha256'],a['path']
prompts=[];routes=[];states=0
for i,entry in enumerate(m['shots']):
 s=read(entry['path']);assert s['edit_start']==i*10 and s['edit_end']==(i+1)*10
 assert (R/s['composite_path']).is_file()
 assert s['actual_duration'] is None and s['actual_fps'] is None
 assert s['requested_generation_duration']==(8 if s['requires_generation'] else None)
 if s['requires_generation']:
  p=R/s['prompt_path'];assert sha(p)==s['prompt_sha256'];t=p.read_text(encoding='utf-8');prompts.append(sha(p))
  fields=['subject_definitions:','summary:','retention_analysis:','detailed_description:','overall_soundscape:','non_diegetic_music:'];assert all(t.count(k)==1 for k in fields)
  assert [t.index(k) for k in fields]==sorted(t.index(k) for k in fields)
  assert set(re.findall(r'<Picture (\d+)>',t))=={'1'}
  for a in s['generation_reference']:assert sha(R/a['path'])==a['sha256']
  assert 'T2VA_BACKGROUND_ONLY' not in t and 'exactly 10 seconds' not in t
 else:assert not (R/entry['path']).with_name('H3_prompt.txt').exists()
 for st in s['states']:
  assert st['asset'] in amap and st['context'] and st['identity'];states+=1
  if st.get('overlay',{} ) and st['overlay']['type']=='running_region':assert len(st['overlay']['regions'])==3
 routes.append(s['route'])
assert len(prompts)==16 and len(set(prompts))==16
assert read('shots/S16/shot.json')['states'][0]['context'].startswith('科研申报助手')
assert read('shots/S21/shot.json')['states'][0]['context'].endswith('结果3')
assert '既有结果3' in read('shots/S26/shot.json')['states'][1]['context']
subs=read('字幕文案.json');assert len(subs)==52
for i,x in enumerate(subs):
 assert len(x['lines'])<=2 and all(len(l)<=22 for l in x['lines'])
 if i:assert subs[i-1]['end']<=x['start']
timeline=read('时间线_v08.json')
for s in timeline['scenes']:assert ''.join(x['text'] for x in subs if x['scene']==s['id'])==s['narration'],s['id']
with (R/'导演表_270秒.csv').open(encoding='utf-8-sig',newline='') as fp:rows=list(csv.DictReader(fp))
assert len(rows)==270 and all(int(r['start'])==i for i,r in enumerate(rows))
report=dict(status='PASS_PREPARATION_CHECKS_NOT_VIDEO_ACCEPTANCE',shots=27,seconds=270,fps=24,frames=6480,assets=len(assets),state_definitions=states,generation_prompts=16,unique_prompts=16,edit_only_shots=11,subtitle_blocks=52,negative_publish_before_confirm_rejected=negative,external_pending=['实际H3片段','服务器模式/fps/实际时长','正式声轨/字幕重新对齐','完整成片人工听审及压缩后扫码'])
(R/'checks/文件与哈希核对.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
