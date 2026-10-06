"""Observation-only wrapper around the unchanged real launcher, synthetic test usage.

No injected failure, new wait, permission changes or child environment flags. Raw
configuration, command arguments, tokens and DB URLs are never recorded.
"""
import json
import os
import runpy
import sys
import time
from pathlib import Path

import psutil

root = Path(__file__).resolve().parents[3]
module = runpy.run_path(str(root / 'scripts/manage.py'))
globals_ = module['main'].__globals__
original_process = globals_['process']
original_popen = globals_['subprocess'].Popen
observations = []
children = {}
started = time.monotonic()


def event(event_name, **values):
    observations.append({'event':event_name,'seconds':round(time.monotonic()-started,6),**values})


def btime():
    if sys.platform != 'linux':
        return None
    return next(line.split()[1] for line in Path('/proc/stat').read_text().splitlines() if line.startswith('btime '))


def launch(*args,**kwargs):
    child = original_popen(*args,**kwargs)
    children[child.pid]=child
    event('launched',pid=child.pid,boot_epoch=btime())
    return child


def observe(record):
    result = original_process(record)
    if result is None:
        child = children.get(record['pid'])
        snapshot={'kind':record['kind'],'pid':record['pid'],'child_returncode':child.poll() if child else 'not_this_invocation','boot_epoch':btime()}
        try:
            process=psutil.Process(record['pid'])
            snapshot.update(status=process.status(),is_running=process.is_running(),command_matches=process.cmdline()==record['command'],creation_delta=round(process.create_time()-record['created_at'],6))
        except psutil.NoSuchProcess:
            snapshot['status']='NO_SUCH_PROCESS'
        except psutil.AccessDenied:
            snapshot['status']='ACCESS_DENIED'
        event('process_rejected',**snapshot)
    return result


globals_['process']=observe
globals_['subprocess'].Popen=launch
try:
    event('begin',command=sys.argv[1])
    module['main']()
    event('returned',status='success')
except BaseException as error:
    event('returned',status='failure',error_type=type(error).__name__)
    raise
finally:
    for pid,child in children.items():
        event('final_child',pid=pid,returncode=child.poll())
    folder=Path(os.environ['SIM2ACT_DATA_DIR'])
    if folder.exists():
        event('log_lengths',**{name:(folder/name).stat().st_size if (folder/name).exists() else None for name in ['api.log','worker.log']})
        output=folder/'observations.jsonl'
        with output.open('a') as out:
            for observation in observations:
                out.write(json.dumps(observation,separators=(',',':'))+'\n')
