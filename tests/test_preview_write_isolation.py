"""AT17_SYNTHETIC_FIXTURE: actual preview SQL writes, not production write capability."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from preview_write_fixture import (
    Target,
    controlled_writer,
    preview_receipts,
    preview_records,
    production_bytes,
)
from sqlalchemy import func, select
from test_internal_lifecycle import create, limits, release, run, setup_draft

from sim2act.db import Store, app_previews, fingerprint, meta
from sim2act.errors import DomainError
from sim2act.tools import TOOLS


def seed(env):
    r, aid, fp = release(env)
    first, second = create(env, r), create(env, r)
    assert run(env, first, r)["status"] == "SUCCEEDED"
    assert run(env, second, r, key="second")["status"] == "SUCCEEDED"
    return aid, fp, r, first, second


def target(env, aid, fp):
    return Target("PREVIEW", env[3], env[5], aid, fp)


def submit(env, aid, key="controlled", column="amount"):
    return env[2].post(
        f"/api/apps/{aid}/previews", json={"input": {"column": column}, "request_key": key}
    )


def reopen(env):
    s = Store(env[1].database_url, test_only=True)
    if not env[0].sqlite:
        s.engine = s.engine.execution_options(**env[0].engine.get_execution_options())
    return s


def readback(env):
    # New engine/connection, independent of the adapter's transaction and in-memory observation.
    s = reopen(env)
    try:
        with s.tx() as c:
            return [dict(x) for x in c.execute(select(preview_records)).mappings()], [
                dict(x) for x in c.execute(select(preview_receipts)).mappings()
            ]
    finally:
        s.engine.dispose()


def assert_production_unchanged(env, before):
    cold = reopen(env)
    try:
        assert (
            production_bytes(cold) == before
        )  # Actual raw stored value bytes, every nonpreview table.
    finally:
        cold.engine.dispose()


def test_actual_preview_write_new_connection_readback_instance_and_grants_bytes_unchanged(
    env, tmp_path
):
    aid, fp, _, first, second = seed(env)
    before = production_bytes(env[0])
    tools = fingerprint(TOOLS)
    with controlled_writer(env[0], tmp_path, target(env, aid, fp), limits(env)) as observation:
        response = submit(env, aid)
        assert response.status_code == 200
        row = response.json()
        assert row["namespace"] == "PREVIEW" and row["status"] == "SUCCEEDED"
        # This public field still describes the production read-tool chain, not the test adapter.
        assert row["business_writes"] == 0 and row["release_id"] is None
        assert observation.writes_executed == 1
    records, receipts = readback(env)
    assert len(records) == len(receipts) == 1
    expected = {
        "preview_id": row["id"],
        "namespace": "PREVIEW",
        "project_id": env[5],
        "app_id": aid,
        "principal_id": env[3],
        "record_text": "controlled note for column=amount\n仅预览 Ω",
    }
    assert records[0] == expected and receipts[0]["record_fingerprint"] == fingerprint(expected)
    assert receipts[0]["request_fingerprint"] == row["fingerprint"]
    assert first["id"] not in records[0].values() and second["id"] not in records[0].values()
    assert_production_unchanged(env, before)
    assert fingerprint(TOOLS) == tools
    assert not {"fixture_preview_records", "fixture_preview_receipts"} & set(meta.tables)
    # Context exit removes hook; later ordinary production preview does not silently write.
    assert submit(env, aid, "ordinary").status_code == 200
    assert readback(env) == (records, receipts)
    assert_production_unchanged(env, before)


def test_after_actual_write_failure_rolls_back_preview_record_and_receipt(env, tmp_path):
    aid, fp, *_ = seed(env)
    before = production_bytes(env[0])
    with controlled_writer(
        env[0], tmp_path, target(env, aid, fp), limits(env), fail_after_write=True
    ) as observation:
        response = submit(env, aid)
        assert (
            response.status_code == 400
            and response.json()["error"]["code"] == "VERIFICATION_FAILED"
        )
        assert observation.writes_executed == 1
        assert (
            observation.inside_transaction_readback == "controlled note for column=amount\n仅预览 Ω"
        )
        assert observation.receipts_executed == 1
        assert observation.inside_transaction_receipt is not None
    assert readback(env) == ([], [])
    with env[0].tx() as c:
        assert c.execute(select(func.count()).select_from(app_previews)).scalar_one() == 0
    assert_production_unchanged(env, before)
    # Rollback did not consume the logical request: retry can genuinely write exactly once.
    with controlled_writer(env[0], tmp_path, target(env, aid, fp), limits(env)) as observation:
        assert submit(env, aid).status_code == 200
        assert submit(env, aid).status_code == 200
        assert observation.writes_executed == 1
    assert len(readback(env)[0]) == 1
    assert_production_unchanged(env, before)


def test_repeated_concurrent_preview_write_one_logical_effect_and_changed_input_reject(
    env, tmp_path
):
    aid, fp, *_ = seed(env)
    before = production_bytes(env[0])
    with controlled_writer(env[0], tmp_path, target(env, aid, fp), limits(env)) as observation:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: submit(env, aid), range(2)))
        assert all(x.status_code == 200 for x in results)
        assert results[0].json()["id"] == results[1].json()["id"]
        assert submit(env, aid).json()["id"] == results[0].json()["id"]
        assert submit(env, aid, column="other").status_code == 409
        assert observation.writes_executed == 1
    assert len(readback(env)[0]) == len(readback(env)[1]) == 1
    assert_production_unchanged(env, before)


@pytest.mark.parametrize(
    "wrong", ["namespace", "instance", "release", "owner", "project", "app", "fingerprint"]
)
def test_explicit_namespace_and_identity_binding_reject_before_fixture_write(env, tmp_path, wrong):
    aid, fp, r, i, _ = seed(env)
    t = target(env, aid, fp)
    if wrong == "namespace":
        t = replace(t, namespace="INSTANCE")
    elif wrong == "instance":
        t = replace(t, instance_id=i["id"])
    elif wrong == "release":
        t = replace(t, release_id=r["id"])
    elif wrong == "owner":
        t = replace(t, principal_id=env[4])
    elif wrong == "project":
        t = replace(t, project_id=env[0].project(env[3], "other isolated project"))
    elif wrong == "app":
        t = replace(t, app_id=setup_draft(env)[0])
    else:
        t = replace(t, candidate_fingerprint="0" * 64)
    before = production_bytes(env[0])
    with controlled_writer(env[0], tmp_path, t, limits(env)) as observation:
        assert submit(env, aid).status_code in {400, 403, 409}
        assert observation.writes_executed == 0
    assert readback(env) == ([], [])
    with env[0].tx() as c:
        assert c.execute(select(func.count()).select_from(app_previews)).scalar_one() == 0
    assert_production_unchanged(env, before)


def test_invalid_preview_input_never_writes_controlled_business_data(env, tmp_path):
    aid, fp, *_ = seed(env)
    before = production_bytes(env[0])
    with controlled_writer(env[0], tmp_path, target(env, aid, fp), limits(env)) as observation:
        response = submit(env, aid, column="missing")
        assert response.status_code == 200 and response.json()["status"] == "FAILED"
        assert observation.writes_executed == 0 and observation.failed_previews_skipped == 1
    assert readback(env) == ([], [])
    assert_production_unchanged(env, before)


def test_fixture_rejects_production_mode_before_setup_or_hook(env, tmp_path, monkeypatch):
    aid, fp, *_ = seed(env)
    before = production_bytes(env[0])
    monkeypatch.setattr(env[0], "test_only", False)
    with pytest.raises(DomainError, match="explicit test Store"):
        with controlled_writer(env[0], tmp_path, target(env, aid, fp), limits(env)):
            pass
    assert submit(env, aid).status_code == 200
    assert_production_unchanged(env, before)


def test_fixture_rejects_wrong_temporary_path_or_shared_pg_schema(env, tmp_path):
    aid, fp, *_ = seed(env)
    before = production_bytes(env[0])
    store = env[0]
    original = store.engine
    try:
        if store.sqlite:
            root = tmp_path / "not-the-db-root"
        else:
            store.engine = original.execution_options(schema_translate_map={None: "public"})
            root = tmp_path
        with pytest.raises(DomainError, match="isolated"):
            with controlled_writer(store, root, target(env, aid, fp), limits(env)):
                pass
    finally:
        store.engine = original
    assert_production_unchanged(env, before)
