"""Known, accepted single-extract completion. No sender or response-import API."""

import hashlib
import math
import os
import re
import stat
import sys
import time
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

import httpx
from pydantic import Field
from sqlalchemy import select, update

from .contracts import Strict, strict_json
from .db import attempts, events, fingerprint, operations, protocol_request_slots, runs
from .errors import DomainError
from .model import normalize_usage, parse_response, require_returned_model, returned_model_identity

ORIGIN = "PROTOCOL_EXTRACT_ORIGIN_V2"
ACCEPTED = "PROTOCOL_EXTRACT_ACCEPTED_V2"
COMPLETED = "PROTOCOL_EXTRACT_RECOVERED_V2"
VERSION = "protocol-extract-completion.v2"
RECEIPT = "protocol-attempt-receipt.v2"


class CompletionInput(Strict):
    expected_version: int = Field(strict=True, ge=1)
    expected_fence: int = Field(strict=True, ge=0)
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")


def require(ok, message="Complete V2 extraction evidence required"):
    if not ok:
        raise DomainError("VERSION_CONFLICT", message)


def _stored(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            raise DomainError("VERSION_CONFLICT", "Malformed V2 extraction evidence") from exc

    return call


def sidecar_path(data_dir, rid):
    require(type(rid) is str and re.fullmatch(r"run_[a-f0-9]{32}", rid))
    return Path(data_dir).resolve() / (rid + ".json")


@contextmanager
def sidecar(data_dir, rid):
    """Existing file/lock only, nonblocking, held through the caller's commit.

    No provider object, lock-file creation, ledger save or permission repair.
    The configured data root and original Run select the file, never the client.
    """
    path = sidecar_path(data_dir, rid)
    lock = path.with_suffix(".lock")
    streams = []
    try:
        for p in (lock, path):
            before = p.lstat()
            require(stat.S_ISREG(before.st_mode) and not p.is_symlink())
            fd = os.open(p, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            stream = os.fdopen(fd, "rb")
            streams.append(stream)
            actual = os.fstat(fd)
            require((before.st_dev, before.st_ino) == (actual.st_dev, actual.st_ino))
            if p == lock:
                if sys.platform == "win32":
                    import msvcrt

                    msvcrt.locking(fd, msvcrt.LK_NBRLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        data = strict_json(streams[1].read(131073), 131072)
        require(type(data) is dict)
        yield data
    except OSError as exc:
        raise DomainError(
            "OUTCOME_UNKNOWN", "Original extraction sidecar unavailable or locked"
        ) from exc
    finally:
        # Closing the existing lock descriptor releases it, including failures.
        for stream in reversed(streams):
            stream.close()


def _one(c, rid, kind):
    values = (
        c.execute(select(events.c.data).where(events.c.run_id == rid, events.c.kind == kind))
        .scalars()
        .all()
    )
    require(len(values) == 1)
    return values[0]


def _mirror(store, c, rid, aid, kind, value):
    store.event(c, rid, kind, value)
    store.event(c, aid, kind, value)


def safe_response(raw):
    message, _ = parse_response(raw)
    return dict(
        model=raw.get("model"),
        usage=raw.get("usage"),
        choices=[dict(message=message, finish_reason=raw["choices"][0]["finish_reason"])],
    )


def _wire(messages, model, max_tokens):
    body = httpx.Request(
        "POST",
        "https://offline.invalid",
        json=dict(model=model, messages=messages, tools=[], stream=False, max_tokens=max_tokens),
    ).content
    return dict(
        sha256=hashlib.sha256(body).hexdigest(),
        bytes=len(body),
        characters=len(body.decode("utf-8")),
    )


def bind_request(worker, run, snapshot, provider, aid, messages, tools):
    """Qualify before sending. Unsupported legacy setups keep their V1 path."""
    if (
        snapshot["phase"] != "extract"
        or snapshot.get("bounded_check_namespace")
        or tools
        or provider.path.absolute() != sidecar_path(worker.s.data_dir, run["id"])
    ):
        return None
    with sidecar(worker.s.data_dir, run["id"]) as data:
        started = data.get("stage_started", {}).get(provider.stage)
        # Historical synthetic clocks / shared files have no new qualification.
        if (
            type(started) not in (int, float)
            or not math.isfinite(started)
            or not started <= time.time() < started + 300
            or data.get("slots") != []
        ):
            return None
        with worker.store.tx() as c:
            from .protocol_jobs import verified_pending
            from .protocol_pool import _reserved_seal

            job, current = verified_pending(worker.store, c, run["principal_id"], run["id"])
            worker.store.guard(c, run["id"], run["fence"])
            require(fingerprint(job["snapshot"]) == fingerprint(snapshot))
            all_attempts = (
                c.execute(select(attempts).where(attempts.c.run_id == run["id"])).mappings().all()
            )
            require(len(all_attempts) == 1 and all_attempts[0]["id"] == aid)
            attempt = all_attempts[0]
            slot = (
                c.execute(
                    select(protocol_request_slots).where(protocol_request_slots.c.attempt_id == aid)
                )
                .mappings()
                .one()
            )
            genesis = c.execute(
                select(events.c.id).where(
                    events.c.run_id == slot["pool_id"], events.c.kind == "PROTOCOL_POOL_INITIALIZED"
                )
            ).scalar_one()
            params = dict(attempt["parameters"])
            wire = _wire(messages, worker.s.model, params["max_tokens"])
            require(
                attempt["status"] == slot["status"] == "STARTED"
                and current["context"]["requests"] == 1
                and slot["phase"] == "extract"
                and fingerprint(params["protocol_wire"]) == fingerprint(wire)
                and params["request_fingerprint"]
                == fingerprint(dict(messages=messages, tools=[], model=worker.s.model))
            )
            frozen = worker.store.frozen_contract(c, current)
            origin = dict(
                namespace=VERSION,
                run_id=run["id"],
                principal_id=current["principal_id"],
                project_id=current["project_id"],
                runtime_id=current["runtime_id"],
                accepted_fingerprint=job["fingerprint"],
                phase="extract",
                attempt_id=aid,
                request_index=0,
                request_key=current["request_key"],
                fence=run["fence"],
                pool_genesis=genesis,
                pool_slot=_reserved_seal(slot),
                wire=wire,
                request_fingerprint=params["request_fingerprint"],
                provider_stage=provider.stage,
                provider_scope_fingerprint=fingerprint(snapshot["scope"]),
                sidecar_name=run["id"] + ".json",
                provider_deadline=started + 300,
                deadline=current["created_at"]
                + min(frozen.limits.run_seconds, worker.s.run_seconds),
            )
            require(time.time() < origin["deadline"] and not current["cancel_intent"])
            params["extract_origin_v2"] = origin
            c.execute(update(attempts).where(attempts.c.id == aid).values(parameters=params))
            _mirror(worker.store, c, run["id"], aid, ORIGIN, origin)
            return origin


def check_actual_wire(origin, body, scope, stage):
    """Provider calls before reservation and again on the actual HTTP request."""
    require(
        type(origin) is dict
        and origin.get("namespace") == VERSION
        and origin.get("phase") == "extract"
        and origin.get("request_index") == 0
        and type(origin.get("request_index")) is int
        and origin.get("provider_stage") == stage
        and origin.get("provider_scope_fingerprint") == fingerprint(scope)
        and origin.get("sidecar_name") == origin.get("run_id", "") + ".json"
        and origin["pool_slot"]["attempt_id"] == origin["attempt_id"]
        and origin["pool_slot"]["run_id"] == origin["run_id"]
        and origin["wire"]
        == dict(
            sha256=hashlib.sha256(body).hexdigest(),
            bytes=len(body),
            characters=len(body.decode("utf-8")),
        )
    )


@_stored
def _received(store, c, user, rid, data):
    from .model_protocol import Scope, validate_candidate
    from .protocol_jobs import _source, verified_pending
    from .protocol_pool import _reserved_seal, audit_pool

    job, run = verified_pending(store, c, user, rid)
    snapshot = job["snapshot"]
    require(
        job["phase"] == "extract"
        and not snapshot.get("bounded_check_namespace")
        and snapshot["scope"]["max_requests"] == 1
        and run["context"]["requests"] == 1
    )
    rows = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all()
    slots = (
        c.execute(select(protocol_request_slots).where(protocol_request_slots.c.run_id == rid))
        .mappings()
        .all()
    )
    require(
        len(rows) == len(slots) == 1
        and not c.execute(select(operations.c.id).where(operations.c.run_id == rid)).first()
    )
    attempt, slot = rows[0], slots[0]
    aid, params = attempt["id"], attempt["parameters"]
    origin = params.get("extract_origin_v2")
    require(
        type(origin) is dict
        and fingerprint(origin)
        == fingerprint(_one(c, rid, ORIGIN))
        == fingerprint(_one(c, aid, ORIGIN))
    )
    genesis = c.execute(
        select(events.c.id).where(
            events.c.run_id == slot["pool_id"], events.c.kind == "PROTOCOL_POOL_INITIALIZED"
        )
    ).scalar_one()
    require(
        origin["namespace"] == VERSION
        and origin["phase"] == "extract"
        and origin["run_id"] == rid
        and origin["attempt_id"] == aid
        and origin["request_index"] == 0
        and type(origin["request_index"]) is int
        and origin["principal_id"] == user
        and origin["project_id"] == run["project_id"]
        and origin["runtime_id"] == run["runtime_id"]
        and origin["request_key"] == run["request_key"]
        and origin["pool_genesis"] == genesis
        and origin["fence"] == slot["fence"]
        and type(origin["fence"]) is int
        and origin["accepted_fingerprint"] == job["fingerprint"]
        and origin["provider_scope_fingerprint"] == fingerprint(snapshot["scope"])
        and origin["sidecar_name"] == rid + ".json"
        and fingerprint(origin["pool_slot"]) == fingerprint(_reserved_seal(slot))
        and origin["request_fingerprint"] == params["request_fingerprint"]
        and fingerprint(origin["wire"])
        == fingerprint(params["protocol_wire"])
        == fingerprint(
            _wire(run["context"]["messages"], attempt["request_model"], params["max_tokens"])
        )
    )
    require(
        attempt["status"] == slot["status"] == "RECEIVED"
        and attempt["mode"] == "MOCK"
        and slot["request_fingerprint"]
        == fingerprint(
            dict(messages=run["context"]["messages"], tools=[], model=attempt["request_model"])
        )
    )
    pool = audit_pool(c, slot["pool_id"])
    require(
        pool["consistent"]
        and not pool["halted"]
        and not pool["has_pending"]
        and not pool["has_unknown"]
    )
    raw = attempt["response"]
    identity = returned_model_identity("intern-s2", raw.get("model"))
    require_returned_model(identity)
    usage = normalize_usage(raw)
    require(
        usage["status"] == "known"
        and fingerprint(usage) == fingerprint(attempt["usage"]) == fingerprint(slot["usage"])
        and fingerprint(identity) == fingerprint(params["model_identity"])
        and fingerprint(raw)
        == slot["safe_response_fingerprint"]
        == params["safe_response_fingerprint"]
        and attempt["response_model"] == raw["model"]
    )
    message, calls = parse_response(raw)
    require(not calls)
    candidate = strict_json(message["content"])
    validate_candidate(candidate, Scope.model_validate(snapshot["scope"]))
    source = _source(
        store, c, user, snapshot["source"]["run_id"], snapshot["source"]["result_fingerprint"]
    )
    require(fingerprint(source) == fingerprint(snapshot["source"]))
    receipt = data["slots"][0]["candidate_receipt"]
    require(
        data["version"] == 1
        and type(data["version"]) is int
        and type(data["halted"]) is bool
        and not data["halted"]
        and type(data["reserved"]) is int
        and type(data["known_tokens"]) is int
        and data["scope_fingerprint"] == fingerprint(snapshot["scope"])
        and len(data["slots"]) == 1
    )
    provider_slot = data["slots"][0]
    require(
        fingerprint(provider_slot.get("protocol_origin_v2")) == fingerprint(origin)
        and provider_slot["stage"] == origin["provider_stage"]
        and provider_slot["status"] == "RECEIVED"
        and receipt["slot"] == 0
        and type(receipt["slot"]) is int
        and provider_slot["body_sha256"] == origin["wire"]["sha256"]
        and provider_slot["bytes"] == origin["wire"]["bytes"]
        and provider_slot["chars"] == origin["wire"]["characters"]
        and provider_slot["reserved"]
        == attempt["reserved_tokens"]
        == slot["reserved_tokens"]
        == data["reserved"]
        and provider_slot["tokens"] == usage["tokens"]["total_tokens"] == data["known_tokens"]
        and fingerprint(provider_slot["normalized_usage_v2"]) == fingerprint(usage)
        and provider_slot["raw_response_fingerprint_v2"] == params["raw_response_fingerprint"]
        and provider_slot["safe_response_fingerprint_v2"] == fingerprint(raw)
        and provider_slot["response_json_fingerprint"] == fingerprint(candidate)
        and data["stage_started"][provider_slot["stage"]] + 300 == origin["provider_deadline"]
    )
    expected = dict(
        scope_fingerprint=fingerprint(snapshot["scope"]),
        stage=origin["provider_stage"],
        slot=0,
        candidate_fingerprint=fingerprint(candidate),
        source_proof_fingerprint=fingerprint(source["proof"]),
        receipt_version=VERSION,
        origin_fingerprint=fingerprint(origin),
        safe_response_fingerprint=fingerprint(raw),
        usage=usage,
    )
    require(fingerprint(receipt) == fingerprint(expected))
    from .protocol_experiment import _binding, _state, is_experiment_run

    experiment = None
    if is_experiment_run(c, rid):
        binding = _binding(c, run)
        policy, bound, advanced, sends, settled, stopped = _state(c, binding["experiment_id"])
        own = [s for s in sends if s["run_id"] == rid]
        finished = [s for s in settled if s["attempt_id"] == aid]
        require(
            not stopped
            and len(own) == len(finished) == 1
            and own[0]["attempt_id"] == aid
            and own[0]["fence"] == origin["fence"]
            and binding["accepted_fingerprint"] == job["fingerprint"]
            and policy["principal_id"] == user
            and policy["project_id"] == run["project_id"]
        )
        historical = [value for value in advanced if value["run_id"] == rid]
        if historical:
            require(
                len(historical) == 1
                and run["status"] == "SUCCEEDED"
                and job["result"] is not None
                and fingerprint(historical[0])
                == fingerprint(
                    dict(
                        run_id=rid,
                        stage=binding["stage"],
                        result_fingerprint=job["result_fingerprint"],
                        proof_fingerprint=fingerprint(None),
                    )
                )
            )
        else:
            require(
                len(advanced) < len(bound) and bound[len(advanced)]["run_id"] == rid,
                "Incomplete extraction is no longer the current experiment stage",
            )
        experiment = dict(binding=binding, send=own[0], settlement=finished[0])
    return job, run, attempt, origin, expected, candidate, source, experiment


@_stored
def persist_acceptance(worker, run, snapshot, provider, receipt):
    """After real provider accept, before original completion. Missing V2 stays V1."""
    if receipt.get("receipt_version") != VERSION:
        return receipt
    with sidecar(worker.s.data_dir, run["id"]) as data, worker.store.tx() as c:
        worker.store.lock_project(c, run["principal_id"], run["project_id"])
        worker.store.guard(c, run["id"], run["fence"])
        job, current, attempt, origin, expected, _, _, experiment = _received(
            worker.store, c, run["principal_id"], run["id"], data
        )
        require(
            fingerprint(receipt) == fingerprint(expected)
            and not current["cancel_intent"]
            and fingerprint(snapshot) == job["fingerprint"]
            and provider.path.absolute() == sidecar_path(worker.s.data_dir, run["id"])
        )
        wrapped = dict(
            receipt, attempt_id=attempt["id"], extraction_run_id=run["id"], namespace=RECEIPT
        )
        witness = dict(
            namespace=VERSION,
            origin=origin,
            receipt=wrapped,
            provider_ledger_fingerprint=fingerprint(data),
            experiment=experiment,
            accepted_at=time.time(),
        )
        _deadlines(worker.store, c, current, job, witness, worker.s)
        params = dict(attempt["parameters"], protocol_candidate_receipt=wrapped)
        c.execute(update(attempts).where(attempts.c.id == attempt["id"]).values(parameters=params))
        _mirror(worker.store, c, run["id"], attempt["id"], ACCEPTED, witness)
        return wrapped


def _deadlines(store, c, run, job, witness, settings):
    frozen = store.frozen_contract(c, run)
    origin = witness["origin"]
    bounds = [
        origin["deadline"],
        origin["provider_deadline"],
        run["created_at"] + min(frozen.limits.run_seconds, settings.run_seconds),
    ]
    if witness["experiment"] is not None:
        bounds.append(witness["experiment"]["binding"]["bound_at"] + 300)
    at = time.time()
    require(
        all(type(x) in (int, float) and math.isfinite(x) for x in bounds)
        and type(witness["accepted_at"]) in (int, float)
        and run["created_at"] <= witness["accepted_at"] <= at < min(bounds),
        "Original extraction completion deadline expired",
    )


@_stored
def verified_receipt(store, c, user, rid, receipt, data):
    facts = _received(store, c, user, rid, data)
    _, _, attempt, origin, expected, _, _, experiment = facts
    witness = _one(c, rid, ACCEPTED)
    require(
        fingerprint(witness) == fingerprint(_one(c, attempt["id"], ACCEPTED))
        and witness["namespace"] == VERSION
        and fingerprint(witness["origin"]) == fingerprint(origin)
        and witness["provider_ledger_fingerprint"] == fingerprint(data)
        and fingerprint(witness["experiment"]) == fingerprint(experiment)
        and fingerprint(witness["receipt"])
        == fingerprint(receipt)
        == fingerprint(
            dict(expected, attempt_id=attempt["id"], extraction_run_id=rid, namespace=RECEIPT)
        )
        == fingerprint(attempt["parameters"].get("protocol_candidate_receipt"))
    )
    return facts, witness


@_stored
def complete_extract(store, user, rid, request, settings):
    """An owner fences an expired writer and completes an already accepted fact.

    This entry receives no provider, transport, callback, response or file path.
    It cannot queue, send, reserve, accept a candidate, refund or clear a halt.
    """
    request = CompletionInput.model_validate(request)
    if not store.test_only or settings.mode != "mock":
        raise DomainError("PERMISSION_DENIED", "Original offline protocol boundary required")
    from .protocol_jobs import compile_extraction, complete_in_tx, verified_pending

    # Authorize before even opening the server-selected private ledger.
    with store.tx() as c:
        job, run = verified_pending(store, c, user, rid)
        require(job["phase"] == "extract" and not job["snapshot"].get("bounded_check_namespace"))
    with sidecar(settings.data_dir, rid) as data, store.tx() as c:
        job, run = verified_pending(store, c, user, rid)
        rows = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all()
        require(len(rows) == 1)
        receipt = rows[0]["parameters"].get("protocol_candidate_receipt")
        facts, witness = verified_receipt(store, c, user, rid, receipt, data)
        job, run, attempt, origin, _, candidate, source, _ = facts
        prior = (
            c.execute(
                select(events.c.data).where(events.c.run_id == rid, events.c.kind == COMPLETED)
            )
            .scalars()
            .all()
        )
        if prior:
            require(
                len(prior) == 1
                and fingerprint(prior[0]) == fingerprint(_one(c, attempt["id"], COMPLETED))
            )
            old = prior[0]
            require(
                fingerprint(old["request"]) == fingerprint(request.model_dump())
                and old["response"]["status"] == run["status"] == "SUCCEEDED"
                and old["response"]["version"] == run["version"]
                and old["response"]["fence"] == run["fence"]
                and old["response"]["plan_fingerprint"]
                == job["result"]["compiled_plan"]["plan_fingerprint"]
                and old["original_send_fence"] == origin["fence"]
                and old["recovery_fence"] == run["fence"] == request.expected_fence + 1
                and run["version"] == request.expected_version + 1
                and type(old["completed_at"]) in (int, float)
                and math.isfinite(old["completed_at"])
                and witness["accepted_at"]
                <= old["completed_at"]
                < min(origin["deadline"], origin["provider_deadline"])
            )
            return dict(old["response"], cached=True)
        at = time.time()
        require(
            run["version"] == request.expected_version
            and run["fence"] == request.expected_fence
            and run["status"] in {"RUNNING", "WAITING_RESOURCE", "RECONCILING"}
            and not run["cancel_intent"]
            and run["lease_until"] <= at
            and job["result"] is None
            and run["result"] is None
            and not c.execute(
                select(events.c.id).where(
                    events.c.run_id == rid, events.c.kind == "PROTOCOL_COMPLETED"
                )
            ).first(),
            "Only an expired, uncancelled, incomplete extraction can finish",
        )
        _deadlines(store, c, run, job, witness, settings)
        result = dict(
            kind="model-protocol.v1",
            candidate=candidate,
            candidate_fingerprint=fingerprint(candidate),
            source_proof=source["proof"],
            source_proof_fingerprint=fingerprint(source["proof"]),
            candidate_receipt=receipt,
            executable_by_existing_apprun=False,
            semantic_status="NOT_RUN",
        )
        compiled = compile_extraction(job["snapshot"], result)
        new_fence = run["fence"] + 1
        changed = c.execute(
            update(runs)
            .where(
                runs.c.id == rid,
                runs.c.version == request.expected_version,
                runs.c.fence == request.expected_fence,
                runs.c.status == run["status"],
                runs.c.lease_until <= at,
                runs.c.cancel_intent.is_(False),
            )
            .values(fence=new_fence)
        )
        require(changed.rowcount == 1, "Extraction recovery fence changed")
        current = dict(run, fence=new_fence)
        complete_in_tx(store, c, current, job["snapshot"], result, compiled, new_fence)
        # Lock acquisition and pure work spend the original clocks. Publish only
        # after a new complete source/authority check and the final finite gate.
        fresh_facts, fresh_witness = verified_receipt(store, c, user, rid, receipt, data)
        fresh_job, fresh = fresh_facts[:2]
        require(
            fingerprint(fresh_witness) == fingerprint(witness)
            and not fresh["cancel_intent"]
            and fresh["status"] == "SUCCEEDED"
            and fresh["fence"] == new_fence
            and fresh["version"] == run["version"] + 1
        )
        _deadlines(store, c, fresh, fresh_job, witness, settings)
        response = dict(
            namespace=VERSION,
            run_id=rid,
            status="SUCCEEDED",
            version=fresh["version"],
            fence=new_fence,
            plan_fingerprint=compiled["plan_fingerprint"],
            provider_requests=0,
            automatic_resend=False,
            cached=False,
        )
        _mirror(
            store,
            c,
            rid,
            attempt["id"],
            COMPLETED,
            dict(
                request=request.model_dump(),
                response=response,
                completed_at=time.time(),
                original_send_fence=origin["fence"],
                recovery_fence=new_fence,
            ),
        )
        final_job, final_run = verified_pending(store, c, user, rid)
        require(
            not final_run["cancel_intent"]
            and final_run["status"] == "SUCCEEDED"
            and final_run["fence"] == new_fence
            and final_run["version"] == run["version"] + 1
        )
        _deadlines(store, c, final_run, final_job, witness, settings)
        return response
