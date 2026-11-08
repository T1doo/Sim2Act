"""Assemble a self-contained editorial handoff, never a claim of generated video."""
from pathlib import Path
import json,hashlib,shutil,struct,csv,re,copy
ROOT=Path(__file__).resolve().parents[3];BASE=ROOT/'submission/04_视频';OUT=BASE/'制作交接_v08'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def js(p,o):write(p,json.dumps(o,ensure_ascii=False,indent=2))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
D=read(BASE/'脚本与提示词/影片状态时间线_v08_working.json');D.update(version='v08',fps=24,total_frames=6480,status='PREPARATION_ASSEMBLED_PENDING_CHECKS')
sc={s['id']:s for s in D['scenes']}
sc['S01']['narration']='科研申报协调人，又收到一批新材料。能否把核查方法，变成同事也能用的应用？'
# English action beats are deliberately different for every generated unit.
G={
'S01':(1,[0,8],['The colleague brings the cream folder from his own side and offers it across the desk.','The coordinator accepts the folder with both hands and sets it next to, not inside, the blue original folder.','She opens its cover once, looks between the two separate material sets, then turns to her laptop.','A short lateral camera move reveals the second workload and ends with the two folders separately grounded.']),
'S02':(2,[0,8],['Begin over the coordinator shoulder on three physical paper groups beside the blank laptop.','Her left index finger follows one line on a guideline page, then moves to the separate budget sheet.','She places an attachment sheet beside that budget and compares the two positions without stamping approval.','She gathers the three piles into an orderly fan, leaving the laptop screen clear for the next editorial cut.']),
'S03':(1,[2,5],['The coordinator turns from her own material folder toward her colleague.','She indicates the other workstation while keeping her original material set on her side.','The colleague brings his own cream folder closer to his own keyboard, establishing a second input.','He looks toward his blank screen; finish before any result or application status appears.']),
'S04':(2,[0,3],['The coordinator draws a new page out of the blue folder with continuous fingertip contact.','She places it beside the keyboard, with the older pages still visible at left.','Her right hand moves onto the trackpad for one deliberate input gesture.','The camera settles with the full empty display visible, ready for a straight cut to the approved target interface.']),
'S08':(3,[0,3],['Establish the paper carrier, central violet method cassette and blank display on one shared base.','Follow one sheet being seated in the carrier; the connector and cassette remain aligned.','A small physical lever on the cassette moves and its linkage reaches the base of the display, without producing a result.','End on the common mounting structure so the editor can explain a shared definition with exact UI layers.']),
'S09':(2,[0,2],['The coordinator lifts one loose sheet from the adjacent pile while her other hand holds the folder open.','She places the sheet into the folder without adding a signature or changing printed content.','She closes the folder lightly and returns her right hand to the trackpad.','End before any software confirmation; the added document and recheck are separate editorial states.']),
'S11':(2,[0,3],['Begin at the coordinator shoulder as she reviews the open folder and blank screen.','She finishes a short page comparison and lowers the paper onto the left side of the desk.','Her gaze shifts to the laptop; her hands rest below its display.','Track slightly toward the screen, keeping all four corners visible for a match cut to the approved preview.']),
'S14':(2,[0,2],['Begin with the coordinator facing the stable blank laptop display.','Her right index finger makes one deliberate trackpad press while her other hand remains by the blue folder.','She lifts the pressing finger and turns her attention to the display without celebrating or gesturing success.','Settle on the screen edge; the exact run request and later result will appear in separate editorial layers.']),
'S15':(1,[0,2],['The coordinator indicates the adjacent workstation rather than handing over an existing answer.','The colleague lowers his cream folder onto his own desk; the blue original stays with the coordinator.','He opens the cream folder and sets a new page by his own keyboard.','The camera tracks toward the colleague screen and ends before a result is displayed.']),
'S16':(3,[3.2,5.5],['Begin with the old blue paper carrier visibly connected to the violet method cassette.','The small connector disengages at its own joint; the cassette does not dissolve or change identity.','The old carrier slides a short distance away while retaining its paper as an original source record.','Leave the detached carrier and stable cassette simultaneously visible; the new input has not yet connected.']),
'S17':(3,[0,3],['The violet cassette and blank output display remain stationary on the base.','The old blue carrier retracts from the joint and stops intact at the rear edge.','The separate ivory new-input carrier approaches the now-free joint without mixing papers with the old carrier.','It stops just short of connection, leaving an explicit gap for the subsequent editorial input-check gate.']),
'S19':(4,[0,2.7],['Establish the three installed tiles and the distinct cyan candidate inset waiting at the side.','The candidate moves closer to the centre violet inset but does not displace it yet.','A narrow controlled light reveals only the centre joint; the two white neighbouring tiles stay untouched.','Both archival sleeves remain motionless and intact; stop before replacement, which requires later explicit confirmation.']),
'S21':(4,[7,9],['Establish the rail after an editorially confirmed update, with the cyan inset now occupying the centre slot.','The old violet inset rests visibly on the side tray instead of being destroyed.','The camera shifts attention toward the two separate archival sleeves in the foreground.','End with both records present and the neighbouring white tiles unchanged; no numbers or results are generated.']),
'S24':(5,[0,5],['The single amber capsule advances once along the track toward the sensor arch.','It stops while the receipt slot remains empty, retaining its distinctive notch and amber colour.','A narrow sensing pulse travels the return channel to query the same original capsule.','The capsule stays singular and unresolved; no second dispatch, duplicate capsule, green light or receipt appears.']),
'S26':(1,[0,2],['Both colleagues sit at their respective workstations with their own folders.','The coordinator makes a short indication toward the colleague screen while her own blue folder stays put.','The colleague uses the trackpad once to open an existing entry, without typing or creating a new result.','The camera settles toward his clear screen; cut to the approved application library before displaying exact content.']),
'S27':(4,[0,2],['Begin in a close product shot of the shared silver rail with the installed tiles.','The camera eases backward, revealing the preserved archival sleeves and coherent assembly.','Cool highlights settle across the material surfaces without changing any object or inventing a logo.','End in a quiet stable composition suitable for a clean cut to the original brand card, not a morph into typography.'])}
names={i:next((OUT/'assets/scenes').glob(f'G{i:02d}_*.png')).name for i in range(1,6)}
# The two optional expansion contexts use existing precise UI instead of adding generic office stock.
sc['S25']['route']='U+P';sc['S25']['requires_generation']=False
sc['S25']['route_decision']='扩展情境新图为可选；保留活动/实验原图，以账目关联和配置对照的精确焦点组织各5秒。'
facts=read(ROOT/'submission/01_赛题与计划/故事事实源_v03.json');oldfacts=copy.deepcopy(facts)
times={'click_input_checks':164,'show_check_report':167,'confirm_pb_scope':172,'publish_pb':173,'show_pb_published':173.5,'click_pb_run':175.5,'editorial_time_jump_to_pb_result':177.3,'confirm_change_and_publish_v2':192,'show_published_v2':193,'click_run_a2':195,'click_history':204.8}
for e in facts['events']:e['time']=times.get(e['action'],e['time'])
facts['reference_review']='review/完整审阅回执_v08.md';facts['runtime_evidence']['source']='evidence/verification.json'
js(OUT/'business_facts.json',facts)
js(OUT/'checks/事件时间差异.json',[dict(action=a['action'],old=a['time'],new=b['time']) for a,b in zip(oldfacts['events'],facts['events']) if a['time']!=b['time']])
sc['S21']['clicks'][0]['at']=4.8
for s in D['scenes']:
 for i,f in enumerate(s['frames']):
  n=int(s['id'][1:]);f['state_id']=s['id']+'_'+str(i+1).zfill(2)
  app='story_app_extracted' if 17<=n<=18 else 'story_app_research'
  if n==16 and f['at']>=3:app=None
  case='case_b' if n==15 else 'case_pb_new' if n==18 else 'case_a'
  release='v2' if n>=20 else 'v1';rule='rule_r2' if n>=20 else 'rule_r1'
  result='story_result_a1' if n==14 and f['at']>=5 else 'story_result_b1' if n==15 and f['at']>=7 else 'story_result_pb_new' if n==18 and f['at']>=7.3 else 'story_result_a2' if n==21 or(n==26 and f['at']>=4) else None
  f['identity']=dict(workspace_id='story_workspace_xingqiao',app_id=app,app_release=release if app else None,rule_revision=rule if app else None,case_id=case,instance_id='story_instance_b' if case=='case_b' else 'story_instance_pb' if case=='case_pb_new' else 'story_instance_a',result_id=result,source_task_id='story_task_once' if n in [16,17,18] and not(n==16 and f['at']<3) else None)
  if n in [22,23]:f['identity']=dict(kind='EVIDENCE_LOCKED',source_commit='21b33dc4',instance_id='iinstance_0c50015fda966e83b7b9d150352cef2f',result_revision=1 if n==22 else 2,semantic_acceptance='NOT_RUN',owner_acceptance='PENDING')
  elif n in [1,2,3,24,25,27] or (n==26 and f['at']<4):f['identity']=dict(kind='SCENE_OR_CATALOG',app_id=None,result_id=None,context=f['context'])
  elif n<13:f['identity'].update(app_release=None,result_id=None,publication_state='CANDIDATE_OR_PREVIEW',preview_rule='rule_r1')
  elif n==13 and f['at']<8:f['identity'].update(app_release=None,publication_state='AWAITING_CONFIRMATION_OR_PUBLISHING')
  elif n==16 and f['at']<3:f['identity']=dict(kind='PA_HISTORY',app_id='story_app_research',app_release='v1',result_ids=['story_result_a1','story_result_b1'],instance_ids=['story_instance_a','story_instance_b'])
  elif n==16:f['identity']=dict(kind='INDEPENDENT_TASK',task_id='story_task_once',app_id=None,result_id=None)
  elif n==17 or (n==18 and f['at']<3.5):f['identity'].update(app_release=None,instance_id=None,result_id=None,publication_state='EXTRACTION_CANDIDATE')
  elif n==19 or (n==20 and f['at']<3):f['identity'].update(app_release='v1',rule_revision='rule_r1',candidate_release='v2',preview_rule='rule_r2',result_id=None)
  if n==21 and f['at']>=5:f['identity'].update(result_ids=['story_result_a1','story_result_a2'],historical_versions=[['v1','rule_r1'],['v2','rule_r2']])
  if n in [18,20] and f.get('overlay',{} ) and f['overlay']['type']=='busy' and '已发布' in f['asset'] or n==20 and f.get('overlay') and f['at']==5:
   f['overlay']={'type':'running_region','text':'正在核查本次材料' if n==18 else '正在按应用 v2 核对','regions':[[.37,.49,.30,.12],[.12,.85,.86,.10],[.83,.115,.155,.07]],'footer':'本次运行进行中 · 人工判断独立保留'}
  # Treat P-A history and P-B task as separate context scopes.
  if n==16:f['context']='科研申报助手 / 授权案例历史' if f['at']<3 else '独立任务 / 申报材料核查'
  f.setdefault('context',s['context'])
  f['at_frame']=round(f['at']*24)
 sc[s['id']]['requires_generation']=s['id'] in G
