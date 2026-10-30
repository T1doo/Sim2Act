"""Fresh SQL facts, not a Worker execution or a full Cold/PB acceptance proof.

The five response byte strings are previously archived test data. All identities,
rows, approvals and upstream stage/extraction facts here are synthetic. No old DB
is resumed. Original producers, full pins, queries and authority gates run intact.
"""

import base64
import copy
import hashlib
import json
import threading
import time
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace

from sqlalchemy import insert, select, update
from test_cold_accounted_component import WIRE
from test_natural_live_admission import frozen
from test_natural_spec_apps import recipe, setup
from test_pa_trial_dispatch import enqueue_generation

from sim2act import cold_accounted as owned
from sim2act import natural_live_admission as gate
from sim2act import natural_source_archives as archive
from sim2act import natural_spec_runtime as runtime
from sim2act import natural_specs as natural
from sim2act import natural_trial_budget as budget
from sim2act import pa_spec_apps as spec
from sim2act import pa_trial_dispatch as dispatch
from sim2act import pb_natural_specs as pb
from sim2act import production_trial_journal as journal
from sim2act import production_trial_policy as policy
from sim2act import production_trial_sender as sender
from sim2act._cold_accounted_values import _Bounds
from sim2act.contracts import FrozenRunContract, GoalCardRunSource
from sim2act.db import (
    app_drafts,
    attempts,
    fingerprint,
    goal_application_candidates,
    grants,
    internal_app_runs,
    internal_approvals,
    internal_instance_data,
    internal_instances,
    internal_releases,
    internal_run_bindings,
    local_effects,
    new_id,
    operations,
    resources,
    run_contracts,
    runs,
    task_extractions,
)
from sim2act.goal_applications import ConfirmInput, response_archive, source_scope_gate
from sim2act.model import normalize_usage
from sim2act.production_trial_admission import canonical_quota_subject
from sim2act.spec_production import ProductionTrialBinding
from sim2act.text_logic_reuse import remember
from sim2act.worker import Worker


def sha(value):
    return hashlib.sha256(value).hexdigest()


def seed_pair(c, owner, entity, kind, key, request, response):
    journal._cas_pair(c, owner, entity, kind, key, None, journal._snapshot(request, response))


def grant_runtime(c, runtime, pid, rid, tool):
    # Existing synthetic user grants stay unchanged after original approval.
    c.execute(
        insert(grants).values(
            id=new_id("grant"),
            principal_id=runtime,
            project_id=pid,
            resource_id=rid,
            tool_ref=tool,
            expires_at=time.time() + 300,
            revision=1,
            revoked=False,
        )
    )


