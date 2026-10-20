"""Bounded internal AppRun queue using the existing durable Worker/Run lease ledger.

Registered pure CSV or explicitly offline R0 agent and atomic typed-result append; no LIVE,
new identity/grant, publication, deployment, external effects or generic business writes.
"""

import copy
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

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


SUBMISSION_REJECTION = "internal-run-rejection.v1"


def rejection_proof(c, user, iid, pid, key, submission, phase):
    from .db import delivery_graph_requests
    from .spec_run_terminals import fenced
    if fenced(c, user, iid, key):
        return None
    # Project lock is held; scalar existence reads never inspect accepted bodies.
    owned = c.execute(select(internal_instances.c.id).where(
        internal_instances.c.id == iid, internal_instances.c.principal_id == user,
        internal_instances.c.project_id == pid)).first()
    if not owned:
        return None
    old = c.execute(select(internal_app_runs.c.id).where(
        internal_app_runs.c.instance_id == iid, internal_app_runs.c.principal_id == user,
        internal_app_runs.c.request_key == key)).first()
    ledger = c.execute(select(delivery_graph_requests.c.request_key).where(
        delivery_graph_requests.c.app_id == iid, delivery_graph_requests.c.principal_id == user,
        delivery_graph_requests.c.request_key == key)).first()
    if old or ledger:
        return None
    return dict(namespace=SUBMISSION_REJECTION, endpoint=submission["endpoint"],
        principal_id=user, project_id=pid, instance_id=iid, request_key=key,
        request_fingerprint=fingerprint(submission["body"]), acceptance="NOT_ACCEPTED",
        previous_request="ABSENT", phase=phase)


@contextmanager
def submission_tx(store, guard):
    failure = None
    try:
        with store.tx() as c:
            try:
                yield c
            except DomainError as exc:
                failure = exc
                raise
    except DomainError as exc:
        # Only the body failed, and the transaction has successfully rolled back.
        # A commit/rollback/connection failure, cached key or unknown effect has no proof.
        if (exc is failure and guard.get("proof") and exc.code in {
                "INVALID_INPUT", "VERSION_CONFLICT", "GRANT_REVOKED", "PERMISSION_DENIED",
                "RESOURCE_UNAVAILABLE", "UNSUPPORTED_CAPABILITY"}):
            exc.submission_rejection = guard["proof"]
        raise


