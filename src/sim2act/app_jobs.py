"""Bounded internal AppRun queue using the existing durable Worker/Run lease ledger.

Registered pure CSV or explicitly offline R0 agent and atomic typed-result append; no LIVE,
new identity/grant, publication, deployment, external effects or generic business writes.
"""

import copy
import threading
import time

from sqlalchemy import insert, select, update

from .apps import validate_frozen_candidate
from .contracts import (
    FrozenRunContract,
    GoalSpec,
    Limits,
    ResourceSnapshot,
    validate_action_input,
    validate_value,
)
from .db import (
    events,
    fingerprint,
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    internal_run_bindings,
    new_id,
    operation_intents,
    operations,
    resources,
    run_contracts,
    runs,
)
from .errors import DomainError
from .extraction import exact_sum_oracle
from .lifecycle import NAMESPACE, data_rows, instance, read_release
from .tools import aggregate_csv_content, authorized_read

KIND = "INTERNAL_APPRUN"


def is_app_job(store, rid):
    with store.engine.connect() as c:
        context = c.execute(select(runs.c.context).where(runs.c.id == rid)).scalar()
        binding = c.execute(
            select(internal_run_bindings.c.run_id).where(internal_run_bindings.c.run_id == rid)
        ).first()
        return bool(binding or (isinstance(context, dict) and context.get("kind") == KIND))


def enqueue(
    store, user, iid, expected_revision, release_fp, input_value, key, limits,
    *, offline_replay=None, require_offline_replay=False,
):
    if not isinstance(key, str) or not 1 <= len(key) <= 100:
        raise DomainError("INVALID_INPUT")
    with store.tx() as c:
        pid = c.execute(
            select(internal_instances.c.project_id).where(internal_instances.c.id == iid)
        ).scalar()
        store.lock_project(c, user, pid)
        i, release = instance(store, c, user, iid, limits, lock=True)
        if "execution_source" in release["snapshot"]:
            from .csv_dag_instances import enqueue_tx
            if offline_replay is not None:
                raise DomainError("INVALID_INPUT", "DAG execution does not accept model replay")
            return enqueue_tx(store, c, user, i, release, expected_revision, release_fp, input_value, key, limits)
        from .agent_apps import is_agent, offline_replay_model

        agent = is_agent(release["snapshot"]["draft"]["candidate"])
        if (not agent and offline_replay is not None) or (
            agent and require_offline_replay and offline_replay is None
        ):
            raise DomainError("INVALID_INPUT", "Explicit offline Replay required only for agent")
        if offline_replay is not None:
            offline_replay = offline_replay_model(offline_replay).responses
        request = {
            "instance_id": iid,
            "expected_revision": expected_revision,
            "expected_release_fp": release_fp,
            "input": input_value,
        }
        if offline_replay is not None:
            request["offline_replay"] = offline_replay
        fp = fingerprint(request)
        old = (
            c.execute(
                select(internal_app_runs).where(
                    internal_app_runs.c.instance_id == iid,
                    internal_app_runs.c.principal_id == user,
                    internal_app_runs.c.request_key == key,
                )
            )
            .mappings()
            .first()
        )
        if old:
            binding = (
                c.execute(
                    select(internal_run_bindings).where(
                        internal_run_bindings.c.app_run_id == old["id"]
                    )
                )
                .mappings()
                .first()
            )
            if not binding or old["fingerprint"] != fp:
                raise DomainError("VERSION_CONFLICT")
            job = c.execute(select(runs).where(runs.c.id == binding["run_id"])).mappings().one()
            load_binding(store, c, user, job, limits)
            return {
                "run_id": job["id"],
                "app_run_id": old["id"],
                "status": job["status"],
                "version": job["version"],
                "cached": True,
                "namespace": NAMESPACE,
            }
        if i["revision"] != expected_revision or release["fingerprint"] != release_fp:
            raise DomainError("VERSION_CONFLICT")
        # Strict input validation happens in the worker so accepted bad inputs keep FAILED history.
        jid, aid = new_id("run"), new_id("iapprun")
        draft = release["snapshot"]["draft"]
        resource_ref = draft["candidate"]["manifest"]["data_bindings"][0]["resource_ref"]
        source = c.execute(select(resources).where(resources.c.id == resource_ref)).mappings().one()
        snapshot = {
            **copy.deepcopy(request),
            "run_id": jid,
            "app_run_id": aid,
            "release_id": release["id"],
            "principal_id": user,
            "project_id": pid,
            "runtime_id": i["runtime_id"],
            "request_fingerprint": fp,
            "limits": limits.model_dump(),
            "namespace": KIND,
            "model_requests": 0,
        }
        goal = "Internal fixed Release result run"
        contract = FrozenRunContract(
            run_id=jid,
            runtime_id=i["runtime_id"],
            contract_version="F1.3",
            goal=GoalSpec(
                goal_id=new_id("goal"),
                project_id=pid,
                owner_id=user,
                goal=goal,
                constraints=[],
                acceptance_version="F1-tool-chain.v1",
                resource_refs=[resource_ref],
                unresolved=["Formal publication disabled; typed result only"],
            ),
            resources=[
                ResourceSnapshot(
                    resource_id=resource_ref,
                    revision=1,
                    content_hash=source["hash"],
                    format=source["format"],
                )
            ],
            limits=limits,
            mode="mock",
            request_model="intern-s2",
        ).model_dump()
        c.execute(
            insert(run_contracts).values(
                run_id=jid, snapshot=contract, fingerprint=fingerprint(contract)
            )
        )
        c.execute(
            insert(runs).values(
                id=jid,
                project_id=pid,
                principal_id=user,
                runtime_id=i["runtime_id"],
                goal=goal,
                resource_refs=[resource_ref],
                status="QUEUED",
                request_key="internal:" + aid,
                fingerprint=fingerprint(snapshot),
                created_at=time.time(),
                lease_until=0,
                fence=0,
                context={
                    "kind": KIND,
                    "messages": [],
                    "requests": 0,
                    "tools": 0,
                    "repairs": 0,
                    "reserved_tokens": 0,
                },
                version=1,
                cancel_intent=False,
            )
        )
        c.execute(
            insert(internal_app_runs).values(
                id=aid,
                instance_id=iid,
                release_id=release["id"],
                principal_id=user,
                request_key=key,
                fingerprint=fp,
                input=copy.deepcopy(input_value),
                status="QUEUED",
                output=None,
                error=None,
                result_version=None,
            )
        )
        c.execute(
            insert(internal_run_bindings).values(
                run_id=jid, app_run_id=aid, snapshot=snapshot, fingerprint=fingerprint(snapshot)
            )
        )
        store.event(
            c,
            jid,
            "ACCEPTED",
            {
                "namespace": KIND,
                "app_run_id": aid,
                "instance_id": iid,
                "release_id": release["id"],
                "input_fingerprint": fp,
            },
        )
        return {
            "run_id": jid,
            "app_run_id": aid,
            "status": "QUEUED",
            "version": 1,
            "cached": False,
            "namespace": NAMESPACE,
        }


