"""Build an allowlisted material delivery; never copy credentials or local registration."""
from pathlib import Path
import json, hashlib, shutil, zipfile, re, struct
ROOT=Path(__file__).resolve().parents[1]
SUB=ROOT/'submission'
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def js(p,obj):write(p,json.dumps(obj,ensure_ascii=False,indent=2))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
release='https://github.com/T1doo/Sim2Act/releases/tag/v0.1.0-dev.20261107.1'
download='https://github.com/T1doo/Sim2Act/releases/download/v0.1.0-dev.20261107.1/'
write(SUB/'README.md',f'''# Sim2Act · 参赛材料

当前版本：**产品书 v04 + 270 秒影片交接 v07**，2026-11-07。参赛方向为方向 3「开放赋能智能体」，主线为 **Sim 构想 → 2 转换 → Act 可用应用**。

- [16 页产品书 PDF](02_技术文档/Sim2Act_产品书_审阅版_v04.pdf) · [可编辑正文](02_技术文档/Sim2Act_产品书_v04.md)
- [影片制作总览](04_视频/制作交接_v07/制作总览.md) · [逐秒导演表](04_视频/制作交接_v07/逐秒导演表_v07.md) · [静帧与状态预演](04_视频/制作交接_v07/静帧与状态预演.html)
- [70 张 1080p 状态图](04_视频/制作交接_v07/状态图/) · [38 张影片参考图](04_视频/制作交接_v07/参考图/) · [架构与四项技术图](03_图片与截图/技术图_v02/)
- [审阅修订及验收范围](01_赛题与计划/审阅修订交付说明_20261107.md) · [18 项工单状态](01_赛题与计划/审阅工单状态.json)
- [脱敏工程证据](05_代码与模型/工程证据_21b33dc4_v02/) · [代码与模型复现说明](05_代码与模型/模型与复现说明.md)
- [Windows 开发版下载]({release}) · [完整材料 ZIP]({download}Sim2Act-Submission-Review-20261107-v07.zip)

制作时以 v07 为准。旧版本文本和原始参考图保留修改过程，不混用其字幕、镜头顺序和业务数字。影片 UI 是正式产品设计；真实工程证据有独立来源与验收范围。

下载整包后保留目录结构，打开 `submission/04_视频/制作交接_v07/静帧与状态预演.html`。若浏览器限制本地音频，可在解压根目录运行 `python -m http.server 8766 --bind 127.0.0.1`，从本机地址打开同一路径。该网页用于素材预演，不改变 Windows 产品运行方式。

最终 H3 小样、正式配音混音、成片网盘链接和赛事上传仍需完成。私有报名资料、密钥、数据库与临时工具不包含在公开交付中。
''')
write(SUB/'05_代码与模型/模型与复现说明.md',f'''# 代码、模型与限定范围复现

`Sim2Act-Source-21b33dc4.zip` 来自提交 `21b33dc4e8d6f0dfb74c65e9cf91cd5af31ed9ce` 的 Git 对象，包含 src、scripts、schemas、tests、依赖锁定文件及配置样例，与 Windows 开发预发布构建提交一致。无数据库、API 密钥或个人配置。

模型通过书生托管 API 调用。合同与账本中的服务别名为 `intern-s2`；未分发本地模型权重，也不把服务别名当作固定权重快照。使用者须配置自己的授权凭据。模型身份字段见 `模型身份摘录_v01.json`。

## 无模型调用的证据复核

解压后，用 Python 3.12 在材料根目录执行：

```powershell
python submission/05_代码与模型/工程证据_21b33dc4_v02/verify_evidence.py
python submission/01_赛题与计划/校验故事事实.py
python submission/01_赛题与计划/校验业务样例.py
```

第一项核对五次请求的 17,336 tokens、六处逐字引用、同实例与应用发布的两次结果、候选规格指纹及阶段耗时，并拒绝三类篡改。后两项只核对影片设计样例及状态顺序。三项仅依赖标准库，不启动数据库、模型或桌面窗口。

## Windows 体验

打开 [Release]({release})，下载 Windows x64 ZIP 与 SHA256SUMS.txt，完整解压到可写目录并双击包内 Sim2Act.exe，保留相邻 runtime 目录。包内附带运行时与 PostgreSQL 程序；模型凭据及正式配置仍须按项目桌面文档填写。不要覆盖已有工程和数据库。

本轮核对了公开下载、包清单、构建提交和哈希，没有重新验收原生窗口、真实模型全流程或 R0。冻结记录保留 INTERNAL_ENGINEERING_ONLY、语义 NOT_RUN、人工 PENDING。全新 Windows 环境由外部人员完成实际复现仍待验收。

技术 PDF 还需补入正式视频网盘链接。比赛外层 ZIP 命名由本地私有报名资料填写；公开工作包不是赛事提交完成证明。
''')
write(SUB/'01_赛题与计划/审阅修订交付说明_20261107.md','''# 审阅修订交付说明

交付基线：**产品书 v04、影片时间线与制作交接 v07、故事事实源 v03、工程证据 v02**。这是材料交付结论，真实运行及成片分别验收。

## 本轮修改

- 补齐 P-A 确认发布、已发布尚未运行、点击运行与独立成果；更新应用与再次运行分开呈现。
- P-B 改为独立一次性核查任务，经过提取检查、授权发布、新输入运行，形成自己的 PB-01 结果。
- 分开案例、实例、应用版本、规则版本及结果编号；甲 90,000 元、乙 76,000 元、更新规则后甲超出 10,000 元保持连续。
- 增加单位拒绝与转换后的字段链、新指南兼容门、资格条款原句及缺证明时的待确认状态。
- 分开 ARCH 架构与 T1–T4 四项机制，补充未知回执的查询对账，不承诺通用 exactly-once。
- 补齐可离线追算的五次请求账本、六处原文引用与同实例冷重开记录。17,336 tokens 有分项；耗时为接受到终态墙钟时间，不是纯模型延迟。
- 中文、数字、确认框与二维码固定图层合成。H3 负责场景及背景；27 段、270 秒导演表、字幕、预演统一派生。
- 能力库显示负责人、适用输入、权限与版本。科研、活动运营、实验复盘分别说明输入与结果含义。
- 产品书加入仓库、Windows 下载、固定源码与可扫码入口。影片 250–260 秒引出团队能力与下载，264–270 秒保持下载片尾供阅读扫码。

## 已执行检查

故事事实：3 条预算链、24 个事件、5 个错误变体拒绝。业务样例：单位、转换、权限 3 个错误变体拒绝。工程证据：5 次请求、6 处引用与 3 个篡改负例。以上不代表新增业务运行通过。

产品书 16 页渲染检查，v04 改动的第 12、16 页再次查看。70 张状态图全部重新导出为 1920×1080，等待图片解码及 SVG 图片加载后才截图，修正此前导出时的空白图。状态图无字幕，字幕及音轨独立交付。

浏览器预演检查桌面及 1280 宽度的材料添加、确认、结果、证据和片尾，无横向溢出。临时旁白音轨 270 秒，实际发声约 203 秒，最长单段约 9.30 秒；52 块字幕，每行最多 21 字，无时间交叠。正式配音仍需重新校时。

## 保留的外部验收

- P0-10：同源代码和下载入口已备好；全新 Windows、真实模型及完整产品验收未重跑。
- P1-03：相关工作与最小对照协议已补；实际对照实验未运行，不写提升百分比。
- P1-06：三个小样选为 S13–S14（发布至运行）、S17–S18（提取至独立结果）、S20–S21（更新至新结果），S12 另查资格证据可读性。实际 H3 输出待生成及逐帧检查。
- P2-02：连续配乐、单一声线与微动效要求已写；正式配音、音乐、混音、视频和网盘链接待制作。

最终上传需要补入成片链接，按本地报名信息命名组包。不能将工作包或截图核对作为赛事已提交或完整 R0 通过。
''')
tickets=json.loads((SUB/'01_赛题与计划/审阅工单状态.json').read_text(encoding='utf-8'))
ev={
'P0-01':'故事事实源_v03.json；故事事实校验_v03.json；状态图索引_v07.json',
'P0-02':'影片状态时间线_v07.json：S13–S15、S20–S21；派生一致性检查.json',
'P0-03':'S16–S18：独立来源、检查、授权发布、PB-01',
'P0-04':'业务样例规范_v02.json；业务样例校验_v02.json；S06–S08',
'P0-05':'规则兼容门；S19 新指南提示；T2-01、T3-01',
'P0-06':'工程证据_21b33dc4_v02/verify_evidence.py；独立核对结果.json',
'P0-07':'技术图_v02/图号映射.json；ARCH-01、T1-01至T4-01',
'P0-08':'制作交接_v07/状态图；story_viewer.html；实际H3输出待验',
'P0-09':'52块字幕；旁白校时_v07.json；270秒逐秒表；正式配音待校时',
'P0-10':'模型与复现说明.md；同源代码ZIP；Release清单；公开链接检查',
'P1-01':'前30秒目标/应用/价值；27段导演表及旁白',
'P1-02':'申报指南_v1/v2.pdf；来源定位核对.json；资格条款图v04',
'P1-03':'相关工作核对_v02.md；产品书第14页；未运行实际对照',
'P1-04':'S22–S23原像素局部与逐字放大引文；720宽度阅读复核',
'P1-05':'正式设计采用统一浅蓝淡紫母版；操作/状态语义修订',
'P1-06':'S13–S14、S17–S18、S20–S21小样选择；尚无H3输出',
'P2-01':'团队能力库v02及交付版；S26；负责人/权限/版本',
'P2-02':'配音配乐与字幕规范；微动效时间线；待正式成片'}
for t in tickets:
    t['status']='materials_ready_external_acceptance_pending' if t['id'] in ['P0-08','P0-09','P0-10','P1-03','P1-06','P2-02'] else 'material_revision_verified'
    t['evidence']=ev[t['id']];t['scope']='参赛材料；不扩签实际产品或成片验收'
