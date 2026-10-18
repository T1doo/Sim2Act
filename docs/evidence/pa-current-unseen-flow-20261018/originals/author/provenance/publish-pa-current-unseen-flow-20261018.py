import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

repo=Path('/workspace/Sim2Act')
branch='dev/pa-unseen-input-current-page-20261018'
stage=sys.argv[1]
out=Path('/workspace/pa-current-unseen-flow-evidence-20261018' if stage=='source' else '/workspace/pa-current-unseen-flow-final-delivery-20261018')
out.mkdir(exist_ok=True)
records=[]
def call(name,args):
    cmd=['git','-c','core.fsmonitor=false',*args]
    started=datetime.datetime.now(datetime.UTC).isoformat()
    try:
        r=subprocess.run(cmd,cwd=repo,capture_output=True,text=True,timeout=180,env={**os.environ,'GIT_TERMINAL_PROMPT':'0'})
        result=dict(command=cmd,started_utc=started,ended_utc=datetime.datetime.now(datetime.UTC).isoformat(),exit_code=r.returncode)
        (out/(stage+'-'+name+'.stdout')).write_text(r.stdout)
        (out/(stage+'-'+name+'.stderr')).write_text(r.stderr)
        result.update(stdout=stage+'-'+name+'.stdout',stderr=stage+'-'+name+'.stderr')
        records.append(result)
        (out/(stage+'-publish-commands.json')).write_text(json.dumps(records,indent=2)+'\n')
        assert r.returncode==0,(name,r.stderr)
        return r.stdout
    except subprocess.TimeoutExpired:
        records.append(dict(command=cmd,started_utc=started,outcome='UNCERTAIN_TIMEOUT_CHECK_REMOTE_BEFORE_ANY_RETRY'))
        (out/(stage+'-publish-commands.json')).write_text(json.dumps(records,indent=2)+'\n')
        raise
assert call('branch',['branch','--show-current']).strip()==branch
mapping=f'refs/heads/{branch}:refs/remotes/origin/{branch}'
fetch=call('fetch-map-before',['config','--get-all','remote.origin.fetch'])
if mapping not in fetch.splitlines():
    call('fetch-map-add',['config','--add','remote.origin.fetch',mapping])
call('fetch-map-after',['config','--get-all','remote.origin.fetch'])
head=call('head',['rev-parse','HEAD']).strip()
call('push',['push','-u','origin',f'HEAD:refs/heads/{branch}'])
call('own-fetch',['fetch','origin',mapping])
remote=call('remote-refs',['ls-remote','--refs','origin'])
assert head+'\trefs/heads/'+branch in remote.splitlines()
assert call('left-right',['rev-list','--left-right','--count','HEAD...origin/'+branch]).split()==['0','0']
assert not call('status',['status','--porcelain=v1','--untracked-files=all'])
print(json.dumps(dict(stage=stage,head=head,remote_sha=head,ordinary_nonforce_push=True,local_remote_left_right=[0,0])))
