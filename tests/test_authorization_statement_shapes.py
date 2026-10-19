"""SQL structure sharing must keep every live authorization read independent."""
import json

import pytest
from sqlalchemy import event, select, update

from sim2act.db import _AUTHORITY_GRANTS_QUERY, _AUTHORIZED_RESOURCE_QUERY, grants, resources
from sim2act.errors import DomainError


def test_authorization_statements_rebind_and_read_current_authority(env, tmp_path):
    store, _, _, user, other, pid, rid = env
    sql, reports = [], []

    def record(c, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT "):
            sql.append((statement, parameters))

    with store.tx() as c:
        runtime = store.own_project(c, user, pid)["runtime_id"]
        event.listen(store.engine, "before_cursor_execute", record)
        try:
            def compare_resource(label, resource, project):
                sql.clear()
                old = c.execute(select(resources.c.id).where(
                    resources.c.id == resource, resources.c.project_id == project)).first()
                expected = list(sql)
                sql.clear()
                actual = c.execute(_AUTHORIZED_RESOURCE_QUERY,
                    {"authorized_resource_id": resource, "authorized_resource_project": project}).first()
                assert actual == old and sql == expected and len(sql) == 1
                reports.append(dict(case=label, rows=0 if old is None else 1, exact_sql_params_rows=True))

            def compare_grants(label, identity, project=pid, resource=rid, tool="resource.read"):
                sql.clear()
                old = c.execute(select(grants).where(grants.c.principal_id == identity,
                    grants.c.project_id == project, grants.c.resource_id == resource,
                    grants.c.tool_ref == tool).order_by(grants.c.id).with_for_update()).mappings().all()
                expected = list(sql)
                sql.clear()
                actual = c.execute(_AUTHORITY_GRANTS_QUERY,
                    {"authority_identity": identity, "authority_project": project,
                     "authority_resource": resource, "authority_tool": tool}).mappings().all()
                assert [dict(row) for row in actual] == [dict(row) for row in old]
                assert sql == expected and len(sql) == 1
                reports.append(dict(case=label, rows=len(old), exact_sql_params_rows=True))

            compare_resource("resource-A", rid, pid)
            compare_resource("missing-resource", rid + "-missing", pid)
            compare_resource("wrong-project", rid, pid + "-missing")
            compare_resource("resource-A-after-wrong", rid, pid)
            compare_grants("principal-A", user)
            compare_grants("runtime-B", runtime)
            compare_grants("missing-identity", other)
            compare_grants("principal-after-B", user)
            compare_grants("wrong-project", user, project=pid + "-missing")
            compare_grants("wrong-resource", user, resource=rid + "-missing")
            compare_grants("other-tool", user, tool="data.aggregate_csv")
            compare_grants("missing-tool", user, tool="missing.tool")
            compare_grants("principal-A-after-wrong", user)

            with store.proof_authorities(c) as checks:
                store.authorize(c, user, runtime, pid, rid, "data.aggregate_csv")
                expected_checks = {(user, runtime, pid, rid, "resource.read"),
                                   (user, runtime, pid, rid, "data.aggregate_csv")}
                assert checks == expected_checks
                captured = dict(_call_authorities=tuple(checks))

            # Mutate one actual matching identity row at a time; the other
            # identity remains valid. No cached rows or permit may survive.
            for identity, change in ((user, {"revoked": True}), (runtime, {"expires_at": 0})):
                savepoint = c.begin_nested()
                try:
                    changed = c.execute(update(grants).where(grants.c.principal_id == identity,
                        grants.c.project_id == pid, grants.c.resource_id == rid,
                        grants.c.tool_ref == "resource.read").values(**change))
                    assert changed.rowcount == 1
                    compare_grants("current-mutated-row", identity)
                    with pytest.raises(DomainError) as refused:
                        store.authorize(c, user, runtime, pid, rid, "data.aggregate_csv")
                    assert refused.value.code == "GRANT_REVOKED"
                    with pytest.raises(DomainError) as recheck:
                        store.recheck_proof_authorities(c, captured)
                    assert recheck.value.code == "GRANT_REVOKED"
                finally:
                    savepoint.rollback()
                store.authorize(c, user, runtime, pid, rid, "data.aggregate_csv")
                compare_grants("current-row-after-rollback", identity)

            with pytest.raises(DomainError) as missing:
                store.authorize(c, user, other, pid, rid, "resource.read")
            assert missing.value.code == "PERMISSION_DENIED"
            store.authorize(c, user, runtime, pid, rid, "resource.read")
        finally:
            event.remove(store.engine, "before_cursor_execute", record)
    (tmp_path / "authorization-query-proof.json").write_text(json.dumps(dict(
        scope="SQL_SHAPE_AND_CURRENT_SYNTHETIC_AUTHORITY_NOT_RUN_OR_LIVE_ACCEPTANCE",
        mock_exchanges=0, real_models=0, cases=reports, successful_authorities_registered=True,
        actual_matching_grant_changes_rolled_back=True, principal_revoke_refused=True,
        runtime_expiry_refused=True, captured_authorities_freshly_rechecked=True), indent=2))