def seed_exchanges(f, c, job, role, phase=None):
    slots = []
    records = [json.loads(line) for line in WIRE.read_text().splitlines()]
    for index in range(3) if role == "generate" else range(3, 5):
        old = records[index]
        wire, payload = (base64.b64decode(old[k]) for k in ("request_b64", "response_b64"))
        parsed, envelope = json.loads(payload), json.loads(wire)
        original, canonical = response_archive(parsed)
        aid, op = new_id("attempt"), new_id("op")
        identity = policy.ReservationIdentity(
            requirements_fingerprint=fingerprint(f.requirements.model_dump()),
            approval_fingerprint=fingerprint(f.approval.model_dump()),
            stage=role,
            stage_fingerprint=fingerprint(phase.authority.model_dump()) if phase else None,
            run_id=job["id"],
            runtime_id=job["runtime_id"],
            version=job["version"],
            fence=job["fence"],
            worker_id=job["worker_id"],
            account_id=f.binding.account_id,
            quota_subject=f.contract.quota_subject,
            attempt_id=aid,
            wire_sha256=sha(wire),
            wire_bytes=len(wire),
        )
        capture = sender._derive(
            payload, True, True, _generation=role == "generate", _production=True
        )
        assert capture.response_verdict == "VALID_PROTOCOL"
        at = f.history_start + index * 60
        slot = policy.Slot(
            identity=identity,
            reserved_at=at,
            attempted=True,
            accepted=True,
            settlement=capture.outcome,
        )
        slots.append(slot)
        marker = dict(
            version=f.binding.version,
            trial_fingerprint=f.binding.contract_fingerprint,
            approval_key=f.binding.approval_key,
            account_id=f.binding.account_id,
            run_version=job["version"],
            fence=job["fence"],
            worker_id=job["worker_id"],
        )
        params = dict(max_tokens=envelope["max_tokens"], pa_trial_binding=marker)
        if role == "generate":
            params.update(
                generation_wire=sha(wire),
                generation_fence=job["fence"],
                generation_raw_evidence=canonical,
                generation_received_raw=original,
            )
        else:
            params.update(
                natural_spec_wire=dict(
                    sha256=sha(wire), bytes=len(wire), characters=len(wire.decode())
                ),
                natural_spec=dict(operation_id=op, fence=job["fence"], run_version=job["version"]),
            )
            c.execute(
                insert(operations).values(
                    id=op, run_id=job["id"], call_id=aid, tool_ref=spec.JSON_TOOL, status="VERIFIED"
                )
            )
        c.execute(
            insert(attempts).values(
                id=aid,
                run_id=job["id"],
                created_at=at,
                mode="LIVE",
                request_model=f.contract.model,
                response_model=f.contract.model,
                status="RECEIVED" if role == "generate" else "VERIFIED",
                reserved_tokens=len(wire) + envelope["max_tokens"],
                parameters=params,
                response=dict(received_raw=original, raw_evidence=canonical),
                usage=normalize_usage(parsed),
            )
        )
        seed_pair(
            c,
            f.user,
            job["id"],
            sender.CAPTURE,
            aid,
            sender._capture_request(identity),
            capture.model_dump(mode="json"),
        )
        for kind, body_kind, data, canonical_sha in (
            (dispatch.REQUEST, archive.REQUEST, wire, None),
            (dispatch.RESPONSE, archive.RESPONSE, payload, canonical["sha256"]),
        ):
            body = archive._body(job, aid, data, True, canonical_sha, body_kind, _production=True)
            seed_pair(
                c,
                f.user,
                job["id"],
                kind,
                aid,
                dict(
                    trial=budget.scope_for(f.contract, f.binding.approval_key).model_dump(),
                    attempt_id=aid,
                    family=kind,
                    wire_sha256=sha(wire),
                ),
                body.model_dump(),
            )
            f.store.event(c, job["id"], "PA_TRIAL_BODY", dispatch._body_event(aid, kind, body))
            if role == "source":
                remember(c, f.user, job["id"], body_kind, aid, body, body.model_dump())
                f.store.event(
                    c,
                    job["id"],
                    "NS_WIRE_ARCHIVED" if body_kind == archive.REQUEST else "NS_BODY_ARCHIVED",
                    dict(attempt_id=aid, archive_fingerprint=fingerprint(body.model_dump())),
                )
    return slots


