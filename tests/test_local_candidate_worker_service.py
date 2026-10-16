"""Script service contract only. No real lease/clock fault or natural recovery."""

import copy
from types import SimpleNamespace

import pytest
from test_local_candidate_demo import demo


class Stop:
    def __init__(self):
        self.stopped, self.waits = False, []

    def is_set(self):
        return self.stopped

    def set(self):
        self.stopped = True

    def wait(self, seconds):
        self.waits.append(seconds)  # Unit service scheduling, no sleeping.


def fixture(monkeypatch, actions):
    clock = [100.0]
    monkeypatch.setattr(demo, "time", SimpleNamespace(time=lambda: clock[0]))
    header = dict(id="synthetic-run", principal_id="synthetic-user", project_id="synthetic-project",
                  created_at=100.0, deadline=400.0, status="QUEUED", fence=0, lease_until=0,
                  unexpected_active_run_ids=[], service_claimed_run_ids=[])
    observed, calls = [], []

    def once():
        calls.append(len(calls) + 1)
        action = actions[len(calls) - 1]
        if isinstance(action, Exception):
            raise action
        claimed, changes = action
        header.update(changes)
        if claimed:
            header["service_claimed_run_ids"] = [header["id"]]
        return claimed

    worker = SimpleNamespace(s=SimpleNamespace(run_seconds=300), stop=Stop(), once=once)
    return worker, header, clock, observed, calls


def test_progress_true_and_idle_false_both_require_actual_target_terminal(monkeypatch):
    worker, header, _, observed, calls = fixture(monkeypatch, [
        (True, dict(status="RUNNING", fence=1, lease_until=130)),
        (False, {}),
        (True, dict(status="SUCCEEDED", fence=3, lease_until=0)),
    ])
    result = demo.serve_accepted_run(worker, lambda: dict(header), lambda rows: observed.append(copy.deepcopy(rows)))
    assert result["status"] == "SUCCEEDED" and calls == [1, 2, 3]
    assert [row["claimed_work"] for row in observed[-1]] == [True, False, True]
    assert [row["after"]["fence"] for row in observed[-1]] == [1, 1, 3]
    assert all(row["after"]["created_at"] == 100 and row["after"]["deadline"] == 400 for row in observed[-1])
    assert worker.stop.waits == [1.0, 1.0] and worker.stop.is_set()


@pytest.mark.parametrize("status", ["WAITING_RESOURCE", "RECONCILING", "PAUSED", "FAILED", "CANCELLED"])
def test_blocked_unknown_or_failed_result_never_resumed_or_retried(monkeypatch, status):
    worker, header, _, observed, calls = fixture(monkeypatch, [(True, dict(status=status, fence=1))])
    with pytest.raises(RuntimeError, match="blocked or stopped"):
        demo.serve_accepted_run(worker, lambda: dict(header), lambda rows: observed.append(copy.deepcopy(rows)))
    assert calls == [1] and worker.stop.waits == [] and worker.stop.is_set()
    assert observed[-1][0]["after"]["status"] == status


def test_original_deadline_stops_service_without_a_new_business_interval(monkeypatch):
    worker, header, clock, _, calls = fixture(monkeypatch, [(True, dict(status="RUNNING", fence=1))])
    header["deadline"] = 101
    def observe(_rows):
        clock[0] = 102
    with pytest.raises(RuntimeError, match="Original accepted Run deadline"):
        demo.serve_accepted_run(worker, lambda: dict(header), observe)
    assert calls == [1] and header["created_at"] == 100 and header["deadline"] == 101
    assert worker.stop.is_set()


def test_changed_accepted_clock_is_rejected_even_if_result_claims_success(monkeypatch):
    worker, header, _, _, calls = fixture(monkeypatch, [
        (True, dict(status="SUCCEEDED", created_at=110, deadline=410)),
    ])
    with pytest.raises(RuntimeError, match="identity or deadline changed"):
        demo.serve_accepted_run(worker, lambda: dict(header), lambda _rows: None)
    assert calls == [1] and worker.stop.is_set()


def test_unexpected_worker_error_is_recorded_and_never_restarted(monkeypatch):
    worker, header, _, observed, calls = fixture(monkeypatch, [RuntimeError("synthetic driver fault")])
    with pytest.raises(RuntimeError, match="synthetic driver fault"):
        demo.serve_accepted_run(worker, lambda: dict(header), lambda rows: observed.append(copy.deepcopy(rows)))
    assert calls == [1] and worker.stop.is_set()
    assert observed[-1][0]["error"] == "synthetic driver fault"


def test_real_worker_service_uses_original_csv_contract_and_records_claim(env, tmp_path):
    store, settings, client, _, _, project, resource = env
    driver = demo.Demo(store, settings, client, tmp_path)
    draft = driver.request("POST", f"/api/projects/{project}/apps/csv-preview",
        dict(name="Synthetic service CSV", resource_id=resource, goal="sum amount"), 201)
    _, release, instance = driver.release(draft["id"], dict(column="amount"))
    queued = driver.request("POST", f"/api/internal/instances/{instance['id']}/runs", dict(
        expected_release_fingerprint=release["fingerprint"], expected_revision=instance["revision"],
        input=dict(column="amount"), request_key="real-service-csv"), 202)
    result = driver.serve_run(queued["run_id"])
    assert result["status"] == "SUCCEEDED"
    receipt = driver.claims[0]
    assert receipt["claim_count"] == receipt["fence"] == receipt["service_turns"] == 1
    assert [event["kind"] for event in receipt["service_ledger"]] == ["CLAIMED"]


def test_other_queued_run_is_never_executed_by_target_service(env, tmp_path):
    from sqlalchemy import select

    from sim2act.db import events, runs

    store, settings, client, _, _, project, resource = env
    driver = demo.Demo(store, settings, client, tmp_path)
    draft = driver.request("POST", f"/api/projects/{project}/apps/csv-preview",
        dict(name="Isolated CSV", resource_id=resource, goal="sum amount"), 201)
    _, release, instance = driver.release(draft["id"], dict(column="amount"))
    accepted = []
    for key in ["other-first", "target-second"]:
        accepted.append(driver.request("POST", f"/api/internal/instances/{instance['id']}/runs", dict(
            expected_release_fingerprint=release["fingerprint"], expected_revision=instance["revision"],
            input=dict(column="amount"), request_key=key), 202)["run_id"])
    with pytest.raises(RuntimeError, match="Unexpected active Run"):
        driver.serve_run(accepted[1])
    with store.engine.connect() as connection:
        states = list(connection.execute(select(runs.c.status).where(runs.c.id.in_(accepted))).scalars())
        claims = list(connection.execute(select(events.c.id).where(events.c.run_id.in_(accepted), events.c.kind == "CLAIMED")))
    assert states == ["QUEUED", "QUEUED"] and claims == []
    assert driver.claims[0]["claim_count"] == 0
    assert driver.claims[0]["last_observation"]["unexpected_active_run_ids"] == [accepted[0]]
