from pathlib import Path
import hashlib,json,subprocess
root=Path('/tmp/sim2act-dag-reuse-20261010')
base=json.loads(Path('/tmp/sim2act-resource-file-20261010/source-freeze.json').read_text())['files']
paths=set(base)|{p for p in subprocess.check_output(['git','ls-files','src','tests'],text=True).splitlines()}
sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
files={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sorted(paths)}
assert all(hashlib.sha256(subprocess.check_output(['git','show',sha+':'+p])).hexdigest()==h for p,h in files.items())
(root/'source-freeze.json').write_text(json.dumps({'source_sha':sha,'base_dev':'67c6ccc8ad7d6f132205c2ac4f33b10defca5da7','files':files},indent=2)+'\n')
print(sha,len(files))
