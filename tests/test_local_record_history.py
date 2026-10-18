"""Typed project history reads keep the legacy execution boundary closed."""

import pytest
from test_local_record_apps import create_body, current, execute, guarded, ok, ready, snapshot

from sim2act.errors import DomainError


def test_typed_history_read_owner_permissions_and_legacy_boundary(env):
    data = ready(env)
    first = execute(env, data, create_body(current(env, data)))
    rid = first["run"]["id"]
    path = "/api/runs/" + rid
    before = snapshot(env[0])
    value = ok(env[2].get(path))
    assert value["namespace"] == "local-record-app.v1"
    assert value["id"] == rid and value["instance_id"] == data["instance"]["id"]
    assert value["app_id"] == data["app"]["id"] and value["project_id"] == env[5]
    assert value["principal_id"] == env[3] and value["event"] == first["run"]["event"]
    assert value["output"] == first["run"]["output"] and value["receipt"]["status"] == "VERIFIED"
    assert snapshot(env[0]) == before
    with pytest.raises(DomainError) as legacy:
        env[0].inspect(env[3], rid)
    assert legacy.value.code == "UNSUPPORTED_CAPABILITY"
    response = env[2].post(path + "/commands", json=dict(command="cancel", version=value["version"]))
    assert response.status_code == 400 and response.json()["error"]["code"] == "UNSUPPORTED_CAPABILITY"
    assert snapshot(env[0]) == before
    with guarded(env[0], [first]) as barrier:
        try:
            env[2].headers["Authorization"] = "Bearer synthetic-test-B"
            assert env[2].get(path).status_code == 403
        finally:
            env[2].headers["Authorization"] = "Bearer synthetic-test-A"
        assert not barrier.blocked and not barrier.full_binding_reads
    grants = ok(env[2].get(f"/api/projects/{env[5]}/grants"))
    grant = next(g for g in grants if g["principal_id"] == env[3]
        and g["resource_id"] == value["output"]["resource_id"] and not g["revoked"])
    ok(env[2].post(f"/api/grants/{grant['id']}/revoke", json=dict(command="revoke", version=grant["revision"])))
    revoked = snapshot(env[0])
    with guarded(env[0], [first]) as barrier:
        assert env[2].get(path).status_code == 403
        assert not barrier.blocked and not barrier.full_binding_reads
    assert snapshot(env[0]) == revoked