js(SUB/'01_赛题与计划/审阅工单状态.json',tickets)
record=SUB/'01_赛题与计划/外部审阅/修订执行与问题确认_20261107.md'
old=record.read_text(encoding='utf-8')
if not old.startswith('> 最终修订入口'):
    write(record,'> 最终修订入口：[交付说明](../审阅修订交付说明_20261107.md)；下文为接收审阅时的历史记录。\n\n'+old)
story=json.loads((SUB/'04_视频/脚本与提示词/影片状态时间线_v07.json').read_text(encoding='utf-8'))
frames=[]
for s in story['scenes']:
    for i,f in enumerate(s['frames'],1):
        p=SUB/f'04_视频/制作交接_v07/状态图/{s["id"]}_{i:02d}.png'
        dim=struct.unpack('>II',p.read_bytes()[16:24]);assert dim==(1920,1080)
        frames.append(dict(file=p.name,scene=s['id'],at=s['start']+f['at'],capture_at=s['start']+f['at']+.1,state=f['state'],source=f['asset'],sha256=sha(p),dimensions=dim))
js(SUB/'04_视频/制作交接_v07/状态图索引_v07.json',dict(count=len(frames),source_sha256=sha(SUB/'04_视频/脚本与提示词/影片状态时间线_v07.json'),method='Wait for HTML img.decode and SVG images, then two animation frames; fixed stage screenshot without subtitles',frames=frames))
qa=SUB/'02_技术文档/产品书排版检查_v04.json';r=json.loads(qa.read_text(encoding='utf-8'));r['visual_review']='Reviewed all 16 pages across v03; v04 changed pages 12 and 16 re-rendered and inspected after corrections';js(qa,r)

