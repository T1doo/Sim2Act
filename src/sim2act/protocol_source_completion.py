"""Complete known ordinary Source facts, without a sender or response import."""

import hashlib
import math
import time

import httpx
from sqlalchemy import select, update

from .contracts import strict_json
from .db import (
    attempts,
    events,
    fingerprint,
    operation_intents,
    operations,
    protocol_request_slots,
    runs,
)
from .errors import DomainError
from .model import normalize_usage, parse_response, require_returned_model, returned_model_identity
from .protocol_extract_completion import (
    CompletionInput,
    _mirror,
    _one,
    _stored,
    require,
    safe_response,
    sidecar,
    sidecar_path,
)

VERSION = "protocol-source-completion.v2"
ORIGIN = "PROTOCOL_SOURCE_ORIGIN_V2"
READY = "PROTOCOL_SOURCE_READY_V2"
COMPLETED = "PROTOCOL_SOURCE_RECOVERED_V2"


def _wire(messages, tools, model, max_tokens):
    body = httpx.Request(
        "POST",
        "https://offline.invalid",
        json=dict(
            model=model,
            messages=messages,
            tools=tools,
            stream=False,
            max_tokens=max_tokens,
        ),
    ).content
    return _wire_value(body)


def _wire_value(body):
    return dict(
        sha256=hashlib.sha256(body).hexdigest(),
        bytes=len(body),
        characters=len(body.decode("utf-8")),
    )


def check_actual_wire(origin, body, scope, stage):
    require(
        type(origin) is dict
        and origin.get("namespace") == VERSION
        and origin.get("phase") == "source"
        and type(origin.get("request_index")) is int
        and 0 <= origin["request_index"] < 3
        and origin.get("provider_stage") == stage
        and origin.get("provider_scope_fingerprint") == fingerprint(scope)
        and origin.get("sidecar_name") == origin.get("run_id", "") + ".json"
        and origin["pool_slot"]["attempt_id"] == origin["attempt_id"]
        and origin["pool_slot"]["run_id"] == origin["run_id"]
        and fingerprint(origin["wire"]) == fingerprint(_wire_value(body)),
        "Source origin does not bind the actual wire",
    )


def _rows(c, table, rid):
    return list(c.execute(select(table).where(table.c.run_id == rid)).mappings())


def _origins(c, rid, rows):
    seals = list(
        c.execute(
            select(events.c.data).where(events.c.run_id == rid, events.c.kind == ORIGIN)
        ).scalars()
    )
    require(len(seals) == len(rows))
    result = []
    for a in rows:
        origin = a["parameters"].get("source_origin_v2")
        require(type(origin) is dict and type(origin.get("request_index")) is int)
        require(
            sum(fingerprint(s) == fingerprint(origin) for s in seals) == 1
            and fingerprint(_one(c, a["id"], ORIGIN)) == fingerprint(origin)
        )
        result.append((origin["request_index"], a, origin))
    result.sort(key=lambda v: v[0])
    require([v[0] for v in result] == list(range(len(rows))))
    return result


