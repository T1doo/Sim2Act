"""PREPARED ONLY. Must calibrate the barrier after final source freeze first.

Author helpers construct only new SQLite/MockTransport fixtures. Fault-injected
persisted objects are labeled corruption probes, not valid old Worker evidence.
No real provider/network/PG/installation/browser/socket is used.
"""

import json

import httpx
import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import DatabaseError

from identifier_private_barrier import IdentifierPrivateBarrier, pa_rules
from test_pa_generation_provider import accepted, approved, configured, prepared, provider

from sim2act.db import attempts, fingerprint, grants, meta, run_contracts, runs
from sim2act.errors import DomainError
from sim2act.worker import Worker


def all_rows(store):
    """Global DB content snapshot, called strictly outside installed read barrier."""
    with store.engine.connect() as conn:
        return {table.name: sorted((dict(row) for row in conn.execute(select(table)).mappings()),
                key=lambda row: json.dumps(row, sort_keys=True, default=str)) for table in meta.sorted_tables}


def revoked(data):
    with data[0].tx() as conn:
        conn.execute(update(grants).where(grants.c.resource_id == data[5]).values(revoked=True, revision=2))


def ready(env, monkeypatch):
    data, clock = configured(env, monkeypatch)
    scope, grant, _ = approved(data)
    rid = accepted(data, grant["activation"])
    transport, sent = provider(data, clock)
    assert Worker(data[0], data[1], goal_planner_transport=transport).once()
    response = data[2].get(f"/api/runs/{rid}")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "PARTIAL" and len(sent) == 2
    return data, clock, scope, grant, rid, sent, result


def full_query_fails(store, barrier, sql, params):
    before = len(barrier.blocked)
    with pytest.raises(DatabaseError), store.engine.connect() as conn:
        conn.execute(text(sql), params).all()
    assert len(barrier.blocked) > before, "Calibration must fail on actual protected cell evaluation/explicit main denial"


def test_barrier_calibration_full_cells_alias_in_join_and_exact_identifier_paths(env, monkeypatch):
    """Instrumentation calibration, separate from product-behavior acceptance."""
    data, _, _, _, rid, _, _ = ready(env, monkeypatch)
    store = data[0]
    rule = pa_rules([rid], [data[5]], [data[6]["id"]])
    with IdentifierPrivateBarrier(store, rule) as barrier:
        # Exact bound nested SQLAlchemy projection; returns only ID lists/strings.
        with store.engine.connect() as conn:
            actual = conn.execute(select(
                run_contracts.c.snapshot["goal"]["resource_refs"],
                run_contracts.c.snapshot["resources"][0]["resource_id"].as_string(),
                run_contracts.c.snapshot["source_goal_card"]["snapshot"]["content"]["resource_refs"],
            ).where(run_contracts.c.run_id == rid)).one()
            assert list(actual) == [[data[5]], data[5], [data[5]]]
            # Join/alias/IN metadata path preserves original public shape too.
            assert conn.execute(text("SELECT json_extract(rc.snapshot, '$.runtime_id') FROM run_contracts AS rc JOIN runs AS rr ON rr.id=rc.run_id WHERE rr.id IN (:rid)"), {"rid": rid}).scalar_one().startswith("runtime_")
        assert not barrier.blocked and not barrier.private_evaluated
        assert barrier.identifier_evaluated
        query_cases = [
            ("SELECT snapshot FROM run_contracts WHERE run_id=:rid", {"rid": rid}),
            ("SELECT rc.snapshot FROM run_contracts AS rc JOIN runs AS rr ON rr.id=rc.run_id WHERE rr.id=:rid", {"rid": rid}),
            ("SELECT context FROM runs WHERE id IN (:rid)", {"rid": rid}),
            ("SELECT result FROM runs", {}),
            ("SELECT snapshot FROM goal_card_versions WHERE card_id=:cid", {"cid": data[6]["id"]}),
            ("SELECT content FROM resources WHERE id=:resource", {"resource": data[5]}),
            ("SELECT parameters FROM attempts WHERE run_id=:rid", {"rid": rid}),
            ("SELECT response FROM attempts WHERE run_id=:rid", {"rid": rid}),
            ("SELECT json_extract(snapshot, '$.goal') FROM run_contracts WHERE run_id=:rid", {"rid": rid}),
            ("SELECT json_extract(snapshot, '$.source_goal_card.snapshot.content.goal') FROM run_contracts WHERE run_id=:rid", {"rid": rid}),
            ("SELECT snapshot FROM main.run_contracts WHERE run_id=:rid", {"rid": rid}),
            ("/* leading comment */ WITH ir_private_run_contracts AS (SELECT snapshot FROM main.run_contracts) SELECT snapshot FROM ir_private_run_contracts", {}),
        ]
        for sql, params in query_cases:
            full_query_fails(store, barrier, sql, params)
        assert any(fact.get("table") == "attempts" for fact in barrier.private_evaluated)