def load_binding(store, c, user, job, limits, *, authorize=True):
    b = (
        c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == job["id"]))
        .mappings()
        .first()
    )
    if not b or job["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    s = b["snapshot"]
    a = (
        c.execute(select(internal_app_runs).where(internal_app_runs.c.id == b["app_run_id"]))
        .mappings()
        .first()
    )
    if not a or fingerprint(s) != b["fingerprint"] or job["fingerprint"] != b["fingerprint"]:
        raise DomainError("VERSION_CONFLICT", "Queue binding fingerprint changed")
    request = {
        k: s[k] for k in ["instance_id", "expected_revision", "expected_release_fp", "input"]
    }
    if "offline_replay" in s:
        request["offline_replay"] = s["offline_replay"]
    if (
        s["namespace"] != KIND
        or job["context"].get("kind") != KIND
        or s["model_requests"] != 0
        or s["run_id"] != job["id"]
        or s["app_run_id"] != a["id"]
        or s["principal_id"] != user
        or s["project_id"] != job["project_id"]
        or s["runtime_id"] != job["runtime_id"]
        or a["instance_id"] != s["instance_id"]
        or a["release_id"] != s["release_id"]
        or a["principal_id"] != user
        or a["input"] != s["input"]
        or a["fingerprint"] != s["request_fingerprint"]
        or fingerprint(request) != s["request_fingerprint"]
    ):
        raise DomainError("VERSION_CONFLICT", "AppRun no longer matches accepted queue binding")
    store.own_project(c, user, s["project_id"])
    if authorize:
        contract = store.frozen_contract(c, job)
        if contract.limits.model_dump() != s["limits"]:
            raise DomainError("VERSION_CONFLICT", "Accepted limits no longer match frozen envelope")
        r = read_release(store, c, user, s["release_id"], limits)
        if "offline_replay" in s:
            from .agent_apps import is_agent, offline_replay_model

            if not is_agent(r["snapshot"]["draft"]["candidate"]):
                raise DomainError("VERSION_CONFLICT", "Offline Replay cannot change executor family")
            offline_replay_model(s["offline_replay"])
        if (
            r["fingerprint"] != s["expected_release_fp"]
            or r["project_id"] != s["project_id"]
            or r["snapshot"]["draft"]["runtime_id"] != s["runtime_id"]
            or job["resource_refs"]
            != [r["snapshot"]["draft"]["candidate"]["manifest"]["data_bindings"][0]["resource_ref"]]
        ):
            raise DomainError("VERSION_CONFLICT")
    return s, a


def inspect_job(store, user, rid):
    with store.tx() as c:
        job = c.execute(select(runs).where(runs.c.id == rid)).mappings().first()
        if not job or job["principal_id"] != user:
            raise DomainError("PERMISSION_DENIED")
        limits = store.frozen_contract(c, job).limits
        s, a = load_binding(store, c, user, job, limits)
        if job["status"] == "SUCCEEDED":
            from .agent_apps import is_agent, verified_source

            release = read_release(store, c, user, s["release_id"], limits)
            if is_agent(release["snapshot"]["draft"]["candidate"]):
                verified_source(store, c, user, rid, limits, require_initial=False)
        records = data_rows(c, s["instance_id"])
        result = next((dict(r) for r in records if r["run_id"] == a["id"]), None)
        return {
            "id": rid,
            "app_run_id": a["id"],
            "instance_id": s["instance_id"],
            "release_id": s["release_id"],
            "status": job["status"],
            "version": job["version"],
            "cancel_intent": job["cancel_intent"],
            "result": a["output"],
            "result_version": a["result_version"],
            "error": job["error"],
            "known_effects": [result] if result else [],
            "events": [
                dict(x)
                for x in c.execute(
                    select(events).where(events.c.run_id == rid).order_by(events.c.created_at)
                ).mappings()
            ],
            "namespace": KIND,
        }


def command_job(store, user, rid, command, version):
    with store.tx() as c:
        pid = c.execute(select(runs.c.project_id).where(runs.c.id == rid)).scalar()
        store.lock_project(c, user, pid)
        job = c.execute(select(runs).where(runs.c.id == rid).with_for_update()).mappings().first()
        if not job or job["principal_id"] != user:
            raise DomainError("PERMISSION_DENIED")
        # Stop commands must remain possible after revocation. Resume requires current gateway.
        s, a = load_binding(store, c, user, job, None, authorize=False)
        if job["version"] != version:
            raise DomainError("VERSION_CONFLICT")
        state = job["status"]
        unknown = store.has_unknown(c, rid)
        if command == "pause" and state in {"QUEUED", "RUNNING"}:
            state = "PAUSED" if state == "QUEUED" else "PAUSE_REQUESTED"
        elif command == "cancel" and state in {
            "QUEUED",
            "RUNNING",
            "PAUSED",
            "PAUSE_REQUESTED",
            "WAITING_RESOURCE",
            "RECONCILING",
        }:
            state = (
                "RECONCILING"
                if unknown
                else "CANCEL_REQUESTED"
                if state == "RUNNING"
                else "CANCELLED"
            )
        elif (
            command == "resume"
            and state in {"PAUSED", "WAITING_RESOURCE"}
            and not job["cancel_intent"]
        ):
            if unknown:
                raise DomainError("OUTCOME_UNKNOWN")
            load_binding(store, c, user, job, store.frozen_contract(c, job).limits)
            state = "QUEUED"
        else:
            raise DomainError("VERSION_CONFLICT")
        c.execute(
            update(runs)
            .where(runs.c.id == rid)
            .values(
                status=state,
                version=version + 1,
                cancel_intent=job["cancel_intent"] or command == "cancel",
            )
        )
        c.execute(
            update(internal_app_runs).where(internal_app_runs.c.id == a["id"]).values(status=state)
        )
        store.event(c, rid, "COMMAND", {"command": command, "status": state})
        return state


def lock_live(store, c, run):
    store.lock_project(c, run["principal_id"], run["project_id"])
    current = store.guard(c, run["id"], run["fence"])
    if current["worker_id"] != run["worker_id"]:
        raise DomainError("VERSION_CONFLICT")
    return current


def stop_state(job, unknown):
    if unknown:
        return "RECONCILING" if job["cancel_intent"] else "WAITING_RESOURCE"
    return "CANCELLED" if job["cancel_intent"] or job["status"] == "CANCEL_REQUESTED" else "PAUSED"


def state_write(store, c, job, aid, state, error=None, result=None):
    c.execute(
        update(runs)
        .where(runs.c.id == job["id"])
        .values(status=state, error=error, result=result, lease_until=0, version=job["version"] + 1)
    )
    c.execute(
        update(internal_app_runs)
        .where(internal_app_runs.c.id == aid)
        .values(status=state, error=error)
    )
    store.event(c, job["id"], "STATE", {"status": state, "error": error})


def prepare_dispatch(worker, run):
    store = worker.store
    with store.tx() as c:
        job = lock_live(store, c, run)
        if store.has_unknown(c, job["id"]):
            raise DomainError("OUTCOME_UNKNOWN", "Unresolved Run operation blocks dispatch")
        s, a = load_binding(
            store,
            c,
            run["principal_id"],
            job,
            None,
            authorize=False,
        )
        if job["status"] != "RUNNING" or worker.stop.is_set():
            state_write(store, c, job, a["id"], stop_state(job, store.has_unknown(c, job["id"])))
            return None
        if time.time() - job["created_at"] > min(worker.s.run_seconds, s["limits"]["run_seconds"]):
            raise DomainError("BUDGET_EXHAUSTED")
        i = (
            c.execute(
                select(internal_instances)
                .where(internal_instances.c.id == s["instance_id"])
                .with_for_update()
            )
            .mappings()
            .one()
        )
        if (
            i["principal_id"] != s["principal_id"]
            or i["project_id"] != s["project_id"]
            or i["runtime_id"] != s["runtime_id"]
            or i["revision"] != s["expected_revision"]
            or i["release_id"] != s["release_id"]
        ):
            raise DomainError("VERSION_CONFLICT", "Accepted instance revision changed")
        load_binding(
            store,
            c,
            run["principal_id"],
            job,
            Limits(**{k: getattr(worker.s, k) for k in Limits.model_fields}),
        )
        release = read_release(
            store,
            c,
            run["principal_id"],
            s["release_id"],
            Limits(**{k: getattr(worker.s, k) for k in Limits.model_fields}),
        )
        if i["source_app_id"] != release["snapshot"]["draft"]["id"]:
            raise DomainError("VERSION_CONFLICT")
        draft, manifest, action, _ = validate_frozen_candidate(
            store,
            c,
            run["principal_id"],
            release["snapshot"]["draft"],
            Limits(**{k: getattr(worker.s, k) for k in Limits.model_fields}),
        )
        validate_value(manifest.input_schema, s["input"])
        args = {"resource_id": manifest.data_bindings[0].resource_ref, **s["input"]}
        validate_action_input(action, args)
        # Authorization includes both read and exact registered action before dispatch.
        agent = action.executor.kind == "bounded_agent"
        store.authorize(
            c,
            run["principal_id"],
            draft["runtime_id"],
            draft["project_id"],
            args["resource_id"],
            "resource.read" if agent else action.executor.ref,
        )
        source = authorized_read(
            store,
            c,
            run["principal_id"],
            draft["runtime_id"],
            draft["project_id"],
            "resource.read",
            {"resource_id": args["resource_id"]},
        )
        intent = (
            {"tool": "resource.read", "args": {"resource_id": args["resource_id"]}}
            if agent
            else {"tool": action.executor.ref, "args": args}
        )
        old = (
            c.execute(
                select(operations).where(
                    operations.c.run_id == run["id"], operations.c.call_id == "instance_result"
                )
            )
            .mappings()
            .first()
        )
        if old:
            if old["fingerprint"] != fingerprint(intent) or old["status"] != "PREPARED":
                raise DomainError(
                    "OUTCOME_UNKNOWN", "Do not overwrite or redispatch committed/unknown operation"
                )
            oid = old["id"]
            saved = c.execute(
                select(operation_intents.c.request).where(operation_intents.c.operation_id == oid)
            ).scalar()
            if saved != intent:
                raise DomainError("VERSION_CONFLICT")
        else:
            oid = new_id("op")
            c.execute(
                insert(operations).values(
                    id=oid,
                    run_id=run["id"],
                    call_id="instance_result",
                    fingerprint=fingerprint(intent),
                    tool_ref=intent["tool"],
                    status="PREPARED",
                )
            )
            c.execute(insert(operation_intents).values(operation_id=oid, request=intent))
        store.event(
            c,
            run["id"],
            "ACTION_PREPARED",
            {"operation_id": oid, "fence": run["fence"], "source_hash": source["hash"]},
        )
        return {
            "operation_id": oid,
            "source": source,
            "args": args,
            "input": s["input"],
            "manifest": manifest.model_dump(),
            "action": action.model_dump(),
            **({"offline_replay": copy.deepcopy(s["offline_replay"])} if "offline_replay" in s else {}),
        }


def compute(plan, model=None, read=None):
    if plan["action"]["executor"]["kind"] == "bounded_agent":
        from .agent_apps import execute_protocol

        return execute_protocol(plan, model, read)
    # No SQL transaction, arbitrary code or model: same registered trusted implementation.
    value = aggregate_csv_content(
        plan["source"]["content"], plan["args"]["resource_id"], plan["args"]["column"]
    )
    validate_value(plan["action"]["output_schema"], value, "action_output")
    output = {field: value[ref["field"]] for field, ref in plan["manifest"]["outputs"].items()}
    validate_value(plan["manifest"]["output_schema"], output, "output")
    exact_sum_oracle(plan["source"]["content"], plan["input"]["column"], output)
    return output


def commit_result(worker, run, plan, output):
    store = worker.store
    with store.tx() as c:
        job = lock_live(store, c, run)
        if store.has_unknown(c, job["id"]):
            raise DomainError("OUTCOME_UNKNOWN", "Unresolved Run operation blocks result append")
        limits = Limits(**{k: getattr(worker.s, k) for k in Limits.model_fields})
        s, a = load_binding(store, c, run["principal_id"], job, None, authorize=False)
        if job["status"] != "RUNNING" or worker.stop.is_set():
            state_write(store, c, job, a["id"], stop_state(job, store.has_unknown(c, job["id"])))
            return
        i = (
            c.execute(
                select(internal_instances)
                .where(internal_instances.c.id == s["instance_id"])
                .with_for_update()
            )
            .mappings()
            .one()
        )
        if (
            i["revision"] != s["expected_revision"]
            or i["release_id"] != s["release_id"]
            or i["principal_id"] != s["principal_id"]
            or i["project_id"] != s["project_id"]
            or i["runtime_id"] != s["runtime_id"]
        ):
            raise DomainError("VERSION_CONFLICT")
        load_binding(store, c, run["principal_id"], job, limits)
        release = read_release(store, c, run["principal_id"], s["release_id"], limits)
        if i["source_app_id"] != release["snapshot"]["draft"]["id"]:
            raise DomainError("VERSION_CONFLICT")
        draft, manifest, action, _ = validate_frozen_candidate(
            store, c, run["principal_id"], release["snapshot"]["draft"], limits
        )
        args = {"resource_id": manifest.data_bindings[0].resource_ref, **s["input"]}
        source = authorized_read(
            store,
            c,
            run["principal_id"],
            draft["runtime_id"],
            draft["project_id"],
            "resource.read",
            {"resource_id": args["resource_id"]},
        )
        if (
            plan["source"] != source
            or plan["args"] != args
            or plan["input"] != s["input"]
            or plan["manifest"] != manifest.model_dump()
            or plan["action"] != action.model_dump()
            or fingerprint(plan.get("offline_replay")) != fingerprint(s.get("offline_replay"))
        ):
            raise DomainError(
                "VERSION_CONFLICT", "Calculation plan no longer matches accepted source/specs"
            )
        if time.time() - job["created_at"] > min(worker.s.run_seconds, s["limits"]["run_seconds"]):
            raise DomainError("BUDGET_EXHAUSTED")
        op = (
            c.execute(
                select(operations)
                .where(operations.c.id == plan["operation_id"], operations.c.run_id == run["id"])
                .with_for_update()
            )
            .mappings()
            .one()
        )
        intent = c.execute(
            select(operation_intents.c.request).where(operation_intents.c.operation_id == op["id"])
        ).scalar()
        agent = action.executor.kind == "bounded_agent"
        expected_intent = (
            {"tool": "resource.read", "args": {"resource_id": args["resource_id"]}}
            if agent
            else {"tool": plan["action"]["executor"]["ref"], "args": plan["args"]}
        )
        if (
            op["status"] != "PREPARED"
            or intent != expected_intent
            or fingerprint(intent) != op["fingerprint"]
        ):
            raise DomainError("OUTCOME_UNKNOWN")
        # Independently recheck output against current exact frozen bytes before the local append.
        validate_value(
            release["snapshot"]["draft"]["candidate"]["manifest"]["output_schema"], output
        )
        if agent:
            from .agent_apps import check_evidence, validate_accepted_replay, validate_protocol

            check = check_evidence(source, args, output)
            protocol = plan.get("protocol")
            if (
                not isinstance(protocol, dict)
                or protocol.get("check") != check
                or protocol.get("mode") != "OFFLINE_REPLAY"
                or protocol.get("provider_requests") != 0
                or fingerprint(protocol.get("messages")) != protocol.get("fingerprint")
            ):
                raise DomainError("VERIFICATION_FAILED", "Verified offline protocol required")
            validate_protocol(plan, protocol, output)
            if "offline_replay" in s:
                validate_accepted_replay(plan, s["offline_replay"], protocol, output)
            checks = [check]
            identities = {"resource_id": args["resource_id"], "source_hash": source["hash"]}
        else:
            exact_sum_oracle(source["content"], s["input"]["column"], output)
            checks = [{"check": "csv.exact_integer_sum.v1", "status": "PASS"}]
            identities = {
                "resource_id": args["resource_id"],
                "column": s["input"]["column"],
                "source_hash": source["hash"],
            }
        for field, ref in manifest.outputs.items():
            if ref.field in identities and output[field] != identities[ref.field]:
                raise DomainError(
                    "VERIFICATION_FAILED", "Output source identity differs from accepted input"
                )
        data = {"result": output}
        if "release_ref" in release["snapshot"]["data_schema"]["properties"]:
            data["release_ref"] = release["id"]
        validate_value(release["snapshot"]["data_schema"], data, "instance_record")
        version = i["data_version"] + 1
        c.execute(
            insert(internal_instance_data).values(
                instance_id=i["id"],
                version=version,
                run_id=a["id"],
                release_id=release["id"],
                schema_version=release["snapshot"]["data_schema_version"],
                data=data,
                fingerprint=fingerprint(data),
            )
        )
        if (
            c.execute(
                update(internal_instances)
                .where(
                    internal_instances.c.id == i["id"],
                    internal_instances.c.data_version == i["data_version"],
                    internal_instances.c.revision == s["expected_revision"],
                )
                .values(data_version=version)
            ).rowcount
            != 1
        ):
            raise DomainError("VERSION_CONFLICT")
        receipt = {
            "operation_id": op["id"],
            "status": "VERIFIED",
            "app_run_id": a["id"],
            "instance_id": i["id"],
            "release_id": release["id"],
            "result_version": version,
            "output_fingerprint": fingerprint(output),
            "data": output,
            "artifact_refs": [],
            "check_results": checks,
        }
        if agent:
            receipt["protocol"] = plan["protocol"]
        c.execute(
            update(operations)
            .where(operations.c.id == op["id"])
            .values(status="VERIFIED", receipt=receipt)
        )
        c.execute(
            update(internal_app_runs)
            .where(internal_app_runs.c.id == a["id"])
            .values(status="SUCCEEDED", output=output, error=None, result_version=version)
        )
        state_write(
            store,
            c,
            job,
            a["id"],
            "SUCCEEDED",
            result={
                "app_run_id": a["id"],
                "instance_id": i["id"],
                "release_id": release["id"],
                "result_version": version,
                "receipt_ref": op["id"],
            },
        )
        store.event(
            c, job["id"], "RESULT_COMMITTED", {"operation_id": op["id"], "result_version": version}
        )


def fail_job(worker, run, error):
    # Contract rejection also needs lease/status fencing, but cannot require the bad contract.
    store = worker.store
    with store.tx() as c:
        store.lock_project(c, run["principal_id"], run["project_id"])
        job = (
            c.execute(select(runs).where(runs.c.id == run["id"]).with_for_update()).mappings().one()
        )
        if (
            job["fence"] != run["fence"]
            or job["worker_id"] != run["worker_id"]
            or job["lease_until"] <= time.time()
            or job["status"] not in {"RUNNING", "PAUSE_REQUESTED", "CANCEL_REQUESTED"}
        ):
            return
        b = (
            c.execute(
                select(internal_run_bindings).where(internal_run_bindings.c.run_id == run["id"])
            )
            .mappings()
            .first()
        )
        # A corrupt raw pointer must never let rejection mutate another instance's history.
        # The independently accepted Run fingerprint anchors the original snapshot even if
        # the binding's own fingerprint field was altered. Without it, save only Run error.
        aid = ""
        if b:
            s = b["snapshot"]
            if (
                fingerprint(s) == job["fingerprint"]
                and s.get("run_id") == job["id"]
                and s.get("app_run_id") == b["app_run_id"]
                and s.get("principal_id") == job["principal_id"]
                and s.get("project_id") == job["project_id"]
                and s.get("runtime_id") == job["runtime_id"]
            ):
                a = (
                    c.execute(
                        select(internal_app_runs).where(
                            internal_app_runs.c.id == b["app_run_id"],
                            internal_app_runs.c.principal_id == job["principal_id"],
                            internal_app_runs.c.instance_id == s.get("instance_id"),
                            internal_app_runs.c.release_id == s.get("release_id"),
                            internal_app_runs.c.fingerprint == s.get("request_fingerprint"),
                        )
                    )
                    .mappings()
                    .first()
                )
                if a:
                    aid = a["id"]
        unknown = store.has_unknown(c, run["id"]) or error.code == "OUTCOME_UNKNOWN"
        state = (
            stop_state(job, unknown)
            if job["status"] != "RUNNING" or unknown
            else "WAITING_RESOURCE"
            if error.code in {"GRANT_REVOKED", "RESOURCE_UNAVAILABLE", "PERMISSION_DENIED"}
            else "FAILED"
        )
        state_write(store, c, job, aid, state, error.public())


def process_job(worker, run):
    stopped = threading.Event()

    def beat():
        while not stopped.wait(worker.s.lease_seconds / 3):
            try:
                worker.store.heartbeat(worker.id, run["id"], run["fence"], worker.s.lease_seconds)
            except Exception:
                stopped.set()

    thread = threading.Thread(target=beat, daemon=True)
    thread.start()
    try:
        plan = prepare_dispatch(worker, run)
        if plan is not None:
            if plan["action"]["executor"]["kind"] == "bounded_agent":

                def read(args):
                    with worker.store.tx() as c:
                        current = lock_live(worker.store, c, run)
                        if current["status"] != "RUNNING" or worker.stop.is_set():
                            raise DomainError("VERSION_CONFLICT")
                        limits = Limits(**{k: getattr(worker.s, k) for k in Limits.model_fields})
                        load_binding(worker.store, c, run["principal_id"], current, limits)
                        return authorized_read(
                            worker.store,
                            c,
                            run["principal_id"],
                            run["runtime_id"],
                            run["project_id"],
                            "resource.read",
                            args,
                        )

                if "offline_replay" in plan:
                    from .agent_apps import offline_replay_model

                    model = offline_replay_model(plan["offline_replay"])
                else:
                    model = worker.model  # Legacy explicit in-memory Replay; exact type enforced.
                output = compute(plan, model, read)
            else:
                output = compute(plan)
            commit_result(worker, run, plan, output)
    except DomainError as exc:
        fail_job(worker, run, exc)
    finally:
        stopped.set()
        thread.join(timeout=2)
