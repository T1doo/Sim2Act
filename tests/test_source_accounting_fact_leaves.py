"""Synthetic fact units, not a successful Source/approval or full P-B trial."""

import base64
import copy
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, insert, select
from test_natural_spec_apps import recipe
from test_pb_live_source_contract import material

from sim2act import natural_source_archives as archive
from sim2act import natural_specs as natural
from sim2act import pa_spec_apps as spec
from sim2act import pa_trial_dispatch as trial
from sim2act import pb_natural_specs as pb
from sim2act.contracts import GoalCardRunSource, Limits
from sim2act.db import attempts, events, fingerprint, new_id, run_contracts, runs
from sim2act.errors import DomainError
from sim2act.goal_applications import response_archive
from sim2act.model import normalize_usage
from sim2act.text_logic_reuse import remember


def failure(call):
    with pytest.raises(DomainError) as denied:
        call()
    return denied.value.public()


@pytest.fixture
def facts(env):
    """Actual SQLite archive pairs, with no Worker, approval, ledger permit or send."""
    store, _, _, user, _, pid, _ = env
    job = dict(id=new_id("run"), principal_id=user, project_id=pid,
        runtime_id="synthetic-app-runtime", status="QUEUED", request_key="synthetic-archive-unit")
    contract = SimpleNamespace(model="intern-s2", caps=SimpleNamespace(max_output_tokens=32))
    ledger, exchanges = {"slots": []}, []
    with store.tx() as c:
        c.execute(insert(runs).values(**job))
        c.execute(insert(run_contracts).values(run_id=job["id"], snapshot={"mode": "mock"},
            fingerprint=fingerprint({"mode": "mock"})))
        for index in range(2):
            aid = new_id("attempt")
            wire = json.dumps(dict(model=contract.model, stream=False, max_tokens=16,
                messages=[dict(role="user", content=f"合成事实 {index}")]), ensure_ascii=False).encode()
            parsed = dict(model=contract.model, usage=dict(prompt_tokens=4, completion_tokens=2,
                total_tokens=6), value=f"原始字节 {index}")
            received = (json.dumps(parsed, ensure_ascii=False, indent=2) + "\n").encode()
            original, canonical = response_archive(parsed)
            request = archive._body(job, aid, wire, True, None, archive.REQUEST)
            response = archive._body(job, aid, received, True, canonical["sha256"], archive.RESPONSE)
            row = dict(id=aid, run_id=job["id"], mode="MOCK", status="VERIFIED",
                request_model=contract.model, response_model=contract.model,
                reserved_tokens=len(wire) + 16, parameters=dict(max_tokens=16,
                    natural_spec_wire=dict(sha256=request.sha256, bytes=len(wire), characters=len(wire.decode())),
                    natural_spec=dict(fence=2, run_version=1, operation_id=f"synthetic-op-{index}")),
                response=dict(received_raw=original, raw_evidence=canonical), usage=normalize_usage(parsed))
            c.execute(insert(attempts).values(**row))
            for kind, body in ((archive.REQUEST, request), (archive.RESPONSE, response)):
                remember(c, user, job["id"], kind, aid, body, body.model_dump())
                store.event(c, job["id"], "NS_WIRE_ARCHIVED" if kind == archive.REQUEST else "NS_BODY_ARCHIVED",
                    dict(attempt_id=aid, archive_fingerprint=fingerprint(body.model_dump())))
            slot = dict(reservation=dict(stage="source", request_key=aid,
                wire_sha256=request.sha256, wire_bytes=len(wire)), accepted=True,
                settlement=dict(response_sha256=canonical["sha256"], response_ascii_bytes=canonical["bytes"],
                    **parsed["usage"]))
            ledger["slots"].append(slot)
            exchanges.append(SimpleNamespace(row=row, slot=slot, request=request, wire=wire,
                response=response, received=received, parsed=parsed, canonical=canonical))
    return SimpleNamespace(store=store, user=user, job=job, contract=contract,
        ledger=ledger, exchanges=exchanges)


