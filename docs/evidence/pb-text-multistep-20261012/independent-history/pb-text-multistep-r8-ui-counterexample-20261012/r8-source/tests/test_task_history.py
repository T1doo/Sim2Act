"""Authorized, bounded persisted history projection; no model execution."""
import pytest
from sqlalchemy import delete, update

from sim2act.contracts import Limits
from sim2act.db import run_contracts


def test_history_summary_is_bounded_text_and_frozen_mode(env):
    store, settings, client, owner, _, project, resource = env
    goal = '  <script>alert(1)</script>\n' + '长' * 200
    run = store.submit(owner, project, goal, [resource], 'history-mode', policy={
        'limits': Limits(max_requests=4, max_tools=4, max_repairs=1, max_total_tokens=64000, max_output_tokens=1024, run_seconds=300).model_dump(), 'mode': 'live', 'request_model': 'intern-s2',
    })
    items = client.get(f'/api/projects/{project}/runs').json()
    assert len(items) == 1
    item = items[0]
    assert item['id'] == run and item['mode'] == 'LIVE'
    assert len(item['goal_summary']) == 161 and item['goal_summary'].endswith('…')
    assert item['goal_summary'].startswith('<script>') and '\n' not in item['goal_summary']
    assert item['status'] == 'QUEUED' and isinstance(item['created_at'], float)
    assert set(item) == {'id', 'status', 'created_at', 'goal_summary', 'mode'}
    assert settings.mode == 'mock'  # Current server setting is not the saved mode.


def test_history_missing_contract_and_protocol_placeholder_are_unknown(env):
    store, _, client, owner, _, project, resource = env
    missing = store.submit(owner, project, 'Missing contract', [resource], 'missing')
    protocol = store.submit(owner, project, 'Protocol-shaped intent', [resource], 'protocol:fixture')
    with store.tx() as c:
        c.execute(delete(run_contracts).where(run_contracts.c.run_id == missing))
    items = {r['id']: r for r in client.get(f'/api/projects/{project}/runs').json()}
    assert items[missing]['mode'] == items[protocol]['mode'] == 'UNKNOWN'


def test_history_is_principal_and_project_scoped(env):
    store, _, client, owner, other_owner, project, resource = env
    run = store.submit(owner, project, 'PRIVATE HISTORY A', [resource], 'own-history')
    other_project = store.project(other_owner, 'Other identity project')
    store.submit(other_owner, other_project, 'PRIVATE HISTORY B', [], 'other-history')
    assert [r['id'] for r in client.get(f'/api/projects/{project}/runs').json()] == [run]
    assert client.get(f'/api/projects/{other_project}/runs').status_code == 403
    client.headers.update({'Authorization': 'Bearer synthetic-test-B'})
    denied = client.get(f'/api/projects/{project}/runs')
    assert denied.status_code == 403 and 'PRIVATE HISTORY A' not in denied.text
    assert client.get(f'/api/projects/{other_project}/runs').json()[0]['goal_summary'] == 'PRIVATE HISTORY B'


def test_history_invalid_saved_mode_does_not_invent_mock(env):
    store, _, client, owner, _, project, resource = env
    run = store.submit(owner, project, 'Legacy incomplete mode', [resource], 'bad-mode')
    with store.tx() as c:
        c.execute(update(run_contracts).where(run_contracts.c.run_id == run).values(snapshot={'mode': []}))
    assert client.get(f'/api/projects/{project}/runs').json()[0]['mode'] == 'UNKNOWN'


def test_history_application_role_route_and_no_ddl(env, runtime_role):
    """Existing temporary non-superuser fixture reads the new joined projection."""
    from fastapi.testclient import TestClient
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from sim2act.api import create_app
    from sim2act.db import Store

    store, settings, client, owner, _, project, resource = env
    run = store.submit(owner, project, 'Application role persisted history', [resource], 'role-history')
    application = Store(runtime_role)
    try:
        with TestClient(create_app(application, settings)) as app_client:
            app_client.headers.update({'Authorization': 'Bearer synthetic-test-A'})
            response = app_client.get(f'/api/projects/{project}/runs')
            assert response.status_code == 200
            assert response.json() == client.get(f'/api/projects/{project}/runs').json()
            assert response.json()[0]['id'] == run and response.json()[0]['mode'] == 'MOCK'
            app_client.headers.update({'Authorization': 'Bearer synthetic-test-B'})
            assert app_client.get(f'/api/projects/{project}/runs').status_code == 403
        with pytest.raises(DBAPIError) as denied:
            with application.tx() as c:
                c.execute(text('CREATE TABLE history_api_must_not_create (id integer)'))
        assert getattr(denied.value.orig, 'sqlstate', None) == '42501'
    finally:
        application.engine.dispose()
