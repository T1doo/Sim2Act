import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import select
from test_text_continuations import legacy
from test_text_logic_reuse import source_barrier
from sim2act.db import goal_card_versions, goal_cards

BASE = Path('/tmp/text-continuation-independent-final-v3-20261012')


@pytest.mark.parametrize('scenario', ['late-connect', 'wrong-key', 'wrong-release'])
def test_shipped_page_exact_key_and_post_fence(legacy, tmp_path, scenario):
    store, settings, client, old = legacy
    store.user('Independent visible foreign synthetic reviewer', 'independent-foreign-token')
    private = old['old_private']
    data = (store, settings, client, old['owner'], old['project'], private['resource'], None)
    with store.tx() as c:
        ids = set(c.execute(select(goal_cards.c.id).where(goal_cards.c.project_id == old['project'])).scalars())
    if old.get('goal'):
        ids.remove(old['goal']['card_id'])
    barrier = source_barrier(data, private['app'], private['release'], private['instance'], private['run'])
    barrier.rules['goal_card_versions'] = (goal_card_versions, 'card_id', ids, {'snapshot'})
    info = dict(project=old['project'], instance=old['instance']['id'], custom=scenario,
                fixture_time=old['fixture_time'], output=str(tmp_path/'proof.json'))
    (tmp_path/'info.json').write_text(json.dumps(info))
    folder = Path(os.environ.get('SIM2ACT_INDEPENDENT_UI_EVIDENCE', str(BASE/'ui-adversarial')))
    folder.mkdir(exist_ok=True)
    stem = ('a747' if old.get('goal') else '233')+'-'+scenario
    with (tmp_path/'stderr.log').open('w') as errors, barrier:
        process = subprocess.Popen(['node', str(BASE/'ui_adversarial.cjs'), str(tmp_path/'info.json')],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
                    env={**os.environ, 'NODE_PATH':'/workspace/node-tools/node_modules'})
        try:
            for line in process.stdout:
                request=json.loads(line)
                if request.get('done'):
                    break
                response=client.request(request['method'],request['path'],json=request.get('body'),headers=request.get('headers'))
                answer=dict(id=request['id'],status=response.status_code,text=response.text,content_type=response.headers.get('content-type'))
                process.stdin.write(json.dumps(answer)+'\n');process.stdin.flush()
            process.stdin.close();code=process.wait(timeout=20)
            assert code==0, (tmp_path/'stderr.log').read_text()
            proof=json.loads((tmp_path/'proof.json').read_text())
            assert proof['status']=='PASS' and not barrier.blocked
            assert len(proof['static_resource_loads'])==20
            for row in proof['static_resource_loads']:
                asset=Path('/workspace/Sim2Act/src/sim2act/web')/(row['path'].lstrip('/') or 'index.html')
                assert hashlib.sha256(asset.read_bytes()).hexdigest()==row['sha256']
        finally:
            if process.poll() is None:
                process.kill();process.wait(timeout=5)
            for file,suffix in [(tmp_path/'stderr.log','.log'),(tmp_path/'proof.json','.json')]:
                if file.exists():(folder/(stem+suffix)).write_bytes(file.read_bytes())
            (folder/(stem+'-sql.json')).write_text(json.dumps({'blocked':barrier.blocked,'evaluated_cells':barrier.evaluated,'sql':barrier.statements},indent=2))
            (folder/(stem+'-exit.json')).write_text(json.dumps({'exit_code':process.returncode,'native_browser':'NOT_RUN','model':'NOT_RUN'}))
