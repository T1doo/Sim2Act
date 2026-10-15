"""Actual offline Worker capture and original-key cold source verification."""

import asyncio
import base64
import copy
import hashlib
import json
import time
from contextlib import contextmanager

import httpx
import pytest
from sqlalchemy import delete, insert, select, update
from test_natural_live_admission import frozen, load_budget
from test_natural_spec_apps import SOURCE, enqueue, ready, recipe, setup, transport
from test_pa_spec_apps import instance

from sim2act import natural_live_admission as gate
from sim2act import natural_source_archives as archive
from sim2act import natural_specs as natural
from sim2act import pb_natural_specs as pb
from sim2act.db import (
    Store,
    attempts,
    delivery_graph_requests,
    events,
    fingerprint,
    grants,
    internal_instance_data,
    internal_instances,
    internal_run_bindings,
    meta,
    reservations,
    runs,
)
from sim2act.errors import DomainError
from sim2act.goal_applications import response_archive
from sim2act.model import normalize_usage
from sim2act.worker import Worker


def snapshot(store):
    with store.tx() as c:
        return {t.name: fingerprint(sorted([dict(r) for r in c.execute(select(t)).mappings()],
                                          key=fingerprint)) for t in meta.sorted_tables}


@contextmanager
def changed(store, table, mutate):
    """Restore only this fixture's explicitly changed primary keys, without SQL hooks."""
    columns = [k.name for k in table.primary_key]
    def key(row):
        return tuple(row[k] for k in columns)
    with store.tx() as c:
        old = {key(r): dict(r) for r in c.execute(select(table)).mappings()}
        mutate(c)
    try:
        yield
    finally:
        with store.tx() as c:
            current = {key(r): dict(r) for r in c.execute(select(table)).mappings()}
            for identity in current.keys() - old.keys():
                c.execute(delete(table).where(*(table.c[k] == v for k, v in zip(columns, identity, strict=True))))
            for identity, row in old.items():
                if identity not in current:
                    c.execute(insert(table).values(**row))
                elif current[identity] != row:
                    c.execute(update(table).where(*(table.c[k] == v for k, v in zip(columns, identity, strict=True)))
                              .values(**row))