def enqueue(
    store, user, iid, expected_revision, release_fp, input_value, key, limits,
    *, offline_replay=None, require_offline_replay=False, owner_goal_fp=None, pb_use=None, submission=None, human_correction=None, pa_use=None, logic_check=None, logic_tx=None, project_check=None, csv_review=None, csv_goal_check=None,
):
    if not isinstance(key, str) or not 1 <= len(key) <= 100:
        raise DomainError("INVALID_INPUT")
    if csv_goal_check is not None and any(x is not None for x in (pa_use,pb_use,human_correction,offline_replay,owner_goal_fp,logic_check,project_check)):
        raise DomainError("INVALID_INPUT", "CSV Goal checks cannot change another execution mode")
    if pa_use is not None and (pb_use is not None or human_correction is not None or offline_replay is not None or owner_goal_fp is not None):
        raise DomainError("INVALID_INPUT", "Per-use modes are mutually exclusive")
    if human_correction is not None and (pb_use is not None or offline_replay is not None or owner_goal_fp is not None):
        raise DomainError("INVALID_INPUT", "Correction cannot change another execution mode")
    if csv_review is not None and any(x is not None for x in (pa_use, pb_use, human_correction, offline_replay, owner_goal_fp, logic_check, project_check)):
        raise DomainError("INVALID_INPUT", "CSV review cannot change another execution mode")
    use_body = pa_use if pa_use is not None else pb_use
    use_field = "pa_use" if pa_use is not None else "pb_use"
    guard: dict = {}
    from contextlib import nullcontext
    if project_check is not None and any(x is not None for x in (pa_use,pb_use,human_correction,offline_replay,owner_goal_fp)):
        raise DomainError("INVALID_INPUT", "Project checks cannot change another execution mode")
    if logic_check is not None and any(x is not None for x in (pa_use,pb_use,human_correction,offline_replay,owner_goal_fp)):
        raise DomainError("INVALID_INPUT", "Local logic checks cannot change another execution mode")
    with (nullcontext(logic_tx) if logic_tx is not None else submission_tx(store, guard)) as c:
        pid = c.execute(
            select(internal_instances.c.project_id).where(internal_instances.c.id == iid)
        ).scalar()
        store.lock_project(c, user, pid)
        from .local_record_apps import reject_legacy as reject_record_legacy
        reject_record_legacy(c, iid=iid)
        from .spec_run_terminals import fenced
        if fenced(c, user, iid, key):
            raise DomainError("VERSION_CONFLICT", "Original spec request key permanently closed")
        if submission is not None:
            guard["proof"] = rejection_proof(c, user, iid, pid, key, submission, "TX_ROLLED_BACK")
        if human_correction is not None:
            from . import natural_spec_corrections
            guard["proof"] = natural_spec_corrections.rejection_proof(c,user,iid,human_correction[1]["parent_run_id"],human_correction[0])
        scope_limits = limits
        if human_correction is not None:
            limits = natural_spec_corrections.bounded_limits(limits,Limits(**human_correction[1]["proposed_limits"]))
        i, release = instance(store, c, user, iid, scope_limits, lock=True)
        from .csv_full_report_instances import is_snapshot
        if is_snapshot(release["snapshot"]):
            raise DomainError("UNSUPPORTED_CAPABILITY", "Prepare and confirm the complete ordinary CSV contract")
        from . import csv_goal_revisions as csv_revision
        if csv_revision.pins(c,user,iid) and csv_goal_check is None:
            raise DomainError("VERSION_CONFLICT", "This isolated instance is reserved for its original CSV Goal CHECK")
        from .text_continuations import execution

        execution(store, c, user, i, release, limits)
        if csv_review is not None:
            from .csv_owner_review import supported
            if not supported(release):
                raise DomainError("UNSUPPORTED_CAPABILITY", "CSV review requires a single sum action")
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
        if owner_goal_fp is not None:
            request["owner_goal_binding_fingerprint"] = owner_goal_fp
        if use_body is not None:
            request[use_field] = use_body.model_dump()
        if human_correction is not None:
            from . import natural_spec_corrections as correction
            correction_body, correction_value = human_correction
            correction_ref = correction.reference(correction_value)
            request["human_correction"] = correction_ref.model_dump()
            request["correction_request"] = correction_body.model_dump()
        if logic_check is not None:
            request["logic_check"] = logic_check.model_dump()
        if project_check is not None:
            from . import project_natural_revalidation as project
            plan,member=project.guard(store,c,user,project_check.model_dump(),limits)
            if release["id"] != member["context"]["release_id"] or iid == member["context"]["instance_id"]:
                raise DomainError("VERSION_CONFLICT")
            request["project_check"] = project_check.model_dump()
        if csv_review is not None:
            request["csv_review"] = csv_review
        csv_ref = csv_goal_check
        if csv_ref is None and csv_revision.SOURCE in release["snapshot"]:
            csv_ref = csv_revision.Reference.model_validate(release["snapshot"][csv_revision.SOURCE]["reference"])
        if csv_ref is not None:
            request[csv_revision.MARKER] = csv_ref.model_dump()
        fp = fingerprint(request)
        old = (
            c.execute(
                select(internal_app_runs.c.id, internal_app_runs.c.fingerprint).where(
                    internal_app_runs.c.instance_id == iid,
                    internal_app_runs.c.principal_id == user,
                    internal_app_runs.c.request_key == key,
                )
            )
            .mappings()
            .first()
        )
        if old:
            binding = c.execute(select(internal_run_bindings.c.run_id,
                internal_run_bindings.c.snapshot["instance_id"].as_string().label("iid"))
                .where(internal_run_bindings.c.app_run_id == old["id"])).mappings().first()
            if not binding or binding["iid"] != iid:
                raise DomainError("VERSION_CONFLICT")
            header = c.execute(select(runs.c.principal_id, runs.c.project_id, runs.c.runtime_id,
                runs.c.request_key).where(runs.c.id == binding["run_id"])).mappings().first()
            if (not header or header["principal_id"] != user or header["project_id"] != pid
                    or header["runtime_id"] != i["runtime_id"] or header["request_key"] != "internal:" + old["id"]):
                raise DomainError("PERMISSION_DENIED")
            from .text_continuations import job_gate

            job_gate(store, c, user, binding["run_id"])
            if old["fingerprint"] != fp:
                raise DomainError("VERSION_CONFLICT")
            job = c.execute(select(runs).where(runs.c.id == binding["run_id"])).mappings().one()
            load_binding(store, c, user, job, limits)
            return {
                "run_id": job["id"], "app_run_id": old["id"], "status": job["status"],
                "version": job["version"], "cached": True, "namespace": NAMESPACE,
            }
        if i["revision"] != expected_revision or release["fingerprint"] != release_fp:
            raise DomainError("VERSION_CONFLICT")
        # Strict input validation happens in the worker so accepted bad inputs keep FAILED history.
        jid, aid = new_id("run"), new_id("iapprun")
        draft = release["snapshot"]["draft"]
        from . import app_owner_goals, text_logic_reuse

        own_goal = app_owner_goals.run_ref(store, c, user, draft, limits) if text_logic_reuse.independent(draft) else None
        if (own_goal is not None and owner_goal_fp != own_goal["binding_fingerprint"]) or (
            own_goal is None and owner_goal_fp is not None
        ):
            raise DomainError("VERSION_CONFLICT", "Confirm the current own GoalCard binding for this Run")
        use_checked = use_goal = None
        logic_goal = None
        if logic_check is not None:
            from . import natural_logic_patches as logic
            _, logic_value = logic.load_preview(store,c,user,logic_check.instance_id,logic_check.preview_key,limits)
            if (logic.reference(logic_check.instance_id,logic_check.preview_key,logic_value) != logic_check
                    or release["id"] != logic_value["context"]["release_id"]
                    or release["fingerprint"] != logic_value["context"]["release_fingerprint"]
                    or iid == logic_check.instance_id):
                raise DomainError("VERSION_CONFLICT")
            draft,_,_,_,logic_goal = logic.effective_bound(release,logic_value,limits)
        elif "natural_logic_source" in release["snapshot"] and use_body is None and human_correction is None:
            from . import natural_logic_patches as logic
            draft,_,_,_,logic_goal = logic.release_bound(store,c,user,release,limits)
        if human_correction is not None:
            correction.approve(store,c,user,iid,correction_ref.parent_run_id,limits,correction_body,correction_value)
            draft = {**copy.deepcopy(draft), "candidate": correction_value["effective_candidate"],
                "fingerprint": fingerprint(correction_value["effective_candidate"])}
        if use_body is not None:
            from . import pb_natural_uses
            use_family = pb_natural_uses.PA if pa_use is not None else pb_natural_uses.PB
            use_checked, _, use_goal = pb_natural_uses.approve(store, c, user, i, release, use_body, limits, family=use_family)
            draft = {**copy.deepcopy(draft), "candidate": use_checked["effective_candidate"],
                     "fingerprint": use_checked["effective_fingerprint"]}
        if csv_ref is not None:
            draft,_,_,_ = csv_revision.bound(store,c,user,release,limits,
                {**request,"instance_id":iid},current=True)
            _,revision_value = csv_revision.load_preview(store,c,user,csv_ref.instance_id,csv_ref.preview_key,limits)
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
        if csv_review is not None:
            from . import csv_owner_review
            material_draft = draft if csv_ref is not None and csv_revision.material_policy(revision_value) else None
            snapshot["csv_owner_review"] = csv_owner_review.prospective(
                release, source, input_value, csv_review, effective_draft=material_draft)
        if pa_use is not None:
            snapshot["pa_base_data_version"] = i["data_version"]
        if own_goal is not None:
            snapshot["owner_goal"] = own_goal
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
        from . import pa_spec_apps, text_workflows
        if csv_ref is not None:
            source_goal = revision_value["context"]["goal"]
            snapshot["csv_goal"] = source_goal
            contract["goal"] = csv_revision.goal_spec(source_goal,contract["goal"])
            FrozenRunContract.model_validate(contract)
            goal = source_goal["snapshot"]["content"]["goal"]
        if pa_spec_apps.is_candidate(draft["candidate"]):
            from .spec_production import generation_mode
            contract["mode"] = generation_mode(c, draft)
            source_goal = correction_value["context"]["source_goal"] if human_correction is not None else use_goal.model_dump() if use_goal is not None else logic_goal if logic_goal is not None else pa_spec_apps.verify_origin(store, c, user, draft, limits)[3]
            snapshot["spec_goal"] = source_goal
            content = source_goal["snapshot"]["content"]
            contract["goal"].update(goal_id=source_goal["card_id"], goal=content["goal"],
                constraints=content["constraints"], unresolved=pa_spec_apps.goal_unresolved(source_goal))
            FrozenRunContract.model_validate(contract)
            goal = content["goal"]

        if text_workflows.is_candidate(draft["candidate"]):
            _, _, _, source_goal = text_workflows.verify_origin(store, c, user, draft, limits)
            snapshot["text_goal"] = source_goal
            content = source_goal["snapshot"]["content"]
            contract["goal"].update(goal_id=source_goal["card_id"], goal=content["goal"],
                constraints=content["constraints"], unresolved=text_workflows.goal_unresolved(source_goal))
            FrozenRunContract.model_validate(contract)
            goal = content["goal"]
        if use_checked is not None:
            snapshot["pa_effective_fingerprint" if pa_use is not None else "pb_effective_fingerprint"] = use_checked["effective_fingerprint"]
        accepted_created_at = time.time()
        from . import natural_specs
        if natural_specs.is_candidate(draft["candidate"]):
            snapshot["natural_spec_clock"] = dict(created_at=accepted_created_at,
                deadline=accepted_created_at + min(limits.run_seconds, draft["candidate"]["manifest"]["runtime_limits"]["run_seconds"]))
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
                created_at=accepted_created_at,
                lease_until=0,
                fence=0,
                context={
                    "kind": KIND,
                    "messages": [],
                    "requests": 0,
                    "tools": 0,
                    "repairs": 0,
                    "reserved_tokens": 0,
                    **({csv_revision.MARKER:fingerprint(csv_ref.model_dump())} if csv_ref is not None else {}),
                    **({"text_workflow": text_workflows.VERSION} if text_workflows.is_candidate(draft["candidate"]) else {}),
                    **({"spec_family": draft["candidate"]["namespace"]} if pa_spec_apps.is_candidate(draft["candidate"]) else {}),
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
        if text_workflows.is_candidate(draft["candidate"]):
            text_workflows.seal_job_scope(c, user, draft, snapshot)
        if pa_spec_apps.is_candidate(draft["candidate"]):
            pa_spec_apps.seal_job_scope(c, user, draft, snapshot)
        if logic_check is not None:
            logic.remember(c,user,jid,logic.JOB,"accepted",logic_check,logic_check.model_dump())
        if csv_ref is not None:
            csv_revision.remember(c,user,jid,csv_revision.JOB,"accepted",csv_ref,csv_ref.model_dump())
            store.event(c,jid,"CSV_GOAL_REVISION_FROZEN",dict(reference=csv_ref.model_dump(),
                reference_fingerprint=fingerprint(csv_ref.model_dump()),instance_id=iid,app_run_id=aid))
        if project_check is not None:
            project.remember(c,user,jid,project.JOB,"accepted",project_check,project_check.model_dump())
        if use_body is not None:
            pb_natural_uses.seal(c, user, release["snapshot"]["draft"], snapshot, use_body, use_checked, family=use_family)
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
        if csv_review is not None:
            store.event(c, jid, "CSV_REVIEW_FROZEN", dict(
                instance_id=iid, app_run_id=aid, release_id=release["id"],
                binding_fingerprint=fingerprint(snapshot),
                policy_fingerprint=fingerprint(snapshot["csv_owner_review"])))
        if human_correction is not None:
            correction.seal(c,user,snapshot,correction_ref)
            store.event(c,jid,"HUMAN_CORRECTION_ACCEPTED",dict(parent_run_id=correction_ref.parent_run_id,
                review_key=correction_ref.review_key,review_fingerprint=correction_ref.review_fingerprint))
            correction.gate(store,c,user,jid)
            from . import owner_acceptance
            owner_acceptance.natural_final_gate(store,c,user,iid,correction_ref.parent_run_id,
                correction_value["context"],expires_at=correction_value["expires_at"])
        if use_body is not None:
            # Verify all new grants, accepted binding and seals before transaction commit.
            job = c.execute(select(runs).where(runs.c.id == jid)).mappings().one()
            pa_spec_apps.verify_job(store, c, user, job, limits)
        return {
            "run_id": jid,
            "app_run_id": aid,
            "status": "QUEUED",
            "version": 1,
            "cached": False,
            "namespace": NAMESPACE,
        }


def _binding_queue_from_facts(job, user, b):
    """Pure original predicates; caller retains all preceding scope/IO gates."""
    if not b or job["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    s = b["snapshot"]
    if (fingerprint(s) != b["fingerprint"] or job["fingerprint"] != b["fingerprint"]
            or s.get("principal_id") != user or s.get("project_id") != job["project_id"]
            or s.get("runtime_id") != job["runtime_id"] or s.get("run_id") != job["id"]):
        raise DomainError("VERSION_CONFLICT", "Accepted queue identity changed before private AppRun read")
    return s


def _binding_app_run_from_facts(job, b, s, a):
    """Pure original predicates; caller retains all preceding scope/IO gates."""
    if not a or fingerprint(s) != b["fingerprint"] or job["fingerprint"] != b["fingerprint"]:
        raise DomainError("VERSION_CONFLICT", "Queue binding fingerprint changed")


def _binding_request_from_facts(job, user, s, a, request):
    """Pure original predicates; caller retains all preceding scope/IO gates."""
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
        or fingerprint(a["input"]) != fingerprint(s["input"])
        or a["fingerprint"] != s["request_fingerprint"]
        or fingerprint(request) != s["request_fingerprint"]
    ):
        raise DomainError("VERSION_CONFLICT", "AppRun no longer matches accepted queue binding")


def _binding_release_from_facts(job, s, r, expected_resource):
    """Pure original predicates; caller retains all preceding scope/IO gates."""
    if (
        r["fingerprint"] != s["expected_release_fp"]
        or r["project_id"] != s["project_id"]
        or r["snapshot"]["draft"]["runtime_id"] != s["runtime_id"]
        or job["resource_refs"]
        != [expected_resource]
    ):
        raise DomainError("VERSION_CONFLICT")


def _binding_checkpoint(store, c, guard):
    if guard is not None:
        from .natural_spec_runtime import _cold_read_checkpoint
        _cold_read_checkpoint(store, c, guard)


def _load_binding_prefix(store, c, user, job, limits, *, authorize=True, return_release=False, _graph_read=None, _graph_key=None):
    from .local_record_apps import reject_legacy as reject_record_legacy
    reject_record_legacy(c, rid=job["id"])
    _binding_checkpoint(store, c, _graph_read)
    if return_release and not authorize:
        raise DomainError("PERMISSION_DENIED", "Verified release requires authorization")
    from . import natural_spec_corrections as correction
    scope = correction.scope_segment(store,c,user,job["id"]) if authorize else None
    _binding_checkpoint(store, c, _graph_read)
    if authorize:
        from .text_continuations import job_gate

        reused_scope = scope is not None
        job_gate(store, c, user, job["id"],_spec_scope_checked=reused_scope)
        _binding_checkpoint(store, c, _graph_read)
        scope = correction.scope_segment(store,c,user,job["id"],_segment=scope)
        _binding_checkpoint(store, c, _graph_read)
        if reused_scope and scope is None:
            # A write invalidated the pure read segment; authorize again before
            # any binding/AppRun body, never merely at the later contract check.
            job_gate(store,c,user,job["id"])
            _binding_checkpoint(store, c, _graph_read)
            scope = correction.scope_segment(store,c,user,job["id"])
            _binding_checkpoint(store, c, _graph_read)
    b = (
        c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == job["id"]))
        .mappings()
        .first()
    )
    _binding_checkpoint(store, c, _graph_read)
    if _graph_read is not None:
        _graph_read.add(_graph_key + ":binding", dict(b) if b is not None else None)
    s = _binding_queue_from_facts(job, user, b)
    a = (
        c.execute(select(internal_app_runs).where(internal_app_runs.c.id == b["app_run_id"],
            internal_app_runs.c.principal_id == user, internal_app_runs.c.instance_id == s.get("instance_id"),
            internal_app_runs.c.release_id == s.get("release_id")))
        .mappings()
        .first()
    )
    _binding_checkpoint(store, c, _graph_read)
    if _graph_read is not None:
        _graph_read.add(_graph_key + ":app-run", dict(a) if a is not None else None)
    _binding_app_run_from_facts(job, b, s, a)
    request = {
        k: s[k] for k in ["instance_id", "expected_revision", "expected_release_fp", "input"]
    }
    for use_field in ("pb_use", "pa_use"):
        if use_field in s:
            request[use_field] = s[use_field]
    if "human_correction" in s:
        request["human_correction"] = s["human_correction"]
        request["correction_request"] = s["correction_request"]
    from . import natural_logic_patches as logic
    logic_marker = logic.graph.lookup(c,user,job["id"],logic.JOB,"accepted")
    _binding_checkpoint(store, c, _graph_read)
    if bool(logic_marker) != ("logic_check" in s):
        raise DomainError("VERSION_CONFLICT", "Local logic check marker cannot be removed")
    if "logic_check" in s:
        request["logic_check"] = s["logic_check"]
    from . import project_natural_revalidation as project
    project.job_gate(store,c,user,job,s,limits)
    _binding_checkpoint(store, c, _graph_read)
    if "project_check" in s:
        request["project_check"] = s["project_check"]
    if "offline_replay" in s:
        request["offline_replay"] = s["offline_replay"]
    if "csv_review" in s:
        request["csv_review"] = s["csv_review"]
    from . import csv_goal_revisions as csv_revision
    if csv_revision.MARKER in s:
        request[csv_revision.MARKER] = s[csv_revision.MARKER]
    if "owner_goal_binding_fingerprint" in s:
        request["owner_goal_binding_fingerprint"] = s["owner_goal_binding_fingerprint"]
    _binding_request_from_facts(job, user, s, a, request)
    store.own_project(c, user, s["project_id"])
    _binding_checkpoint(store, c, _graph_read)
    return s, a, scope


