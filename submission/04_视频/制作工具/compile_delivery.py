"""Generate all video handoff derivatives from the same explicit scene-state source."""
from pathlib import Path
import json,csv,html,hashlib,shutil,wave,struct,re,argparse
ROOT=Path(__file__).resolve().parents[3];BASE=ROOT/'submission/04_视频'
ap=argparse.ArgumentParser();ap.add_argument('--source',default='影片状态时间线_v07.json');ap.add_argument('--voice-dir',default=str(ROOT/'.local/voice-v07'));ap.add_argument('--output',default='制作交接_v07');args=ap.parse_args()
SRC=BASE/'脚本与提示词'/args.source;D=json.loads(SRC.read_text(encoding='utf-8'));OUT=BASE/args.output;OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_sha=sha(SRC);voice_dir=Path(args.voice_dir);vrec=json.loads((voice_dir/'voice-source.json').read_text(encoding='utf-8-sig'))
assert [(s['id'],s['narration']) for s in D['scenes']]==[(s['id'],s['narration']) for s in vrec['scenes']]
facts=(SRC.parent/D['facts_file']).resolve();assert sha(facts)==D['facts_sha256']
def origin(name):
    folder='submission/03_图片与截图/技术图_v02' if name.startswith(('ARCH-','T1-','T2-','T3-','T4-')) else ('submission/03_图片与截图/实际运行' if name.startswith('E_') else 'submission/04_视频/生成图片')
    return ROOT/folder/name
used={f['asset'] for s in D['scenes'] for f in s['frames']}
used.update(x['asset'] for s in D['scenes'] for f in s['frames'] for x in f.get('compare',[]))
assets=OUT/'参考图';assets.mkdir(exist_ok=True);D['asset_dimensions']={};inventory=[]
for name in sorted(used):
    p=origin(name);assert p.is_file(),name;b=p.read_bytes();dim=list(struct.unpack('>II',b[16:24]));D['asset_dimensions'][name]=dim
    shutil.copy2(p,assets/name);inventory.append(dict(file=name,sha256=sha(p),dimensions=dim,kind='engineering_original' if name.startswith('E_') else 'technical_diagram' if name.startswith(('ARCH-','T1-','T2-','T3-','T4-')) else 'formal_design'))
