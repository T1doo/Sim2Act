import json,hashlib,subprocess
from pathlib import Path
repo=Path('/workspace/Sim2Act');root=Path('/tmp/sim2act-csv-data-free-logic-20261010');out=repo/'docs/evidence/csv-data-free-logic-reuse-20261010'
f=json.loads((root/'source-freeze-fixed.json').read_text());w=json.loads((out/'COPY_WHITELIST.json').read_text())
def verify(index=False):
    for item in f['files']:
        b=(repo/item['path']).read_bytes();assert len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256'],item['path']
    items=[dict(path='docs/evidence/csv-data-free-logic-reuse-20261010/'+i['path'],bytes=i['bytes'],sha256=i['sha256']) for i in w['files']]
    items+=f['files']
    if index:
        p=subprocess.Popen(['git','cat-file','--batch'],cwd=repo,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        for item in items:
            p.stdin.write((':'+item['path']+'\n').encode());p.stdin.flush()
            header=p.stdout.readline().decode().strip().split();assert len(header)==3 and header[1]=='blob',header
            size=int(header[2]);b=p.stdout.read(size);assert p.stdout.read(1)==b'\n'
            assert size==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256'],item['path']
        p.stdin.close();assert p.wait()==0
    else:
        for item in items:
            b=(repo/item['path']).read_bytes();assert len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256'],item['path']
    return len(items)
count=verify(index=True)
changed=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=repo).decode().split('\0');assert all(not x or x.startswith('docs/') for x in changed)
assert hashlib.sha256((repo/'docs/F2/CsvDataFreeLogicSafety20261010.md').read_bytes()).hexdigest()=='014dc78e6e29772ce4d37400c0150ed52f7c37adcf8aafc843b3bec768acacd8'
(root/'staged-byte-verification.json').write_text(json.dumps(dict(source_sha=f['source_sha'],non_docs=378,products=72,evidence_objects=w['count'],indexed_objects_verified=count,all_exact=True,docs_only=True,LIVE=0),indent=2)+'\n')
print('indexed source/evidence exact; docs-only')
