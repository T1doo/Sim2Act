from pathlib import Path
import base64,hashlib,json,re,sys
root=Path(sys.argv[1]); raw=(root/'job.log').read_bytes(); text=raw.decode('utf-8-sig'); dest=root/'native'; dest.mkdir(exist_ok=True)
meta={}; chunks={}
for line in text.splitlines():
 m=re.search(r'SIM2ACT_COMPLETION_READBACK_UI_FILE (\{.*\})$',line)
 if m:
  v=json.loads(m[1]); assert v['name'] not in meta; assert Path(v['name']).name==v['name'];meta[v['name']]=v
 m=re.search(r'SIM2ACT_COMPLETION_READBACK_UI_CHUNK (\S+) (\d+) ([A-Za-z0-9+/=]+)$',line)
 if m:
  name,index=m[1],int(m[2]); rows=chunks.setdefault(name,{});assert index not in rows;rows[index]=m[3]
for name,v in meta.items():
 rows=chunks[name];assert set(rows)==set(range(v['chunks']));data=base64.b64decode(''.join(rows[i] for i in range(v['chunks'])),validate=True)
 assert len(data)==v['bytes'] and hashlib.sha256(data).hexdigest()==v['sha256'];(dest/name).write_bytes(data)
assert set(meta)==set(chunks)
(root/'decoded-originals.json').write_text(json.dumps({'job_log':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'files':meta},indent=2)+'\n')
print(json.dumps({'job_log_bytes':len(raw),'job_log_sha256':hashlib.sha256(raw).hexdigest(),'files':[(x,v['bytes']) for x,v in meta.items()]}))