def test_sqlite_archive_bytes_order_keys_and_complete_multisets(facts, tmp_path):
    f = facts
    ledger = {"slots": list(reversed(f.ledger["slots"]))}
    with f.store.tx() as c:
        requests, responses, public = archive._source_bodies(c, f.user, f.contract, f.job, ledger)
        assert requests == [e.wire for e in reversed(f.exchanges)]
        assert responses == [e.received for e in reversed(f.exchanges)]
        assert [p["attempt_id"] for p in public] == [e.row["id"] for e in reversed(f.exchanges)]
        for e in f.exchanges:
            body, payload = archive._read(c, f.user, f.job, e.row["id"], archive.RESPONSE)
            anchors = [dict(attempt_id=e.row["id"], archive_fingerprint=fingerprint(body.model_dump()))]
            assert archive._body_payload_from_facts(body, anchors, e.row["id"]) == payload == e.received
            assert body.sha256 != body.canonical_sha256
            assert archive._source_exchange_from_facts(f.contract, e.row, e.slot, e.request,
                e.wire, body, payload, False) == e.canonical
        malformed = {"slots": [*ledger["slots"], ledger["slots"][0]]}
        error = failure(lambda: archive._source_bodies(c, f.user, f.contract, f.job, malformed))
        rows = c.execute(select(attempts).where(attempts.c.run_id == f.job["id"])).mappings().all()
        assert error == failure(lambda: archive._source_slots_from_facts(rows, malformed, False))
        assert error["code"] == "VERSION_CONFLICT"
        ids = {e.row["id"] for e in f.exchanges}
        for keys, code in ((set(), "OUTCOME_UNKNOWN"), (ids | {"foreign"}, "VERSION_CONFLICT")):
            assert failure(lambda keys=keys: archive._source_keys_from_facts(ids, keys))["code"] == code
    (tmp_path / "synthetic-byte-facts.json").write_text(json.dumps(dict(
        synthetic_only=True, successful_source_claim=False, actual_sqlite_pair_reads=True,
        raw_bytes_preserved=True, raw_and_canonical_distinct=True, ledger_order_preserved=True,
        complete_history_cardinality_refused=True, real_model_calls=0), indent=2))


@pytest.mark.parametrize("damage", ["missing_anchor", "duplicate_anchor", "incomplete", "encoding"])
def test_body_tail_preserves_unknown_corrupt_and_complete_anchor_errors(facts, damage):
    f, e = facts, facts.exchanges[0]
    body = e.response
    with f.store.tx() as c:
        if damage.endswith("anchor"):
            event = dict(c.execute(select(events).where(events.c.run_id == f.job["id"],
                events.c.kind == "NS_BODY_ARCHIVED",
                events.c.data["attempt_id"].as_string() == e.row["id"])).mappings().one())
            if damage == "missing_anchor":
                c.execute(delete(events).where(events.c.id == event["id"]))
                anchors = []
            else:
                c.execute(insert(events).values(**{**event, "id": new_id("event")}))
                anchors = [event["data"], event["data"]]
            assert failure(lambda: archive._read(c, f.user, f.job, e.row["id"], archive.RESPONSE)) == failure(
                lambda: archive._body_payload_from_facts(body, anchors, e.row["id"]))
        else:
            body = body.model_copy(update={"received_complete": False, "extent": "RECEIVED_PREFIX"}
                if damage == "incomplete" else {"body_b64": "!!!!"})
            anchors = [dict(attempt_id=e.row["id"], archive_fingerprint=fingerprint(body.model_dump()))]
            error = failure(lambda: archive._body_payload_from_facts(body, anchors, e.row["id"]))
            assert error["code"] == ("OUTCOME_UNKNOWN" if damage == "incomplete" else "VERSION_CONFLICT")