# Public repository material selection: latest compiled outputs plus editable history.
chosen={SUB/'README.md',Path(__file__).resolve()}
for name in ['01_赛题与计划','03_图片与截图','05_代码与模型','04_视频/生成图片','04_视频/脚本与提示词','04_视频/制作工具','04_视频/制作交接_v07']:
    for p in (SUB/name).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and not re.match(r'page-\d+\.png',p.name):chosen.add(p)
for p in (SUB/'02_技术文档').rglob('*'):
    if p.is_file() and not any('预览' in x for x in p.parts) and (p.suffix in ['.md','.json','.py'] or p.name=='Sim2Act_产品书_审阅版_v04.pdf'):chosen.add(p)
chosen={p for p in chosen if p.suffix.lower() not in ['.pyc']}
text_ext={'.md','.txt','.json','.csv','.py','.ps1','.js','.html','.srt','.yaml','.yml'}
leaks=[]
for p in chosen:
    assert '00_报名信息_本地' not in p.parts
    if p.suffix in text_ext:
        t=p.read_text(encoding='utf-8-sig')
        if re.search(r'\bsk-[A-Za-z0-9]{24,}\b|\b(?:ghp|gho)_[A-Za-z0-9]{25,}\b|\b1[3-9]\d{9}\b|postgres(?:ql)?://[^\s]+:[^\s]+@',t):leaks.append(str(p.relative_to(ROOT)))
assert not leaks,leaks
assert all(p.stat().st_size<95*1024**2 for p in chosen)
manifest=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(chosen)]
mp=SUB/'公开交付清单_v07.json';js(mp,dict(files=len(manifest),scope='Allowlisted public artifacts; no local registration, API keys or database',items=manifest));chosen.add(mp)
out=SUB/'Sim2Act-Submission-Review-20261107-v07.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(chosen):z.write(p,p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(out) as z:assert z.testzip() is None
write(SUB/'SHA256SUMS-v07.txt',sha(out)+'  '+out.name+'\n'+sha(SUB/'02_技术文档/Sim2Act_产品书_审阅版_v04.pdf')+'  Sim2Act_产品书_审阅版_v04.pdf\n')
# Copies public files only; git operations are a separate explicit step.
target=ROOT/'.local/publish-main'
assert (target/'.git').exists()
for p in chosen|{SUB/'SHA256SUMS-v07.txt'}:
    dest=target/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
print(json.dumps(dict(files=len(chosen),zip_bytes=out.stat().st_size,zip_sha256=sha(out),source_zip_bytes=(SUB/'05_代码与模型/Sim2Act-Source-21b33dc4.zip').stat().st_size,frames=len(frames)),ensure_ascii=True))