def seed(env):
    data = setup(env)
    store, settings, client, user, pid, _, _ = data
    assert store.test_only and store.sqlite
    original, consent = frozen(data)
    account = "offline-accounted-sqlite-only"
    contract = gate.PBTrialContract(
        **(original.model_dump() | dict(quota_subject=canonical_quota_subject(account))),
        path="P-B",
        extraction_request_key="offline-extraction",
        extraction_recipe=recipe("ordered"),
    )
    consent = consent.model_copy(
        update=dict(expected_contract_fingerprint=fingerprint(contract.model_dump()))
    )
    gate.approve(store, user, contract, consent)
    binding = ProductionTrialBinding(contract, consent.request_key, account)
    gen_id = enqueue_generation(data, binding)  # enqueue only; never claim/Worker.
    f = SimpleNamespace(
        store=store,
        settings=settings,
        client=client,
        user=user,
        contract=binding.contract,
        binding=binding,
        gen_id=gen_id,
    )
    # Explicit synthetic past chronology, including the sealed approval witness.
    # No clock patch, sleep, reserve/send or replay of a consumed grant.
    f.history_start = time.time() - 245
    with store.tx() as c:
        old = budget._load(c, user, gate.entity(contract), gate.APPROVE, "approve")
        approval = gate.Approval.model_validate(old["request"])
        f.approval = approval.model_copy(update=dict(approved_at=f.history_start - 1))
        replacement = journal._snapshot(f.approval.model_dump(), f.approval.model_dump())
        journal._cas_pair(c, user, gate.entity(contract), gate.APPROVE, "approve", old, replacement)
        c.execute(
            update(runs)
            .where(runs.c.id == gen_id)
            .values(
                status="SUCCEEDED",
                created_at=f.history_start,
                fence=1,
                worker_id="offline-synthetic-owner",
            )
        )
        frozen_raw = c.execute(
            select(run_contracts.c.snapshot).where(run_contracts.c.run_id == gen_id)
        ).scalar_one()
        frozen_raw = copy.deepcopy(frozen_raw) | dict(mode="live")
        f.frozen = FrozenRunContract.model_validate(frozen_raw)
        c.execute(
            update(run_contracts)
            .where(run_contracts.c.run_id == gen_id)
            .values(snapshot=frozen_raw, fingerprint=fingerprint(frozen_raw))
        )
        gen = dict(c.execute(select(runs).where(runs.c.id == gen_id)).mappings().one())
        assert source_scope_gate(store, c, gen_id) is True
        _, f.requirements = policy._requirements(user, contract, consent.request_key)
        slots = seed_exchanges(f, c, gen, "generate")
        first, cold = contract.bindings
        aid, app_runtime = f.frozen.application_generation.app_id, new_id("runtime")
        candidate = natural.expand(
            recipe("ordered"),
            aid,
            first.card_id,
            pid,
            first.source_hash,
            first.resource_id,
            first.goal_snapshot.content,
            gate._limits(contract),
            "a" * 64,
        )
        candidate["goal_application"] = dict(run_id=gen_id)
        f.raw, f.metadata = (
            copy.deepcopy(candidate),
            dict(runtime_id=contract.runtime_id, resource_refs=[first.resource_id]),
        )
        draft = dict(
            id=aid,
            project_id=pid,
            runtime_id=app_runtime,
            name="SQL synthetic Source",
            candidate=candidate,
            fingerprint=fingerprint(candidate),
            created_at=f.history_start + 121,
        )
        c.execute(insert(app_drafts).values(**draft))
        c.execute(
            insert(goal_application_candidates).values(
                app_id=aid,
                run_id=gen_id,
                principal_id=user,
                candidate_fingerprint=draft["fingerprint"],
                confirmation=ConfirmInput(
                    expected_version=gen["version"],
                    candidate_fingerprint=draft["fingerprint"],
                    request_key="offline-confirmation",
                    name=draft["name"],
                    artifact_write_consent=spec.CONSENT,
                ).model_dump(exclude_none=True),
            )
        )
        grant_runtime(c, app_runtime, pid, first.resource_id, "resource.read")
        grant_runtime(c, app_runtime, pid, pid, natural.SAVE)
        release_snapshot = dict(draft=draft)
        approval_payload = dict(snapshot=release_snapshot)
        approval_id, release_id, iid, app_run_id, source_id = (
            new_id(prefix) for prefix in ("iapproval", "irelease", "iinstance", "iapprun", "run")
        )
        c.execute(
            insert(internal_approvals).values(
                id=approval_id,
                principal_id=user,
                project_id=pid,
                kind="release",
                payload=approval_payload,
                fingerprint=fingerprint(approval_payload),
                expires_at=contract.expires_at,
                consumed=True,
            )
        )
        release = dict(
            id=release_id,
            project_id=pid,
            principal_id=user,
            approval_id=approval_id,
            snapshot=release_snapshot,
            fingerprint=fingerprint(release_snapshot),
        )
        c.execute(insert(internal_releases).values(**release))
        instance = dict(
            id=iid,
            project_id=pid,
            principal_id=user,
            source_app_id=aid,
            runtime_id=app_runtime,
            release_id=release_id,
            revision=1,
            data_version=1,
            history=[],
        )
        c.execute(insert(internal_instances).values(**instance))
        app_run = dict(
            id=app_run_id,
            instance_id=iid,
            release_id=release_id,
            principal_id=user,
            request_key=contract.stage_keys.source,
            fingerprint="b" * 64,
            input={},
            status="SUCCEEDED",
            output={},
            result_version=1,
        )
        c.execute(insert(internal_app_runs).values(**app_run))
        source_job = dict(
            id=source_id,
            principal_id=user,
            project_id=pid,
            runtime_id=app_runtime,
            goal="Synthetic SQL Source only",
            resource_refs=[first.resource_id],
            status="SUCCEEDED",
            request_key="internal:" + app_run_id,
            fingerprint="c" * 64,
            created_at=f.history_start + 180,
            fence=1,
            version=1,
            worker_id="offline-synthetic-owner",
        )
        c.execute(insert(runs).values(**source_job))
        source_job = dict(c.execute(select(runs).where(runs.c.id == source_id)).mappings().one())
        c.execute(
            insert(run_contracts).values(
                run_id=source_id,
                snapshot={"mode": "live"},
                fingerprint=fingerprint({"mode": "live"}),
            )
        )
        snap = dict(
            run_id=source_id,
            instance_id=iid,
            app_run_id=app_run_id,
            release_id=release_id,
            request_fingerprint=app_run["fingerprint"],
        )
        c.execute(
            insert(internal_run_bindings).values(
                run_id=source_id,
                app_run_id=app_run_id,
                snapshot=snap,
                fingerprint=fingerprint(snap),
            )
        )
        store.event(
            c,
            source_id,
            "ACCEPTED",
            dict(
                namespace="INTERNAL_APPRUN",
                app_run_id=app_run_id,
                instance_id=iid,
                release_id=release_id,
                input_fingerprint=app_run["fingerprint"],
            ),
        )
        spec.seal_job_scope(c, user, draft, snap)
        assert spec.job_scope_gate(store, c, user, source_id)
        bound = dict(
            snapshot=snap,
            draft=draft,
            release=release,
            app_run=app_run,
            source=dict(
                resource_id=first.resource_id, hash=first.source_hash, content=first.content
            ),
            goal=dict(
                card_id=first.card_id,
                version=first.goal_version,
                fingerprint=first.goal_fingerprint,
                snapshot=first.goal_snapshot.model_dump(),
            ),
        )
        fields = gate._stage_authority_fields_from_facts(
            contract,
            "source",
            {},
            source_job,
            bound,
            instance,
            draft,
            release,
            gen_id,
            f.raw,
            first,
        )
        authority = gate.StageAuthority(
            **fields,
            authorization_fingerprint=gate.authorization_fingerprint(
                c, user, pid, app_runtime, [x.resource_id for x in contract.bindings]
            ),
        )
        phase = gate.StageApproveInput(
            authority=authority,
            expected_authority_fingerprint=fingerprint(authority.model_dump()),
            approval_key=consent.request_key,
            request_key="offline-source-phase",
            consent="BIND_ONLY_THIS_ACCEPTED_STAGE_RUN_APP_RELEASE_AND_COMPLETE_GOAL_TO_ORIGINAL_TRIAL",
        )
        gate._save(c, user, gate.entity(contract), gate.PHASE, "source", phase)
        slots.extend(seed_exchanges(f, c, source_job, "source", phase))
        state = policy._ledger(
            policy.Ledger(scope=f.requirements, account_id=account, slots=tuple(slots))
        )
        cursor = policy.AccountQuotaCursor(
            account_id=account,
            quota_subject=contract.quota_subject,
            last_reserved_at=slots[-1].reserved_at,
        )
        _, _, request, quota_request, quota_entity = journal._context(
            store, c, user, contract, consent.request_key, account
        )
        seed_pair(
            c,
            journal.QUOTA,
            quota_entity,
            journal.QUOTA,
            "quota",
            quota_request,
            dict(revision=10, cursor=cursor.model_dump(mode="json")),
        )
        seed_pair(
            c,
            user,
            pid,
            journal.KIND,
            contract.trial_key,
            request,
            dict(revision=10, quota_revision=10, ledger=state.model_dump(mode="json")),
        )
        f.source_id, f.bound, f.gen, f.phase = source_id, bound, gen, phase
        f.source_job = source_job
        # Independent committed artifact pointers required by the real PB scope.
        artifact = new_id("res")
        artifact_text = json.dumps(dict(synthetic_sql_artifact=True))
        artifact_hash = sha(artifact_text.encode())
        c.execute(
            insert(resources).values(
                id=artifact,
                project_id=pid,
                name="SQL synthetic output",
                format="json",
                content=artifact_text,
                hash=artifact_hash,
            )
        )
        grant_runtime(c, user, pid, artifact, natural.READ)
        grant_runtime(c, app_runtime, pid, artifact, natural.READ)
        save_id = new_id("op")
        c.execute(
            insert(operations).values(
                id=save_id, run_id=source_id, tool_ref=natural.SAVE, status="VERIFIED"
            )
        )
        c.execute(
            insert(local_effects).values(
                operation_id=save_id, resource_id=artifact, content_hash=artifact_hash
            )
        )
        store.event(c, source_id, "SPEC_COMMITTED", dict(artifact_resource=artifact))
        c.execute(
            update(internal_app_runs)
            .where(internal_app_runs.c.id == app_run_id)
            .values(output=dict(resource_id=artifact))
        )
        typed = dict(result=dict(resource_id=artifact))
        bound["app_run"] = dict(
            c.execute(select(internal_app_runs).where(internal_app_runs.c.id == app_run_id))
            .mappings()
            .one()
        )
        c.execute(
            insert(internal_instance_data).values(
                instance_id=iid,
                version=1,
                run_id=app_run_id,
                release_id=release_id,
                schema_version=1,
                data=typed,
                fingerprint=fingerprint(typed),
            )
        )
        f.proof = dict(
            version="synthetic-upstream-source-proof",
            run_id=source_id,
            full_source_validation_claim=False,
            recipe_fingerprint=fingerprint(recipe("ordered")),
            output_fingerprint=fingerprint(typed),
        )
        extracted = pb.ExtractInput(
            review=pb.ReviewInput(
                source_run_id=source_id,
                expected_source_proof_fingerprint=fingerprint(f.proof),
                expected_source_recipe_fingerprint=fingerprint(recipe("ordered")),
                card_id=cold.card_id,
                expected_goal_version=cold.goal_version,
                expected_goal_fingerprint=cold.goal_fingerprint,
                expected_source_hash=cold.source_hash,
                recipe=contract.extraction_recipe,
                name="SQL synthetic extraction",
                request_key=contract.extraction_request_key,
            ),
            expected_review_fingerprint="d" * 64,
            consent=pb.CONSENT,
            artifact_write_consent=spec.CONSENT,
        )
        xid, xruntime = new_id("app"), new_id("runtime")
        target = dict(resource_id=cold.resource_id, hash=cold.source_hash, content=cold.content)
        goal = GoalCardRunSource(
            card_id=cold.card_id,
            version=cold.goal_version,
            fingerprint=cold.goal_fingerprint,
            snapshot=cold.goal_snapshot.model_dump(),
        )
        xcandidate = pb.candidate(
            extracted.review, f.proof, target, goal, xid, pid, gate._limits(contract)
        )
        xdraft = dict(
            id=xid,
            project_id=pid,
            runtime_id=xruntime,
            name="SQL synthetic extraction",
            candidate=xcandidate,
            fingerprint=fingerprint(xcandidate),
            created_at=time.time(),
        )
        c.execute(insert(app_drafts).values(**xdraft))
        # Shape-complete upstream facts; review/source audit were NOT executed.
        checked = dict(
            app_id=xid,
            runtime_id=xruntime,
            review_fingerprint="d" * 64,
            candidate_fingerprint=xdraft["fingerprint"],
            source_proof_fingerprint=fingerprint(f.proof),
            approved_source_limits=gate._limits(contract).model_dump(),
        )
        extraction_snapshot = pb.frozen_for(user, pid, extracted, checked)
        c.execute(
            insert(task_extractions).values(
                task_id=source_id,
                principal_id=user,
                request_key=contract.extraction_request_key,
                request_fingerprint=fingerprint(extracted.model_dump()),
                app_id=xid,
                snapshot=extraction_snapshot,
            )
        )
        meta = spec.Metadata(
            app_id=xid,
            principal_id=user,
            project_id=pid,
            runtime_id=xruntime,
            resource_id=cold.resource_id,
            source_run_id=source_id,
        )
        remember(c, user, xid, pb.META, "scope", meta, meta.model_dump())
        remember(
            c,
            user,
            xid,
            pb.EXTRACT,
            contract.extraction_request_key,
            extracted,
            extraction_snapshot,
        )
        grant_runtime(c, xruntime, pid, cold.resource_id, natural.READ)
        grant_runtime(c, xruntime, pid, pid, natural.SAVE)
        f.extraction = (
            xdraft,
            extracted,
            dict(resource_id=cold.resource_id, hash=cold.source_hash, content=cold.content),
            dict(
                card_id=cold.card_id,
                version=cold.goal_version,
                fingerprint=cold.goal_fingerprint,
                snapshot=cold.goal_snapshot.model_dump(),
            ),
        )
        assert spec.scope_gate(store, c, user, xid)
    # Exact shell is a CGR identity carrier, with constructor and execution forbidden.
    worker = object.__new__(Worker)
    worker.store, worker.s, worker.pa_trial = store, settings, binding
    worker.id, worker.stop, worker.goal_planner_transport = (
        "offline-pin-shell",
        threading.Event(),
        None,
    )
    worker._journal_trial_store, worker._journal_trial_binding = store, binding
    worker._journal_trial_drift = False
    f.worker = worker
    return f


