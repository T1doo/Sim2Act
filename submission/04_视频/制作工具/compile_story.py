from pathlib import Path
import json,csv,html,hashlib,shutil,argparse
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'submission/04_视频'
parser=argparse.ArgumentParser();parser.add_argument('--source',default='影片状态时间线_v04.json');parser.add_argument('--output',default='审阅修订_A轮_v04');args=parser.parse_args()
SRC=BASE/'脚本与提示词'/args.source
OUT=BASE/args.output;OUT.mkdir(exist_ok=True)
D=json.loads(SRC.read_text(encoding='utf-8'));assert D['duration']==270 and len(D['scenes'])==27
facts=(SRC.parent/D['facts_file']).resolve();assert hashlib.sha256(facts.read_bytes()).hexdigest()==D['facts_sha256']
def source(name):
    folder='submission/03_图片与截图/技术图_v02/' if name.startswith(('ARCH-','T1-','T2-','T3-','T4-')) else ('submission/03_图片与截图/实际运行/' if name.startswith('E_') else 'submission/04_视频/生成图片/')
    return ROOT/folder/name
used={f['asset'] for s in D['scenes'] for f in s['frames']}
for name in used:assert source(name).is_file(),name
assets=OUT/'参考图';assets.mkdir(exist_ok=True)
for name in used:shutil.copy2(source(name),assets/name)
rows=[];preview=[];md=['# 270秒状态导演表 v04','','由影片状态时间线v04生成。A轮修订：关键因果状态已接入；技术实例、工程账本等后续工单仍待完成。',''];voice=['# 旁白待校时稿 v03','','本稿随状态时间线修订；旧270秒语音不再与本版混用。',''];upload=['# 逐段制作说明 v03','','除人物镜头外，H3仅生成无文字环境底片。业务UI、文字与确认状态由参考图和确定性图层呈现。当前A轮不是全部工单完成版。','']
for idx,s in enumerate(D['scenes']):
    assert s['start']==idx*10 and s['duration']==10
    assert s['frames'][0]['at']==0
    assert all(0<=f['at']<10 for f in s['frames'])
    assert [f['at'] for f in s['frames']]==sorted(f['at'] for f in s['frames'])
    for click in s['clicks']:assert 0<=click['at']<10 and 0<=click['x']<=1 and 0<=click['y']<=1
    folder=OUT/s['id'];folder.mkdir(exist_ok=True)
    if s['route']=='I2VA_SCENE':
        prompt=(BASE/'脚本与提示词/H3_v02'/f'{s["id"]}_v02.txt').read_text(encoding='utf-8');mode='I2VA';hint='上传Picture 1：'+s['frames'][0]['asset']
    else:
        prompt='''integrated_multimodal_description: [Shot 1] A refined 16:9 abstract background plate for a Chinese desktop product film. Keep the central ninety percent clean near-white with a very faint cool-blue tint. During 0–4 seconds a restrained cyan glow drifts along the far upper edge; during 4–7 seconds a faint lavender sheen follows it; during 7–10 seconds the motion settles. Keep the camera locked and exposure constant. No interface, text, numbers, buttons, checkbox, diagram, logo or person appears. The exact product UI, state transitions, pointer and subtitles are composited later as fixed layers, not generated here. Duration is exactly 10 seconds.

overall_soundscape: A low even air tone, without clicks, voices, alerts or speech. Deterministic action sounds are added in editing at the specified click times.

non_diegetic_music: N/A
''';mode='T2VA_BACKGROUND_ONLY';hint='不上传业务截图给H3重绘；同色背景可跨段复用，无需每段重复生成。'
    if s['id'] in ['S03','S27']:
        prompt=prompt.replace('near-white with a very faint cool-blue tint','deep midnight indigo').replace('far upper edge','far lower edge')
        prompt=prompt.replace('The exact product UI, state transitions, pointer and subtitles are composited later as fixed layers, not generated here.','The brand, URL, real QR code and download panel are composited later as fixed, sharp foreground layers. Never generate or animate a QR pattern, URL or brand lettering.')
    (folder/f'{s["id"]}_背景提示词_v03.txt').write_text(prompt,encoding='utf-8')
    instructions=[f'# {s["id"]} · {s["start"]}–{s["start"]+10}秒','',f'模式：{mode}。{hint}','',f'旁白：{s["narration"]}','','| 局部秒数 | 固定图层 | 状态 |','| --- | --- | --- |']
    for f in s['frames']:instructions.append(f'| {f["at"]:.1f} | [{f["asset"]}](../参考图/{f["asset"]}) | {f["state"]} |')
    instructions+=['','点击时刻：'+('；'.join(f'{c["at"]}秒 {c["label"]}' for c in s['clicks']) or '无新增点击'),'','处理方式：图层按源文件精确切换；busy状态为确定性遮罩，consent状态为明确勾选后的控件覆盖。不能把新图计入工程实测。','',s['transition']]
    (folder/'制作说明.md').write_text('\n'.join(instructions),encoding='utf-8')
    upload += [f'## {s["id"]}','','\n'.join(instructions[2:]),'']
    voice += [f'## {s["id"]} · {s["start"]}–{s["start"]+10}秒','',s['narration'],'']
    md += [f'## {s["id"]}','','| 全片秒数 | 局部秒数 | 状态画面 | 动作 |','| --- | --- | --- | --- |']
    for j in range(10):
        frame=max((f for f in s['frames'] if f['at']<=j),key=lambda f:f['at'])
        actions='；'.join(c['label'] for c in s['clicks'] if j<=c['at']<j+1) or '保持阅读'
        r=dict(scene=s['id'],start_seconds=s['start']+j,end_seconds=s['start']+j+1,local_start=j,local_end=j+1,asset=frame['asset'],state=frame['state'],overlay=json.dumps(frame['overlay'],ensure_ascii=False),action=actions,context=s['context'],camera=s['camera'],transition=s['transition'] if j==9 else '保持本镜',narration=s['narration'] if j==0 else '',screen_text=s['screen_text'])
        rows.append(r);md.append(f'| {r["start_seconds"]}–{r["end_seconds"]} | {j}–{j+1} | {frame["state"]} | {actions} |')
    md+=['',s['transition'],''];preview.append(s)