def test_revoked_prepare_uses_only_id_projection_before_denial(env, monkeypatch):
    data, _ = configured(env, monkeypatch)
    revoked(data)
    before = all_rows(data[0])
    card = data[6]
    body = dict(card_id=card["id"], expected_version=card["version"], expected_fingerprint=card["fingerprint"],
                generation_request_key="new-exact", request_key="new-scope")
    with IdentifierPrivateBarrier(data[0], pa_rules(resource_ids=[data[5]], card_ids=[card["id"]])) as barrier:
        response = data[2].post(f"/api/projects/{data[4]}/application-provider-scopes", json=body)
        assert response.status_code in {403, 409}, response.text
        assert not barrier.blocked and not barrier.private_evaluated
    assert all_rows(data[0]) == before


@pytest.mark.parametrize("route", ["inspect", "recover", "confirm"])
def test_revoked_cold_scope_routes_deny_before_full_private_cells(env, monkeypatch, route):
    data, _, _, _, rid, _, result = ready(env, monkeypatch)
    revoked(data)
    before = all_rows(data[0])
    with IdentifierPrivateBarrier(data[0], pa_rules([rid], [data[5]], [data[6]["id"]])) as barrier:
        if route == "inspect":
            response = data[2].get(f"/api/runs/{rid}")
        elif route == "recover":
            response = data[2].get(f"/api/projects/{data[4]}/goal-cards/{data[6]['id']}/application-runs", params={"request_key": "exact-generation"})
        else:
            response = data[2].post(f"/api/runs/{rid}/confirm-application-candidate", json={
                "candidate_fingerprint": result["result"]["candidate_fingerprint"],
                "expected_version": result["version"], "name": "must reject revoked source", "request_key": "blocked-confirm"})
        assert response.status_code in {403, 409}, response.text
        assert not barrier.blocked and not barrier.private_evaluated
    assert all_rows(data[0]) == before


def test_stripped_p_a_version_plus_revoke_still_closes_before_body(env, monkeypatch):
    data, _, _, _, rid, _, _ = ready(env, monkeypatch)
    with data[0].tx() as conn:
        saved = conn.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id == rid)).scalar_one()
        saved["application_generation"].pop("version")
        conn.execute(update(run_contracts).where(run_contracts.c.run_id == rid).values(snapshot=saved, fingerprint=fingerprint(saved)))
    revoked(data)
    before = all_rows(data[0])
    with IdentifierPrivateBarrier(data[0], pa_rules([rid], [data[5]], [data[6]["id"]])) as barrier:
        response = data[2].get(f"/api/runs/{rid}")
        assert response.status_code in {403, 409}, response.text
        assert not barrier.blocked and not barrier.private_evaluated
    assert all_rows(data[0]) == before


def test_claim_revoked_queue_writes_metadata_rejection_without_loading_payload(env, monkeypatch):
    data, _ = configured(env, monkeypatch)
    _, grant, _ = approved(data)
    rid = accepted(data, grant["activation"])
    revoked(data)
    with IdentifierPrivateBarrier(data[0], pa_rules([rid], [data[5]], [data[6]["id"]])) as barrier:
        assert data[0].claim("independent-scope-worker", data[1].lease_seconds) is None
        assert not barrier.blocked and not barrier.private_evaluated
    with data[0].tx() as conn:
        status = conn.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one()
        assert status == "FAILED"
        assert not conn.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).first()


def test_finish_revoked_source_denies_before_contract_body_with_zero_write(env, monkeypatch):
    data, _ = configured(env, monkeypatch)
    _, grant, _ = approved(data)
    rid = accepted(data, grant["activation"])
    worker = Worker(data[0], data[1])
    claimed = data[0].claim(worker.id, data[1].lease_seconds)
    assert claimed["id"] == rid
    revoked(data)
    before = all_rows(data[0])
    with IdentifierPrivateBarrier(data[0], pa_rules([rid], [data[5]], [data[6]["id"]])) as barrier:
        with pytest.raises(DomainError):
            worker.finish(rid, claimed["fence"], "FAILED", error={"code": "SYNTHETIC"}, verify_goal_source=True)
        assert not barrier.blocked and not barrier.private_evaluated
    assert all_rows(data[0]) == before


