import json,subprocess
from pathlib import Path
p=Path('/workspace/ordinary-owner-final-delivery-verification.json');v=json.loads(p.read_text());refs=v['protected_nineteen_refs'];refs[v['branch']]=v['delivery'];g=['git','-c','core.fsmonitor=false'];sha=subprocess.check_output(g+['rev-parse','HEAD'],text=True).strip();assert sha==v['delivery'];assert not subprocess.check_output(g+['status','--porcelain'])
a=subprocess.check_output(g+['ls-remote','origin',*[f'refs/heads/{b}' for b in refs]],text=True);a={l.split()[1].removeprefix('refs/heads/'):l.split()[0] for l in a.splitlines()};assert a==refs
Path('/workspace/ordinary-goal-md-evidence-20261017/preflight.json').write_text(json.dumps(dict(base=sha,branch='dev/ordinary-goal-md-delivery-20261017',protected_twenty_refs=refs,actual_remote=a,clean=True,default_Git_network=True,sole_writer=True,capacity=subprocess.check_output(['df','-h','/workspace','/tmp'],text=True)),indent=2)+'\n')
