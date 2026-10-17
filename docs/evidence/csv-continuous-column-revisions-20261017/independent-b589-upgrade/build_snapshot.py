import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile

base=Path('/tmp/csv-upgrade-independent-b5898093-20261017')
repo=Path('/workspace/Sim2Act')
sha='b589809375c89b4d93617d91c780a1e0f7f704e2'
prefixes=['src','tests','schemas','pyproject.toml','docs/evidence/bounded-agent-offline-20261006','docs/evidence/protocol-store-loop-20261006/evaluation','docs/evidence/model-protocol-preparation-20261006/materials']
snapshot=base/'snapshot'
snapshot.mkdir()
archive_command=['git','archive','--format=tar',sha,*prefixes]
archive=subprocess.check_output(archive_command,cwd=repo)
with tarfile.open(fileobj=io.BytesIO(archive),mode='r:') as bundle:
    bundle.extractall(snapshot,filter='data')
listing=subprocess.check_output(['git','ls-tree','-rz',sha,'--',*prefixes],cwd=repo)
entries=[]
for entry in listing.split(b'\0'):
    if not entry:
        continue
    info,name=entry.split(b'\t',1)
    mode,kind,blob=info.decode().split()
    path=name.decode()
    assert kind=='blob' and mode in ('100644','100755'),(path,mode,kind)
    content=(snapshot/path).read_bytes()
    actual=subprocess.check_output(['git','hash-object','--stdin'],input=content,cwd=repo).decode().strip()
    assert actual==blob,(path,actual,blob)
    entries.append(dict(path=path,git_blob=blob,sha256=hashlib.sha256(content).hexdigest(),size=len(content),mode=mode))
assert len(entries)==len([p for p in snapshot.rglob('*') if p.is_file()])
for prefix,expected in [(prefixes[4],32),(prefixes[5],5),(prefixes[6],14)]:
    actual=sum(entry['path'].startswith(prefix+'/') for entry in entries)
    assert actual==expected,(prefix,actual,expected)
(snapshot/'scripts/engineering-ci').mkdir(parents=True)
(snapshot/'scripts/engineering-ci/node_modules').symlink_to('/workspace/Sim2Act/scripts/engineering-ci/node_modules',target_is_directory=True)
for entry in entries:
    (snapshot/entry['path']).chmod(0o555 if entry['mode']=='100755' else 0o444)
for directory in [p for p in snapshot.rglob('*') if p.is_dir() and not p.is_symlink()]:
    directory.chmod(0o555)
snapshot.chmod(0o555)
manifest=dict(sha=sha,parent=subprocess.check_output(['git','rev-parse',sha+'^'],cwd=repo).decode().strip(),archive_command=archive_command,entries=entries,git_blob_checks=len(entries),mismatches=[],extra_runtime_symlinks=[dict(path='scripts/engineering-ci/node_modules',target='/workspace/Sim2Act/scripts/engineering-ci/node_modules')])
(base/'inputs-before.json').write_text(json.dumps(manifest,indent=2)+'\n')
(base/'commands.txt').write_text('Snapshot command: '+repr(archive_command)+'\nGit byte check: git hash-object --stdin for each exported Git blob\nPython: /workspace/sim2act-venv/bin/python\nNODE_PATH: /workspace/Sim2Act/scripts/engineering-ci/node_modules\n')
print(json.dumps(dict(sha=sha,snapshot=str(snapshot),git_blob_checks=len(entries),input_bytes=sum(x['size'] for x in entries),asset_counts={'bounded':32,'evaluation':5,'materials':14})))