def test_exchange_and_accounting_keep_usage_wire_caps_and_ns_controller_bytes(facts):
    f, e = facts, facts.exchanges[0]
    identity = SimpleNamespace(stage="source", run_id=f.job["id"], attempt_id=e.row["id"],
        wire_sha256=e.request.sha256, wire_bytes=len(e.wire), fence=2, version=1)
    slot = SimpleNamespace(identity=identity, settlement=SimpleNamespace(**e.parsed["usage"]))
    capture = SimpleNamespace(raw_sha256=e.response.sha256,
        body_b64=base64.b64encode(e.received).decode(), canonical_sha256=e.canonical["sha256"])
    binding = SimpleNamespace(contract=f.contract)
    trial._journal_attempt_from_facts(binding, e.wire, slot, e.row)
    trial._stage_usage_from_facts(e.row, "source", slot, e.parsed, e.row)
    trial._stage_source_archive_from_facts(e.row, e.response, e.received, e.wire, slot, capture, e.parsed)
    # A raw hash cannot stand in for canonical ASCII, or vice versa.
    production_slot = copy.deepcopy(e.slot)
    production_slot["settlement"]["response_sha256"] = e.response.sha256
    assert archive._source_exchange_from_facts(f.contract, e.row, production_slot, e.request,
        e.wire, e.response, e.received, True) == e.canonical
    assert failure(lambda: archive._source_exchange_from_facts(f.contract, e.row, e.slot,
        e.request, e.wire, e.response, e.received, True))["code"] == "VERSION_CONFLICT"
    bad_usage = copy.deepcopy(e.row)
    bad_usage["usage"]["tokens"]["completion_tokens"] += 1
    assert failure(lambda: trial._stage_usage_from_facts(bad_usage, "source", slot,
        e.parsed, bad_usage))["code"] == "VERSION_CONFLICT"
    lower = SimpleNamespace(model=f.contract.model, caps=SimpleNamespace(max_output_tokens=15))
    assert failure(lambda: trial._journal_attempt_from_facts(SimpleNamespace(contract=lower),
        e.wire, slot, e.row))["code"] == "VERSION_CONFLICT"
    assert failure(lambda: trial._stage_source_archive_from_facts(e.row, e.response,
        e.received + b" ", e.wire, slot, capture, e.parsed))["code"] == "VERSION_CONFLICT"
    slots = [SimpleNamespace(identity=SimpleNamespace(stage="source", run_id=f.job["id"],
        attempt_id=x.row["id"])) for x in f.exchanges]
    state = SimpleNamespace(slots=slots, halted=False)
    trial._stage_slots_from_facts(state, [x.row for x in f.exchanges], f.job["id"], "source")
    assert failure(lambda: trial._stage_slots_from_facts(state,
        [x.row for x in f.exchanges] + [e.row], f.job["id"], "source"))["code"] == "VERSION_CONFLICT"