def _binding_contract_limits(store, c, user, job, limits, s, scope, _logic_out, *, _graph_read=None):
    contract = (store._frozen_contract_after_scope(c,job) if scope is not None
        else store.frozen_contract(c, job))
    _binding_checkpoint(store, c, _graph_read)
    if contract.limits.model_dump() != s["limits"]:
        raise DomainError("VERSION_CONFLICT", "Accepted limits no longer match frozen envelope")
    logic_source: dict[str, Any] = _logic_out if _logic_out is not None else {}
    scope_limits = limits
    if "human_correction" in s:
        from . import natural_spec_corrections
        ref = s["human_correction"]
        _, reviewed = natural_spec_corrections.load_review(store,c,user,ref["instance_id"],ref["parent_run_id"],ref["review_key"])
        scope_limits = natural_spec_corrections.validation_limits(reviewed,limits)
    _binding_checkpoint(store, c, _graph_read)
    return contract, logic_source, scope_limits


def _binding_release_base(store, c, user, job, limits, s, r, contract, archival_software=None, *, _graph_read=None):
    from . import csv_goal_revisions as csv_revision
    from .app_owner_goals import verify_frozen_run

    verify_frozen_run(store, c, user, r["snapshot"]["draft"], limits, s, archival_software=archival_software)
    _binding_checkpoint(store, c, _graph_read)
    csv_revision.verify_job(store,c,user,job,s,r,limits,contract)
    _binding_checkpoint(store, c, _graph_read)
    if "offline_replay" in s:
        from .agent_apps import is_agent, offline_replay_model

        if not is_agent(r["snapshot"]["draft"]["candidate"]):
            raise DomainError("VERSION_CONFLICT", "Offline Replay cannot change executor family")
        offline_replay_model(s["offline_replay"])
    expected_resource = r["snapshot"]["draft"]["candidate"]["manifest"]["data_bindings"][0]["resource_ref"]
    return expected_resource