def seed_cold(f):
    """Add a synthetic accepted Cold Run, without executing any business step."""
    draft, _, target, goal = f.extraction
    ids = [new_id(k) for k in ("iapproval", "irelease", "iinstance", "iapprun", "run")]
    approval_id, release_id, iid, app_id, rid = ids
    at = time.time()
    release_snapshot = dict(draft=draft)
    approval_payload = dict(snapshot=release_snapshot)
    release = dict(
        id=release_id,
        project_id=f.contract.project_id,
        principal_id=f.user,
        approval_id=approval_id,
        snapshot=release_snapshot,
        fingerprint=fingerprint(release_snapshot),
    )
    instance = dict(
        id=iid,
        project_id=f.contract.project_id,
        principal_id=f.user,
        source_app_id=draft["id"],
        runtime_id=draft["runtime_id"],
        release_id=release_id,
        revision=1,
        data_version=1,
        history=[],
    )
    app_run = dict(
        id=app_id,
        instance_id=iid,
        release_id=release_id,
        principal_id=f.user,
        request_key=f.contract.stage_keys.cold,
        fingerprint="a" * 64,
        input={},
        status="RUNNING",
        output=None,
        error=None,
        result_version=None,
    )
    snap = dict(
        run_id=rid,
        instance_id=iid,
        app_run_id=app_id,
        release_id=release_id,
        request_fingerprint=app_run["fingerprint"],
    )
    with f.store.tx() as c:
        c.execute(
            insert(internal_approvals).values(
                id=approval_id,
                principal_id=f.user,
                project_id=f.contract.project_id,
                kind="release",
                payload=approval_payload,
                fingerprint=fingerprint(approval_payload),
                expires_at=f.contract.expires_at,
                consumed=True,
            )
        )
        c.execute(insert(internal_releases).values(**release))
        c.execute(insert(internal_instances).values(**instance))
        c.execute(insert(internal_app_runs).values(**app_run))
        c.execute(
            insert(runs).values(
                id=rid,
                principal_id=f.user,
                project_id=f.contract.project_id,
                runtime_id=draft["runtime_id"],
                goal="Synthetic Cold prewrite context",
                resource_refs=[f.contract.bindings[1].resource_id],
                status="RUNNING",
                request_key="internal:" + app_id,
                fingerprint="b" * 64,
                created_at=at,
                lease_until=at + f.contract.caps.lease_seconds,
                version=1,
                fence=1,
                worker_id=f.worker.id,
            )
        )
        job = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        c.execute(
            insert(run_contracts).values(
                run_id=rid, snapshot={"mode": "live"}, fingerprint=fingerprint({"mode": "live"})
            )
        )
        c.execute(
            insert(internal_run_bindings).values(
                run_id=rid, app_run_id=app_id, snapshot=snap, fingerprint=fingerprint(snap)
            )
        )
        f.store.event(
            c,
            rid,
            "ACCEPTED",
            dict(
                namespace="INTERNAL_APPRUN",
                app_run_id=app_id,
                instance_id=iid,
                release_id=release_id,
                input_fingerprint=app_run["fingerprint"],
            ),
        )
        spec.seal_job_scope(c, f.user, draft, snap)
        bound = dict(
            snapshot=snap, draft=draft, release=release, app_run=app_run, source=target, goal=goal
        )
        fields = gate._stage_authority_fields_from_facts(
            f.contract,
            "cold",
            {},
            job,
            bound,
            instance,
            draft,
            release,
            f.gen_id,
            f.raw,
            f.contract.bindings[1],
        )
        authority = gate.StageAuthority(
            **fields,
            authorization_fingerprint=gate.authorization_fingerprint(
                c,
                f.user,
                f.contract.project_id,
                draft["runtime_id"],
                [b.resource_id for b in f.contract.bindings],
            ),
        )
        phase = gate.StageApproveInput(
            authority=authority,
            expected_authority_fingerprint=fingerprint(authority.model_dump()),
            approval_key=f.binding.approval_key,
            request_key="offline-cold-phase",
            consent="BIND_ONLY_THIS_ACCEPTED_STAGE_RUN_APP_RELEASE_AND_COMPLETE_GOAL_TO_ORIGINAL_TRIAL",
        )
        gate._save(c, f.user, gate.entity(f.contract), gate.PHASE, "cold", phase)
    f.cold_job, f.cold_bound, f.cold_phase = job, bound, phase


