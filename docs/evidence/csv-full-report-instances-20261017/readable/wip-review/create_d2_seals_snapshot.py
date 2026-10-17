import datetime, hashlib, json, os, pathlib, subprocess
repo=pathlib.Path('/workspace/Sim2Act')
sha='d2bacd5ccab8ac848956aa637771848ca58404a5'
out=pathlib.Path('/tmp/f2-csv-full-report-d2bacd5c-seals-independent')
out.mkdir()
snapshot=out/'snapshot'
snapshot.mkdir()
freeze_path=pathlib.Path('/workspace/csv-full-report-instances-evidence-20261017/code-freeze.json')
freeze_raw=freeze_path.read_bytes()
freeze=json.loads(freeze_raw)
assert freeze['head']==sha
(out/'root-code-freeze.json').write_bytes(freeze_raw)
paths=set(freeze['files'])
extra=['schemas','docs/evidence/bounded-agent-offline-20261006','docs/evidence/protocol-store-loop-20261006/evaluation','docs/evidence/model-protocol-preparation-20261006/materials']
for prefix in extra:
 names=subprocess.check_output(['git','ls-tree','-r','--name-only',sha,'--',prefix],cwd=repo,text=True).splitlines()
 paths.update(names)
proof={}
for name in sorted(paths):
 assert not name.startswith('/') and '..' not in pathlib.PurePosixPath(name).parts
 raw=subprocess.check_output(['git','show',sha+':'+name],cwd=repo)
 info=subprocess.check_output(['git','ls-tree',sha,'--',name],cwd=repo,text=True).split()
 assert info[0] in ('100644','100755') and info[1]=='blob'
 git_blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 assert git_blob==info[2]
 digest=hashlib.sha256(raw).hexdigest()
 if name in freeze['files']:
  assert digest==freeze['files'][name],name
 p=snapshot/name
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_bytes(raw)
 p.chmod(0o444)
 proof[name]={'sha256':digest,'git_blob':git_blob,'bytes':len(raw),'frozen_input':name in freeze['files']}
for folder in sorted((p for p in snapshot.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
 folder.chmod(0o555)
snapshot.chmod(0o555)
meta={'sha':sha,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'root':str(snapshot),'source':'git show exact commit; no working-copy bytes copied','frozen_input_count':len(freeze['files']),'all_input_count':len(proof),'root_freeze_sha256':hashlib.sha256(freeze_raw).hexdigest(),'files':proof}
(out/'inputs-before.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps({k:v for k,v in meta.items() if k!='files'}))