def load_binding(store, c, user, job, limits, *, authorize=True, archival_software=None, return_release=False, _logic_out=None, _origin_out=None, _use_out=None):
    from . import csv_goal_revisions as csv_revision
    s, a, scope = _load_binding_prefix(store, c, user, job, limits, authorize=authorize, return_release=return_release)
    if authorize:
        contract, logic_source, scope_limits = _binding_contract_limits(store, c, user, job, limits, s, scope, _logic_out)
        if (scope is not None and archival_software is None
                and scope["reference"] == s.get("human_correction")
                and scope["release"]["id"] == s["release_id"]
                and scope["logic"].get("platform_limits") == scope_limits.model_dump()):
            r = scope["release"]
            logic_source.update(scope["logic"])
        else:
            r = read_release(store, c, user, s["release_id"], scope_limits,
                archival_software=archival_software,_logic_out=logic_source,
                **({"_origin_out": _origin_out} if _origin_out is not None else {}))
        expected_resource = _binding_release_base(store, c, user, job, limits, s, r, contract, archival_software)
        if csv_revision.MARKER in s:
            effective_draft,_,_,_ = csv_revision.bound(store,c,user,r,limits,s)
            expected_resource = effective_draft["candidate"]["manifest"]["data_bindings"][0]["resource_ref"]
        elif "human_correction" in s:
            from . import natural_spec_corrections
            _, _, _, correction_source, _ = natural_spec_corrections.bound(store,c,user,job,s,r,limits,_logic_out=logic_source)
            expected_resource = correction_source["resource_id"]
        elif "pb_use" in s or "pa_use" in s:
            from . import pb_natural_uses
            use_family = pb_natural_uses.PA if "pa_use" in s else pb_natural_uses.PB
            plain_use_out = (_use_out if use_family == pb_natural_uses.PB
                and "natural_logic_source" not in r["snapshot"]
                and not {"human_correction", "logic_check", "project_check", "offline_replay"}.intersection(s)
                else None)
            use_value = pb_natural_uses.bound(store, c, user, job, s, r, limits, family=use_family,_logic_out=logic_source,
                **({"_read_out": plain_use_out} if plain_use_out is not None else {}))
            _, _, _, use_source, _ = use_value
            if plain_use_out is not None:
                plain_use_out["bound"] = copy.deepcopy(use_value)
                plain_use_out["bound_fingerprint"] = pb_natural_uses._bound_fingerprint(use_value)
            expected_resource = use_source["resource_id"]
        _binding_release_from_facts(job, s, r, expected_resource)
    return (s, a, r) if return_release else (s, a)


