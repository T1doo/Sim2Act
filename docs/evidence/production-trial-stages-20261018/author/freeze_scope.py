import json
import subprocess
from pathlib import Path

repo=Path('/workspace/Sim2Act');out=Path('/workspace/production-trial-stages-20261018')
def git(*args):
    return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=repo)
base='4bb3c26f5f67511795771c9187537aee4e852590'
head=git('rev-parse','HEAD').decode().strip()
changed=git('diff','--name-only',base,head).decode().splitlines()
tracked=git('ls-tree','-r','--name-only',base).decode().splitlines()
prod=[p for p in tracked if p.startswith('src/')]
inputs=[p for p in tracked if p.startswith(('src/','tests/')) or p in ('pyproject.toml','uv.lock')]
record=dict(baseline=base,source_freeze=head,changed=changed,
    baseline_production_count=len(prod),production_changed=[p for p in prod if p in changed],
    unchanged_production_count=len([p for p in prod if p not in changed]),
    baseline_input_count=len(inputs),new_inputs=[p for p in changed if p not in tracked],
    base_is_ancestor=subprocess.run(['git','-c','core.fsmonitor=false','merge-base','--is-ancestor',base,head],cwd=repo).returncode==0,
    worktree_clean=git('status','--porcelain')==b'',
    changed_blobs={p:git('rev-parse',head+':'+p).decode().strip() for p in changed})
(out/'final-freeze-scope.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
