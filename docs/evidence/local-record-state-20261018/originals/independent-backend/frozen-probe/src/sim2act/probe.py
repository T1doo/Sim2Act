"""Repeatable offline capability probe; it never loads secrets or opens a live connection."""

import json
import tempfile
from dataclasses import replace
from pathlib import Path

import httpx
from sqlalchemy import select

from .config import Settings
from .db import Store, attempts, operations
from .errors import DomainError
from .model import (
    MODEL_IDENTITY_POLICY_VERSION,
    InternModel,
    MockModel,
    parse_response,
    require_returned_model,
    returned_model_identity,
)
from .worker import Worker


def parse_model_list(raw):
    if (
        not isinstance(raw, dict)
        or raw.get("object") != "list"
        or not isinstance(raw.get("data"), list)
    ):
        raise DomainError("MODEL_OUTPUT_INVALID", "Model list is malformed")
    entries = []
    for row in raw["data"]:
        if (
            not isinstance(row, dict)
            or row.get("object") != "model"
            or not isinstance(row.get("id"), str)
        ):
            raise DomainError("MODEL_OUTPUT_INVALID", "Model entry is malformed")
        entries.append(
            {
                "id": row["id"],
                "ref_model": row.get("ref_model")
                if isinstance(row.get("ref_model"), str)
                else None,
            }
        )
    return entries


def offline_probe():
    with tempfile.TemporaryDirectory(prefix="sim2act-probe-") as directory:
        s = Settings("sqlite:///" + str(Path(directory) / "probe.db"), Path(directory), mode="mock")
        store = Store(s.database_url, test_only=True)
        store.initialize()
        owner = store.user("SYNTHETIC PROBE", "synthetic-probe-identity")
        project = store.project(owner, "synthetic capability probe")
        resource = store.resource(owner, project, "probe.txt", "txt", "synthetic authorized input")
        calls = []
        synthetic = MockModel()

        def transport(request):
            if str(request.url) != "https://chat.intern-ai.org.cn/api/v1/chat/completions":
                raise AssertionError("Offline probe does not allow other requests")
            body = json.loads(request.content)
            calls.append(
                {"model": body["model"], "stream": body["stream"], "max_tokens": body["max_tokens"]}
            )
            raw = synthetic.request(body["messages"], body["tools"])
            raw["model"] = (
                "Intern-S2"  # Synthetic reproduction of independently observed wire name.
            )
            require_returned_model(returned_model_identity(body["model"], raw["model"]))
            return httpx.Response(200, json=raw)

        wire_settings = replace(s, mode="live", live_enabled=True, token="SYNTHETIC_OFFLINE_ONLY")
        adapter = InternModel(wire_settings, httpx.MockTransport(transport))
        rid = store.submit(
            owner,
            project,
            "Read synthetic material and revise from tool feedback",
            [resource],
            "offline-probe",
        )
        Worker(store, s, adapter).once()
        result = store.inspect(owner, rid)
        assert result["status"] == "PARTIAL"
        with store.engine.connect() as c:
            audit = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all()
            receipts = (
                c.execute(
                    select(operations.c.id).where(
                        operations.c.run_id == rid, operations.c.status == "VERIFIED"
                    )
                )
                .scalars()
                .all()
            )
        failures = []
        for finish in ["length", None]:
            try:
                parse_response(
                    {
                        "choices": [
                            {
                                "finish_reason": finish,
                                "message": {"role": "assistant", "content": "synthetic incomplete"},
                            }
                        ]
                    }
                )
            except DomainError as e:
                failures.append({"injection": str(finish), "error": e.code, "result": "PASS"})
        model_list = parse_model_list(
            {
                "object": "list",
                "data": [{"object": "model", "id": "intern-s2", "ref_model": "intern-s2"}],
            }
        )
        report = {
            "report_version": "F1-2",
            "mode": "MOCK / FAULT_INJECTION",
            "network": "httpx.MockTransport only; no external request",
            "live_status": "BLOCKED",
            "live_reason": "No confirmed safe injection or approved budget",
            "native_windows": "BLOCKED",
            "request_model": "intern-s2",
            "model_identity_policy_version": MODEL_IDENTITY_POLICY_VERSION,
            "returned_model_identities": [
                (a["parameters"] or {}).get("model_identity") for a in audit
            ],
            "weight_version": "unknown",
            "model_list": {"provenance": "SYNTHETIC", "entries": model_list},
            "wire_requests": calls,
            "run_id": rid,
            "operation_ids": receipts,
            "attempt_modes": [a["mode"] for a in audit],
            "usage": [a["usage"] for a in audit],
            "tool_feedback_revision": "PASS (MOCK)",
            "malformed_responses": failures,
            "goal_acceptance": "NOT_RUN",
        }
        store.engine.dispose()
        return report