def test_review_source_target_order_complete_result_and_distinct_limits(monkeypatch):
    target, old = material(2), material(1)
    goal = GoalCardRunSource(card_id=target.card_id, version=target.goal_version,
        fingerprint=target.goal_fingerprint, snapshot=target.goal_snapshot.model_dump())
    actual_material = dict(resource_id=target.resource_id, hash=target.source_hash,
        content=target.content, format="txt")
    approved = Limits(max_requests=2, max_tools=4, max_repairs=1,
        max_total_tokens=64000, max_output_tokens=1024, run_seconds=300)
    platform = approved.model_copy(update={"max_requests": 4})
    graph = recipe("ordered")
    proof = dict(recipe_fingerprint=fingerprint(graph), output_fingerprint="a" * 64,
        runtime_audit_fingerprint="b" * 64, source_run_id="run_" + "4" * 32)
    body = pb.ReviewInput(source_run_id=proof["source_run_id"],
        expected_source_proof_fingerprint=fingerprint(proof), expected_source_recipe_fingerprint=fingerprint(graph),
        card_id=goal.card_id, expected_goal_version=goal.version, expected_goal_fingerprint=goal.fingerprint,
        expected_source_hash=target.source_hash, recipe=graph, name="Synthetic fact review", request_key="facts-review")
    binding = dict(goal=dict(card_id=old.card_id), source=dict(resource_id=old.resource_id, hash=old.source_hash),
        draft=dict(candidate=dict(spec_recipe=graph, manifest=dict(runtime_limits=approved.model_dump()))))
    trace = []
    monkeypatch.setattr(pb, "source", lambda *a: (trace.append("source") or (binding, proof)))
    monkeypatch.setattr(spec, "target", lambda *a, **k: (trace.append("target") or (actual_material, goal)))
    roles = []
    original_candidate, original_compile = pb.candidate, natural.compile_candidate
    def candidate(*args):
        roles.append(("inherited", args[-1].model_dump()))
        return original_candidate(*args)
    def compile_candidate(value, limits):
        roles.append(("compile", limits.model_dump()))
        return original_compile(value, limits)
    monkeypatch.setattr(pb, "candidate", candidate)
    monkeypatch.setattr(natural, "compile_candidate", compile_candidate)
    complete = pb.review(None, None, "synthetic-user", "proj_" + "1" * 32, body, platform)
    pb._review_source_from_facts(body, proof)
    assert complete == pb._review_from_facts("synthetic-user", "proj_" + "1" * 32,
        body, platform, binding, proof, actual_material, goal)
    assert complete[0]["approved_source_limits"] == approved.model_dump()
    # Existing expand derives zero candidate repairs; it does not overwrite the
    # inherited source approval or substitute it for caller compilation Limits.
    assert complete[0]["candidate"]["manifest"]["runtime_limits"] == {
        **approved.model_dump(), "max_repairs": 0}
    assert roles[:2] == [("inherited", approved.model_dump()), ("compile", platform.model_dump())]
    assert trace == ["source", "target"]
    trace.clear()
    broken = body.model_copy(update={"expected_source_proof_fingerprint": "f" * 64})
    assert failure(lambda: pb.review(None, None, "synthetic-user", "proj_" + "1" * 32,
        broken, platform)) == failure(lambda: pb._review_source_from_facts(broken, proof))
    assert trace == ["source"], "A source mismatch must not read the target"


def test_source_proof_prefix_hashes_precede_fresh_audit(monkeypatch):
    trace = []
    draft = dict(id="app-facts", fingerprint="d" * 64, candidate=dict(spec_recipe={"full": ["recipe"]}))
    snap = dict(instance_id="instance", release_id="release")
    app_run = dict(id="app-run", result_version=1, output={"full": ["output"]})
    binding = dict(draft=draft, snapshot=snap, app_run=app_run,
        release=dict(fingerprint="e" * 64), goal=dict(fingerprint="f" * 64),
        source=dict(hash="a" * 64), audit_fingerprint="b" * 64)
    job, typed, proved = {"id": "run-facts"}, {"full": ["typed"]}, [{"full": "receipt"}]
    prefix = pb._source_proof_fields("user", "project", job["id"], binding,
        draft, snap, app_run, job, typed, proved)
    assert prefix["typed_fingerprint"] == fingerprint(typed)
    assert "runtime_audit_fingerprint" not in prefix
    class Result:
        def __init__(self, value): self.value = value
        def scalar_one(self): return self.value
        def mappings(self): return self
        def one(self): return self.value
    class Connection:
        def __init__(self): self.items = ["SUCCEEDED", job, typed]
        def execute(self, statement):
            trace.append("select")
            return Result(self.items.pop(0))
    monkeypatch.setattr(pb, "source_gate", lambda *a: trace.append("gate"))
    monkeypatch.setattr(spec, "verify_job", lambda *a, **k: (trace.append("verify") or (binding, None, proved)))
    monkeypatch.setattr(natural, "is_candidate", lambda *a: True)
    def audit(*a):
        trace.append("audit")
        # Old prefix hashes were already computed before this callback.
        app_run["output"] = {"changed": True}
        return "c" * 64
    monkeypatch.setattr(pb, "source_audit", audit)
    result = pb._source(None, Connection(), "user", "project", job["id"], None)
    assert result == (binding, {**prefix, "runtime_audit_fingerprint": "c" * 64,
        "citation_status": "PASS", "semantic_status": "UNKNOWN", "owner_acceptance": "PENDING"})
    assert trace == ["gate", "select", "select", "verify", "select", "audit"]