@contextmanager
def segment(f, c, phase="pre", *, prewrite=False, cohort=None):
    inputs = {"synthetic-offline-integration": True}
    roles = dict.fromkeys(("source", "generate", "platform", "trial", "per_use"))
    with (
        pb._source_reads(f.store, c),
        runtime._cold_graph_read(f.worker, c, inputs, roles, phase) as graph,
        ExitStack() as stack,
    ):
        state, cursor, _ = dispatch._graph_journal_state(graph, f.store, c, f.binding)
        # Finite fixture allowance only, not a general production bound.
        size = len(WIRE.read_bytes()) * 4
        fixture_bounds = _Bounds(size, size * 2, size, size * 4, size * 16)
        selected = None
        mode = (
            stack.enter_context(owned._owned_prewrite(graph, fixture_bounds)) if prewrite else None
        )
        if cohort is not None:
            bounds, limits = cohort
            selected = stack.enter_context(owned._bounded_cohort(
                graph, bounds, limits, state, cursor, f.source_id, f.gen_id
            ))
            source, generated, mode = selected.source, selected.generated, selected.mode
        elif mode is not None:
            source = dispatch._graph_stage_accounted(
                graph, f.store, c, f.binding, state, cursor, f.source_id, "source", _owned=mode
            )
            generated = dispatch._graph_stage_accounted(
                graph, f.store, c, f.binding, state, cursor, f.gen_id, "generate", _owned=mode
            )
        else:
            generated = dispatch._graph_stage_accounted(
                graph, f.store, c, f.binding, state, cursor, f.gen_id, "generate"
            )
            source = dispatch._graph_stage_accounted(
                graph, f.store, c, f.binding, state, cursor, f.source_id, "source"
            )
        from sim2act import _cold_source_packet as source_owned
        source_packet = source if source_owned.is_packet(source) else None
        # Match production's complete Source pin and independent current Run
        # reader; do not reconstruct or thaw the owned Source family.
        source_job = (c.execute(select(runs).where(runs.c.id==f.source_id)).mappings().one()
            if source_packet is not None else None)
        full = dict(
            binding=getattr(f, "cold_bound", {}),
            cold_job=getattr(f, "cold_job", {}),
            source_binding=f.bound,
            source=(source_owned.pin(graph,source_packet) if source_packet is not None
                else source if mode is not None else dict(run=source[0])),
            generated=generated if mode is not None else None,
            generation=dict(
                raw=f.raw,
                metadata=f.metadata,
                run=generated.run if mode is not None else generated[0],
            ),
            source_proof=f.proof,
            extraction=dict(
                draft=f.extraction[0],
                request=f.extraction[1].model_dump(),
                target=f.extraction[2],
                goal=f.extraction[3],
            ),
        )
        if mode is None:
            graph.add("cold-trial:complete", full)
        else:
            mode.seal(full)
            mode.pin_legacy_complete(mode.complete)
        graph.add("trial-generated-model-facet", dict(frozen=f.frozen.model_dump()))
        stage = (
            source_job if source_packet is not None else source.run if mode is not None else source[0],
            f.bound,
            f.raw,
            f.metadata,
            generated.run if mode is not None else generated[0],
            f.frozen,
            generated,
            None,
            None,
        )
        cold_stage = (
            (
                f.cold_job,
                f.cold_bound,
                f.raw,
                f.metadata,
                generated.run if mode is not None else generated[0],
                f.frozen,
                generated,
                source,
                f.extraction,
            )
            if hasattr(f, "cold_job")
            else None
        )
        # Explicit allowance for THIS finite offline fixture, empirically checked
        # by issuance below. Serialized length is a sizing input, not a proven
        # general node/edge/depth/sidecar bound or product admission qualification.
        size = len(graph.input_bytes())
        bounds = _Bounds(size, size * 2, size, size * 4, size * 16)
        scope = (
            mode.scope
            if mode is not None
            else owned._scope_for_graph(graph, bounds)
            if phase == "pre" and selected is None
            else None
        )
        if mode is not None:
            handle, bridge = source.handle, None
        elif scope is not None:
            handle = scope.issue("source", state, cursor, f.source_id)
            bridge = owned._SourceTestBridge(scope, handle)
        else:
            handle = bridge = None
        try:
            yield SimpleNamespace(
                graph=graph,
                state=state,
                cursor=cursor,
                source=source,
                generated=generated,
                stage=stage,
                scope=scope,
                handle=handle,
                bridge=bridge,
                c=c,
                f=f,
                mode=mode,
                cold_stage=cold_stage,
                cohort=selected,
            )
        finally:
            if scope is not None and mode is None:
                scope.close()