@dataclass(frozen=True)
class _ColdBindingPrefix:
    guard: Any
    key: str
    user: str
    job: Any
    limits: Limits
    role: str
    snapshot: dict
    app_run: Any
    contract: Any


def _cold_binding_prefix(store, c, user, job, limits, guard, role):
    from .natural_spec_runtime import _ColdGraphRead
    from .pa_spec_apps import require
    try:
        require(type(guard) is _ColdGraphRead and role in {"source", "cold"} and type(limits) is Limits)
        _binding_checkpoint(store, c, guard)
        key = "binding-prefix:" + role + ":" + job["id"] + ":" + fingerprint(limits.model_dump())
        s, a, scope = _load_binding_prefix(store, c, user, job, limits, return_release=True, _graph_read=guard, _graph_key=key)
        contract, _, scope_limits = _binding_contract_limits(store, c, user, job, limits, s, scope, None, _graph_read=guard)
        require(scope is None and scope_limits is limits
            and not {"human_correction", "logic_check", "project_check", "offline_replay", "csv_review", "owner_goal_binding_fingerprint"}.intersection(s),
            "Cold graph binding changed family")
        guard.add(key, dict(job=dict(job), snapshot=s, app_run=dict(a), contract=contract.model_dump(), limits=limits))
        return _ColdBindingPrefix(guard, key, user, job, limits, role, s, a, contract)
    except BaseException:
        if type(guard) is _ColdGraphRead:
            guard.invalidate()
        raise