def test_explicit_provider_revoke_forbids_first_confirmation_with_zero_write(env, monkeypatch):
    data, _, scope, _, rid, _, result = ready(env, monkeypatch)
    response = data[2].post(f"/api/application-provider-scopes/{scope['approval_id']}/revoke", json={
        "expected_scope_fingerprint": scope["scope_fingerprint"], "request_key": "explicit-stop", "reason": "synthetic revocation before first app confirmation"})
    assert response.status_code == 200, response.text
    before = all_rows(data[0])
    response = data[2].post(f"/api/runs/{rid}/confirm-application-candidate", json={
        "candidate_fingerprint": result["result"]["candidate_fingerprint"], "expected_version": result["version"],
        "name": "must not mint after explicit withdrawal", "request_key": "stopped-confirm"})
    assert response.status_code == 409, response.text
    assert all_rows(data[0]) == before


def test_unknown_usage_keeps_original_attempt_and_never_resends(env, monkeypatch):
    data, clock = configured(env, monkeypatch)
    _, grant, _ = approved(data)
    rid = accepted(data, grant["activation"])
    transport, sent = provider(data, clock, mutate=lambda raw, stage, payload: raw.pop("usage", None))
    worker = Worker(data[0], data[1], goal_planner_transport=transport)
    assert worker.once()
    assert len(sent) == 1
    original = all_rows(data[0])
    # Original HTTP key recovers an accepted Run; it must not create another send.
    same = accepted(data, grant["activation"])
    assert same == rid
    worker.once()
    with data[0].tx() as conn:
        rows = conn.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all()
        current = conn.execute(select(runs).where(runs.c.id == rid)).mappings().one()
    assert len(rows) == len(sent) == 1 and current["result"] is None
    assert all_rows(data[0])["reservations"] == original["reservations"]


@pytest.mark.parametrize("late", ["lease", "approval"])
def test_terminal_write_window_late_gates_roll_back_partial_and_retain_settlement(env, monkeypatch, late):
    """Synthetic post-STATE clock edge, not the permanently excluded install race."""
    data, clock = configured(env, monkeypatch)
    scope, grant, _ = approved(data)
    rid = accepted(data, grant["activation"])
    transport, sent = provider(data, clock)
    original_event = data[0].event
    armed = []

    def event(conn, run_id, kind, payload):
        original_event(conn, run_id, kind, payload)
        if run_id == rid and kind == "STATE" and payload.get("status") == "PARTIAL":
            armed.append(kind)
            if late == "approval":
                clock["at"] = grant["deadline"]
            else:
                import sim2act.worker as worker_module
                # UPDATE has set live lease to zero. Recover immutable guarded lease
                # from the queued fixture before terminal UPDATE via the spy below.
                monkeypatch.setattr(worker_module.time, "time", lambda: deadline["lease"] + .001)

    original_finish = Worker.finish
    deadline = {}

    def finish(worker, run_id, fence, state, *args, **kwargs):
        if state == "PARTIAL":
            with data[0].engine.connect() as conn:
                deadline["lease"] = conn.execute(select(runs.c.lease_until).where(runs.c.id == rid)).scalar_one()
        return original_finish(worker, run_id, fence, state, *args, **kwargs)

    monkeypatch.setattr(data[0], "event", event)
    monkeypatch.setattr(Worker, "finish", finish)
    Worker(data[0], data[1], goal_planner_transport=transport).once()
    assert armed == ["STATE"] and len(sent) == 2
    with data[0].tx() as conn:
        current = conn.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert current["status"] != "PARTIAL" and current["result"] is None
        from sim2act import generation_approvals as approval
        from sim2act.db import events
        charges, sending, settled = approval.audit(data[0], conn, data[3], scope["approval_id"])
        assert len(charges) == len(sending) == len(settled) == 2
        assert all(conn.execute(select(attempts.c.error).where(attempts.c.id == row.attempt_id)).scalar() is None for row in charges)
        assert not conn.execute(select(events.c.id).where(events.c.run_id == rid, events.c.kind == "STATE", events.c.data["status"].as_string() == "PARTIAL")).first()
        assert conn.execute(select(events.c.id).where(events.c.run_id == rid, events.c.kind == "GA_POST_SETTLEMENT_REJECTION")).first()
