"""Deliberately corrupted FAILED history, not a valid old Worker fixture."""
import copy
import json
from pathlib import Path

from sqlalchemy import insert, select
from test_text_continuations import legacy, path, rows
from sim2act.db import fingerprint, internal_app_runs, internal_run_bindings, new_id, runs

BASE = Path('/tmp/text-continuation-independent-final-v2-20261012/terminal-history')


def test_corrupted_failed_history_denied_before_continuation(legacy):
    store, _, client, info = legacy
    # Preserve the genuine old SUCCEEDED run, typed v1, all data and history.
    # Append a synthetic terminal FAILED job with a deliberately broken binding.
    with store.tx() as c:
        original = dict(c.execute(select(runs).where(runs.c.id == info['successful_old_run_id'])).mappings().one())
        binding = dict(c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == original['id'])).mappings().one())
        app_run = dict(c.execute(select(internal_app_runs).where(internal_app_runs.c.id == binding['app_run_id'])).mappings().one())
        rid, aid = new_id('run'), new_id('iapprun')
        snapshot = copy.deepcopy(binding['snapshot'])
        snapshot.update(run_id=rid, app_run_id=aid, request_key='independent-corrupted-failed-history')
        original.update(id=rid, request_key='internal:'+aid, status='FAILED', result=None,
                        error={'code':'FI_CORRUPTED_FAILED_HISTORY','message':'Synthetic damaged history; never a valid Worker result'},
                        fingerprint=fingerprint(snapshot), worker_id=None, lease_until=0)
        original['context'] = copy.deepcopy(original['context'])
        original['context'].update(app_run_id=aid, request_key='independent-corrupted-failed-history')
        app_run.update(id=aid, status='FAILED', output=None, result_version=None,
                       request_key='independent-corrupted-failed-history', error=original['error'])
        binding.update(run_id=rid, app_run_id=aid, snapshot=snapshot, fingerprint='0'*64)
        c.execute(insert(runs).values(**original))
        c.execute(insert(internal_app_runs).values(**app_run))
        c.execute(insert(internal_run_bindings).values(**binding))
    before=rows(store)
    chosen=next(x for x in client.get('/api/projects/'+info['project']+'/software-continuation-options').json()['items']
                if x['id']==info['instance']['id'])
    request=dict(expected_revision=chosen['revision'], expected_release_fingerprint=chosen['release_fingerprint'],
                 expected_candidate_fingerprint=chosen['fingerprint'], expected_source_implementation=chosen['source_implementation'],
                 input={'term':'Alpha'}, request_key='independent-failed-history-preflight')
    preflight=client.post(path(info).replace('software-continuations','software-continuation-preflights'),json=request)
    evidence={'classification':'DELIBERATELY_CORRUPTED_FAILED_HISTORY_NOT_VALID_OLD_WORKER',
              'preflight_status':preflight.status_code,'preflight_body':preflight.json(),'run_id':rid}
    if preflight.status_code==201:
        value=preflight.json()
        body=dict(approval_id=value['approval_id'],expected_approval_fingerprint=value['approval_fingerprint'],
                  consent='CONTINUE_ONLY_THIS_EXACT_EXISTING_INSTANCE_WITH_THIS_SOFTWARE',request_key='independent-failed-history-commit')
        commit=client.post(path(info),json=body)
        evidence.update(commit_status=commit.status_code,commit_body=commit.json())
        cold=client.get('/api/internal/instances/'+info['instance']['id'])
        old_job=client.get('/api/internal/instances/'+info['instance']['id']+'/runs/'+rid)
        evidence.update(cold_instance_status=cold.status_code,cold_instance_body=cold.json(),
                        cold_failed_run_status=old_job.status_code,cold_failed_run_body=old_job.json())
    BASE.mkdir(exist_ok=True)
    (BASE/(('a747' if info.get('goal') else '233')+'.json')).write_text(json.dumps(evidence,indent=2)+'\n')
    assert preflight.status_code==409, evidence
    assert rows(store)==before