def _cold_binding_release_prefix(store, c, user, prefix, release):
    from .natural_spec_runtime import _ColdGraphRead, _model_inputs
    from .pa_spec_apps import require
    try:
        require(type(prefix) is _ColdBindingPrefix)
        g = prefix.guard
        _binding_checkpoint(store, c, g)
        require(prefix.user == user and release["id"] == prefix.snapshot["release_id"]
            and "natural_logic_source" not in release["snapshot"]
            and _model_inputs(dict(job=dict(prefix.job), snapshot=prefix.snapshot,
                app_run=dict(prefix.app_run), contract=prefix.contract.model_dump(), limits=prefix.limits))
                == _model_inputs(g.inputs[prefix.key]))
        resource = _binding_release_base(store, c, user, prefix.job, prefix.limits,
            prefix.snapshot, release, prefix.contract, _graph_read=g)
        require(not {"human_correction", "logic_check", "project_check", "offline_replay"}.intersection(prefix.snapshot))
        g.add(prefix.key + ":release", dict(release=dict(release), resource=resource))
        return resource
    except BaseException:
        if type(prefix) is _ColdBindingPrefix and type(prefix.guard) is _ColdGraphRead:
            prefix.guard.invalidate()
        raise


def _cold_binding_from_use(store, c, user, prefix, release, use_value):
    from .natural_spec_runtime import _ColdGraphRead
    from .pa_spec_apps import require
    try:
        require(type(prefix) is _ColdBindingPrefix)
        g = prefix.guard
        _binding_checkpoint(store, c, g)
        stored = g.inputs[prefix.key + ":release"]
        require(prefix.user == user and stored["release"] == dict(release))
        resource = stored["resource"]
        if "pb_use" in prefix.snapshot:
            require(prefix.role == "cold" and "pa_use" not in prefix.snapshot
                and type(use_value) is tuple and len(use_value) == 5)
            resource = use_value[3]["resource_id"]
        else:
            require(prefix.role == "source" and "pa_use" not in prefix.snapshot and use_value is None)
        _binding_release_from_facts(prefix.job, prefix.snapshot, release, resource)
        _binding_checkpoint(store, c, g)
        return prefix.snapshot, prefix.app_run, release
    except BaseException:
        if type(prefix) is _ColdBindingPrefix and type(prefix.guard) is _ColdGraphRead:
            prefix.guard.invalidate()
        raise


def _cold_binding_facet(store, c, user, prefix, limits):
    """Same complete raw queue identity, with a distinct caller Limits facet."""
    from .natural_spec_runtime import _ColdGraphRead, _model_inputs
    from .pa_spec_apps import require
    try:
        require(type(prefix) is _ColdBindingPrefix and type(limits) is Limits)
        guard = prefix.guard
        _binding_checkpoint(store, c, guard)
        require(prefix.user == user and _model_inputs(dict(job=dict(prefix.job), snapshot=prefix.snapshot,
            app_run=dict(prefix.app_run), contract=prefix.contract.model_dump(), limits=prefix.limits))
            == _model_inputs(guard.inputs[prefix.key]))
        key = "binding-prefix:" + prefix.role + ":" + prefix.job["id"] + ":" + fingerprint(limits.model_dump())
        guard.add(key, dict(job=dict(prefix.job), snapshot=prefix.snapshot, app_run=dict(prefix.app_run),
            contract=prefix.contract.model_dump(), limits=limits))
        return _ColdBindingPrefix(guard, key, user, prefix.job, limits, prefix.role,
            prefix.snapshot, prefix.app_run, prefix.contract)
    except BaseException:
        if type(prefix) is _ColdBindingPrefix and type(prefix.guard) is _ColdGraphRead:
            prefix.guard.invalidate()
        raise


