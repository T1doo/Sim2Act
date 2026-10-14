"""FAULT_INJECTION: finite elapsed time inside a locked real SAVE transaction.

This is a mechanism regression, not a natural reproduction of the retained
historical failure or a wall-clock performance claim. No budget or claim limit
is changed. All requests remain synthetic and all writes use the actual Worker.
"""
import json
import time

from sqlalchemy import select
from test_natural_spec_apps import SOURCE, transport
from test_project_natural_revalidation import cohort, freeze, start

from sim2act import pa_spec_apps as spec
from sim2act import project_natural_revalidation as project
from sim2act.db import runs
from sim2act.errors import DomainError
from sim2act.natural_spec_runtime import fail_owned
from sim2act.worker import Worker


def test_peer_save_bounded_elapsed_transaction(env, monkeypatch, tmp_path):
    values = cohort(env)
    data, aid, _, _, _, peer, _, _, base, _ = values
    plan = freeze(values)
    checked = start(values, plan, peer)
    assert data[1].run_seconds == 300 and data[1].lease_seconds == 30
    clock = [time.time()]
    active = [False]
    segments = []
    original_advance = spec._advance_local
    original_load = project._load_plan

    def advance(worker, c, run, job, b=None, checked=None):
        saved = (run['id'] == peer_run and b is not None and checked is not None
                 and b['plan']['definition']['actions'][len(checked[1])]['executor']['ref'] == spec.SAVE)
        active[0] = saved
        try:
            return original_advance(worker, c, run, job, b, checked)
        finally:
            active[0] = False

    def load(*args, **kwargs):
        value = original_load(*args, **kwargs)
        if active[0]:
            before = clock[0]
            clock[0] += 8
            segments.append(dict(before=before, after=clock[0], seconds=8))
        return value

    peer_run = checked['run_id']
    monkeypatch.setattr(time, 'time', lambda: clock[0])
    monkeypatch.setattr(spec, '_advance_local', advance)
    monkeypatch.setattr(project, '_load_plan', load)
    sent = []
    claims = None
    try:
        worker = Worker(data[0], data[1], goal_planner_transport=transport(sent, SOURCE))
        claims = []
        for _ in range(3):
            run = data[0].claim(worker.id, data[1].lease_seconds)
            assert run is not None and run['id'] == peer_run
            error = None
            for _ in range(6):
                # The production lease API on the original owner/fence; this
                # isolates one real locked phase from the background scheduler.
                data[0].heartbeat(worker.id, run['id'], run['fence'], data[1].lease_seconds)
                try:
                    again = spec.advance(worker, run)
                except DomainError as exc:
                    error = exc.public()
                    fail_owned(worker, run, exc)
                    break
                if not again:
                    break
            with data[0].tx() as c:
                header = dict(c.execute(select(runs.c.status, runs.c.fence,
                    runs.c.lease_until, runs.c.created_at, runs.c.cancel_intent)
                    .where(runs.c.id == peer_run)).mappings().one())
            claims.append(dict(header=header, error=error))
            if header['status'] == 'SUCCEEDED':
                break
            assert header['status'] == 'RUNNING' and not header['cancel_intent']
            assert clock[0] >= header['lease_until']
            assert clock[0] < header['created_at'] + data[1].run_seconds
        assert header['status'] == 'SUCCEEDED', 'Original bounded SAVE lease interval did not commit' 
        assert len(sent) == 2
        response = data[2].get(base + '/plans/project-two')
        assert response.status_code == 200, response.text
        assert response.json()['local_checks_status'] == 'PARTIAL'
        assert response.json()['project_revalidation_completed'] is False
        assert response.json()['dependency_completeness'] == 'BLOCKED_UNKNOWN'
    finally:
        (tmp_path / 'bounded-elapsed-transaction.json').write_text(json.dumps(dict(
            method='FAULT_INJECTION: isolated real Store/Worker/spec.advance phase, synchronized original lease30; 8 test-clock seconds after each complete SAVE-scope replay; not Worker.once full flow',
            historical_failure_root_cause='UNKNOWN', original_run_seconds=300,
            original_lease_seconds=30, original_max_claims=3, run_id=peer_run,
            segments=segments, claims=claims, synthetic_model_requests=len(sent),
            real_model_requests=0), indent=2) + '\n')
