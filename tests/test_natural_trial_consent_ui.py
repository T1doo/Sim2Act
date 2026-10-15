"""Full delivered page assets, native DOM gestures and actual authenticated HTTP IPC."""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import delete, update
from test_natural_trial_preparation import business, prepared_data  # noqa: F401

from sim2act.db import delivery_graph_requests, grants
from sim2act.natural_trial_preparation import PREPARE


@pytest.mark.parametrize("scenario", ["happy", "lost-preparation", "lost-consent", "lost-withdrawal",
    "cold", "late-navigation", "goal", "revoke-read", "expiry", "after-read-revoke", "unknown400", "lost-cold"])
def test_actual_page_preparation_consent_recovery(prepared_data, monkeypatch, tmp_path, scenario):  # noqa: F811
    data, body = prepared_data
    store, _, client, _, pid = data[:5]
    before = business(store)
    cards = [client.get('/api/goal-cards/' + b['card_id']).json() for b in body['bindings']]
    if scenario == 'unknown400':
        seeded = client.post(f'/api/projects/{pid}/natural-trials/seeded-key/preparation', json=body)
        assert seeded.status_code == 200
        (tmp_path / 'SEEDED_PARTIAL_PAIR.json').write_text(json.dumps(seeded.json(), indent=2))
        with store.tx() as c:
            c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.kind == PREPARE))
    info = tmp_path / 'info.json'
    info.write_text(json.dumps(dict(project=pid, source=body['bindings'][0]['card_id'],
        cold=body['bindings'][1]['card_id'], scenario=scenario,
        goalTexts=[v for card in cards for v in [card['content']['goal'], *card['content']['constraints'],
            *card['content']['acceptance_checks'], *card['content']['unresolved']]],
        output=str(tmp_path / 'results.json'))))
    process = subprocess.Popen(['node', 'tests/natural_trial_consent_ui.cjs', str(info)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={k: v for k, v in dict(os.environ, NODE_PATH='/workspace/node-tools/node_modules').items()
             if k not in ('SIM2ACT_TEST_DATABASE_URL', 'DATABASE_URL')})
    raw = []
    try:
        for line in process.stdout:
            request = json.loads(line)
            if request.get('done'):
                break
            if request.get('command'):
                command = request['command']
                if command == 'goal':
                    card = cards[0]
                    content = dict(card['content'], goal=card['content']['goal'] + ' revised')
                    assert client.put('/api/goal-cards/' + card['id'], json=dict(content,
                        expected_version=card['version'])).status_code == 200
                elif command == 'revoke-read':
                    with store.tx() as c:
                        c.execute(update(grants).where(grants.c.resource_id == data[5]).values(revoked=True))
                else:
                    assert command == 'expiry'
                    import time
                    at = time.time() + 301
                    monkeypatch.setattr(time, 'time', lambda at=at: at)
                answer = dict(id=request['id'], status=200, text='{}')
            else:
                response = client.request(request['method'], request['path'],
                    json=request.get('body'), headers=request.get('headers'))
                answer = dict(id=request['id'], status=response.status_code, text=response.text,
                              content_type=response.headers.get('content-type'))
                raw.append(dict(request=request, response=answer))
            process.stdin.write(json.dumps(answer) + '\n')
            process.stdin.flush()
        errors = process.stderr.read()
        code = process.wait(timeout=20)
        (tmp_path / 'HTTP_RAW.json').write_text(json.dumps(raw, indent=2))
        (tmp_path / 'driver.log').write_text(errors)
        assert code == 0, errors
        proof = json.loads((tmp_path / 'results.json').read_text())
        assert proof['status'] == 'PASS' and len(proof['checks']) >= (10 if scenario == 'unknown400' else 15)
        web = Path(__file__).parents[1] / 'src/sim2act/web'
        assert set(proof['loaded_source_sha256']) == {'index.html', 'app.css',
            *re.findall(r'<script src="/([^"]+)"', (web / 'index.html').read_text())}
        assert proof['loaded_source_sha256'] == {name: hashlib.sha256((web / name).read_bytes()).hexdigest()
            for name in proof['loaded_source_sha256']}
        assert business(store) == before
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