def inspect_job(store, user, rid):
    with store.tx() as c:
        from .local_record_apps import reject_legacy as reject_record_legacy
        reject_record_legacy(c, rid=rid)
        from .text_continuations import job_gate

        job_gate(store, c, user, rid)
        job = c.execute(select(runs).where(runs.c.id == rid, runs.c.principal_id == user)).mappings().first()
        if not job or job["principal_id"] != user:
            raise DomainError("PERMISSION_DENIED")
        limits = store.frozen_contract(c, job).limits
        s, a, release = load_binding(store, c, user, job, limits, return_release=True)
        from . import text_workflows

        workflow = text_workflows.is_candidate(release["snapshot"]["draft"]["candidate"])
        proof_steps: list[dict] = []
        from . import pa_spec_apps
        spec = pa_spec_apps.is_candidate(release["snapshot"]["draft"]["candidate"])
        if spec:
            _, _, proof_steps = pa_spec_apps.verify_job(store, c, user, job, limits)
        if workflow:
            _, _, proof_steps = text_workflows.verify_job(store, c, user, job, limits)
        if job["status"] == "SUCCEEDED":
            from .agent_apps import is_agent, verified_source

            if is_agent(release["snapshot"]["draft"]["candidate"]):
                verified_source(store, c, user, rid, limits, require_initial=False)
        records = data_rows(c, s["instance_id"], store=store, user=user, run_id=a["id"])
        result = next((dict(r) for r in records if r["run_id"] == a["id"]), None)
        if (release["snapshot"]["draft"]["candidate"]["actions"][0]["executor"]["ref"] == "text.literal_evidence"
                and (job["status"] == "SUCCEEDED" or a["output"] is not None or a["result_version"] is not None
                     or job["result"] is not None or result is not None
                     or c.execute(select(operations.c.id).where(operations.c.run_id == rid,
                         operations.c.status == "VERIFIED")).first())):
            from .text_run_checks import verify

            verify(store, c, user, job, limits)
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
            **({"steps": [dict(step_id=p["step_id"], status=p["status"], fingerprint=fingerprint(p)) for p in proof_steps],
                "semantic_status": "UNKNOWN", "owner_acceptance": "PENDING", "formal_publication_enabled": False}
               if workflow or spec else {}),
            **({"citation_status": "PASS" if job["status"] == "SUCCEEDED" else "NOT_RUN",
                "semantic_goal_acceptance": "NOT_RUN", "markdown_view": pa_spec_apps.markdown_view(a["output"]["checklist"]) if a["output"] else None}
                if spec else {}),
        }


def command_job(store, user, rid, command, version):
    with store.tx() as c:
        pid = c.execute(select(runs.c.project_id).where(runs.c.id == rid)).scalar()
        store.lock_project(c, user, pid)
        from .local_record_apps import reject_legacy as reject_record_legacy
        reject_record_legacy(c, rid=rid)
        from .pb_natural_uses import control_scope

        metadata = control_scope(store, c, user, rid, lock=True)
        if metadata is None:
            from .csv_goal_revisions import control_scope as csv_control_scope
            metadata = csv_control_scope(store,c,user,rid,lock=True)
        if metadata is not None and command != "resume":
            job, a = metadata
        else:
            if metadata is not None:
                from .text_continuations import job_gate

                job_gate(store, c, user, rid)
            job = c.execute(select(runs).where(runs.c.id == rid).with_for_update()).mappings().first()
        if not job or job["principal_id"] != user:
            raise DomainError("PERMISSION_DENIED")
        # Stop commands must remain possible after revocation. Resume requires current gateway.
        if metadata is None or command == "resume":
            binding_limits = store.frozen_contract(c, job).limits if command == "resume" else None
            s, a = load_binding(store, c, user, job, binding_limits, authorize=False)
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
            _, _, release = load_binding(store, c, user, job, binding_limits,
                return_release=True)
            from .text_continuations import execution

            limits = binding_limits
            instance_row = c.execute(select(internal_instances).where(internal_instances.c.id == s["instance_id"])).mappings().one()
            execution(store, c, user, instance_row, release, limits)
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