# Original pixel assets, never regenerated.
used={f['asset'] for s in D['scenes'] for f in s['frames']};used.update(x['asset'] for s in D['scenes'] for f in s['frames'] for x in f.get('compare',[]))
assetmap={};inventory=[]
for name in sorted(used):
 src=BASE/'制作交接_v07/参考图'/name
 category='EVIDENCE_LOCKED' if name.startswith('E_') else 'EDIT_ONLY' if name.startswith(('ARCH-','T4-','A12_')) else 'GENERATE_SCENE' if name.startswith('A01_工作') else 'APPROVED_UI_LOCKED'
 folder='evidence' if category=='EVIDENCE_LOCKED' else 'scenes' if category=='GENERATE_SCENE' else 'ui_locked'
 dst=OUT/'assets'/folder/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assetmap[name]=dst.relative_to(OUT).as_posix()
 inventory.append(dict(path=assetmap[name],sha256=sha(dst),dimensions=list(struct.unpack('>II',dst.read_bytes()[16:24])),category=category,regenerate=False if category!='GENERATE_SCENE' else None,source='v07 adopted original'))
for i,name in names.items():
 p=OUT/'assets/scenes'/name;assetmap[name]=p.relative_to(OUT).as_posix();inventory.append(dict(path=assetmap[name],sha256=sha(p),dimensions=list(struct.unpack('>II',p.read_bytes()[16:24])),category='GENERATE_SCENE',source='built-in imagegen, inspected 2026-11-08',reference_role='composition_and_identity_not_forced_keyframe'))