def tc(sec):
    ms=round(sec*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'
def wrap(line):
    if len(line)<=22:return [line]
    pairs=[]
    for k in range(1,len(line)):
        a,b=line[:k],line[k:]
        if max(len(a),len(b))>22 or b[0] in '，。！？；：、）》」』】,.!?;:' or a[-1] in '（《「『【':continue
        if re.match(r'[A-Za-z0-9_]',a[-1]) and re.match(r'[A-Za-z0-9_]',b[0]):continue
        broken_word=a[-1]+b[0] in {'整理','生成','应用','版本','回读','输入','结果','核查','确认','声明','材料','权限','规则','团队','保存','通过','运行'}
        pairs.append((abs(len(a)-len(b))-(30 if a[-1] in '，。！？；：、' and len(a)>=7 else 0)+(20 if broken_word else 0),a,b))
    assert pairs,line
    _,a,b=min(pairs);return [a,b]
subtitles=[];audio_parts=[];timings=[];rows=[];manifest=[]
director=['# 270秒逐秒导演表 v07','','所有图片、状态、动作、旁白和字幕由同一时间线派生。视频实际生成及正式配音仍待验收。',''];voice=['# 旁白稿 v07','','一条连续声线，按全片节奏录制；临时音频只用于校时。',''];screen=['# 屏幕文案与字幕安全带','','主界面文字来自固定图层，不要求H3改写。字幕安全带独立占底部10.5%，画面等比缩放，保持底栏可见。',''];upload=['# H3与后期制作总览','','总片270秒、27个十秒制作单元。人物空间用I2VA；其余精确UI采用固定图层、确定性指针/遮罩/切页，H3仅提供可复用环境底片。无须为每个UI镜头单独抽取一次背景视频。','']
for index,s in enumerate(D['scenes']):
    assert s['start']==index*10 and s['duration']==10 and s['frames'][0]['at']==0
    assert [f['at'] for f in s['frames']]==sorted(f['at'] for f in s['frames'])
    assert all(0<=f['at']<10 for f in s['frames']) and all(0<=c['at']<10 for c in s['clicks'])
    with wave.open(str(voice_dir/(s['id']+'.wav')),'rb') as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,16000)
        samples=w.readframes(w.getnframes());length=w.getnframes()/16000
    assert length<=9.6,(s['id'],length)
    audio_parts.append(b'\0'*(3200*2)+samples+b'\0'*((160000-3200-len(samples)//2)*2))
    timings.append(dict(scene=s['id'],start=s['start']+.2,end=round(s['start']+.2+length,4),speech_seconds=round(length,4)))
    text=s['narration'];positions=[m.end() for m in re.finditer('[，。？；：]',text) if 7<m.end()<len(text)-7]
    parts=[text] if len(text)<=24 else [text[:(cut:=min(positions,key=lambda x:abs(x-len(text)/2)) if positions else len(text)//2)],text[cut:]]
    elapsed=0
    for part in parts:
        duration=length*len(part)/len(text);start=s['start']+.2+elapsed;end=start+duration;elapsed+=duration
        subtitles.append(dict(scene=s['id'],start=start,end=end,text=part,lines=wrap(part),alignment='temporary_phrase_proportion'))
    folder=OUT/s['id'];folder.mkdir(exist_ok=True)
    if s['id']=='S01':
        prompt=(BASE/'脚本与提示词/H3_v02/S01_v02.txt').read_text(encoding='utf-8');mode='I2VA';refs=[dict(label='Picture 1',asset=s['frames'][0]['asset'],role='first_frame')]
    else:
        dark=s['id'] in ['S03','S27'];background='deep midnight indigo with restrained cyan and lavender light along the lower outer edge' if dark else 'near-white cool blue, with a faint lavender sheen at the outer edges'
        prompt=f'''integrated_multimodal_description: [Shot 1] An abstract 16:9 background plate, {background}. The central ninety percent remains clean and steady. During 0–3 seconds a soft edge light drifts slowly; during 3–7 seconds the motion gently continues; during 7–10 seconds it settles. Static camera, constant exposure, no foreground objects. No interface, text, number, button, cursor, logo or QR pattern. Exact UI, business states, brand, URL, QR and subtitles are added as fixed editorial layers. The clip lasts 10 seconds.

overall_soundscape: An unobtrusive continuous air tone without voices, speech, clicks or success alarms. Action sounds and continuous narration are added during editing.

non_diegetic_music: N/A
''';mode='T2VA_BACKGROUND_ONLY';refs=[]
    pf=f'{s["id"]}_H3_v07.txt';(folder/pf).write_text(prompt,encoding='utf-8')
    fields=['integrated_multimodal_description:','overall_soundscape:','non_diegetic_music:'];assert all(prompt.count(k)==1 for k in fields)
    note=[f'# {s["id"]} · {s["start"]}–{s["start"]+10}秒','',f'模式：{mode}。提示词：[{pf}]({pf})。','']
    if refs:note+=['上传Picture 1作为首帧：'+refs[0]['asset'],'']
    else:note+=['不向H3提交业务界面重新生成文字。背景片可复用，本段主要工作是按照下表剪辑固定图层。','']
    note+=['| 局部秒数 | 固定画面 | 状态与后期处理 |','| --- | --- | --- |']
    for f in s['frames']:
        effect=json.dumps({k:f[k] for k in ['overlay','evidence','compare','note'] if f.get(k)},ensure_ascii=False)
        note.append(f'| {f["at"]} | [{f["asset"]}](../参考图/{f["asset"]}) | {f["state"]} |')
        if effect!='{}':note+=['',f'该状态的确定性图层参数：`{effect}`','']
    note+=['','点击：'+('；'.join(f'{c["at"]}秒 {c["label"]} @({c["x"]},{c["y"]})' for c in s['clicks']) or '无点击'),'','旁白：'+s['narration'],'','衔接：'+s['transition'],'','工程截图只裁切原像素；正式设计结果不计入实测。']
    (folder/'制作说明.md').write_text('\n'.join(note),encoding='utf-8')
    manifest.append(dict(scene=s['id'],start=s['start'],duration=10,mode=mode,references=refs,edit_frames=s['frames'],clicks=s['clicks'],prompt=s['id']+'/'+pf,narration=s['narration']))
    upload+=[f'- [{s["id"]} · {s["start"]}–{s["start"]+10}秒]({s["id"]}/制作说明.md)：{mode}']
    voice += [f'## {s["id"]} · {s["start"]}–{s["start"]+10}秒','',s['narration'],'']
    screen += [f'## {s["id"]}','',s['screen_text'],'']
    director += [f'## {s["id"]}','','| 全片秒数 | 状态起点 | 秒内变化与动作 |','| --- | --- | --- |']
    for j in range(10):
        f=max((f for f in s['frames'] if f['at']<=j),key=lambda x:x['at'])
        changes=[f'{x["at"]}秒 {x["state"]}' for x in s['frames'] if j<x['at']<j+1]
        actions=[f'{c["at"]}秒 {c["label"]}' for c in s['clicks'] if j<=c['at']<j+1]
        row=dict(scene=s['id'],start_seconds=s['start']+j,end_seconds=s['start']+j+1,local_start=j,local_end=j+1,asset=f['asset'],state=f['state'],within_second='；'.join(changes+actions) or '保持阅读',context=f.get('context',s['context']),camera=s['camera'],transition=s['transition'] if j==9 else '保持本镜',narration=s['narration'] if j==0 else '',visible_text=s['screen_text'],sound='轻点击与可见动作同步' if actions else '连续环境声，旁白优先',music='连续主轨；阅读段落降低配器，267秒起收束')
        rows.append(row);director.append(f'| {row["start_seconds"]}–{row["end_seconds"]} | {row["state"]} | {row["within_second"]} |')
    director+=['',s['transition'],'']
assert len(rows)==270 and all(x['start_seconds']==i for i,x in enumerate(rows))
assert all(subtitles[i]['end']<=subtitles[i+1]['start']+.001 for i in range(len(subtitles)-1))
with wave.open(str(OUT/'预演旁白_270秒.wav'),'wb') as w:w.setparams((1,2,16000,0,'NONE','not compressed'));w.writeframes(b''.join(audio_parts))
srt=[]
for i,x in enumerate(subtitles,1):srt.extend([str(i),tc(x['start'])+' --> '+tc(x['end']),'\n'.join(x['lines']),''])
(OUT/'字幕时间草案_v07.srt').write_text('\n'.join(srt),encoding='utf-8-sig')
for name,obj in [('字幕文案_v07.json',subtitles),('旁白校时_v07.json',timings),('镜头上传清单_v07.json',manifest),('素材清单_v07.json',inventory),('影片状态时间线_v07.json',D)]:
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
for name,content in [('逐秒导演表_v07.md',director),('旁白稿_v07.md',voice),('屏幕文案_v07.md',screen),('制作总览.md',upload)]: (OUT/name).write_text('\n'.join(content),encoding='utf-8')
with (OUT/'逐秒导演表_v07.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
template=(Path(__file__).parent/'story_viewer.html').read_text(encoding='utf-8')
(OUT/'静帧与状态预演.html').write_text(template.replace('__DATA__',json.dumps(D,ensure_ascii=False)).replace('__SUBS__',json.dumps(subtitles,ensure_ascii=False)),encoding='utf-8')
shutil.copy2(facts,OUT/facts.name)
shutil.copy2(BASE/'脚本与提示词/配音配乐与字幕规范_v01.md',OUT/'配音配乐与字幕规范.md')
report=dict(status='DERIVED_FROM_ONE_SOURCE_NOT_H3_VERIFIED',source_sha256=source_sha,voice_source_sha256=vrec['source_sha256'],scenes=27,seconds=270,frames=sum(len(s['frames']) for s in D['scenes']),assets=len(used),subtitles=len(subtitles),max_line_characters=max(len(line) for x in subtitles for line in x['lines']),speech_seconds=round(sum(x['speech_seconds'] for x in timings),3),max_speech_seconds=max(x['speech_seconds'] for x in timings),html_source_embedded=True,actual_video_generated=False)
report['voice_texts_match']=True
report['voice_source_note']='27段旁白逐字一致；语音录制后的视觉状态修订使整份时间线哈希不同，未改变语音文本。'
(OUT/'派生一致性检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
