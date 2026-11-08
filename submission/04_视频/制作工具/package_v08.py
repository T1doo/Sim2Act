from pathlib import Path
import json,hashlib,zipfile,shutil,re,subprocess
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'submission/04_视频/制作交接_v08'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copytree(ROOT/'submission/03_图片与截图/业务样例',OUT/'business_samples',dirs_exist_ok=True)
# Keep editable build sources outside the execution directory's active manifest.
excluded={'时间线_修订工作稿.json','SHA256SUMS.txt'}
files=[p for p in OUT.rglob('*') if p.is_file() and p.name not in excluded and '__pycache__' not in p.parts]
for p in files:
 if p.suffix in {'.md','.txt','.json','.py','.html','.csv','.srt'}:
  t=p.read_text(encoding='utf-8-sig')
  assert not re.search(r'\bsk-[A-Za-z0-9]{24,}\b|\b(?:ghp|gho)_[A-Za-z0-9]{25,}\b|\b1[3-9]\d{9}\b',t),p
sumfile=OUT/'SHA256SUMS.txt';sumfile.write_text(''.join(sha(p)+'  '+p.relative_to(OUT).as_posix()+'\n' for p in sorted(files)),encoding='utf-8');files.append(sumfile)
zpath=ROOT/'submission/Sim2Act-Video-Handoff-v08-20261108.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,'Sim2Act-v08/'+p.relative_to(OUT).as_posix())
with zipfile.ZipFile(zpath) as z:assert z.testzip() is None
report={'zip':zpath.name,'sha256':sha(zpath),'bytes':zpath.stat().st_size,'members':len(files),'entry':'Sim2Act-v08/START_HERE_服务器接手.md','status':'LOCAL_PACKAGE_VALIDATED_PUBLICATION_PENDING'}
(ROOT/'submission/Video-Handoff-v08-download.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
target=ROOT/'.local/publish-main/submission/04_视频/制作交接_v08'
for p in files:
 q=target/p.relative_to(OUT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
other=['submission/04_视频/制作工具/build_v08.py','submission/04_视频/制作工具/package_v08.py','submission/04_视频/脚本与提示词/影片状态时间线_v08_working.json','submission/02_技术文档/Sim2Act_产品书_审阅版_v05.pdf','submission/02_技术文档/Sim2Act_产品书_v05.md','submission/02_技术文档/产品书内容结构_v05.json','submission/02_技术文档/排版源/render_product_book_v05.py','submission/01_赛题与计划/外部审阅/Sim2Act_给WindowsCodex_完整审阅回执与视频交接要求_v08.md','submission/Video-Handoff-v08-download.json']
for rel in other:
 q=ROOT/'.local/publish-main'/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,q)
print(json.dumps(report,ensure_ascii=True))
