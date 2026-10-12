"""Reproduce synthetic persisted databases with exact accepted Git software.

Only the ordinary approved fixture helpers run; no race probes or remote tools.
Run with the repository Python and an empty output directory.
"""

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

KNOWN = {"233ba9618ba462aad19e1ca16f085cd0d7242632", "a747a7aafe7a537858f75bbfa129addd8696d0a6"}
CREATE = '''import json
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import select
import sim2act
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store,meta
from test_registered_text_extraction import prepared
from test_text_logic_reuse import mint,bind,binding,revoke_source
from test_goal_text_applications import release_instance,run_input
root=Path(__file__).parent
assert Path(sim2act.__file__).is_relative_to(root/'src')
db=root/'actual-old.db';assert not db.exists()
s=Settings('sqlite:///'+str(db),root/'old-data',mode='mock',live_enabled=False)
store=Store(s.database_url,test_only=True);store.initialize()
a=store.user('fixture A','synthetic-test-A');b=store.user('fixture B','synthetic-test-B')
client=TestClient(create_app(store,s));client.headers['Authorization']='Bearer synthetic-test-A'
pid=client.post('/api/projects',json={'name':'exact old synthetic software'}).json()['id']
rid=client.post(f'/api/projects/{pid}/resources',json={'name':'unrelated.csv','format':'csv','content':(root/'tests/fixtures/f1.csv').read_text()}).json()['id']
data,source,oldrel,oldinst,oldrun,target,resource,url=prepared((store,s,client,a,b,pid,rid))
logic,_=mint(data,url);made=bind(data,logic,binding(data,logic,target))
release,instance=release_instance(data,made['id'])
signature=None;goal=None
if (root/'src/sim2act/app_owner_goals.py').exists():
 from test_text_logic_owner import save_goal,own_run
 from test_owner_acceptance import prepare,choice_body,state
 goal,_=save_goal(data,made,resource)
 job=own_run(data,made,release,instance,key='old-native-goal-worker')
 review,_=prepare(data,release,instance,job)
 decision=client.post(f"/api/internal/instances/{instance['id']}/owner-review-requests",json=choice_body(review))
 assert decision.status_code==201,decision.text
 signature=state(data,instance);assert signature['owner_acceptance']=='ACCEPTED'
else:
 job=run_input(data,release,instance,{'term':'Gamma'},'old233-durable-input')
assert job['status']=='SUCCEEDED'
failed=None
if __import__('os').environ.get('SIM2ACT_LEGACY_INCLUDE_FAILURE')=='1':
 if goal:
  failed=own_run(data,made,release,instance,term=' padded ',key='old-invalid-input')
 else:
  failed=run_input(data,release,instance,{'term':' padded '},'old-invalid-input')
 assert failed['status']=='FAILED' and failed['result_version'] is None
other=client.post('/api/internal/releases/'+release['id']+'/instances',json={'expected_release_fingerprint':release['fingerprint'],'request_key':'other-unapproved-instance'});assert other.status_code==201,other.text
revoke_source(data)
with store.tx() as c:
 snapshot={t.name:[dict(r) for r in c.execute(select(t)).mappings()] for t in meta.sorted_tables}
(root/'old-rows.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2))
info={'software_fp':logic['implementation_fingerprint'],'logic':logic,'app':made,'release':release,'instance':instance,'successful_old_run_id':job['id'],'failed_old_run_id':failed['id'] if failed else None,'other_instance':other.json(),'project':pid,'owner':a,'resource':resource,'old_private':{'app':source,'release':oldrel,'instance':oldinst,'run':oldrun,'resource':data[5]},'goal':goal,'old_signature':signature,'fixture_time':logic['created_at']+20,'kind':'ACTUAL_SQLITE_CREATED_BY_EXACT_APPROVED_GIT_TESTCLIENT_AND_NORMAL_WORKER','real_model_requests':0}
(root/'old-info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
print(json.dumps({'status':'PASS','old_worker_status':job['status'],'actual_data_version':1,'old_owner_status':signature['owner_acceptance'] if signature else 'ABSENT','software_fp':logic['implementation_fingerprint'],'real_model_requests':0}))
client.close();store.engine.dispose()
'''


def build(sha, destination):
    assert sha in KNOWN and not destination.exists()
    destination.mkdir(parents=True)
    repository = Path(__file__).resolve().parents[1]

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=repository)

    paths = git("ls-tree", "-r", "--name-only", sha, "src").decode().splitlines()
    helpers = set()
    pending = ["test_registered_text_extraction", "test_text_logic_reuse", "test_goal_text_applications"]
    if sha.startswith("a747"):
        pending.append("test_text_logic_owner")
    while pending:
        name = pending.pop()
        if name in helpers:
            continue
        assert not any(x in name for x in ("exact_install", "recovery_ui", "cancelled"))
        helpers.add(name)
        path = "tests/" + name + ".py"
        raw = git("show", sha + ":" + path)
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        for node in ast.walk(ast.parse(raw)):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("test_"):
                pending.append(node.module)
    paths += ["tests/fixtures/f1.csv", "docs/evidence/bounded-agent-offline-20261006/independent-gold.json"]
    for path in paths:
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git("show", sha + ":" + path))
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (destination / "src/sim2act").glob("*.py") if p.name != "config.py"}
    fp = hashlib.sha256(json.dumps(files, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    (destination / "archive-manifest.json").write_text(json.dumps({"sha": sha, "exact_old_software_fp": fp, "python_files": files, "imported_helper_modules": sorted(helpers)}, indent=2))
    script = destination / "create_old_store.py"
    script.write_text(CREATE)
    result = subprocess.run([sys.executable, str(script)], cwd=destination,
        env={**os.environ, "PYTHONPATH": str(destination / "src") + os.pathsep + str(destination / "tests")}, capture_output=True, text=True)
    (destination / "create-old.log").write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads((destination / "old-info.json").read_text())["software_fp"] == fp
    print(result.stdout)


if __name__ == "__main__":
    build(sys.argv[1], Path(sys.argv[2]))
