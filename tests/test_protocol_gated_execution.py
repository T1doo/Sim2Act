"""Complete bounded package: exact-wire gates and experiment share actual store path."""

import importlib.util
import json
import os
import socket
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "gated_protocol_demo", Path(__file__).parents[1] / "scripts/protocol-store-dryrun.py"
)
assert SPEC and SPEC.loader
DEMO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEMO)


def assert_report(report, calls, completed):
    assert report["mock_calls"] == report["attempt_count"] == calls
    assert report["experiment"]["requests"] == report["experiment"]["settled"] == calls
    assert report["experiment"]["status"] == ("COMPLETED" if completed else "STOPPED")
    assert report["external_requests"] == report["live_budget"] == 0
    assert report["owner_acceptance"] == "PENDING"
    assert report["slot_attempt_bijection"]
    assert report["request_bounds"]["max_chars"] <= 8000
    assert report["request_bounds"]["max_bytes"] <= 10000
    for family in ("a", "b"):
        source_id = f"protocol.synthetic.{family}-source.v1"
        answer = DEMO.evaluation_contract(source_id)[0]["expected_output"]
        for request in report["wire"]:
            DEMO.assert_isolated_wire(request["body"], answer=answer)
            encoded = json.dumps(request["body"])
            assert '"gold_sha256"' not in encoded and '"rubric_sha256"' not in encoded
            assert '"max_tokens": 1024' in encoded and '"stream": false' in encoded
    if completed:
        assert report["experiment"]["accepted_stages"] == 6


@pytest.mark.parametrize("fail_source,calls", [(None, 8), ("a", 2), ("b", 6)])
def test_whole_package_zero_network(monkeypatch, fail_source, calls):
    def forbidden(*args, **kwargs):
        pytest.fail("Gated mock package attempted socket connection")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    report = DEMO.demonstrate(experiment=True, fail_source=fail_source)
    assert_report(report, calls, fail_source is None)
    assert report["backend"] == "sqlite"


def test_whole_package_actual_postgresql_two_forms():
    url = os.environ.get("SIM2ACT_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Explicit isolated PostgreSQL required for full gated controller package")
    report = DEMO.demonstrate(experiment=True, database_url=url)
    assert_report(report, 8, True)
    assert report["backend"] == "postgresql"


@pytest.mark.parametrize("mutation", ["parameters", "witness", "coherent_numeric_types"])
def test_complete_durable_wire_tamper_never_reaches_transport(monkeypatch, mutation):
    import copy

    import httpx
    from sqlalchemy import select, update

    from sim2act.db import attempts, events
    from sim2act.worker import Worker

    reserve = Worker.reserve
    transport = httpx.MockTransport.handle_request
    sent = []

    def observed(self, request):
        sent.append(request.content)
        return transport(self, request)

    def altered(worker, rid, fence, context, **kwargs):
        aid = reserve(worker, rid, fence, context, **kwargs)
        with worker.store.tx() as c:
            parameters = copy.deepcopy(
                c.execute(select(attempts.c.parameters).where(attempts.c.id == aid)).scalar_one()
            )
            row = (
                c.execute(
                    select(events).where(
                        events.c.run_id == rid, events.c.kind == "PROTOCOL_WIRE_RESERVED"
                    )
                )
                .mappings()
                .one()
            )
            witness = copy.deepcopy(row["data"])
            if mutation == "parameters":
                parameters["protocol_wire"]["sha256"] = "0" * 64
            elif mutation == "witness":
                witness["wire"]["sha256"] = "0" * 64
            else:
                parameters["protocol_wire"]["bytes"] = float(parameters["protocol_wire"]["bytes"])
                witness["wire"]["bytes"] = float(witness["wire"]["bytes"])
                witness["fence"] = True
            c.execute(update(attempts).where(attempts.c.id == aid).values(parameters=parameters))
            c.execute(update(events).where(events.c.id == row["id"]).values(data=witness))
        return aid

    monkeypatch.setattr(Worker, "reserve", altered)
    monkeypatch.setattr(httpx.MockTransport, "handle_request", observed)
    with pytest.raises(AssertionError) as exc:
        DEMO.demonstrate(experiment=True)
    assert "VERSION_CONFLICT" in str(exc.value) and sent == []