D['asset_dimensions']={Path(a['path']).name:a['dimensions'] for a in inventory};D['asset_paths']=assetmap
shots=[];director=[];voices=[]
for s in D['scenes']:
 sid=s['id'];folder=OUT/'shots'/sid;folder.mkdir(parents=True,exist_ok=True);n=int(sid[1:]);gen=sid in G
 info=dict(shot_id=sid,edit_start=s['start'],edit_end=s['start']+10,edit_duration=10,edit_fps=24,route=s['route'],requires_generation=gen,states=s['frames'],clicks=s['clicks'],initial_state=s['frames'][0]['state'],end_state=s['frames'][-1]['state'],main_action=s['action_brief'],transition=s['transition'],actual_duration=None,actual_fps=None,actual_frame_count=None,status='PREPARATION_READY_VIDEO_NOT_GENERATED',audio_role='连续后期旁白，现场声候选须试听，配乐连续主轨',fallback='生成动作失败则定点修订；贴屏跟踪困难改为匹配剪切。不得循环/长定格/改fps头凑时长。')
 info['source_assets']=[a for a in inventory if Path(a['path']).name in {f['asset'] for f in s['frames']}]
 if gen:
  refidx,window,beats=G[sid];refname=names[refidx];rp=OUT/assetmap[refname]
  info.update(requested_generation_duration=8,requested_generation_fps=24,generation_mode='Ref2VA',mode_status='SERVER_VERIFY_EXISTING_APPROVED_CAPABILITY',generation_reference=[dict(label='<Picture 1>',path=assetmap[refname],sha256=sha(rp),role='subject_environment_composition',forced_time=None)],generation_edit_window=window,source_in_out_policy='从实际源片选择动作完整片段；所需编辑时长短于8秒，不必强塞全源片。',priority='SIM-D1' if sid in ['S04','S11'] else 'SIM-D2' if sid in ['S14','S15'] else 'SIM-D3' if sid in ['S19','S21'] else 'AFTER_D1_D2_D3')
  subject=('the coordinator in the blue shirt, her colleague in the cream shirt, the two distinct folders and their twilight office workstations' if refidx==1 else 'the blue-shirted coordinator, blue folder, paper groups and unobstructed neutral laptop display' if refidx==2 else 'the single modular apparatus, its separately identifiable input carrier, central cassette and blank output surface' if refidx==3 else 'the three installed tiles, old violet inset, separate cyan candidate and two preserved archival sleeves' if refidx==4 else 'the single notched amber capsule, sensor arch, empty receipt slot and return sensing channel')
  detail=f'''The target is an eight-second continuous product-film scene. [Shot 1] Establish {subject} as <Subject 1> from <Picture 1>. Use the reference for material, object identity, lighting direction and spatial relationships, rather than claiming it is a forced first frame. Compose the action with clear foreground and background separation. The viewer should follow one physical change and understand which objects remain. Keep the visible object count stable and make contact, depth and occlusion plausible.

During 0–2 seconds: {beats[0]} Give this initial action a clear anticipation and a measured start. The moving item should have continuous edges and a stable orientation, with no spontaneous duplicates. Keep other objects stationary enough to establish a visual baseline. Let the subject movement carry the story; do not substitute a lens zoom or decorative light shimmer for the event.

During 2–4 seconds: {beats[1]} Preserve the causal connection to the preceding motion. A hand or connector must remain attached to the object it controls until release is visibly complete. Let the camera make a short smooth lateral adjustment only when it helps reveal the contact point. Preserve the reference light direction, surface texture and scene geometry throughout the movement.

During 4–6 seconds: {beats[2]} The visible change must occur on the same identified object, without a cut that exchanges it for another. Allow a brief settling motion after contact rather than mechanical freezing. Avoid adding an unrequested object, readable document content, generated interface, badge, celebration or claimed business outcome. Keep the screen or blank product surface neutral and stable for editorial use, while preserving natural reflections without glare that obscures its boundary.

During 6–8 seconds: {beats[3]} Complete the action with a usable moving tail and a clear composition for the next editorial cut. Maintain coherent perspective and enough separation around the important object to support a precise callout. The final image must communicate the specified unresolved or retained state, not invent success. No dialogue or lip-synchronised speech is required. Camera motion remains subordinate to the described action; avoid sudden orbits, spinning panels and a transition that melts one object into another. All exact product text and business state transitions are handled in a separate editorial composition, outside this generated scene.'''
  prompt=f'''subject_definitions:
<Subject 1> is {subject} in <Picture 1>; retain the visible identities and spatial relationships. This is a composition and appearance reference, not a forced multi-keyframe instruction.

summary:
[reference generation] {beats[0]} {beats[3]} Generate the physical action in eight seconds, without generating a software interface or business result.

retention_analysis:
<Subject 1> (appears in [Shot 1]): partially_preserved - preserve identity, costume or material, and surrounding geometry; change only the explicitly described poses and object positions. Blank surfaces remain blank.

detailed_description:
{detail}

overall_soundscape:
{'Quiet twilight office ambience, restrained paper and folder contact, one light input touch where visibly motivated.' if refidx<3 else 'Subtle contact and sliding sounds matching the visible mechanical metaphor, low neutral room tone.'} No dialogue, spoken claims, success chime or music.

non_diegetic_music:
N/A
'''
  pp=folder/'H3_prompt.txt';write(pp,prompt);info['prompt_path']=pp.relative_to(OUT).as_posix();info['prompt_sha256']=sha(pp);info['action_beats']=beats
  s['generation_reference_asset']=refname;s['generation_edit_window']=window
 else:info.update(requested_generation_duration=None,generation_mode=None,mode_status='NOT_REQUIRED',generation_reference=[],priority='EDIT_ONLY')
 # A2 local labels remain outside actual UI claims.
 comp=[f'# {sid} · {s["start"]}–{s["start"]+10}秒', '',f'路线：{s["route"]}。主动作：{s["action_brief"]}', '',f'保持：{s["locked_constraints"]}', '', '画布1920×1080、24fps。UI原比例；精确文字、字幕与品牌在场景画质处理之后合成。原图有标题时不再叠同义大标题。', '', '采用图与状态（时间为镜内秒）：','']
 for f in s['frames']:
  comp.append(f'- {f["at"]}秒：`../../{assetmap[f["asset"]]}`；{f["state"]}；页头：{f["context"]}。状态ID {f["state_id"]}。')
  if f.get('overlay',{} ) and f['overlay']['type']=='running_region':comp.append('  本次运行区域、底栏等待文字及启动按钮用不透明精确层替换，保留材料、已确认范围与旧历史；不能使用透明busy层让“尚未运行”透出。规范坐标见shot.json。')
 if gen:
  comp+=['',f'生成参考：`../../{assetmap[refname]}`，Picture 1。编辑局部 {window[0]}–{window[1]} 秒取实际源片动作；参考静帧不是已生成视频。', '贴屏可选，默认采用匹配剪切至正面UI。G02原图屏幕内角归一化约(0.467,0.205)、(0.738,0.205)、(0.738,0.500)、(0.467,0.500)，仅供初始参考，实际片逐帧跟踪重算；手跨屏时需遮挡蒙版。G01右屏有手遮挡，优先左屏或剪切。机制场景为视觉比喻，不能表达软件需要硬件设备。']
 comp+=['','每镜最多一条局部短标注，标题与标注分时显示；金额、结果、确认顺序依states与business_facts。','旁白：'+s['narration'],'衔接：'+s['transition'],'声音：人物不对口型；旁白章节连续录制，现场声实际试听后取用。']
 write(folder/'composite.md','\n'.join(comp));info['composite_path']=(folder/'composite.md').relative_to(OUT).as_posix();js(folder/'shot.json',info);shots.append(info)
 voices.extend([f'## {sid} · {s["start"]}–{s["start"]+10}秒','',s['narration'],''])
 for sec in range(10):
  f=max((f for f in s['frames'] if f['at']<=sec),key=lambda f:f['at']);ev=[c['label'] for c in s['clicks'] if sec<=c['at']<sec+1]
  action=G[sid][2][min(3,sec//2)] if gen and G[sid][1][0]<=sec<G[sid][1][1] else s['action_brief']
  director.append(dict(shot_id=sid,start=s['start']+sec,end=s['start']+sec+1,route=s['route'],subject_action=action,object_state=f['state'],state_id=f['state_id'],context=f['context'],camera='参考动作指定景别；生成片短横移，UI正面阅读/按需局部',exact_interaction='；'.join(ev) or '阅读当前状态，不推定新执行',edit='生成主体取用' if gen and G[sid][1][0]<=sec<G[sid][1][1] else '定稿UI/精确图层，按state切换',exact_constraints=s['locked_constraints']))
js(OUT/'asset_manifest.json',inventory);js(OUT/'ui_locked_manifest.json',[a for a in inventory if a['category'] in ['APPROVED_UI_LOCKED','EVIDENCE_LOCKED']]);js(OUT/'时间线_v08.json',D)
js(OUT/'film_manifest.json',dict(version='v08',product_book='v05',duration=270,fps=24,total_frames=6480,status='PREPARATION_READY_NOT_VIDEO_ACCEPTANCE',generation_mode_policy='Ref2VA preferred only if existing approved server supports it; no inferred capability',actual_video_generated=False,shots=[dict(shot_id=x['shot_id'],path=f'shots/{x["shot_id"]}/shot.json',requires_generation=x['requires_generation'],priority=x['priority']) for x in shots]))
with (OUT/'导演表_270秒.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(director[0]));w.writeheader();w.writerows(director)
write(OUT/'旁白稿.md','# 连续章节旁白\n\n按章节连读，不每10秒机械重起；正式录音后重对齐字幕。\n\n'+'\n'.join(voices))
subs=read(BASE/'制作交接_v07/字幕文案_v07.json');s24=[x for x in subs if x['scene']=='S24'];parts=['回执未确认，先核对原操作；','不盲目重发，也不把未知当成功。']
for x,t in zip(s24,parts):x['text']=t;x['lines']=[t]
for x,t in zip([x for x in subs if x['scene']=='S01'],['科研申报协调人，又收到一批新材料。','能否把核查方法，变成同事也能用的应用？']):x['text']=t;x['lines']=[t]
def tc(t):ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
write(OUT/'字幕时间草案.srt','\n'.join(f'{i}\n{tc(x["start"])} --> {tc(x["end"])}\n'+ '\n'.join(x['lines'])+'\n' for i,x in enumerate(subs,1)))
js(OUT/'字幕文案.json',subs)
# Preview displays generation reference stills honestly; precise state renderer is executable.
tpl=(BASE/'制作工具/story_viewer.html').read_text(encoding='utf-8')
tpl=tpl.replace("'参考图/'+encodeURIComponent(n)","D.asset_paths[n]")
tpl=tpl.replace("const o=f.overlay;","const o=f.overlay;if(o?.type==='running_region'){h+=o.regions.map((r,i)=>`<div class=\"running-patch\" style=\"${rect(r)}\">${i===0?esc(o.text):i===1?esc(o.footer):'运行中'}</div>`).join('');}")
tpl=tpl.replace('</style>','.running-patch{position:absolute;background:#eef2ff;display:grid;place-items:center;color:#17365d;font-size:1.9cqw;font-weight:600;border-radius:10px;z-index:4}</style>')
tpl=tpl.replace("$('state').textContent=s.id+' · '+f.state", "$('state').textContent=s.id+' · '+f.state+' · '+s.route+(s.requires_generation?' · 另有主体生成片段，见制作说明':' · 精确剪辑')")
guide="""const guided={S05:[[2,4,.13,.24,.24,.54],[4,6,.39,.24,.25,.54],[6,8,.67,.24,.30,.54]],S06:[[1,3,.13,.25,.27,.50],[3,6,.43,.25,.23,.50],[6,9,.70,.25,.26,.50]],S10:[[1,4,.70,.25,.26,.20],[4,6,.70,.47,.26,.18],[6,9,.70,.66,.26,.20]],S24:[[0,3,.05,.23,.25,.50],[3,7,.35,.23,.28,.50],[7,10,.66,.23,.28,.50]]};$('content').querySelectorAll('.reading-guide').forEach(e=>e.remove());for(const g of guided[s.id]||[]){if(local>=g[0]&&local<g[1])$('content').insertAdjacentHTML('beforeend',`<div class="reading-guide" style="position:absolute;${rect(g.slice(2))};border-left:3px solid #6e60dc;pointer-events:none;background:linear-gradient(90deg,#9a8aff18,transparent);transition:opacity .2s"></div>`)}"""
tpl=tpl.replace("const sub=subs.find",guide+"const sub=subs.find")
tpl=tpl.replace("const context=f.context||(f.asset.startsWith('A07_')?'任务 · 申报材料核查':s.context)","const context=f.context")
tpl=tpl.replace('固定图层与状态时间线 · 临时语音用于校时 · 实际H3效果另行验收','v08 精确交互预演 · 生成场景仅参考静帧，不是动态小样 · 正式配音待制作')
tpl=tpl.replace('<audio id="track" src="预演旁白_270秒.wav" preload="metadata"></audio>','<audio id="track" preload="none"></audio>')
tpl=tpl.replace("if(location.protocol.startsWith('http'))fetch('预演旁白_270秒.wav')","if(false)fetch('unused')")
tpl=tpl.replace('__DATA__',json.dumps(D,ensure_ascii=False)).replace('__SUBS__',json.dumps(subs,ensure_ascii=False))
write(OUT/'精确交互预演.html',tpl)
print(json.dumps(dict(shots=27,generation_units=len(G),edit_only=27-len(G),assets=len(inventory),frames=sum(len(s['frames']) for s in D['scenes'])),ensure_ascii=True))