def test_actual_worker_to_cold_store_same_trial_archive(env, monkeypatch, tmp_path):
    budget = load_budget()
    data = setup(env)
    store, settings, client, user, pid = data[:5]
    pa, approval = frozen(data, ttl=1200)
    contract = gate.PBTrialContract(**pa.model_dump(), path="P-B",
        extraction_request_key="archive-extraction", extraction_recipe=recipe("ordered"))
    approval = approval.model_copy(update={"expected_contract_fingerprint": fingerprint(contract.model_dump())})
    gate.approve(store, user, contract, approval)
    scope = budget.scope_for(contract, approval.request_key)
    fee = gate.SyntheticOnlyFeeAuthority(fingerprint(contract.model_dump()), contract.quota_subject)
    original_handle = httpx.MockTransport.handle_request
    dispatches = []
    captured = {}

    def admission(*args):
        return gate.admit(*args, fee_authority=fee)

    async def accountable(self, request):
        await request.aread()
        try:
            previous = budget.read(store, user, scope.model_dump())["ledger"]["last_reserved_at"]
        except DomainError as error:
            assert error.code == "VERSION_CONFLICT"
            previous = None
        while previous is not None and time.time() < previous + 60:
            await asyncio.sleep(min(.5, previous + 60 - time.time()))
        with store.tx() as c:
            active = c.execute(select(runs).where(runs.c.status == "RUNNING",
                runs.c.principal_id == user, runs.c.project_id == pid)).mappings().one()
            attempt = c.execute(select(attempts).where(attempts.c.run_id == active["id"],
                attempts.c.status == "STARTED")).mappings().one()
        stage = "generate" if active["runtime_id"] == contract.runtime_id else "source"
        reserved = budget.Reservation(request_key=attempt["id"], stage=stage,
            run_id=active["id"], expected_version=active["version"], fence=active["fence"],
            wire_sha256=hashlib.sha256(request.content).hexdigest(), wire_bytes=len(request.content))
        budget.reserve(store, user, scope, contract, reserved, admission=admission)
        response = original_handle(self, request)
        if stage == "source":
            raw = response.json()
            raw["archive_note"] = "离线原体"
            response = httpx.Response(200, content=(json.dumps(raw, ensure_ascii=False, indent=2) + "\n").encode())
            captured[attempt["id"]] = (request.content, response.content)
        original, evidence = response_archive(response.json())
        assert original is not None and evidence["status"] == "COMPLETE"
        usage = normalize_usage(response.json())
        settled = budget.Settlement(request_key=attempt["id"], response_sha256=evidence["sha256"],
            response_ascii_bytes=evidence["bytes"], **usage["tokens"])
        result = budget.settle(store, user, scope, contract, settled, admission=admission)
        assert result["ledger"]["slots"][-1]["accepted"] is True
        dispatches.append(stage)
        return response

    monkeypatch.setattr(httpx.MockTransport, "handle_async_request", accountable)
    _, _, release, inst, generation_sent = ready(data, style="ordered")
    assert len(generation_sent) == 3
    source_id = enqueue(data, release, inst)
    reviewed = gate.stage_review(store, user, contract, approval.request_key, "source", source_id)
    stage_body = gate.StageApproveInput(authority=gate.StageAuthority.model_validate(reviewed["authority"]),
        expected_authority_fingerprint=reviewed["authority_fingerprint"], approval_key=approval.request_key,
        request_key="archive-source-consent",
        consent="BIND_ONLY_THIS_ACCEPTED_STAGE_RUN_APP_RELEASE_AND_COMPLETE_GOAL_TO_ORIGINAL_TRIAL")
    gate.approve_stage(store, user, contract, stage_body)
    source_sent = []
    assert Worker(store, settings, goal_planner_transport=transport(source_sent, SOURCE)).once()
    assert len(source_sent) == 2 and dispatches == ["generate"] * 3 + ["source"] * 2
    assert client.get("/api/runs/" + source_id).json()["status"] == "SUCCEEDED"
    route = f"/api/projects/{pid}/natural-spec-task-runs/{source_id}"
    options = client.get(route + "/extraction-options").json()
    cold = contract.bindings[1]
    review = dict(source_run_id=source_id,
        expected_source_proof_fingerprint=options["source_proof_fingerprint"],
        expected_source_recipe_fingerprint=options["recipe_fingerprint"],
        card_id=cold.card_id, expected_goal_version=cold.goal_version,
        expected_goal_fingerprint=cold.goal_fingerprint, expected_source_hash=cold.source_hash,
        recipe=contract.extraction_recipe.model_dump(exclude_none=True), name="Archived source",
        request_key=contract.extraction_request_key)
    preview = client.post(route + "/extraction-reviews", json=review)
    assert preview.status_code == 200, preview.text
    made = client.post(route + "/extractions", json=dict(review=review,
        expected_review_fingerprint=preview.json()["review_fingerprint"], consent=pb.CONSENT,
        artifact_write_consent=natural.CONSENT))
    assert made.status_code == 201, made.text
    instance(data, made.json()["id"])
    before = snapshot(store)
    cold_store = Store(settings.database_url, test_only=True)
    try:
        resolved = archive.resolve_trial_source(cold_store, user, contract, approval.request_key)
        receipt = resolved.public_receipt
        assert receipt["verification"] == "ACTUAL_MOCK_ARCHIVE_NOT_LIVE_VERIFIED"
        assert receipt["live_allowed"] is receipt["dispatch_authorized"] is False
        assert receipt["new_model_requests"] == receipt["new_reservations"] == receipt["project_writes"] == 0
        assert receipt["source_run_id"] == source_id and len(receipt["attempts"]) == 2
        for index, item in enumerate(receipt["attempts"]):
            wire, received = captured[item["attempt_id"]]
            assert resolved.request_bodies[index] == wire and resolved.response_bodies[index] == received
            assert item["request_sha256"] == hashlib.sha256(wire).hexdigest()
            assert item["decoded_body_sha256"] == hashlib.sha256(received).hexdigest()
            assert item["decoded_body_sha256"] != item["canonical_ascii_sha256"]
        assert snapshot(store) == before and len(dispatches) == 5
        path = f"/api/projects/{pid}/natural-trials/{contract.trial_key}/approvals/{approval.request_key}/source-archive"
        assert client.get(path).json() == receipt
        assert client.get(path).json() == receipt
        serialized = json.dumps(receipt)
        assert all(k not in serialized for k in ("body_b64", "received_raw", "synthetic-offline-natural-spec", "离线原体"))
        assert snapshot(store) == before
        checks = []

        def refused(label, call):
            baseline = snapshot(store)
            with pytest.raises(DomainError) as failure:
                call()
            assert snapshot(store) == baseline and len(dispatches) == 5
            checks.append(dict(case=label, error=failure.value.code, all_tables_unchanged=True))

        refused("foreign_principal", lambda: archive.resolve_trial_source(cold_store, env[4], contract, approval.request_key))
        refused("wrong_approval_key", lambda: archive.resolve_trial_source(cold_store, user, contract, "wrong-approval"))
        for field, value in (("trial_key", "other-trial"), ("software_fingerprint", "0" * 64),
                             ("extraction_request_key", "other-extraction"), ("extraction_recipe", recipe("single"))):
            altered = contract.model_dump()
            altered[field] = value
            altered = gate.PBTrialContract.model_validate(altered)
            refused("changed_" + field, lambda altered=altered: archive.resolve_trial_source(
                cold_store, user, altered, approval.request_key))

        aid = receipt["attempts"][0]["attempt_id"]
        archive_query = (delivery_graph_requests.c.app_id == source_id,
            delivery_graph_requests.c.principal_id == user, delivery_graph_requests.c.request_key == aid)

        def rewrite_archive(c):
            rows = c.execute(select(delivery_graph_requests).where(*archive_query,
                delivery_graph_requests.c.kind.in_([archive.RESPONSE, archive.RESPONSE + "_seal"]))).mappings().all()
            for row in rows:
                saved = copy.deepcopy(row["snapshot"])
                for side in ("request", "response"):
                    saved[side]["body_b64"] = base64.b64encode(b'{"coordinated":"different"}').decode()
                    saved[side]["byte_count"] = len(b'{"coordinated":"different"}')
                    saved[side]["sha256"] = hashlib.sha256(b'{"coordinated":"different"}').hexdigest()
                c.execute(update(delivery_graph_requests).where(*archive_query,
                    delivery_graph_requests.c.kind == row["kind"]).values(snapshot=saved,
                    fingerprint=fingerprint(saved), request_fingerprint=fingerprint(saved["request"])))

        cases = [
            ("coordinated_archive_without_event", delivery_graph_requests, rewrite_archive),
            ("missing_response_archive", delivery_graph_requests, lambda c: c.execute(
                delete(delivery_graph_requests).where(*archive_query,
                    delivery_graph_requests.c.kind.in_([archive.RESPONSE, archive.RESPONSE + "_seal"])))),
            ("missing_request_seal", delivery_graph_requests, lambda c: c.execute(
                delete(delivery_graph_requests).where(*archive_query,
                    delivery_graph_requests.c.kind == archive.REQUEST + "_seal"))),
            ("unknown_usage", attempts, lambda c: c.execute(update(attempts).where(attempts.c.id == aid)
                .values(usage=dict(status="unknown", tokens=None)))),
            ("label_flip_live", attempts, lambda c: c.execute(update(attempts).where(attempts.c.id == aid).values(mode="LIVE"))),
            ("cancelled_source", runs, lambda c: c.execute(update(runs).where(runs.c.id == source_id).values(cancel_intent=True))),
            ("unknown_source_status", runs, lambda c: c.execute(update(runs).where(runs.c.id == source_id).values(status="RECONCILING"))),
            ("instance_revision", internal_instances, lambda c: c.execute(update(internal_instances)
                .where(internal_instances.c.id == inst["id"]).values(revision=inst["revision"] + 1))),
            ("source_grant_revoked", grants, lambda c: c.execute(update(grants).where(
                grants.c.principal_id == inst["runtime_id"], grants.c.resource_id == data[5]).values(revoked=True))),
        ]
        for label, table, mutate in cases:
            with changed(store, table, mutate):
                refused(label, lambda: archive.resolve_trial_source(cold_store, user, contract, approval.request_key))
            assert snapshot(store) == before
        with store.tx() as c:
            job = dict(c.execute(select(runs).where(runs.c.id == source_id)).mappings().one())
        wire, received = captured[aid]
        canonical = receipt["attempts"][0]["canonical_ascii_sha256"]
        with store.tx() as c:
            archive.record_request(store, c, job, aid, wire)
            archive.record_response(store, c, job, aid, received, True, canonical, request_body=wire)
        assert snapshot(store) == before
        refused("immutable_changed_body", lambda: record_again(store, job, aid, received + b" ", wire, canonical))
        refused("immutable_complete_to_partial", lambda: record_again(store, job, aid, received, wire, canonical, complete=False))
        wrong_owner = {**job, "runtime_id": contract.runtime_id}
        refused("append_moved_runtime", lambda: record_again(store, wrong_owner, aid, received, wire, canonical))
        # A deliberately late clock affects this read only, after actual authority
        # checks; it is fault injection, never a faster budget/performance proof.
        with monkeypatch.context() as local:
            original_recheck = cold_store.recheck_proof_authorities

            def expire_after_recheck(c, proof):
                original_recheck(c, proof)
                local.setattr(archive.time, "time", lambda: contract.expires_at + 1)

            local.setattr(cold_store, "recheck_proof_authorities", expire_after_recheck)
            refused("expiry_after_authority_recheck_FAULT_INJECTION", lambda:
                archive.resolve_trial_source(cold_store, user, contract, approval.request_key))
        assert snapshot(store) == before
        ledger = budget.read(store, user, scope.model_dump())["ledger"]
        assert len(ledger["slots"]) == 5 and ledger["halted"] is False
        assert all(s["accepted"] and s["settlement"] is not None for s in ledger["slots"])
        gaps = [b["reserved_at"] - a["reserved_at"] for a, b in zip(ledger["slots"], ledger["slots"][1:], strict=False)]
        assert len(gaps) == 4 and all(g >= 60 for g in gaps)
        assert archive.resolve_trial_source(cold_store, user, contract, approval.request_key).public_receipt == receipt
        assert snapshot(store) == before and len(dispatches) == 5
        (tmp_path / "actual-source-archive.json").write_text(json.dumps(dict(receipt=receipt,
            checks=checks, actual_dispatch_stages=dispatches, reservation_gaps=gaps,
            all_read_tables_unchanged=True, run_seconds=settings.run_seconds,
            lease_seconds=settings.lease_seconds, real_models=0, cold_model_dispatches=0), indent=2))
    finally:
        cold_store.engine.dispose()
        client.close()


