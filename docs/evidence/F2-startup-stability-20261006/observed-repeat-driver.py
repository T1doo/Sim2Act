import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tests'))
from conftest import env,runtime_role
from test_lifecycle import test_AT05_real_process_stop_accept_restart_reopen as original


@pytest.mark.parametrize('repeat',range(4))
def test_observed_original_at05(env,runtime_role,tmp_path,monkeypatch,repeat):
    run=subprocess.run
    def observed(args,*a,**kw):
        if len(args)>1 and args[1]=='scripts/manage.py':
            args=[args[0],'docs/evidence/F2-startup-stability-20261006/at05-probe.py',*args[2:]]
        return run(args,*a,**kw)
    monkeypatch.setattr(subprocess,'run',observed)
    try:
        original(env,runtime_role,tmp_path)
    finally:
        data=tmp_path/'中文 空格数据'/'observations.jsonl'
        if data.exists():
            target=Path(__file__).resolve().parent/f'observed-{repeat}.json'
            target.write_text(json.dumps([json.loads(line) for line in data.read_text().splitlines()],indent=2)+'\n')