def reject_queued_scope(store, c, rid, error):
    """Reject before claim without reading revoked Run or AppRun payloads."""
    from . import local_record_apps as record_apps
    if record_apps.is_job_tx(c, rid):
        return record_apps.reject_queued_scope(store, c, rid, error)
    header = c.execute(select(
        runs.c.id, runs.c.principal_id, runs.c.project_id, runs.c.runtime_id,
        runs.c.status, runs.c.version, runs.c.fence, runs.c.fingerprint,
        runs.c.request_key, runs.c.cancel_intent,
    ).where(runs.c.id == rid, runs.c.status == "QUEUED").with_for_update()).mappings().first()
    if header is None:
        return
    state = ("CANCELLED" if header["cancel_intent"] else "WAITING_RESOURCE"
             if error.code in {"GRANT_REVOKED", "RESOURCE_UNAVAILABLE"} else "FAILED")
    binding = c.execute(select(
        internal_run_bindings.c.app_run_id, internal_run_bindings.c.fingerprint,
    ).where(internal_run_bindings.c.run_id == rid)).mappings().first()
    accepted = c.execute(select(
        events.c.data["namespace"].as_string().label("namespace"),
        events.c.data["app_run_id"].as_string().label("aid"),
        events.c.data["instance_id"].as_string().label("iid"),
        events.c.data["release_id"].as_string().label("release"),
        events.c.data["input_fingerprint"].as_string().label("request_fp"),
    ).where(events.c.run_id == rid, events.c.kind == "ACCEPTED")).mappings().all()
    if (binding and len(accepted) == 1 and accepted[0]["namespace"] == KIND
            and all(isinstance(accepted[0][key], str) and accepted[0][key]
                    for key in ("aid", "iid", "release", "request_fp"))
            and binding["fingerprint"] == header["fingerprint"]
            and binding["app_run_id"] == accepted[0]["aid"]
            and header["request_key"] == "internal:" + accepted[0]["aid"]):
        anchor = accepted[0]
        owned = c.execute(select(internal_instances.c.id).where(
            internal_instances.c.id == anchor["iid"],
            internal_instances.c.principal_id == header["principal_id"],
            internal_instances.c.project_id == header["project_id"],
            internal_instances.c.runtime_id == header["runtime_id"],
        )).first()
        if owned:
            c.execute(update(internal_app_runs).where(
                internal_app_runs.c.id == anchor["aid"],
                internal_app_runs.c.principal_id == header["principal_id"],
                internal_app_runs.c.instance_id == anchor["iid"],
                internal_app_runs.c.release_id == anchor["release"],
                internal_app_runs.c.fingerprint == anchor["request_fp"],
                internal_app_runs.c.status == "QUEUED",
            ).values(status=state, error=error.public()))
    changed = c.execute(update(runs).where(
        runs.c.id == rid, runs.c.status == "QUEUED", runs.c.version == header["version"],
        runs.c.fence == header["fence"], runs.c.principal_id == header["principal_id"],
        runs.c.cancel_intent == header["cancel_intent"],
        runs.c.project_id == header["project_id"], runs.c.runtime_id == header["runtime_id"],
        runs.c.fingerprint == header["fingerprint"], runs.c.request_key == header["request_key"],
    ).values(status=state, error=error.public(), lease_until=0, version=header["version"] + 1))
    if changed.rowcount != 1:
        raise DomainError("VERSION_CONFLICT", "Queued rejection ownership changed")
    store.event(c, rid, "CONTRACT_REJECTED", error.public())


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
        from .text_continuations import execution

        execution(store, c, run["principal_id"], i, release,
                  Limits(**{k: getattr(worker.s, k) for k in Limits.model_fields}))
        from .csv_goal_revisions import bound as csv_bound
        draft, manifest, action, _ = csv_bound(
            store,
            c,
            run["principal_id"],
            release,
            Limits(**{k: getattr(worker.s, k) for k in Limits.model_fields}),
            s,current=True,
        )
        from .app_owner_goals import check_run

        check_run(store, c, run["principal_id"], draft,
                  Limits(**{k: getattr(worker.s, k) for k in Limits.model_fields}), s)
        validate_value(manifest.input_schema, s["input"])
        args = {"resource_id": manifest.data_bindings[0].resource_ref, **s["input"]}
        validate_action_input(action, args)
        # Authorization includes both read and exact registered action before dispatch.
        agent = action.executor.kind == "bounded_agent"
        literal = action.executor.ref == "text.literal_evidence"
        store.authorize(
            c,
            run["principal_id"],
            draft["runtime_id"],
            draft["project_id"],
            args["resource_id"],
            "resource.read" if agent or literal else action.executor.ref,
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
            if agent or literal
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
    if plan["action"]["executor"]["ref"] == "text.literal_evidence":
        from .text_apps import compute as compute_text

        return compute_text(plan["source"], plan["args"])
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
        from .text_continuations import execution

        execution(store, c, run["principal_id"], i, release, limits)
        from .csv_goal_revisions import bound as csv_bound
        draft, manifest, action, _ = csv_bound(
            store, c, run["principal_id"], release, limits,s,current=True
        )
        from .app_owner_goals import check_run

        check_run(store, c, run["principal_id"], draft, limits, s)
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
        literal = action.executor.ref == "text.literal_evidence"
        expected_intent = (
            {"tool": "resource.read", "args": {"resource_id": args["resource_id"]}}
            if agent or literal
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
        elif literal:
            from .agent_apps import check_evidence

            checks = [check_evidence(source, args, output)]
            identities = {"resource_id": args["resource_id"], "source_hash": source["hash"],
                          "term": args["term"]}
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
        # This independent authority may expire while the local append is made.
        # Recheck before transaction commit so the entire append rolls back.
        if "csv_goal_revision" in s:
            csv_bound(store,c,run["principal_id"],release,limits,s,current=True)
        if draft["candidate"].get("task_proof", {}).get("proof", {}).get("kind") == "authorized_data_free_text_logic.v1":
            validate_frozen_candidate(store, c, run["principal_id"], draft, limits)
            check_run(store, c, run["principal_id"], draft, limits, s)
            execution(store, c, run["principal_id"], i, release, limits)


def fail_job(worker, run, error):
    from . import local_record_apps as record_apps
    if record_apps.is_job(worker.store, run["id"]):
        return record_apps.fail_job(worker, run, error)
    from .natural_specs import VERSION as natural_version
    if run["context"].get("spec_family") == natural_version:
        from .natural_spec_runtime import fail_owned
        return fail_owned(worker, run, error)
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
    from . import local_record_apps as record_apps
    if record_apps.is_job(worker.store, run["id"]):
        return record_apps.process_job(worker, run)
    from . import natural_specs, pa_spec_apps
    # The frozen family is a routing hint. The first advance still checks the
    # current owner, full source scope, binding and receipts before any effect.
    # Start that validation under the existing heartbeat loop instead of doing
    # a duplicate full-project classification before its thread exists.
    natural_hint = (isinstance(run.get("context"), dict)
                    and run["context"].get("spec_family") == natural_specs.VERSION)
    if natural_hint or pa_spec_apps.is_job(worker.store, run):
        return pa_spec_apps.process_job(worker, run)
    from . import text_workflows

    if text_workflows.is_job(worker.store, run):
        return text_workflows.process_job(worker, run)
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