with (OUT/'逐秒导演表_v04.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(OUT/'逐秒导演表_v04.md').write_text('\n'.join(md),encoding='utf-8')
(OUT/'旁白待校时稿_v03.md').write_text('\n'.join(voice),encoding='utf-8')
(OUT/'逐段制作说明_v03.md').write_text('\n'.join(upload),encoding='utf-8')
shutil.copy2(SRC,OUT/SRC.name);shutil.copy2(facts,OUT/facts.name)
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sim2Act · A轮状态审阅</title><style>*{box-sizing:border-box}body{margin:0;background:#0d1728;color:#e6efff;font:16px/1.6 "Microsoft YaHei",sans-serif}main{max-width:1550px;margin:auto;padding:16px}header,nav{display:flex;align-items:center;gap:14px}header{justify-content:space-between}h1{font-size:22px;margin:0}small{color:#b5c6df}button,select{font:inherit;background:#244b83;border:1px solid #6387be;color:white;padding:8px 14px;border-radius:6px;cursor:pointer}input{flex:1}.stage{position:relative;aspect-ratio:1672/941;background:#eff4ff;margin:18px 0;overflow:hidden;border-radius:8px}.stage img{position:absolute;width:100%;height:100%;object-fit:contain}.context{position:absolute;left:13%;top:0;height:7.6%;right:0;background:linear-gradient(105deg,#f6f8ff,#e9effc);display:flex;align-items:center;padding:0 2%;gap:2%;font-size:clamp(12px,1.35vw,23px);font-weight:600;color:#142942;border-bottom:1px solid #dce4f4;white-space:nowrap}.veil{position:absolute;inset:7.6% 0 0;background:#edf2fa9c;display:grid;place-items:center;backdrop-filter:blur(2px)}.busy{background:#fff;border:1px solid #adbfdf;box-shadow:0 18px 45px #24416533;border-radius:12px;padding:2.5% 4%;font-size:clamp(17px,1.7vw,28px);font-weight:600;color:#183357;display:flex;gap:18px;align-items:center}.spin{width:28px;height:28px;border:3px solid #d9e5ff;border-top-color:#346cff;border-radius:50%;animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}.tick,.enable{position:absolute;display:grid;place-items:center;background:linear-gradient(135deg,#2586ff,#4630ef);color:white;border-radius:5px;font-weight:600}.tick{font-size:clamp(14px,1.6vw,28px)}.enable{font-size:clamp(15px,1.65vw,28px);box-shadow:0 3px 8px #284da330}.pointer{position:absolute;width:2.4%;height:auto;filter:drop-shadow(0 1px 2px #17314b88);z-index:7;transform:translate(-20%,-10%)}.ring{position:absolute;border:3px solid #2978ff;border-radius:50%;width:3.6%;aspect-ratio:1;transform:translate(-50%,-50%);z-index:6}article{display:grid;grid-template-columns:1.3fr 1fr;gap:24px}p{margin:10px 0}#clock{min-width:135px;font-variant-numeric:tabular-nums}#state{color:#8bd8ff}#error{color:#ffb7a7}@media(max-width:800px){article{grid-template-columns:1fr}header{display:block}nav{flex-wrap:wrap}}</style><main><header><div><h1>Sim2Act · A轮状态审阅</h1><small>关键因果与固定UI图层 · 无旧语音混播 · 其余审阅工单仍在修改</small></div><select id="scene" aria-label="选择镜头"></select></header><div class="stage" id="stage"><img id="frame" alt="当前正式设计状态"><div id="layers"></div></div><nav><button id="play">播放</button><input id="seek" type="range" min="0" max="270" step="0.1" value="0" aria-label="时间轴"><span id="clock"></span></nav><p id="error"></p><article><div><p id="state"></p><p id="voice"></p></div><div><p id="asset"></p><p id="transition"></p></div></article></main><script>const scenes=__DATA__;let t=0,playing=false,last=performance.now(),file='';const $=id=>document.getElementById(id);const esc=s=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const stamp=n=>String(Math.floor(n/60)).padStart(2,'0')+':'+(n%60).toFixed(1).padStart(4,'0');scenes.forEach(s=>{const o=document.createElement('option');o.value=s.start;o.textContent=s.id+' · '+stamp(s.start);$('scene').append(o)});function rect(r){return `left:${r[0]*100}%;top:${r[1]*100}%;width:${r[2]*100}%;height:${r[3]*100}%`}function draw(){const s=scenes[Math.min(26,Math.floor(t/10))],local=t-s.start,f=[...s.frames].reverse().find(f=>f.at<=local);if(file!==f.asset){file=f.asset;$('frame').src='参考图/'+file}$('clock').textContent=stamp(t)+' / 04:30.0';$('seek').value=t;$('scene').value=s.start;$('state').textContent=s.id+' · '+f.state;$('voice').textContent=s.narration;$('asset').textContent=f.asset;$('transition').textContent=s.transition;$('play').textContent=playing?'暂停':'播放';let h='';const isUI=!/^A12_|A01_工作|E_|ARCH-|T[1-4]-/.test(f.asset);if(isUI){const context=f.asset.startsWith('A07_')?'任务 · 申报材料核查':s.context;h+=`<div class="context">工作区　星桥研究团队　›　${esc(context)}</div>`}if(f.overlay?.type==='busy')h+=`<div class="veil"><div class="busy"><span class="spin"></span>${esc(f.overlay.text)}</div></div>`;if(f.overlay?.type==='consent')h+=`<div class="tick" style="${rect(f.overlay.checkbox)}">✓</div><div class="enable" style="${rect(f.overlay.button)}">${esc(f.overlay.button_text)}</div>`;for(const c of s.clicks){const delta=local-c.at;if(delta>=-.5&&delta<=.55){h+=`<svg class="pointer" viewBox="0 0 32 40" style="left:${c.x*100}%;top:${c.y*100}%"><path d="M3 2L3 30L11 24L17 37L23 34L17 22L28 22Z" fill="white" stroke="#183454" stroke-width="2"/></svg>`;if(delta>=0)h+=`<div class="ring" style="left:${c.x*100}%;top:${c.y*100}%;opacity:${1-delta/.55}"></div>`}}$('layers').innerHTML=h;window.currentState={scene:s.id,local,state:f.state,asset:f.asset,overlay:f.overlay?.type||null}}$('frame').onerror=()=>$('error').textContent='图像加载失败，请保留参考图目录';$('seek').oninput=e=>{t=Number(e.target.value);draw()};$('scene').onchange=e=>{t=Number(e.target.value);draw()};$('play').onclick=()=>{if(t===270)t=0;playing=!playing;last=performance.now();draw()};function tick(now){if(playing){t=Math.min(270,t+(now-last)/1000);if(t===270)playing=false;draw()}last=now;requestAnimationFrame(tick)}draw();requestAnimationFrame(tick);</script></html>'''
(OUT/'状态预演.html').write_text(page.replace('__DATA__',json.dumps(preview,ensure_ascii=False)),encoding='utf-8')
# Validate rendered intent from the source rather than writing unrelated timing descriptions.
def frame_at(time):
    s=D['scenes'][int(time)//10];return max((f for f in s['frames'] if f['at']<=time-s['start']),key=lambda f:f['at'])
expected={128:'A04_已发布尚未运行_v01.png',130:'A04_已发布尚未运行_v01.png',135:'A04_科研申报助手_v01.png',142:'A06_项目乙材料已确认_v01.png',153:'A07_独立任务来源_v02.png',169:'A07_独立检查报告_v02.png',170:'A07_提取发布确认_v01.png',172:'A07_提取应用已发布_v01.png',177:'A07_独立新运行结果_v01.png',197:'A08_v2发布尚未运行_v01.png',200:'A08_应用更新后结果_v01.png'}
for time,name in expected.items():assert frame_at(time)['asset']==name
assert frame_at(171)['overlay']['type']=='consent'
assert frame_at(132)['overlay']['type']=='busy'
assert len(rows)==270 and all(r['start_seconds']==i for i,r in enumerate(rows))
report=dict(status='STATIC_STATE_DERIVATION_PASS_BROWSER_PENDING',source_sha256=hashlib.sha256(SRC.read_bytes()).hexdigest(),seconds=270,states=sum(len(s['frames']) for s in D['scenes']),assets=len(used),expected_states=expected,scope='状态派生与素材引用；不等于业务实测或视频小样验收')
(OUT/'状态派生检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='expected_states'},ensure_ascii=True))
