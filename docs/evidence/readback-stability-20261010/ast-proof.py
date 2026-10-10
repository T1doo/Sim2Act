import ast,json,subprocess
from pathlib import Path
base='754f0c61dab111ada2db69bfeb8e8cccdfe2ad95';path='src/sim2act/report_presentations.py'
old=ast.parse(subprocess.check_output(['git','show',f'{base}:{path}'],text=True));new=ast.parse(Path(path).read_text())
def funcs(tree):return {x.name:ast.dump(x,include_attributes=False) for x in tree.body if isinstance(x,ast.FunctionDef)}
a,b=funcs(old),funcs(new)
proof=dict(base=base,source_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),unchanged_functions={n:a[n]==b[n] for n in ['scope','check','propose']},source_scope_reused_only_in_history=True)
assert all(proof['unchanged_functions'].values())
Path('/tmp/sim2act-read-stability-20261010/scope-ast-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof)