def bind_request(worker, run, snapshot, provider, aid, messages, tools):
    """Issue at the existing producer; unsupported legacy runs do not qualify."""
    if (
        snapshot["phase"] != "source"
        or snapshot.get("bounded_check_namespace")
        or not 2 <= snapshot["scope"]["max_requests"] <= 3
        or provider.path.absolute() != sidecar_path(worker.s.data_dir, run["id"])
    ):
        return None
    with sidecar(worker.s.data_dir, run["id"]) as data:
        started = data.get("stage_started", {}).get(provider.stage)
        with worker.store.tx() as c:
            from .protocol_api import provider_stage
            from .protocol_jobs import verified_pending
            from .protocol_pool import _reserved_seal

            job, current = verified_pending(worker.store, c, run["principal_id"], run["id"])
            worker.store.guard(c, run["id"], run["fence"])
            rows = _rows(c, attempts, run["id"])
            prior = [a for a in rows if a["id"] != aid]
            qualified = any(a["parameters"].get("source_origin_v2") for a in prior)
            compatible = (
                type(started) in (int, float)
                and math.isfinite(started)
                and started <= time.time() < started + 300
            )
            if not qualified and (prior or data.get("slots") != [] or not compatible):
                return None
            require(
                compatible
                and fingerprint(snapshot) == job["fingerprint"]
                and provider.stage == provider_stage(snapshot)
            )
            ordered = _origins(c, run["id"], prior) if prior else []
            require(len(data["slots"]) == len(prior))
            for i, a, o in ordered:
                require(
                    a["status"] == "RECEIVED"
                    and data["slots"][i]["status"] == "RECEIVED"
                    and fingerprint(data["slots"][i]["protocol_origin_v2"]) == fingerprint(o)
                )
            require(
                len(rows) == len(prior) + 1
                and current["context"]["requests"] == len(rows)
                and len(rows) <= snapshot["scope"]["max_requests"]
            )
            a = next(a for a in rows if a["id"] == aid)
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
            params = dict(a["parameters"])
            wire = _wire(messages, tools, worker.s.model, params["max_tokens"])
            require(
                a["status"] == slot["status"] == "STARTED"
                and slot["phase"] == "source"
                and slot["fence"] == run["fence"]
                and fingerprint(params["protocol_wire"]) == fingerprint(wire)
                and params["request_fingerprint"]
                == fingerprint(dict(messages=messages, tools=tools, model=worker.s.model))
            )
            frozen = worker.store.frozen_contract(c, current)
            origin = dict(
                namespace=VERSION,
                run_id=run["id"],
                principal_id=current["principal_id"],
                project_id=current["project_id"],
                runtime_id=current["runtime_id"],
                accepted_fingerprint=job["fingerprint"],
                phase="source",
                attempt_id=aid,
                request_index=len(prior),
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
            params["source_origin_v2"] = origin
            c.execute(update(attempts).where(attempts.c.id == aid).values(parameters=params))
            _mirror(worker.store, c, run["id"], aid, ORIGIN, origin)
            return origin


def _experiment(c, job, run, ordered, proof):
    from .protocol_experiment import _binding, _state, is_experiment_run

    if not is_experiment_run(c, run["id"]):
        return None
    binding = _binding(c, run)
    policy, bound, advanced, sends, settled, stopped = _state(c, binding["experiment_id"])
    own = [s for s in sends if s["run_id"] == run["id"]]
    aids = [a["id"] for _, a, _ in ordered]
    own.sort(key=lambda s: aids.index(s["attempt_id"]) if s["attempt_id"] in aids else -1)
    finished = [s for s in settled if s["attempt_id"] in aids]
    finished.sort(key=lambda s: aids.index(s["attempt_id"]))
    require(
        not stopped
        and len(own) == len(finished) == len(aids)
        and [s["attempt_id"] for s in own] == [s["attempt_id"] for s in finished] == aids
        and all(s["fence"] == o["fence"] for s, (_, _, o) in zip(own, ordered, strict=True))
        and binding["accepted_fingerprint"] == job["fingerprint"]
        and policy["principal_id"] == run["principal_id"]
        and policy["project_id"] == run["project_id"]
    )
    historical = [s for s in advanced if s["run_id"] == run["id"]]
    if historical:
        require(
            proof is not None
            and len(historical) == 1
            and fingerprint(historical[0])
            == fingerprint(
                dict(
                    run_id=run["id"],
                    stage=binding["stage"],
                    result_fingerprint=job["result_fingerprint"],
                    proof_fingerprint=fingerprint(proof),
                )
            )
        )
    else:
        require(len(advanced) < len(bound) and bound[len(advanced)]["run_id"] == run["id"])
    return dict(policy=policy, binding=binding, sends=own, settlements=finished)


@_stored
def _facts(store, c, user, rid, data):
    from .model_protocol import OUTPUTS, _no_gold, validate_value
    from .protocol_api import provider_stage
    from .protocol_jobs import _attempt_seal, _operation_seal, authorized_read, verified_pending
    from .protocol_pool import _finished_seal, _reserved_seal, audit_pool

    job, run = verified_pending(store, c, user, rid)
    snapshot = job["snapshot"]
    require(
        job["phase"] == "source"
        and not snapshot.get("bounded_check_namespace")
        and snapshot["scope"]["mode"] == "offline"
    )
    rows, slots, ops = (
        _rows(c, table, rid) for table in (attempts, protocol_request_slots, operations)
    )
    n = len(rows)
    require(
        2 <= n <= snapshot["scope"]["max_requests"] <= 3
        and len(slots) == n == run["context"]["requests"]
        and 1 <= len(ops) <= 4
    )
    ordered = _origins(c, rid, rows)
    require({s["attempt_id"] for s in slots} == {a["id"] for a in rows})
    proof = None
    if run["status"] == "SUCCEEDED":
        from .protocol_reviews import review_proof

        proof = review_proof(store, c, user, rid)
    summary = audit_pool(c, snapshot["request_pool_id"])
    require(
        summary["consistent"]
        and not summary["halted"]
        and not summary["has_pending"]
        and not summary["has_unknown"]
    )
    require(
        type(data["version"]) is int
        and data["version"] == 1
        and type(data["halted"]) is bool
        and not data["halted"]
        and type(data["reserved"]) is int
        and type(data["known_tokens"]) is int
        and data["scope_fingerprint"] == fingerprint(snapshot["scope"])
        and type(data["slots"]) is list
        and len(data["slots"]) == n
        and set(data["stage_started"]) == {provider_stage(snapshot)}
    )
    payload = snapshot["payload"]
    trace, metadata, used, output = [], [], set(), None
    total_reserved = total_tokens = 0
    all_origins, ordered_slots = [], []
    for i, a, origin in ordered:
        params, raw = a["parameters"], a["response"]
        slot = next(s for s in slots if s["attempt_id"] == a["id"])
        pslot = data["slots"][i]
        genesis = c.execute(
            select(events.c.id).where(
                events.c.run_id == slot["pool_id"], events.c.kind == "PROTOCOL_POOL_INITIALIZED"
            )
        ).scalar_one()
        require(
            origin["namespace"] == VERSION
            and origin["phase"] == "source"
            and origin["run_id"] == rid
            and origin["attempt_id"] == a["id"]
            and origin["principal_id"] == user
            and origin["project_id"] == run["project_id"]
            and origin["runtime_id"] == run["runtime_id"]
            and origin["request_key"] == run["request_key"]
            and origin["accepted_fingerprint"] == job["fingerprint"]
            and origin["pool_genesis"] == genesis
            and origin["fence"] == slot["fence"]
            and type(origin["fence"]) is int
            and slot["phase"] == "source"
            and fingerprint(origin["pool_slot"]) == fingerprint(_reserved_seal(slot))
            and origin["request_fingerprint"]
            == params["request_fingerprint"]
            == slot["request_fingerprint"]
            and fingerprint(origin["wire"]) == fingerprint(params["protocol_wire"])
            and origin["provider_stage"] == provider_stage(snapshot)
            and origin["provider_scope_fingerprint"] == fingerprint(snapshot["scope"])
            and origin["sidecar_name"] == rid + ".json"
            and a["status"] == slot["status"] == "RECEIVED"
            and a["mode"] == "MOCK"
        )
        if all_origins:
            require(
                all(
                    origin[k] == all_origins[0][k]
                    for k in (
                        "fence",
                        "deadline",
                        "provider_deadline",
                        "provider_stage",
                        "pool_genesis",
                    )
                )
            )
        require(type(raw) is dict and fingerprint(safe_response(raw)) == fingerprint(raw))
        identity = returned_model_identity("intern-s2", raw.get("model"))
        require_returned_model(identity)
        usage = normalize_usage(raw)
        require(
            usage["status"] == "known"
            and fingerprint(usage) == fingerprint(a["usage"]) == fingerprint(slot["usage"])
            and fingerprint(identity) == fingerprint(params["model_identity"])
            and a["response_model"] == raw["model"]
            and a["request_model"] == "intern-s2"
            and params["max_tokens"] == 1024
            and fingerprint(raw)
            == params["safe_response_fingerprint"]
            == slot["safe_response_fingerprint"]
        )
        require(
            fingerprint(pslot["protocol_origin_v2"]) == fingerprint(origin)
            and pslot["status"] == "RECEIVED"
            and pslot["stage"] == origin["provider_stage"]
            and type(pslot["bytes"]) is int
            and type(pslot["chars"]) is int
            and pslot["body_sha256"] == origin["wire"]["sha256"]
            and pslot["bytes"] == origin["wire"]["bytes"]
            and pslot["chars"] == origin["wire"]["characters"]
            and type(pslot["reserved"]) is int
            and pslot["reserved"]
            == a["reserved_tokens"]
            == slot["reserved_tokens"]
            == pslot["bytes"] + 1024
            and pslot["bytes"] <= 10000
            and pslot["chars"] <= 8000
            and type(pslot["tokens"]) is int
            and pslot["tokens"] == usage["tokens"]["total_tokens"] <= pslot["reserved"]
            and usage["tokens"]["completion_tokens"] <= 1024
            and fingerprint(pslot["normalized_usage_v2"]) == fingerprint(usage)
            and pslot["safe_response_fingerprint_v2"] == fingerprint(raw)
            and type(params.get("raw_response_fingerprint")) is str
            and pslot["raw_response_fingerprint_v2"] == params["raw_response_fingerprint"]
        )
        started, sent_at = data["stage_started"][pslot["stage"]], pslot["time"]
        require(
            type(started) in (int, float)
            and math.isfinite(started)
            and type(sent_at) in (int, float)
            and math.isfinite(sent_at)
            and started <= sent_at < started + 300 == origin["provider_deadline"]
            and (i == 0 or sent_at >= data["slots"][i - 1]["time"] + 6)
        )
        message, calls = parse_response(raw)
        require(bool(calls) == (i < n - 1))
        metadata.append(dict(identity=identity, usage=usage))
        for call in calls:
            tool, args = call["function"]["name"], call["args"]
            require(
                tool == "resource.read"
                and tool in snapshot["scope"]["tool_refs"]
                and args.get("resource_id") in payload["resource_ids"]
            )
            cid = "protocol:" + fingerprint(dict(attempt_id=a["id"], tool_call_id=call["id"]))
            matched = [o for o in ops if o["call_id"] == cid]
            require(len(matched) == 1 and matched[0]["id"] not in used)
            op = matched[0]
            intent = c.execute(
                select(operation_intents.c.request).where(
                    operation_intents.c.operation_id == op["id"]
                )
            ).scalar_one()
            require(
                op["status"] == "VERIFIED"
                and op["tool_ref"] == tool
                and fingerprint(intent)
                == op["fingerprint"]
                == fingerprint(dict(tool=tool, args=args))
            )
            value = authorized_read(
                store, c, user, run["runtime_id"], run["project_id"], tool, args
            )
            validate_value(OUTPUTS[tool], value, "trusted_read")
            require(value["resource_id"] == args["resource_id"])
            expected = dict(
                operation_id=op["id"],
                status="VERIFIED",
                data=value,
                artifact_refs=[],
                receipt_ref=op["id"],
                check_results=[dict(check="receipt.readback.v1", status="PASS")],
                usage_ref=None,
                error=None,
            )
            require(fingerprint(op["receipt"]) == fingerprint(expected))
            trace.append(dict(tool=tool, args=args, data=value))
            used.add(op["id"])
        if not calls:
            output = strict_json(message["content"], 16000)
            require(
                type(output) is dict and pslot["response_json_fingerprint"] == fingerprint(output)
            )
        total_reserved += pslot["reserved"]
        total_tokens += pslot["tokens"]
        all_origins.append(origin)
        ordered_slots.append(slot)
    require(
        len(used) == len(ops)
        and data["reserved"] == total_reserved <= 24000
        and data["known_tokens"] == total_tokens <= 24000
    )
    evidence = dict(
        goal=payload["goal"],
        inputs=payload["inputs"],
        resource_ids=payload["resource_ids"],
        tool_trace=trace,
        output=output,
        attempts=metadata,
    )
    _no_gold(evidence)
    result = dict(
        kind="model-protocol.v1",
        status="AWAITING_EVALUATION",
        semantic_status="UNKNOWN",
        evidence=evidence,
        verification=None,
    )
    # This final frozen context must be the actual final request, including tools.
    from .model_protocol import TOOLS

    tools = [
        dict(type="function", function=dict(name=t, description=t, parameters=TOOLS[t]))
        for t in snapshot["scope"]["tool_refs"]
    ]
    last = ordered[-1][1]
    require(
        fingerprint(
            _wire(
                run["context"]["messages"],
                tools,
                last["request_model"],
                last["parameters"]["max_tokens"],
            )
        )
        == fingerprint(all_origins[-1]["wire"])
    )
    seals = dict(
        attempts=[_attempt_seal(a) for _, a, _ in ordered],
        slots=[_finished_seal(s) for s in ordered_slots],
        operations=[_operation_seal(c, o) for o in sorted(ops, key=lambda o: o["id"])],
    )
    experiment = _experiment(c, job, run, ordered, proof)
    return job, run, ordered[-1][1]["id"], all_origins, result, seals, experiment


def _bounds(store, c, run, witness, settings, *, current=True):
    frozen = store.frozen_contract(c, run)
    bounds = [
        run["created_at"]
        + (
            min(frozen.limits.run_seconds, settings.run_seconds)
            if current
            else frozen.limits.run_seconds
        )
    ]
    for origin in witness["origins"]:
        bounds.extend([origin["deadline"], origin["provider_deadline"]])
    if witness["experiment"] is not None:
        bounds.append(witness["experiment"]["binding"]["bound_at"] + 300)
        for send, settlement in zip(
            witness["experiment"]["sends"], witness["experiment"]["settlements"], strict=True
        ):
            require(
                run["created_at"] <= send["at"] <= settlement["at"] <= witness["ready_at"]
                and witness["experiment"]["binding"]["bound_at"] <= send["at"]
            )
    require(
        all(type(x) in (int, float) and math.isfinite(x) for x in bounds)
        and type(witness["ready_at"]) in (int, float)
        and math.isfinite(witness["ready_at"])
    )
    return bounds


def _deadlines(store, c, run, job, witness, settings):
    bounds = _bounds(store, c, run, witness, settings)
    require(
        run["created_at"] <= witness["ready_at"] <= time.time() < min(bounds),
        "Original Source completion deadline expired",
    )


def _admission(c, rid, witness, version, fence):
    """Only the original claim or its one existing metadata-only recovery."""
    v, f = witness["ready_version"], witness["ready_fence"]
    require(type(v) is int and type(f) is int and f == witness["origins"][0]["fence"])
    if (version, fence) == (v, f):
        return dict(kind="original", version=v, fence=f)
    require((version, fence) == (v + 1, f + 1), "Unknown Source ownership transition")
    states = list(
        c.execute(
            select(events.c.data).where(
                events.c.run_id == rid, events.c.kind == "PROTOCOL_RECOVERY_STATE"
            )
        ).scalars()
    )
    expected_state = dict(
        status="WAITING_RESOURCE",
        reason="CONTINUATION_NOT_IMPLEMENTED",
        provider_requests=0,
        receipts_preserved=True,
    )
    proofs = [p for p in states if fingerprint(p) == fingerprint(expected_state)]
    requests = list(
        c.execute(
            select(events.c.data).where(
                events.c.run_id == rid, events.c.kind == "PROTOCOL_RECOVERY_REQUEST"
            )
        ).scalars()
    )
    for p in requests:
        if type(p) is not dict or set(p) != {"request_key", "request_fingerprint", "response"}:
            continue
        response = p["response"]
        if type(response) is not dict or type(response.get("global_send_blocked")) is not bool:
            continue
        expected_response = dict(
            namespace="protocol-recovery.v1",
            run_id=rid,
            status="WAITING_RESOURCE",
            version=v + 1,
            fence=f + 1,
            recovery="CONTINUATION_NOT_IMPLEMENTED",
            provider_requests=0,
            automatic_resend=False,
            global_send_blocked=response["global_send_blocked"],
            cached=False,
        )
        if fingerprint(response) == fingerprint(expected_response) and p[
            "request_fingerprint"
        ] == fingerprint(dict(expected_version=v, expected_fence=f, request_key=p["request_key"])):
            proofs.append(p)
    require(len(proofs) == 1, "Original metadata-only recovery witness required")
    return dict(
        kind="state-only-recovery",
        version=version,
        fence=fence,
        witness_fingerprint=fingerprint(proofs[0]),
    )


@_stored
def persist_ready(worker, run, snapshot, provider, result):
    with worker.store.tx() as c:
        rows = _rows(c, attempts, run["id"])
        if not any(a["parameters"].get("source_origin_v2") for a in rows):
            return False
        from .protocol_jobs import verified_pending

        verified_pending(worker.store, c, run["principal_id"], run["id"])
    with sidecar(worker.s.data_dir, run["id"]) as data, worker.store.tx() as c:
        worker.store.lock_project(c, run["principal_id"], run["project_id"])
        worker.store.guard(c, run["id"], run["fence"])
        job, current, aid, origins, actual, seals, experiment = _facts(
            worker.store, c, run["principal_id"], run["id"], data
        )
        require(
            fingerprint(result) == fingerprint(actual)
            and fingerprint(snapshot) == job["fingerprint"]
            and provider.path.absolute() == sidecar_path(worker.s.data_dir, run["id"])
            and not current["cancel_intent"]
        )
        witness = dict(
            namespace=VERSION,
            origins=origins,
            seals=seals,
            result_fingerprint=fingerprint(actual),
            provider_ledger_fingerprint=fingerprint(data),
            experiment=experiment,
            ready_at=time.time(),
            ready_version=current["version"],
            ready_fence=current["fence"],
        )
        _deadlines(worker.store, c, current, job, witness, worker.s)
        _mirror(worker.store, c, run["id"], aid, READY, witness)
        return True


@_stored
def _verified(store, c, user, rid, data):
    facts = _facts(store, c, user, rid, data)
    _, _, aid, origins, result, seals, experiment = facts
    witness = _one(c, rid, READY)
    require(
        fingerprint(witness) == fingerprint(_one(c, aid, READY))
        and witness["namespace"] == VERSION
        and fingerprint(witness["origins"]) == fingerprint(origins)
        and fingerprint(witness["seals"]) == fingerprint(seals)
        and witness["result_fingerprint"] == fingerprint(result)
        and witness["provider_ledger_fingerprint"] == fingerprint(data)
        and fingerprint(witness["experiment"]) == fingerprint(experiment)
    )
    return facts, witness


@_stored
def complete_source(store, user, rid, request, settings):
    """Owner-only, original known facts only. No model/runner is constructed."""
    from .protocol_jobs import complete_in_tx, verified_pending

    request = CompletionInput.model_validate(request)
    if not store.test_only or settings.mode != "mock":
        raise DomainError("PERMISSION_DENIED", "Original offline protocol boundary required")
    with store.tx() as c:
        job, run = verified_pending(store, c, user, rid)
        require(job["phase"] == "source" and not job["snapshot"].get("bounded_check_namespace"))
    with sidecar(settings.data_dir, rid) as data, store.tx() as c:
        facts, witness = _verified(store, c, user, rid, data)
        job, run, aid, origins, result, _, _ = facts
        prior = list(
            c.execute(
                select(events.c.data).where(events.c.run_id == rid, events.c.kind == COMPLETED)
            ).scalars()
        )
        if prior:
            require(
                len(prior) == 1 and fingerprint(prior[0]) == fingerprint(_one(c, aid, COMPLETED))
            )
            old = prior[0]
            response = old["response"]
            require(
                fingerprint(old["request"]) == fingerprint(request.model_dump())
                and response["namespace"] == VERSION
                and response["run_id"] == rid
                and response["status"] == "WAITING_APPROVAL"
                and not run["cancel_intent"]
                and run["error"] is None
                and response["version"]
                == request.expected_version + 1
                == job["result"]["completed_run_version"]
                and response["fence"]
                == run["fence"]
                == job["completed_fence"]
                == request.expected_fence + 1
                and response["result_fingerprint"] == job["result_fingerprint"]
                and old["original_send_fence"] == origins[0]["fence"]
                and old["recovery_fence"] == run["fence"]
                and type(old["completed_at"]) in (int, float)
                and math.isfinite(old["completed_at"])
                and run["created_at"]
                <= witness["ready_at"]
                <= old["completed_at"]
                < min(_bounds(store, c, run, witness, settings, current=False))
            )
            expected_response = dict(
                namespace=VERSION,
                run_id=rid,
                status="WAITING_APPROVAL",
                version=request.expected_version + 1,
                fence=request.expected_fence + 1,
                result_fingerprint=job["result_fingerprint"],
                provider_requests=0,
                automatic_resend=False,
                cached=False,
            )
            require(
                fingerprint(response) == fingerprint(expected_response)
                and fingerprint(old["admission"])
                == fingerprint(
                    _admission(c, rid, witness, request.expected_version, request.expected_fence)
                )
            )
            if run["status"] == "SUCCEEDED":
                from .protocol_reviews import review_proof

                review_proof(store, c, user, rid)
                require(run["version"] == response["version"] + 1)
            else:
                require(
                    run["status"] == "WAITING_APPROVAL" and run["version"] == response["version"]
                )
            return dict(response, cached=True)
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
            "Only an expired uncancelled incomplete Source can finish",
        )
        admission = _admission(c, rid, witness, request.expected_version, request.expected_fence)
        if admission["kind"] == "state-only-recovery":
            require(
                run["status"] == "WAITING_RESOURCE"
                and run["lease_until"] == 0
                and run["worker_id"] is None
                and fingerprint(run["error"])
                == fingerprint(dict(code="CONTINUATION_NOT_IMPLEMENTED"))
            )
        else:
            require(run["error"] is None)
        _deadlines(store, c, run, job, witness, settings)
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
            .values(fence=new_fence, error=None)
        )
        require(changed.rowcount == 1, "Source recovery fence changed")
        complete_in_tx(
            store, c, dict(run, fence=new_fence), job["snapshot"], result, None, new_fence
        )
        fresh_facts, fresh_witness = _verified(store, c, user, rid, data)
        fresh_job, fresh = fresh_facts[:2]
        require(
            fingerprint(witness) == fingerprint(fresh_witness)
            and not fresh["cancel_intent"]
            and fresh["status"] == "WAITING_APPROVAL"
            and fresh["fence"] == new_fence
            and fresh["version"] == run["version"] + 1
        )
        _deadlines(store, c, fresh, fresh_job, witness, settings)
        response = dict(
            namespace=VERSION,
            run_id=rid,
            status="WAITING_APPROVAL",
            version=fresh["version"],
            fence=new_fence,
            result_fingerprint=fresh_job["result_fingerprint"],
            provider_requests=0,
            automatic_resend=False,
            cached=False,
        )
        _mirror(
            store,
            c,
            rid,
            aid,
            COMPLETED,
            dict(
                request=request.model_dump(),
                response=response,
                completed_at=time.time(),
                original_send_fence=origins[0]["fence"],
                recovery_fence=new_fence,
                admission=admission,
            ),
        )
        final_job, final_run = verified_pending(store, c, user, rid)
        require(
            not final_run["cancel_intent"]
            and final_run["status"] == "WAITING_APPROVAL"
            and final_run["fence"] == new_fence
            and final_run["version"] == fresh["version"]
        )
        _deadlines(store, c, final_run, final_job, witness, settings)
        return response