def record_again(store, job, aid, received, wire, canonical, *, complete=True):
    with store.tx() as c:
        archive.record_response(store, c, job, aid, received, complete, canonical, request_body=wire)


@pytest.mark.parametrize("fault", ["invalid_json", "empty", "oversize", "network_prefix", "cancel", "revoked",
                                   "request_write_failure", "response_write_failure"])
def test_received_failure_facts_survive_without_business_success(env, tmp_path, monkeypatch, fault):
    data = setup(env)
    store, settings, client = data[:3]
    _, _, release, inst, _ = ready(data)
    source_id = enqueue(data, release, inst)
    sent = []
    normal = transport([], SOURCE)
    if fault.endswith("write_failure"):
        original_event = store.event
        boundary = "NS_WIRE_ARCHIVED" if fault == "request_write_failure" else "NS_BODY_ARCHIVED"

        def fail_after_archive_write(c, rid, kind, data):
            original_event(c, rid, kind, data)
            if rid == source_id and kind == boundary:
                raise DomainError("VERSION_CONFLICT", "Explicit archive transaction fault")

        monkeypatch.setattr(store, "event", fail_after_archive_write)

    class BrokenStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'{"received":"partial"}'
            raise httpx.ReadError("Explicit offline receive fault")

    def handler(request):
        sent.append(request.content)
        if fault == "invalid_json":
            payload = b'{"broken":'
        elif fault == "empty":
            payload = b''
        elif fault == "oversize":
            payload = json.dumps(dict(padding="x" * 40000)).encode()
        elif fault == "network_prefix":
            handler.received = b'{"received":"partial"}'
            return httpx.Response(200, stream=BrokenStream())
        else:
            if fault == "cancel":
                with store.tx() as c:
                    c.execute(update(runs).where(runs.c.id == source_id).values(cancel_intent=True))
            elif fault == "revoked":
                with store.tx() as c:
                    c.execute(update(grants).where(grants.c.principal_id == inst["runtime_id"],
                        grants.c.resource_id == data[5]).values(revoked=True))
            payload = normal.handle_request(request).content
        handler.received = payload
        return httpx.Response(200, content=payload)

    assert Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler)).once()
    with store.tx() as c:
        job = c.execute(select(runs).where(runs.c.id == source_id)).mappings().one()
        app_run_id = c.execute(select(internal_run_bindings.c.app_run_id).where(
            internal_run_bindings.c.run_id == source_id)).scalar_one()
        assert not c.execute(select(internal_instance_data).where(
            internal_instance_data.c.run_id == app_run_id)).first()
        if fault == "request_write_failure":
            assert not c.execute(select(attempts.c.id).where(attempts.c.run_id == source_id)).first()
            assert not c.execute(select(reservations.c.id).where(reservations.c.run_id == source_id)).first()
            assert not c.execute(select(delivery_graph_requests.c.request_key).where(
                delivery_graph_requests.c.app_id == source_id,
                delivery_graph_requests.c.kind.in_([archive.REQUEST, archive.REQUEST + "_seal"]))).first()
            assert job["context"]["requests"] == job["context"]["reserved_tokens"] == 0
            assert not sent and job["status"] != "SUCCEEDED"
            (tmp_path / "request-rollback.json").write_text(json.dumps(dict(
                no_attempt=True, no_reservation=True, no_archive=True, actual_sends=0)))
            client.close()
            return
        row = c.execute(select(attempts).where(attempts.c.run_id == source_id)).mappings().one()
        if fault == "response_write_failure":
            assert row["status"] == "STARTED" and row["response"] is None
            assert row["usage"] == dict(status="unknown", tokens=None)
            assert not c.execute(select(delivery_graph_requests.c.request_key).where(
                delivery_graph_requests.c.app_id == source_id,
                delivery_graph_requests.c.kind.in_([archive.RESPONSE, archive.RESPONSE + "_seal"]))).first()
            assert c.execute(select(reservations.c.id).where(reservations.c.id == row["id"])).first()
            assert len(sent) == 1 and job["status"] != "SUCCEEDED"
            (tmp_path / "response-rollback.json").write_text(json.dumps(dict(
                response_transaction_rolled_back=True, preserved_reservation=True, actual_sends=1,
                state="UNKNOWN", raw_receipt="NOT_PERSISTED_IN_EXPLICIT_WRITE_FAILURE")))
            client.close()
            return
        body, _ = archive.pair(c, data[3], source_id, archive.RESPONSE, row["id"], archive.BodyArchive)
        assert body.byte_count == len(handler.received)
        assert body.sha256 == hashlib.sha256(handler.received).hexdigest()
        assert c.execute(select(reservations).where(reservations.c.id == row["id"])).first()
        assert row["reserved_tokens"] > 0 and job["status"] != "SUCCEEDED"
        if fault in {"cancel", "revoked"}:
            assert row["status"] == "REJECTED_KNOWN" and row["usage"]["status"] == "known"
            assert body.body_b64 and body.canonical_sha256 == row["response"]["raw_evidence"]["sha256"]
        else:
            assert row["status"] == "STARTED" and row["response"] is None
            assert row["usage"] == dict(status="unknown", tokens=None)
            assert body.canonical_sha256 is None
        if fault in {"oversize", "empty"}:
            assert body.omission == ("OVERSIZE" if fault == "oversize" else "EMPTY") and body.body_b64 is None
        else:
            assert base64.b64decode(body.body_b64) == handler.received
        assert body.extent == ("RECEIVED_PREFIX" if fault == "network_prefix" else "COMPLETE_BODY")
        public_events = [dict(r) for r in c.execute(select(events).where(events.c.run_id == source_id)).mappings()]
        assert "body_b64" not in json.dumps(public_events)
        assert "synthetic-offline-natural-spec" not in json.dumps(public_events)
    before = snapshot(store)
    client.get("/api/runs/" + source_id)
    assert snapshot(store) == before and len(sent) == 1
    (tmp_path / "received-failure.json").write_text(json.dumps(dict(fault=fault,
        run_status=job["status"], attempt_status=row["status"], archive=body.model_dump(exclude={"body_b64"}),
        actual_sends=1, real_models=0, preserved_reservation=True, new_typed_results=0), indent=2))
    client.close()
