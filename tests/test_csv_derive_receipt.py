"""Exact read-only derive recovery and authorization before journal bodies."""

import json
import re

from sqlalchemy import event
from test_csv_goal_revisions import raw_trace as raw_trace
from test_csv_goal_revisions import ready
from test_spec_app_operations import snapshot

from sim2act.db import fingerprint


def _private_journal_body_select(statement):
    """Recognize actual body projection, not a public identity-only SELECT."""
    sql = re.sub(r'["`\[\]]', "", statement).strip().lower()
    if not re.match(r"^select\b", sql):
        return False
    projection = re.split(r"\bfrom\b", sql, maxsplit=1)[0]
    if re.search(r"\bdelivery_graph_requests\.snapshot\b", projection):
        return True
    # Also catch a future raw SELECT * rather than only SQLAlchemy's explicit
    # column projection. The positive control below exercises the real reader.
    return bool(re.search(
        r"^select\s+(?:\*|(?:[a-z_][a-z_0-9]*\.)?delivery_graph_requests\.\*)"
        r"\s+from\s+(?:[a-z_][a-z_0-9]*\.)?delivery_graph_requests\b", sql
    ))


def _readonly_get(data, url, evidence, label):
    before = snapshot(data[0])
    private_reads = []

    def observe(connection, cursor, statement, parameters, context, executemany):
        if _private_journal_body_select(statement):
            private_reads.append({"sql": statement, "parameters": repr(parameters)})

    # Keep snapshots outside the listener: those intentionally read every table
    # and must never masquerade as endpoint access in the zero-read assertion.
    event.listen(data[0].engine, "before_cursor_execute", observe)
    try:
        response = data[2].get(url)
    finally:
        event.remove(data[0].engine, "before_cursor_execute", observe)
    after = snapshot(data[0])
    evidence[label] = {
        "path": url,
        "status": response.status_code,
        "body": response.json(),
        "private_journal_body_selects": private_reads,
        "database_before_fingerprint": fingerprint(before),
        "database_after_fingerprint": fingerprint(after),
    }
    assert after == before, label
    return response, private_reads


def test_exact_derive_receipt_is_frozen_readonly_and_revocation_precedes_journal_body(env, tmp_path):
    client = env[2]
    original_request = client.request
    accepted_derives = []
    evidence = {"fixture": "ready(env, prior=False)", "worker_started": False, "model_requests": 0}

    def capture_original_derive(method, url, **kwargs):
        response = original_request(method, url, **kwargs)
        if method.upper() == "POST" and str(url).endswith("/delivery-graph/derive"):
            accepted_derives.append({
                "path": str(url), "request": kwargs.get("json"),
                "status": response.status_code, "response": response.json(),
            })
        return response

    try:
        # This creates the actual v1 baseline derive receipt with the existing
        # deterministic CSV helper. No prior business Run or CHECK is executed.
        client.request = capture_original_derive
        try:
            data, aid, base, instance, path, body, value, goal = ready(env)
        finally:
            client.request = original_request
        assert len(accepted_derives) == 1, accepted_derives
        original = accepted_derives[0]
        evidence["actual_original_derive"] = original
        assert original["status"] == 201
        expected_request = {
            "request_key": "baseline",
            "expected_candidate_fingerprint": base["snapshot"]["draft"]["fingerprint"],
        }
        assert original["request"] == expected_request
        assert original["response"]["cached"] is False
        expected_response = {key: val for key, val in original["response"].items() if key != "cached"}
        route = f"/api/projects/{data[5]}/apps/{aid}/delivery-graph/derive-requests/"

        recovered, positive_reads = _readonly_get(data, route + "baseline", evidence, "exact_accepted_key")
        assert recovered.status_code == 200, recovered.text
        assert recovered.json() == {
            "namespace": "delivery-graph-derive-request.v1",
            "principal_id": data[3], "project_id": data[5], "app_id": aid,
            "request_key": "baseline", "request": expected_request,
            "request_fingerprint": fingerprint(expected_request),
            "response": expected_response,
        }
        assert positive_reads, "positive SQL control must observe private journal body loading"

        missing, _ = _readonly_get(data, route + "never-accepted-key", evidence, "missing_original_key")
        assert missing.status_code == 409, missing.text
        assert missing.json()["error"]["code"] == "VERSION_CONFLICT"

        listed = client.get(f"/api/projects/{data[5]}/grants")
        assert listed.status_code == 200, listed.text
        runtime_id = base["snapshot"]["draft"]["runtime_id"]
        matches = [grant for grant in listed.json()
            if grant["principal_id"] == runtime_id and grant["resource_id"] == data[6]
            and grant["tool_ref"] == "resource.read" and not grant["revoked"]]
        assert len(matches) == 1, matches
        grant = matches[0]
        revoked = client.post("/api/grants/" + grant["id"] + "/revoke", json={
            "command": "revoke", "version": grant["revision"],
        })
        evidence["explicit_exact_grant_revocation"] = {
            "grant": grant, "status": revoked.status_code, "body": revoked.json(),
        }
        assert revoked.status_code == 200, revoked.text

        denied, denied_reads = _readonly_get(data, route + "baseline", evidence, "revoked_current_authority")
        assert denied.status_code == 403, denied.text
        assert denied.json()["error"]["code"] in {"PERMISSION_DENIED","GRANT_REVOKED"}
        assert denied_reads == [], denied_reads
    finally:
        client.request = original_request
        (tmp_path / "actual-derive-receipt.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )
