"""Strict synthetic snapshot oracle for one versioned local-record control chain."""

import math
import re

from sim2act.db import fingerprint


def assert_control_changes(before, after, rid, *, probe_worker_id=None, time_bounds=None):
    assert before.keys() == after.keys()
    mutable = {"runs", "internal_app_runs", "events", "heartbeats"}
    for table in before:
        if table not in mutable:
            assert before[table] == after[table], table
    original = next(row for row in before["runs"] if row["id"] == rid)
    assert original["status"] == "QUEUED" and original["version"] == 1
    assert {row["id"]: row for row in after["runs"]} == {
        row["id"]: ({**row, "status": "CANCELLED", "version": row["version"] + 3, "cancel_intent": True}
            if row["id"] == rid else row) for row in before["runs"]}
    binding = next(row for row in before["internal_run_bindings"] if row["run_id"] == rid)
    aid = binding["app_run_id"]
    assert {row["id"]: row for row in after["internal_app_runs"]} == {
        row["id"]: ({**row, "status": "CANCELLED"} if row["id"] == aid else row)
        for row in before["internal_app_runs"]}
    old_events = {row["id"]: row for row in before["events"]}
    assert all(row == old_events[row["id"]] for row in after["events"] if row["id"] in old_events)
    assert old_events.keys() <= {row["id"] for row in after["events"]}
    added = [row for row in after["events"] if row["id"] not in old_events]
    assert len(added) == 3 and {row["run_id"] for row in added} == {rid}
    assert all(row["kind"] == "COMMAND" for row in added)
    assert sorted((row["data"]["command"], row["data"]["status"]) for row in added) == sorted([
        ("pause", "PAUSED"), ("resume", "QUEUED"), ("cancel", "CANCELLED")])
    assert all(set(row["data"]) == {"command", "status"} for row in added)
    old_heartbeats = {row["id"]: row for row in before["heartbeats"]}
    current_heartbeats = {row["id"]: row for row in after["heartbeats"]}
    assert old_heartbeats.keys() <= current_heartbeats.keys()
    assert all(current_heartbeats[key] == row for key, row in old_heartbeats.items())
    new_heartbeats = [row for row in after["heartbeats"] if row["id"] not in old_heartbeats]
    assert len(new_heartbeats) == 1
    heartbeat = new_heartbeats[0]
    assert set(heartbeat) == {"id", "at"} and re.fullmatch(r"worker_[a-f0-9]{32}", heartbeat["id"])
    assert isinstance(heartbeat["at"], (int, float)) and math.isfinite(heartbeat["at"])
    if probe_worker_id is not None:
        assert heartbeat["id"] == probe_worker_id
    if time_bounds is not None:
        assert time_bounds[0] <= heartbeat["at"] <= time_bounds[1]
    return dict(original_run=original, final_run=next(row for row in after["runs"] if row["id"] == rid),
        command_events=added, probe_heartbeat=heartbeat, probe_worker_id_captured=probe_worker_id is not None,
        changed_tables=[name for name in before if before[name] != after[name]],
        database_before_fingerprint=fingerprint(before), database_after_fingerprint=fingerprint(after),
        other_tables_unchanged=len(before) - len(mutable), old_rows_preserved=True,
        page_post_count=3, page_worker_calls=0, worker_probes=1, worker_claims=0, model_calls=0)
