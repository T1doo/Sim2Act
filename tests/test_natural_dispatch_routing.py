"""Natural routing hint preserves the real dispatch guards; MOCK/SQLite only."""
import copy
import hashlib
import json
import time
from pathlib import Path

import pytest
from sqlalchemy import delete, select, update
from test_natural_spec_apps import enqueue, ready, setup, transport
from test_project_natural_revalidation import (
    test_late_project_change_no_partial_save as original_cancel,
)

from sim2act import app_jobs, natural_specs, pa_spec_apps
from sim2act.db import (
    Store,
    app_drafts,
    attempts,
    grants,
    internal_instance_data,
    internal_run_bindings,
    operations,
    runs,
)
from sim2act.errors import DomainError
from sim2act.worker import Worker


def test_slow_classification_does_not_spend_initial_lease_before_cancel(env, monkeypatch, tmp_path):
    """FAULT_INJECTION: old classification consumes31s, original lease stays30s.

    Invoke the original whole two-app cancellation case without changing any of
    its assertions. No wall-time throughput or historical reproduction claim.
    """
    claim, classify = Store.claim, pa_spec_apps.is_job
    clock, injected, headers = [], [], []

    def observed_claim(store, *args, **kwargs):
        result = claim(store, *args, **kwargs)
        if result is not None and result['request_key'].startswith('internal:'):
            assert not clock
            assert result['context']['spec_family'] == natural_specs.VERSION
            clock.append(time.time())
            headers.append({k: result[k] for k in ('id', 'created_at', 'lease_until', 'fence')})
            monkeypatch.setattr(time, 'time', lambda: clock[0])
        return result

    def slow_classification(*args, **kwargs):
        result = classify(*args, **kwargs)
        assert len(clock) == 1
        injected.append(31)
        clock[0] += 31
        return result

    monkeypatch.setattr(Store, 'claim', observed_claim)
    monkeypatch.setattr(pa_spec_apps, 'is_job', slow_classification)
    try:
        original_cancel(env, 'cancel')
        assert headers and injected == []
    finally:
        (tmp_path/'classification-fault.json').write_text(json.dumps(dict(
            classification_clock_advances=injected, claimed=headers,
            app_jobs_path=app_jobs.__file__,
            app_jobs_sha256=hashlib.sha256(Path(app_jobs.__file__).read_bytes()).hexdigest(),
            fault_injection=True, original_lease_seconds=30, original_run_seconds=300,
            original_cancel_assertions_unchanged=True), indent=2)+'\n')


@pytest.mark.parametrize('fault', ['marker_removed', 'namespace', 'binding_missing',
                                 'read_revoke', 'lease', 'fence', 'worker'])
def test_routing_hint_cannot_authorize_effects_without_current_proofs(env, fault):
    data = setup(env)
    store, settings = data[:2]
    _, aid, release, inst, _ = ready(data)
    rid = enqueue(data, release, inst)
    sent = []
    worker = Worker(store, settings, goal_planner_transport=transport(sent))
    run = store.claim(worker.id, settings.lease_seconds)
    assert run['id'] == rid and run['context']['spec_family'] == natural_specs.VERSION
    with store.tx() as c:
        before = [dict(x) for x in c.execute(select(internal_instance_data).where(
            internal_instance_data.c.instance_id == inst['id'])).mappings()]
        if fault == 'marker_removed':
            context = copy.deepcopy(run['context'])
            context.pop('spec_family')
            c.execute(update(runs).where(runs.c.id == rid).values(context=context))
        elif fault == 'namespace':
            candidate = copy.deepcopy(c.execute(select(app_drafts.c.candidate).where(
                app_drafts.c.id == aid)).scalar_one())
            candidate['namespace'] = 'untrusted-family'
            c.execute(update(app_drafts).where(app_drafts.c.id == aid).values(candidate=candidate))
        elif fault == 'binding_missing':
            c.execute(delete(internal_run_bindings).where(internal_run_bindings.c.run_id == rid))
        elif fault == 'read_revoke':
            c.execute(update(grants).where(grants.c.resource_id == data[5],
                grants.c.tool_ref == 'resource.read').values(revoked=True))
        else:
            value = {'lease': dict(lease_until=time.time()-1),
                     'fence': dict(fence=run['fence']+1),
                     'worker': dict(worker_id='different-worker')}[fault]
            c.execute(update(runs).where(runs.c.id == rid).values(**value))
    try:
        app_jobs.process_job(worker, run)
    except DomainError:
        pass  # Fail-closed metadata settlement may itself lack current authority.
    assert sent == []
    with store.tx() as c:
        assert c.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).first() is None
        assert c.execute(select(operations.c.id).where(operations.c.run_id == rid)).first() is None
        assert [dict(x) for x in c.execute(select(internal_instance_data).where(
            internal_instance_data.c.instance_id == inst['id'])).mappings()] == before
