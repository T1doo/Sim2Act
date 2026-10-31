"""Explicit P-B extraction of one proved natural-spec Run, never cached answers.

The editable recipe is bounded by the source budget and existing codec. A review
is read-only; its exact fingerprint is rederived under the project transaction.
Source lineage remains authorized audit evidence, not runtime inference input.
"""

import copy
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import get_ident
from typing import Any, Literal

from fastapi import Depends
from pydantic import Field, ValidationError
from sqlalchemy import bindparam, insert, select

from . import natural_specs as natural
from . import _cold_source_packet as _source_fact_code
from .contracts import GoalCardRunSource, Limits, Strict
from .db import (
    app_drafts,
    attempts,
    delivery_graph_requests,
    events,
    fingerprint,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    internal_releases,
    internal_run_bindings,
    local_effects,
    new_id,
    operation_intents,
    operations,
    principals,
    reservations,
    run_contracts,
    runs,
    task_extractions,
)
from .delivery_graph_apps import HASH, controlled
from .errors import DomainError
from .pa_material_bindings import Metadata
from .text_logic_reuse import KEY, pair, remember, require

def _owned_source_enabled(_module=_source_fact_code,_check=_source_fact_code.CHECK,
        _enabled=_source_fact_code._SOURCE_OK):
    if not _enabled:return False
    fn,code,defaults=_check
    if (_source_fact_code is not _module or _module.current is not fn
            or fn.__code__ is not code or fn.__defaults__ is not defaults):
        raise DomainError('VERSION_CONFLICT','Source fact qualifier changed')
    fn()
    return True


VERSION = "pb-natural-spec-extraction.v1"
KIND = "pb_natural_spec_task.v1"
META, EXTRACT = "pb_natural_spec_metadata", "pb_natural_spec_extract"
CONSENT = "EXTRACT_THIS_SUCCESSFUL_NATURAL_SPEC_RUN_WITH_THIS_REVIEW_AND_TARGET"
MAX = 64

# Immutable SQL shapes only. Each execution still reads the current rows in
# the original order, with fresh parameters and all original authority gates.
_GATE_RUN = bindparam("pb_gate_run", type_=runs.c.id.type)
_GATE_APP = bindparam("pb_gate_app", type_=app_drafts.c.id.type)
_GATE_INSTANCE = bindparam("pb_gate_instance", type_=internal_instances.c.id.type)
_GATE_HEADER = select(runs.c.principal_id, runs.c.project_id, runs.c.runtime_id).where(runs.c.id == _GATE_RUN)
_GATE_APPS = select(app_drafts.c.id,
    app_drafts.c.candidate["namespace"].as_string().label("family"),
    app_drafts.c.candidate["manifest"]["origin"].as_string().label("origin"),
    app_drafts.c.candidate["spec_task"]["kind"].as_string().label("task")).where(
        app_drafts.c.runtime_id == bindparam("pb_gate_runtime", type_=app_drafts.c.runtime_id.type),
        app_drafts.c.project_id == bindparam("pb_gate_project", type_=app_drafts.c.project_id.type))
_GATE_KIND = select(task_extractions.c.snapshot["kind"].as_string()).where(task_extractions.c.app_id == _GATE_APP)
_GATE_STATUS = select(runs.c.status).where(runs.c.id == _GATE_RUN)
_GATE_SAVED = select(local_effects.c.resource_id).join(operations,
    operations.c.id == local_effects.c.operation_id).where(operations.c.run_id == _GATE_RUN,
        operations.c.tool_ref == natural.SAVE, operations.c.status == "VERIFIED")
_GATE_COMMITTED = select(events.c.data["artifact_resource"].as_string()).where(
    events.c.run_id == _GATE_RUN, events.c.kind == "SPEC_COMMITTED")
_GATE_OUTPUT = select(internal_app_runs.c.output["resource_id"].as_string()).where(
    internal_app_runs.c.id == bindparam("pb_gate_app_run", type_=internal_app_runs.c.id.type),
    internal_app_runs.c.instance_id == _GATE_INSTANCE)
_GATE_TYPED = select(internal_instance_data.c.data["result"]["resource_id"].as_string()).where(
    internal_instance_data.c.run_id == bindparam("pb_gate_app_run", type_=internal_instance_data.c.run_id.type),
    internal_instance_data.c.instance_id == _GATE_INSTANCE)
_GATE_LEDGER = select(delivery_graph_requests.c.app_id).where(
    delivery_graph_requests.c.app_id == _GATE_APP,
    delivery_graph_requests.c.kind.in_([META, META + "_seal", EXTRACT, EXTRACT + "_seal"]))


class ReviewInput(Strict):
    source_run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    expected_source_proof_fingerprint: str = Field(pattern=HASH)
    expected_source_recipe_fingerprint: str = Field(pattern=HASH)
    card_id: str = Field(pattern=r"^goal_[a-f0-9]{32}$")
    expected_goal_version: int = Field(strict=True, ge=1)
    expected_goal_fingerprint: str = Field(pattern=HASH)
    expected_source_hash: str = Field(pattern=HASH)
    recipe: natural.Recipe
    name: str = Field(min_length=1, max_length=100)
    request_key: str = Field(pattern=KEY)


class ExtractInput(Strict):
    review: ReviewInput
    expected_review_fingerprint: str = Field(pattern=HASH)
    consent: Literal["EXTRACT_THIS_SUCCESSFUL_NATURAL_SPEC_RUN_WITH_THIS_REVIEW_AND_TARGET"]
    artifact_write_consent: Literal[
        "ALLOW_ONLY_THIS_APP_TO_SAVE_VALIDATED_CHECKLIST_JSON_IN_THIS_PROJECT"
    ]


def _checkpoint_graph(store, c, guard):
    if guard is not None:
        from .natural_spec_runtime import _cold_read_checkpoint
        _cold_read_checkpoint(store, c, guard)


def _checkpoint_graph_owner(guard):
    if guard is not None:
        from .natural_spec_runtime import _ColdGraphRead
        require(type(guard) is _ColdGraphRead, "Exact Cold graph read scope required")
        guard.check(guard.store, guard.connection)


def _invalidate_graph(guard):
    from .natural_spec_runtime import _ColdGraphRead
    if type(guard) is _ColdGraphRead:
        _ColdGraphRead.invalidate(guard)


def _invalidate_cold_inputs(*values):
    """Invalidate only known exact local facts; never invoke an impostor hook."""
    from .natural_spec_runtime import _ColdGraphRead, _ColdRunFacts

    pending, seen = list(values), set()
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        kind = type(value)
        if kind is _ColdGraphRead:
            _ColdGraphRead.invalidate(value)
        elif kind is _ColdRunFacts:
            pending.extend((getattr(value, "guard", None), getattr(value, "_origin_guard", None)))
        elif kind in {_ColdSourcePrefix, _ColdSourceAuditPrefix,
                      _ColdExtractionPrefix, _ColdExtractionAuditPrefix, _ColdReviewRead}:
            pending.extend((getattr(value, "guard", None), getattr(value, "_origin_guard", None)))
        elif kind in {_ColdSourceTyped, _ColdSourceAuditFacts}:
            pending.append(getattr(value, "prefix", None))
        elif kind is _ColdSourceFacts:
            pending.extend((getattr(value, "typed", None), getattr(value, "audit", None)))
        elif kind is _ColdExtractionReview:
            pending.extend((getattr(value, "prefix", None), getattr(value, "source", None)))


def _cold_fields(store, c, guard, key, value):
    """Only continuity of full explicit facts; never an authority or resolver."""
    try:
        from .natural_spec_runtime import _source_fields_equal
        _checkpoint_graph(store, c, guard)
        require(guard is not None and type(key) is str and key in guard.inputs,
                "Cold extraction facts belong to a different read segment")
        owned=_source_fact_code
        saved=owned.fact(guard,key)
        require(_source_fields_equal(saved,value),
                "Cold extraction facts changed in this read segment")
    except BaseException:
        _invalidate_cold_inputs(guard)
        raise


def _cold_model_dump(expected, model):
    """Only fixed known model serializers; no instance/subclass dump hook."""
    from .text_workflows import RunScopeInput
    allowed = (ExtractInput, ReviewInput, Metadata, GoalCardRunSource, RunScopeInput, Limits)
    require(any(expected is kind for kind in allowed) and type(model) is expected,
            "Exact owned Cold typed model required")
    if expected is ExtractInput:
        require(type(model.review) is ReviewInput and type(model.review.recipe) is natural.Recipe)
    elif expected is ReviewInput:
        require(type(model.recipe) is natural.Recipe)
    return expected.model_dump(model)


def _cold_typed_checkpoint(store, c, guard, models):
    """Check only fixed typed JSON subtrees at owned callee return boundaries."""
    try:
        _checkpoint_graph(store, c, guard)
        if guard is None:
            return
        from .natural_live_admission import _trial_typed_equal
        require(type(models) is list)
        for expected, model, raw in models:
            require(any(expected is kind for kind in (ExtractInput, Metadata, GoalCardRunSource))
                    and type(raw) is dict, "Complete owned typed subtree pin required")
            require(_trial_typed_equal(_cold_model_dump(expected, model), raw),
                    "Owned Cold typed model changed after its complete raw proof")
    except BaseException:
        _invalidate_cold_inputs(guard)
        raise


def source_gate(store, c, user, pid, rid, *, _graph_read=None):
    """Scalar classification bounds lineage depth before any protected Run body."""
    from . import pa_spec_apps as spec
    from .text_workflows import RunScopeInput

    _checkpoint_graph(store, c, _graph_read)
    store.own_project(c, user, pid)
    _checkpoint_graph(store, c, _graph_read)
    parameters = {"pb_gate_run": rid}
    result = c.execute(_GATE_HEADER, parameters)
    _checkpoint_graph(store, c, _graph_read)
    header = result.mappings().first()
    if header is None or header["principal_id"] != user or header["project_id"] != pid:
        raise DomainError("PERMISSION_DENIED")
    result = c.execute(_GATE_APPS, {"pb_gate_runtime": header["runtime_id"],
        "pb_gate_project": pid})
    _checkpoint_graph(store, c, _graph_read)
    apps = result.mappings().all()
    require(len(apps) == 1 and apps[0]["family"] == natural.VERSION
            and apps[0]["origin"] == "goal" and apps[0]["task"] is None,
            "Only an original natural-spec successful task may be extracted; no extraction chains")
    aid = apps[0]["id"]
    app_parameters = {"pb_gate_app": aid}
    result = c.execute(_GATE_KIND, app_parameters)
    _checkpoint_graph(store, c, _graph_read)
    kind = result.scalar()
    require(kind in {None, spec.KIND})
    result = c.execute(_GATE_LEDGER, app_parameters)
    _checkpoint_graph(store, c, _graph_read)
    require(result.first() is None, "P-B lineage cannot be disguised as P-A")
    scoped = spec.job_scope_gate(store, c, user, rid,
        **({"_graph_read": _graph_read} if _graph_read is not None else {}))
    _checkpoint_graph(store, c, _graph_read)
    require(scoped)
    result = c.execute(_GATE_STATUS, parameters)
    _checkpoint_graph(store, c, _graph_read)
    require(result.scalar_one() == "SUCCEEDED",
            "Only a completed successful task is a P-B source")
    # Independent committed metadata must agree before any source Run/receipt body.
    paired = (pair(c, user, rid, spec.RUN_META, "accepted", RunScopeInput)
        if _graph_read is None else _cold_persisted_pair(store, c, user,
            rid, spec.RUN_META, "accepted", RunScopeInput, _graph_read))
    _checkpoint_graph(store, c, _graph_read)
    scope, seal = paired
    require(fingerprint(scope.model_dump()) == fingerprint(seal))
    result = c.execute(_GATE_SAVED, parameters)
    _checkpoint_graph(store, c, _graph_read)
    saved = result.scalars().all()
    result = c.execute(_GATE_COMMITTED, parameters)
    _checkpoint_graph(store, c, _graph_read)
    committed = result.scalars().all()
    pointer_parameters = {"pb_gate_app_run": scope.app_run_id, "pb_gate_instance": scope.instance_id}
    result = c.execute(_GATE_OUTPUT, pointer_parameters)
    _checkpoint_graph(store, c, _graph_read)
    output = result.scalars().all()
    result = c.execute(_GATE_TYPED, pointer_parameters)
    _checkpoint_graph(store, c, _graph_read)
    typed = result.scalars().all()
    require(len(saved) == 1 and saved == committed == output == typed and saved[0],
            "Independent committed source artifact pointers differ")
    store.authorize(c, user, header["runtime_id"], pid, saved[0], natural.READ)
    _checkpoint_graph(store, c, _graph_read)


def source_audit(store, c, user, pid, rid):
    """Complete audit once per original read segment, with fresh authorities.

    This immutable digest never supplies a binding or stage permit. The first
    audit after every write still reads the complete original source evidence.
    """
    token = c.info.get("pb_source_reads")
    if not _source_reads_current(store, c, token):
        return _source_audit(store, c, user, pid, rid)
    key = ("source_audit", user, pid, rid)
    require(key not in token.inflight, "Recursive source audit cannot reuse an incomplete result")
    if key in token.results:
        value, authorities = token.results[key]
        try:
            # Retain the original lineage/status/committed-pointer gate on
            # every call, including a hit, before returning an audit digest.
            source_gate(store, c, user, pid, rid)
            store.recheck_proof_authorities(c, {"_call_authorities": authorities})
        except BaseException:
            token.results.clear()
            raise
        if _source_reads_current(store, c, token):
            return value
        return _source_audit(store, c, user, pid, rid)
    token.inflight.add(key)
    try:
        with store.proof_authorities(c) as authorities:
            value = _source_audit(store, c, user, pid, rid)
        if _source_reads_current(store, c, token):
            token.results[key] = (value, tuple(sorted(authorities)))
        return value
    except BaseException:
        token.results.clear()
        raise
    finally:
        token.inflight.discard(key)


def _source_audit_prefix(store, c, user, pid, rid, *, _graph_read=None):
    from . import pa_spec_apps as spec
    from .text_workflows import RunScopeInput

    source_gate(store, c, user, pid, rid, **({"_graph_read": _graph_read} if _graph_read is not None else {}))
    _checkpoint_graph(store, c, _graph_read)
    paired = (pair(c, user, rid, spec.RUN_META, "accepted", RunScopeInput)
        if _graph_read is None else _cold_persisted_pair(store, c, user,
            rid, spec.RUN_META, "accepted", RunScopeInput, _graph_read))
    _checkpoint_graph(store, c, _graph_read)
    scope, seal = paired
    result = c.execute(select(app_drafts).where(app_drafts.c.id == scope.app_id,
        app_drafts.c.project_id == pid, app_drafts.c.runtime_id == scope.runtime_id))
    _checkpoint_graph(store, c, _graph_read)
    original = result.mappings().one()
    require("spec_task" not in original["candidate"])
    rows = dict(scope=scope.model_dump(), seal=seal)
    return scope, seal, original, rows


def _source_audit_rows(store, c, user, pid, rid, scope, original, rows, original_audit,
                       *, _graph_read=None, _source_reader=None):
    from . import pa_spec_apps as spec
    from .db import delivery_graph_requests, goal_card_versions, goal_cards

    _checkpoint_graph(store, c, _graph_read)
    rows = dict(rows)
    rows["original_audit"] = original_audit
    queries = {
        "run": select(runs).where(runs.c.id == rid, runs.c.principal_id == user, runs.c.project_id == pid),
        "contract": select(run_contracts).where(run_contracts.c.run_id == rid),
        "binding": select(internal_run_bindings).where(internal_run_bindings.c.run_id == rid),
        "app_run": select(internal_app_runs).join(internal_instances,
            internal_instances.c.id == internal_app_runs.c.instance_id).where(
            internal_app_runs.c.id == scope.app_run_id, internal_app_runs.c.instance_id == scope.instance_id,
            internal_instances.c.principal_id == user, internal_instances.c.project_id == pid),
        "typed": select(internal_instance_data).where(
            internal_instance_data.c.instance_id == scope.instance_id,
            internal_instance_data.c.run_id == scope.app_run_id),
        "release": select(internal_releases).where(internal_releases.c.id == scope.release_id,
            internal_releases.c.principal_id == user, internal_releases.c.project_id == pid),
        "attempts": select(attempts).where(attempts.c.run_id == rid).order_by(attempts.c.id),
        "operations": select(operations).where(operations.c.run_id == rid).order_by(operations.c.id),
        "intents": select(operation_intents).join(operations,
            operations.c.id == operation_intents.c.operation_id).where(operations.c.run_id == rid)
            .order_by(operation_intents.c.operation_id),
        "effects": select(local_effects).join(operations,
            operations.c.id == local_effects.c.operation_id).where(operations.c.run_id == rid)
            .order_by(local_effects.c.operation_id),
        "events": select(events).where(events.c.run_id == rid).order_by(events.c.id),
        "reservations": select(reservations).where(reservations.c.run_id == rid).order_by(reservations.c.id),
    }
    queries["origin_marker"] = select(task_extractions).where(task_extractions.c.app_id == scope.app_id,
        task_extractions.c.principal_id == user)
    queries["origin_seals"] = select(delivery_graph_requests).where(
        delivery_graph_requests.c.app_id == scope.app_id,
        delivery_graph_requests.c.principal_id == user,
        delivery_graph_requests.c.kind.in_([spec.META, spec.META + "_seal", spec.BIND, spec.BIND + "_seal"])
        ).order_by(delivery_graph_requests.c.kind, delivery_graph_requests.c.request_key)
    result = c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id == rid))
    _checkpoint_graph(store, c, _graph_read)
    contract = result.scalar_one()
    goal_id = contract["goal"]["goal_id"]
    queries["current_goal"] = select(goal_cards).where(goal_cards.c.id == goal_id,
        goal_cards.c.project_id == pid)
    queries["current_goal_versions"] = select(goal_card_versions).join(goal_cards,
        goal_cards.c.id == goal_card_versions.c.card_id).where(goal_cards.c.id == goal_id,
        goal_cards.c.project_id == pid).order_by(goal_card_versions.c.version)
    rows["original"] = dict(original)
    for name, query in queries.items():
        if _source_reader is not None and name in {"attempts", "operations"}:
            from .natural_spec_runtime import _ColdRunFacts
            require(type(_source_reader) is _ColdRunFacts)
            _source_reader.check(store, c, _source_reader.job)
            require(_source_reader.guard is _graph_read
                and _source_reader.job["id"] == rid
                and _source_reader.job["principal_id"] == user
                and _source_reader.job["project_id"] == pid)
            if name == "attempts":
                raw = _source_reader.attempt_rows(ledger=True)
            else:
                raw = sorted(_source_reader.receipt_operations(), key=lambda row: row["id"])
            _checkpoint_graph(store, c, _graph_read)
            _source_reader.check(store, c, _source_reader.job)
            rows[name] = [dict(row) for row in raw]
        else:
            result = c.execute(query)
            _checkpoint_graph(store, c, _graph_read)
            rows[name] = [dict(row) for row in result.mappings()]
    return rows


def _source_audit(store, c, user, pid, rid):
    """Original complete current source scope and audit bytes, never a permit."""
    from . import pa_spec_apps as spec

    scope, _, original, rows = _source_audit_prefix(store, c, user, pid, rid)
    original_audit = spec.audit_fingerprint(store, c, user, original)
    return fingerprint(_source_audit_rows(store, c, user, pid, rid,
        scope, original, rows, original_audit))


@dataclass(frozen=True)
class _ColdSourceAuditPrefix:
    guard: Any
    key: str
    user: str
    pid: str
    rid: str
    scope: Any
    seal: dict
    original: Any
    rows: dict
    _origin_guard: Any = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, "_origin_guard", self.guard)

    def fields(self):
        from .text_workflows import RunScopeInput
        boundary=self.key+':original-boundary'
        if boundary in self.guard.inputs:
            require(self.guard is self._origin_guard and self.guard.inputs[boundary] is self.original,
                'Source original native boundary changed identity')
            original=('original-native-boundary.v1',boundary)
        else:original=dict(self.original)
        return _source_fact_code.fields_ref(self.guard,self.key,dict(user=self.user,pid=self.pid,rid=self.rid,
            scope=_cold_model_dump(RunScopeInput,self.scope),seal=self.seal,original=original,rows=self.rows))


@dataclass(frozen=True)
class _ColdSourceAuditFacts:
    prefix: _ColdSourceAuditPrefix
    key: str
    original_audit_rows: dict
    rows: dict
    digest: str

    def fields(self):
        return _source_fact_code.fields_ref(self.prefix.guard,self.key,dict(prefix=self.prefix.fields(),
            original_audit_rows=self.original_audit_rows,rows=self.rows,digest=self.digest))


def _cold_source_audit_prefix(store, c, user, pid, rid, guard):
    """Stop exactly before the original native spec audit dependency."""
    try:
        if guard is None:
            raise DomainError("VERSION_CONFLICT", "Exact Cold graph read scope required")
        _checkpoint_graph(store, c, guard)
        scope, seal, original, rows = _source_audit_prefix(store, c, user, pid, rid, _graph_read=guard)
        owned=_source_fact_code
        if _owned_source_enabled():
            # The native Generation audit still consumes this exact original
            # RowMapping. Keep that unmigrated boundary fully pinned.
            boundary='pb-source-audit:'+user+':'+pid+':'+rid+':original-boundary'
            guard.add(boundary,original)
            payload=owned.own_fact(guard,boundary+':payload',dict(seal=seal,rows=rows))
            seal,rows=payload['seal'],payload['rows']
        prefix = _ColdSourceAuditPrefix(guard, "pb-source-audit:" + user + ":" + pid + ":" + rid,
                                        user, pid, rid, scope, seal, original, rows)
        if _owned_source_enabled():owned.own_fact(guard,prefix.key,prefix.fields())
        else:guard.add(prefix.key, prefix.fields())
        return prefix
    except BaseException:
        _invalidate_cold_inputs(guard)
        raise


def _cold_source_audit_from_original(store, c, user, prefix, original_audit_rows, *, source_reader=None):
    """Collect every original row after a complete, explicitly supplied native audit.

    Only the exact same-epoch Run reader may supply complete Attempt/Operation
    raw rows at their original positions. It supplies no authority or proof.
    """
    guard = None
    try:
        from .natural_spec_runtime import _ColdRunFacts

        require(type(prefix) is _ColdSourceAuditPrefix)
        guard = prefix.guard
        require(guard is prefix._origin_guard, "Cold extraction read scope cannot be replaced")
        if guard is None:
            raise DomainError("VERSION_CONFLICT", "Exact Cold graph read scope required")
        _cold_fields(store, c, guard, prefix.key, prefix.fields())
        require(user == prefix.user and (source_reader is None or type(source_reader) is _ColdRunFacts))
        owned=_source_fact_code
        immutable_native=owned.image.is_kind(original_audit_rows,'d')
        require((type(original_audit_rows) is dict or immutable_native) and set(original_audit_rows) == {
            "run", "contract", "original", "attempts", "operations", "intents", "events",
            "confirmation", "goal_head", "goal_version"}, "Complete original native audit rows required")
        if immutable_native:
            native_key='original-native-audit:'+original_audit_rows['original']['id']
            require(owned.image.same(owned.fact(guard,native_key),original_audit_rows),
                'Original native audit must be the first registered complete fact')
        native_rows=(owned.own_fact(guard,prefix.key+':native',original_audit_rows)
            if _owned_source_enabled() else None)
        if native_rows is None:
            guard.add(prefix.key+':native',original_audit_rows)
            native_rows=original_audit_rows
        rows = _source_audit_rows(store, c, user, prefix.pid, prefix.rid,
            prefix.scope, prefix.original, prefix.rows, fingerprint(original_audit_rows),
            _graph_read=guard, _source_reader=source_reader)
        _checkpoint_graph(store, c, guard)
        digest=fingerprint(rows)
        if _owned_source_enabled():rows=owned.own_fact(guard,prefix.key+':rows',rows)
        facts = _ColdSourceAuditFacts(prefix, prefix.key + ":complete", native_rows,rows,digest)
        if _owned_source_enabled():owned.own_fact(guard,facts.key,facts.fields())
        else:guard.add(facts.key, facts.fields())
        return facts
    except BaseException:
        _invalidate_cold_inputs(guard, prefix, source_reader)
        raise


def scope_gate(store, c, user, aid, location, *, _graph_read=None):
    """Called by spec dispatch before full candidate or extraction ledger reads."""
    _checkpoint_graph(store, c, _graph_read)
    store.own_project(c, user, location["project_id"])
    _checkpoint_graph(store, c, _graph_read)
    store.authorize(c, user, location["runtime_id"], location["project_id"],
                    location["resource"], natural.READ)
    _checkpoint_graph(store, c, _graph_read)
    store.authorize(c, user, location["runtime_id"], location["project_id"],
                    location["project_id"], natural.SAVE)
    _checkpoint_graph(store, c, _graph_read)
    result = c.execute(select(task_extractions.c.snapshot["kind"].as_string())
                     .where(task_extractions.c.app_id == aid))
    _checkpoint_graph(store, c, _graph_read)
    kind = result.scalar()
    require(kind == KIND and location["family"] == natural.VERSION and location["task"] == KIND)
    paired = (pair(c, user, aid, META, "scope", Metadata)
        if _graph_read is None else _cold_persisted_pair(store, c, user,
            aid, META, "scope", Metadata, _graph_read))
    _checkpoint_graph(store, c, _graph_read)
    meta, seal = paired
    require(fingerprint(meta.model_dump()) == fingerprint(seal)
            and meta.app_id == aid and meta.principal_id == user
            and meta.project_id == location["project_id"]
            and meta.runtime_id == location["runtime_id"] and meta.resource_id == location["resource"])
    source_gate(store, c, user, meta.project_id, meta.source_run_id,
                **({"_graph_read": _graph_read} if _graph_read is not None else {}))
    _checkpoint_graph(store, c, _graph_read)
    return True


@dataclass
class _SourceReads:
    store: object
    connection: object
    transaction: object
    driver: object
    epoch: int
    thread: int
    results: dict = field(default_factory=dict)
    inflight: set = field(default_factory=set)


def _source_transaction(store, c):
    if not store.test_only or not store.sqlite or c.closed or not c.in_transaction():
        return None
    driver = c.connection.driver_connection
    if driver is None or not driver.in_transaction:
        return None
    return c.get_transaction(), driver


def _source_reads_current(store, c, token):
    current = _source_transaction(store, c)
    return (type(token) is _SourceReads and current is not None
        and token.store is store and token.connection is c
        and token.transaction is current[0] and token.driver is current[1]
        and token.thread == get_ident()
        and token.epoch == c.info.get("source_proof_write_epoch", 0)
        and c.info.get("pb_source_reads") is token)


@contextmanager
def _source_reads(store, c):
    """Private synchronous read call; never retains authority across writes/exit."""
    current = _source_transaction(store, c)
    if current is None:
        yield
        return
    old = c.info.get("pb_source_reads")
    if _source_reads_current(store, c, old):
        try:
            yield
        except BaseException:
            old.results.clear()
            raise
        return
    token = _SourceReads(store, c, current[0], current[1],
        c.info.get("source_proof_write_epoch", 0), get_ident())
    c.info["pb_source_reads"] = token
    try:
        yield
    finally:
        token.results.clear()
        token.inflight.clear()
        if c.info.get("pb_source_reads") is token:
            c.info.pop("pb_source_reads", None)


@controlled
def source(store, c, user, pid, rid, limits):
    """A complete first proof, with fresh authorities on every same-call reuse."""
    token = c.info.get("pb_source_reads")
    if not _source_reads_current(store, c, token):
        return _source(store, c, user, pid, rid, limits)
    key = (user, pid, rid, fingerprint(limits.model_dump()))
    require(key not in token.inflight, "Recursive source proof cannot reuse an incomplete result")
    if key in token.results:
        value, authorities = token.results[key]
        try:
            store.recheck_proof_authorities(c, {"_call_authorities": authorities})
        except BaseException:
            token.results.clear()
            raise
        if (_source_reads_current(store, c, token)
                and fingerprint(limits.model_dump()) == key[3]):
            return copy.deepcopy(value)
        # A callback changed this segment or Limits. Recompute through the
        # original full origin path, without starting another local reuse.
        return _source(store, c, user, pid, rid, limits, _source_origin=False)
    token.inflight.add(key)
    try:
        with store.proof_authorities(c) as authorities:
            value = _source(store, c, user, pid, rid, limits)
        if (_source_reads_current(store, c, token)
                and fingerprint(limits.model_dump()) == key[3]):
            token.results[key] = (copy.deepcopy(value), tuple(sorted(authorities)))
        return value
    except BaseException:
        token.results.clear()
        raise
    finally:
        token.inflight.discard(key)


def _source_prefix(store, c, user, pid, rid, *, _graph_read=None):
    source_gate(store, c, user, pid, rid, **({"_graph_read": _graph_read} if _graph_read is not None else {}))
    _checkpoint_graph(store, c, _graph_read)
    result = c.execute(select(runs.c.status).where(runs.c.id == rid))
    _checkpoint_graph(store, c, _graph_read)
    status = result.scalar_one()
    require(status == "SUCCEEDED", "Only a completed successful task is a P-B source")
    result = c.execute(select(runs).where(runs.c.id == rid, runs.c.principal_id == user,
                                        runs.c.project_id == pid))
    _checkpoint_graph(store, c, _graph_read)
    return result.mappings().one()


def _source_typed(store, c, user, pid, rid, job, binding, proved, *, _graph_read=None):
    _checkpoint_graph(store, c, _graph_read)
    draft, snap, app_run = binding["draft"], binding["snapshot"], binding["app_run"]
    is_natural = natural.is_candidate(draft["candidate"])
    _checkpoint_graph(store, c, _graph_read)
    require(is_natural and "spec_task" not in draft["candidate"])
    result = c.execute(select(internal_instance_data).where(
        internal_instance_data.c.instance_id == snap["instance_id"],
        internal_instance_data.c.run_id == app_run["id"]))
    _checkpoint_graph(store, c, _graph_read)
    typed = result.mappings().one()
    proof = _source_proof_fields(user, pid, rid, binding, draft, snap, app_run, job, typed, proved)
    _checkpoint_graph(store, c, _graph_read)
    return typed, proof


def _source_from_audit(proof, digest):
    proof.update(runtime_audit_fingerprint=digest,
        citation_status="PASS", semantic_status="UNKNOWN", owner_acceptance="PENDING")
    return proof


def _source(store, c, user, pid, rid, limits, *, _source_origin=True):
    from . import pa_spec_apps as spec

    job = _source_prefix(store, c, user, pid, rid)
    binding, _, proved = spec.verify_job(store, c, user, job, limits, _source_origin=_source_origin)
    _, proof = _source_typed(store, c, user, pid, rid, job, binding, proved)
    return binding, _source_from_audit(proof, source_audit(store, c, user, pid, rid))


@dataclass(frozen=True)
class _ColdSourcePrefix:
    guard: Any
    key: str
    user: str
    pid: str
    rid: str
    limits: Limits
    role: str
    job: Any
    _origin_guard: Any = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, "_origin_guard", self.guard)

    def fields(self):
        return _source_fact_code.fields_ref(self.guard,self.key,dict(user=self.user,pid=self.pid,rid=self.rid,
            role=self.role,limits=_cold_model_dump(Limits,self.limits),job=self.job))


@dataclass(frozen=True)
class _ColdSourceTyped:
    prefix: _ColdSourcePrefix
    key: str
    binding: dict
    outputs: dict
    proved: list
    typed: Any
    proof: dict

    def fields(self):
        typed=(self.typed if _source_fact_code.image.is_kind(self.typed,'r','d') else dict(self.typed))
        return _source_fact_code.fields_ref(self.prefix.guard,self.key,dict(prefix=self.prefix.fields(),
            binding=self.binding,outputs=self.outputs,proved=self.proved,typed=typed,proof=self.proof))


@dataclass(frozen=True)
class _ColdSourceFacts:
    typed: _ColdSourceTyped
    audit: _ColdSourceAuditFacts
    key: str
    proof: dict

    @property
    def binding(self):
        return self.typed.binding

    def fields(self):
        return _source_fact_code.fields_ref(self.typed.prefix.guard,self.key,
            dict(typed=self.typed.fields(),audit=self.audit.fields(),proof=self.proof))


def _cold_source_prefix(store, c, user, pid, rid, limits, guard, role):
    """Stop before verify_job; caller supplies its complete role-specific result."""
    try:
        if guard is None:
            raise DomainError("VERSION_CONFLICT", "Exact Cold graph read scope required")
        _checkpoint_graph(store, c, guard)
        require(type(limits) is Limits and role in {"source", "generate", "cold"})
        job = _source_prefix(store, c, user, pid, rid, _graph_read=guard)
        key = ":".join(("pb-source", role, user, pid, rid, fingerprint(limits.model_dump())))
        owned=_source_fact_code
        if _owned_source_enabled():
            job=owned.own_fact(guard,key+':job',job)
            known=vars(guard).get('_source_fact_run_ids',())
            if rid not in known:vars(guard)['_source_fact_run_ids']=(*known,rid)
        prefix = _ColdSourcePrefix(guard, key, user, pid, rid, limits, role, job)
        if _owned_source_enabled():owned.own_fact(guard,prefix.key,prefix.fields())
        else:guard.add(prefix.key, prefix.fields())
        return prefix
    except BaseException:
        _invalidate_cold_inputs(guard)
        raise


def _cold_source_typed(store, c, user, prefix, binding, outputs, proved):
    """Consume complete verify_job facts, then read the original typed row."""
    guard = None
    try:
        require(type(prefix) is _ColdSourcePrefix)
        guard = prefix.guard
        require(guard is prefix._origin_guard, "Cold extraction read scope cannot be replaced")
        if guard is None:
            raise DomainError("VERSION_CONFLICT", "Exact Cold graph read scope required")
        _cold_fields(store, c, guard, prefix.key, prefix.fields())
        require(user == prefix.user)
        require(type(binding) is dict and (type(outputs) is dict or _source_fact_code.image.is_kind(outputs,'d'))
            and (type(proved) is list or _source_fact_code.image.is_kind(proved,'l')))
        if _owned_source_enabled():
            payload=_source_fact_code.own_fact(guard,prefix.key+':verified',dict(binding=binding,outputs=outputs,proved=proved))
            binding,outputs,proved=payload['binding'],payload['outputs'],payload['proved']
        else:guard.add(prefix.key+':verified',dict(binding=binding,outputs=outputs,proved=proved))
        typed, proof = _source_typed(store, c, user, prefix.pid, prefix.rid,
            prefix.job, binding, proved, _graph_read=guard)
        if _owned_source_enabled():
            typed=_source_fact_code.own_fact(guard,prefix.key+':typed-row',typed)
            proof=_source_fact_code.own_fact(guard,prefix.key+':typed-proof',proof)
        facts=_ColdSourceTyped(prefix,prefix.key+':typed',binding,outputs,proved,typed,proof)
        if _owned_source_enabled():_source_fact_code.own_fact(guard,facts.key,facts.fields())
        else:guard.add(facts.key,facts.fields())
        return facts
    except BaseException:
        _invalidate_cold_inputs(guard, prefix)
        raise


def _cold_source_from_audit(store, c, user, typed, audit):
    """Append only the original full Source audit at its original dependency edge."""
    guard = None
    try:
        require(type(typed) is _ColdSourceTyped and type(typed.prefix) is _ColdSourcePrefix
            and type(audit) is _ColdSourceAuditFacts and type(audit.prefix) is _ColdSourceAuditPrefix)
        prefix = typed.prefix
        guard = prefix.guard
        require(guard is prefix._origin_guard, "Cold extraction read scope cannot be replaced")
        if guard is None:
            raise DomainError("VERSION_CONFLICT", "Exact Cold graph read scope required")
        _cold_fields(store, c, guard, typed.key, typed.fields())
        _cold_fields(store, c, guard, audit.key, audit.fields())
        require(user == prefix.user == audit.prefix.user and guard is audit.prefix.guard
                and audit.prefix.guard is audit.prefix._origin_guard
                and prefix.pid == audit.prefix.pid and prefix.rid == audit.prefix.rid)
        proof = _source_from_audit(dict(typed.proof), audit.digest)
        if _owned_source_enabled():proof=_source_fact_code.own_fact(guard,prefix.key+':proof',proof)
        facts=_ColdSourceFacts(typed,audit,prefix.key+':complete',proof)
        if _owned_source_enabled():_source_fact_code.own_fact(guard,facts.key,facts.fields())
        else:guard.add(facts.key,facts.fields())
        return facts
    except BaseException:
        _invalidate_cold_inputs(guard, typed, audit)
        raise


def _cold_source_facet_from_source(store, c, user, source_facts, limits, binding, outputs, proved, *, role=None):
    """Rebuild one full Limits facet from complete new verify_job facts.

    Root must independently prove bound/clock/counters/receipts/result for this
    exact Limits facet before supplying binding/outputs/proved. Only the same
    epoch's complete Run/typed/native+Source audit raw facts are reused here.
    """
    guard = None
    try:
        require(type(source_facts) is _ColdSourceFacts
            and type(source_facts.typed) is _ColdSourceTyped
            and type(source_facts.typed.prefix) is _ColdSourcePrefix
            and type(source_facts.audit) is _ColdSourceAuditFacts
            and type(source_facts.audit.prefix) is _ColdSourceAuditPrefix)
        original = source_facts.typed.prefix
        guard = original.guard
        require(guard is original._origin_guard, "Cold Source read scope cannot be replaced")
        if guard is None:
            raise DomainError("VERSION_CONFLICT", "Exact Cold graph read scope required")
        _cold_fields(store, c, guard, source_facts.key, source_facts.fields())
        require(user == original.user == source_facts.audit.prefix.user
            and guard is source_facts.audit.prefix.guard
            and source_facts.audit.prefix.guard is source_facts.audit.prefix._origin_guard
            and original.pid == source_facts.audit.prefix.pid
            and original.rid == source_facts.audit.prefix.rid
            and type(limits) is Limits and type(binding) is dict
            and (type(outputs) is dict or _source_fact_code.image.is_kind(outputs,'d'))
            and (type(proved) is list or _source_fact_code.image.is_kind(proved,'l')))
        facet_role = original.role if role is None else role
        require(facet_role in {"source", "generate", "cold"})
        key = ":".join(("pb-source", facet_role, user, original.pid, original.rid,
                        fingerprint(limits.model_dump())))
        prefix = _ColdSourcePrefix(guard, key, user, original.pid, original.rid,
                                    limits, facet_role, original.job)
        if _owned_source_enabled():_source_fact_code.own_fact(guard,prefix.key,prefix.fields())
        else:guard.add(prefix.key,prefix.fields())
        guard.add(prefix.key+':limits',limits)
        if _owned_source_enabled():
            payload=_source_fact_code.own_fact(guard,prefix.key+':verified',dict(binding=binding,outputs=outputs,proved=proved))
            binding,outputs,proved=payload['binding'],payload['outputs'],payload['proved']
        else:guard.add(prefix.key+':verified',dict(binding=binding,outputs=outputs,proved=proved))
        draft, snap, app_run = binding["draft"], binding["snapshot"], binding["app_run"]
        is_natural = natural.is_candidate(draft["candidate"])
        _checkpoint_graph(store, c, guard)
        require(is_natural and "spec_task" not in draft["candidate"])
        typed = source_facts.typed.typed
        # These are the exact predicates of the original typed row SELECT.
        require(typed["instance_id"] == snap["instance_id"] and typed["run_id"] == app_run["id"])
        proof = _source_proof_fields(user, original.pid, original.rid, binding,
            draft, snap, app_run, original.job, typed, proved)
        _checkpoint_graph(store, c, guard)
        if _owned_source_enabled():
            # Existing typed row is already immutable; keep its exact parent.
            proof=_source_fact_code.own_fact(guard,prefix.key+':typed-proof',proof)
        typed_facts=_ColdSourceTyped(prefix,prefix.key+':typed',binding,outputs,proved,typed,proof)
        if _owned_source_enabled():_source_fact_code.own_fact(guard,typed_facts.key,typed_facts.fields())
        else:guard.add(typed_facts.key,typed_facts.fields())
        return _cold_source_from_audit(store, c, user, typed_facts, source_facts.audit)
    except BaseException:
        _invalidate_cold_inputs(guard, source_facts)
        raise


def _source_proof_fields(user, pid, rid, binding, draft, snap, app_run, job, typed, proved):
    """Build only the original prefix, before the caller's fresh source_audit.

    Requires the complete same-transaction source gate, successful Run,
    role-Limits verify_job result and typed row. This is not a source verifier
    or authority; the caller must still append the complete current audit.
    """
    return dict(version=VERSION, principal_id=user, project_id=pid, source_run_id=rid,
        source_app_id=draft["id"], source_app_fingerprint=draft["fingerprint"],
        instance_id=snap["instance_id"], app_run_id=app_run["id"], release_id=snap["release_id"],
        release_fingerprint=binding["release"]["fingerprint"], result_version=app_run["result_version"],
        goal_fingerprint=binding["goal"]["fingerprint"], source_hash=binding["source"]["hash"],
        recipe_fingerprint=fingerprint(draft["candidate"]["spec_recipe"]),
        run_fingerprint=fingerprint(dict(job)), binding_fingerprint=fingerprint(snap),
        app_run_fingerprint=fingerprint(dict(app_run)), typed_fingerprint=fingerprint(dict(typed)),
        output_fingerprint=fingerprint(app_run["output"]),
        receipt_fingerprint=fingerprint(proved), audit_fingerprint=binding["audit_fingerprint"])


@dataclass(frozen=True)
class _ColdReviewRead:
    guard: Any
    key: str
    body: ReviewInput
    limits: Limits
    approved: Limits
    binding: dict
    proof: dict
    material: dict
    goal: Any
    _origin_guard: Any = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, "_origin_guard", self.guard)

    def fields(self):
        return dict(body=_cold_model_dump(ReviewInput, self.body), limits=self.limits, approved=self.approved,
                    binding=self.binding, proof=self.proof, material=self.material,
                    goal=_cold_model_dump(GoalCardRunSource, self.goal))

    def check(self):
        guard = None
        try:
            from .natural_spec_runtime import _ColdGraphRead
            require(type(self) is _ColdReviewRead)
            guard = self.guard
            require(guard is self._origin_guard, "Cold review read scope cannot be replaced")
            if guard is None:
                raise DomainError("VERSION_CONFLICT", "Exact Cold graph read scope required")
            require(type(guard) is _ColdGraphRead)
            _cold_fields(guard.store, guard.connection, guard, self.key, self.fields())
        except BaseException:
            _invalidate_cold_inputs(guard, self)
            raise


def _check_review_read(guard, read):
    try:
        if read is not None:
            require(type(read) is _ColdReviewRead and read.guard is guard)
            read.check()
        else:
            require(guard is None, "Complete strict review inputs required")
    except BaseException:
        _invalidate_cold_inputs(guard, read)
        raise


def candidate(body, proof, material, goal, aid, pid, limits, *, _graph_read=None, _review_read=None):
    recipe = body.recipe.model_dump(exclude_none=True)
    value = natural.expand(recipe, aid, goal.card_id, pid, material["hash"], material["resource_id"],
                           goal.snapshot["content"], limits, proof["output_fingerprint"])
    _checkpoint_graph_owner(_graph_read)
    if _review_read is not None:
        _check_review_read(_graph_read, _review_read)
    value["manifest"]["origin"] = "task_run"
    value["manifest"]["source_run_ref"] = body.source_run_id
    value["spec_task"] = dict(kind=KIND, source_run_id=body.source_run_id,
        source_proof_fingerprint=fingerprint(proof), source_recipe_fingerprint=proof["recipe_fingerprint"],
        edited_recipe_fingerprint=fingerprint(recipe), target_goal_fingerprint=goal.fingerprint)
    return value


def review(store, c, user, pid, body, limits, runtime=None):
    from . import pa_spec_apps as spec

    binding, proof = source(store, c, user, pid, body.source_run_id, limits)
    _review_source_from_facts(body, proof)
    material, goal = spec.target(store, c, user, pid, body.card_id, body.expected_goal_version,
        body.expected_goal_fingerprint, runtime, family=natural.VERSION)
    return _review_from_facts(user, pid, body, limits, binding, proof, material, goal)


def _review_source_from_facts(body, proof):
    """Original source comparison before target IO; proof must be complete/current."""
    require(fingerprint(proof) == body.expected_source_proof_fingerprint
            and proof["recipe_fingerprint"] == body.expected_source_recipe_fingerprint)


def _review_from_facts(user, pid, body, limits, binding, proof, material, goal, *, _graph_read=None, _graph_key=None):
    """Original target/candidate tail after source comparison and current target gates.

    Supply full Source proof/history/audit, the exact target material/Goal and
    this role's complete Limits. The inherited source Limits stay distinct.
    No IO, authority refresh or earlier source comparison is performed here.
    """
    require(goal.card_id != binding["goal"]["card_id"] and body.name.strip()
            and material["resource_id"] != binding["source"]["resource_id"]
            and material["hash"] != binding["source"]["hash"]
            and material["hash"] == body.expected_source_hash,
            "An explicit different current Goal and material are required")
    aid = "app_" + fingerprint(dict(kind=KIND, user=user, project=pid, request=body.model_dump()))[:32]
    runtime_id = "appruntime_" + fingerprint(dict(kind=KIND, app=aid))[:32]
    approved = Limits(**binding["draft"]["candidate"]["manifest"]["runtime_limits"])
    review_read = None
    if _graph_read is not None:
        from .contracts import GoalCardRunSource
        _checkpoint_graph_owner(_graph_read)
        require(type(_graph_key) is str and type(body) is ReviewInput
            and type(limits) is Limits and type(goal) is GoalCardRunSource)
        review_read = _ColdReviewRead(_graph_read, _graph_key + ":inputs", body, limits,
            approved, binding, proof, material, goal)
        _graph_read.add(review_read.key, review_read.fields())
    value = candidate(body, proof, material, goal, aid, pid, approved,
        **({"_graph_read": _graph_read, "_review_read": review_read} if _graph_read is not None else {}))
    _checkpoint_graph_owner(_graph_read)
    if review_read is not None:
        review_read.check()
        _graph_read.add(review_read.key + ":candidate", value)
    compiled = natural.compile_candidate(value, limits)
    _checkpoint_graph_owner(_graph_read)
    if review_read is not None:
        review_read.check()
    _, _, report = compiled
    result = dict(namespace=VERSION, principal_id=user, project_id=pid, source_run_id=body.source_run_id,
        request=body.model_dump(), request_fingerprint=fingerprint(body.model_dump()),
        source_proof=proof, source_proof_fingerprint=fingerprint(proof),
        original_recipe=binding["draft"]["candidate"]["spec_recipe"],
        original_recipe_fingerprint=proof["recipe_fingerprint"],
        edited_recipe=body.recipe.model_dump(exclude_none=True),
        edited_recipe_fingerprint=fingerprint(body.recipe.model_dump(exclude_none=True)),
        edited_recipe_execution="NOT_RUN", sample_scope="SUCCESSFUL_SOURCE_ONLY",
        target_goal=goal.model_dump(),
        variable_bindings=dict(source=dict(binding_id="source", resource_id=material["resource_id"],
            source_hash=material["hash"], format=material["format"]),
            goal=dict(card_id=goal.card_id, version=goal.version, fingerprint=goal.fingerprint)),
        candidate=value, candidate_fingerprint=fingerprint(value), app_id=aid, runtime_id=runtime_id,
        report=report, approved_source_limits=approved.model_dump(),
        preview=_review_preview(material, value, _graph_read,
            **({"_review_read": review_read} if review_read is not None else {})), consent=CONSENT,
        artifact_write_consent=natural.CONSENT, new_model_requests=0, project_writes=0,
        semantic_status="UNKNOWN", owner_acceptance="PENDING", formal_publication_enabled=False)
    return {**result, "review_fingerprint": fingerprint(result)}, material, goal


def _review_preview(material, value, guard, *, _review_read=None):
    preview = natural.preview(material, value, {})
    _checkpoint_graph_owner(guard)
    if _review_read is not None:
        _check_review_read(guard, _review_read)
    return preview


def frozen_for(user, pid, body, checked):
    return dict(kind=KIND, principal_id=user, project_id=pid, app_id=checked["app_id"],
        runtime_id=checked["runtime_id"], source_run_id=body.review.source_run_id,
        request_key=body.review.request_key, request_fingerprint=fingerprint(body.model_dump()),
        review_fingerprint=checked["review_fingerprint"], candidate_fingerprint=checked["candidate_fingerprint"],
        source_proof_fingerprint=checked["source_proof_fingerprint"],
        approved_source_limits=checked["approved_source_limits"])


def _persisted_pair_input(expected, value):
    """Only the three fixed owned persisted schemas inherit the old mapping."""
    from .text_workflows import RunScopeInput

    require(any(expected is kind for kind in (ExtractInput, Metadata, RunScopeInput)),
            "Fixed owned Cold persisted schema required")
    try:
        if expected is ExtractInput:
            return ExtractInput.model_validate(value)
        if expected is Metadata:
            return Metadata.model_validate(value)
        return RunScopeInput.model_validate(value)
    except (ValidationError, KeyError, TypeError, ValueError):
        raise DomainError("VERSION_CONFLICT", "Malformed persisted DeliveryGraph binding") from None


def _persisted_extract_input(value):
    # Retain the existing fixed ExtractInput parser boundary and its callers.
    return _persisted_pair_input(ExtractInput, value)


_PAIR_FINGERPRINT_FUNCTION = fingerprint
_PAIR_FINGERPRINT_CODE = fingerprint.__code__
_PAIR_INPUT_CODE = _persisted_pair_input.__code__
_PAIR_EXTRACT_CODE = _persisted_extract_input.__code__
_PAIR_INPUT_FUNCTION = _persisted_pair_input
_PAIR_EXTRACT_FUNCTION = _persisted_extract_input
_PAIR_REQUIRE_FUNCTION = require
_PAIR_REQUIRE_CODE = require.__code__


def _cold_persisted_pair(store, c, user, aid, kind, key, expected, guard):
    """Fixed existing pairs; IO/checkpoints and external callees are not mapped."""
    try:
        require(guard is not None, "Exact Cold extraction read scope required")
        from . import delivery_graph_apps as graph
        from . import pa_spec_apps as spec
        from .text_workflows import RunScopeInput

        require((expected is ExtractInput and kind == EXTRACT)
                or (expected is Metadata and kind == META and key == "scope")
                or (expected is RunScopeInput and kind == spec.RUN_META and key == "accepted"),
                "Fixed owned Cold persisted pair required")
        _checkpoint_graph(store, c, guard)
        rows = []
        for stored_kind in (kind, kind + "_seal"):
            row = graph.lookup(c, user, aid, stored_kind, key)
            _checkpoint_graph(store, c, guard)
            rows.append(row)
        if (fingerprint is _PAIR_FINGERPRINT_FUNCTION
                and fingerprint.__code__ is _PAIR_FINGERPRINT_CODE
                and spec._scope_pair_code_current()
                and require is _PAIR_REQUIRE_FUNCTION and require.__code__ is _PAIR_REQUIRE_CODE
                and _persisted_pair_input is _PAIR_INPUT_FUNCTION
                and _persisted_pair_input.__code__ is _PAIR_INPUT_CODE
                and _persisted_extract_input is _PAIR_EXTRACT_FUNCTION
                and _persisted_extract_input.__code__ is _PAIR_EXTRACT_CODE):
            result = spec._SCOPE_PAIR_CORE(rows, expected, spec._persisted_snapshot_finite,
                require, pin=lambda: _checkpoint_graph(store, c, guard))
            if result is not spec._pair_segments._UNSUITABLE:
                return result
        require(all(rows), "Independent text logic seals missing")
        values = []
        for row in rows:
            spec._persisted_snapshot_finite(row['snapshot'])
            value = graph.checked(row)
            _checkpoint_graph(store, c, guard)
            values.append(value)
        left, right = values
        require(set(left) == {"request", "response"})
        left_fingerprint = fingerprint(left)
        _checkpoint_graph(store, c, guard)
        right_fingerprint = fingerprint(right)
        _checkpoint_graph(store, c, guard)
        require(left_fingerprint == right_fingerprint)
        # No checkpoint, SQL or external callback is enclosed by this mapper.
        body = (_persisted_extract_input(left["request"]) if expected is ExtractInput
                else _persisted_pair_input(expected, left["request"]))
        _checkpoint_graph(store, c, guard)
        for row in rows:
            request_fingerprint = fingerprint(expected.model_dump(body))
            _checkpoint_graph(store, c, guard)
            require(row["request_fingerprint"] == request_fingerprint)
        return body, left["response"]
    except BaseException:
        _invalidate_cold_inputs(guard)
        raise


def _cold_extract_pair(store, c, user, aid, key, guard):
    return _cold_persisted_pair(store, c, user, aid, EXTRACT, key, ExtractInput, guard)


def _verify_prefix(store, c, user, draft, *, _graph_read=None):
    from . import pa_spec_apps as spec

    _checkpoint_graph(store, c, _graph_read)
    scoped = spec.scope_gate(store, c, user, draft["id"],
        **({"_graph_read": _graph_read} if _graph_read is not None else {}))
    _checkpoint_graph(store, c, _graph_read)
    require(scoped)
    result = c.execute(select(task_extractions).where(task_extractions.c.app_id == draft["id"]))
    _checkpoint_graph(store, c, _graph_read)
    marker = result.mappings().one()
    paired = (pair(c, user, draft["id"], EXTRACT, marker["request_key"], ExtractInput)
        if _graph_read is None else _cold_extract_pair(store, c, user,
            draft["id"], marker["request_key"], _graph_read))
    _checkpoint_graph(store, c, _graph_read)
    body, frozen = paired
    paired = (pair(c, user, draft["id"], META, "scope", Metadata)
        if _graph_read is None else _cold_persisted_pair(store, c, user,
            draft["id"], META, "scope", Metadata, _graph_read))
    _checkpoint_graph(store, c, _graph_read)
    meta, _ = paired
    require(marker["principal_id"] == user and marker["task_id"] == body.review.source_run_id == meta.source_run_id
            and marker["request_key"] == body.review.request_key
            and marker["request_fingerprint"] == fingerprint(body.model_dump()))
    return marker, body, frozen, meta


def _extraction_name(store, c, draft, guard, *, _typed_models=None):
    result = c.execute(select(app_drafts.c.name).where(app_drafts.c.id == draft["id"]))
    _cold_typed_checkpoint(store, c, guard, _typed_models)
    return result.scalar_one()


def _verify_from_review(store, c, user, draft, limits, marker, body, frozen, meta,
                        checked, material, goal, *, _graph_read=None, _typed_models=None):
    _cold_typed_checkpoint(store, c, _graph_read, _typed_models)
    require(body.expected_review_fingerprint == checked["review_fingerprint"]
            and frozen == frozen_for(user, draft["project_id"], body, checked)
            and fingerprint(marker["snapshot"]) == fingerprint(frozen)
            and draft["id"] == checked["app_id"] and draft["runtime_id"] == checked["runtime_id"]
            and fingerprint(draft["candidate"]) == draft["fingerprint"] == checked["candidate_fingerprint"]
            and _extraction_name(store, c, draft, _graph_read,
                **({"_typed_models": _typed_models} if _graph_read is not None else {})) == body.review.name
            and meta.resource_id == material["resource_id"])
    compiled = natural.compile_candidate(draft["candidate"], limits)
    _cold_typed_checkpoint(store, c, _graph_read, _typed_models)
    manifest, _, report = compiled
    return manifest, report, material, goal.model_dump()


@controlled
def verify(store, c, user, draft, limits):
    marker, body, frozen, meta = _verify_prefix(store, c, user, draft)
    checked, material, goal = review(store, c, user, draft["project_id"], body.review, limits, draft["runtime_id"])
    return _verify_from_review(store, c, user, draft, limits,
        marker, body, frozen, meta, checked, material, goal)


@dataclass(frozen=True)
class _ColdExtractionPrefix:
    guard: Any
    key: str
    user: str
    draft: Any
    limits: Limits
    role: str
    marker: Any
    body: ExtractInput
    frozen: dict
    meta: Metadata
    _origin_guard: Any = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, "_origin_guard", self.guard)

    def fields(self):
        return dict(user=self.user, draft=dict(self.draft), limits=_cold_model_dump(Limits, self.limits), role=self.role,
                    marker=dict(self.marker), body=_cold_model_dump(ExtractInput, self.body),
                    frozen=self.frozen, meta=_cold_model_dump(Metadata, self.meta))


@dataclass(frozen=True)
class _ColdExtractionReview:
    prefix: _ColdExtractionPrefix
    source: _ColdSourceFacts
    key: str
    checked: dict
    material: dict
    goal: Any

    def fields(self):
        return dict(prefix=self.prefix.fields(), source=self.source.fields(), checked=self.checked,
                    material=self.material, goal=_cold_model_dump(GoalCardRunSource, self.goal))


def _cold_verify_prefix(store, c, user, draft, limits, guard, role):
    """Stop after exact extraction identity and before its Source dependency."""
    try:
        if guard is None:
            raise DomainError("VERSION_CONFLICT", "Exact Cold graph read scope required")
        _checkpoint_graph(store, c, guard)
        require(type(limits) is Limits and role in {"source", "generate", "cold"})
        marker, body, frozen, meta = _verify_prefix(store, c, user, draft, _graph_read=guard)
        key = ":".join(("pb-extraction", role, user, draft["id"], fingerprint(limits.model_dump())))
        prefix = _ColdExtractionPrefix(guard, key, user, draft, limits, role, marker, body, frozen, meta)
        guard.add(prefix.key, prefix.fields())
        return prefix
    except BaseException:
        _invalidate_cold_inputs(guard)
        raise


def _cold_review_from_source(store, c, user, prefix, source_facts):
    """Compare Source first, then original current target gates and full review."""
    guard = None
    try:
        from . import pa_spec_apps as spec

        require(type(prefix) is _ColdExtractionPrefix and type(source_facts) is _ColdSourceFacts
            and type(source_facts.typed) is _ColdSourceTyped
            and type(source_facts.typed.prefix) is _ColdSourcePrefix)
        guard = prefix.guard
        require(guard is prefix._origin_guard, "Cold extraction read scope cannot be replaced")
        if guard is None:
            raise DomainError("VERSION_CONFLICT", "Exact Cold graph read scope required")
        _cold_fields(store, c, guard, prefix.key, prefix.fields())
        _cold_fields(store, c, guard, source_facts.key, source_facts.fields())
        source_prefix = source_facts.typed.prefix
        require(user == prefix.user == source_prefix.user and guard is source_prefix.guard
                and source_prefix.guard is source_prefix._origin_guard
                and prefix.draft["project_id"] == source_prefix.pid
                and prefix.body.review.source_run_id == source_prefix.rid
                and prefix.limits is source_prefix.limits and prefix.role == source_prefix.role)
        models: list[tuple[type[Strict], Strict, dict]] = [(ExtractInput, prefix.body, guard.inputs[prefix.key]["body"]),
                  (Metadata, prefix.meta, guard.inputs[prefix.key]["meta"])]
        _review_source_from_facts(prefix.body.review, source_facts.proof)
        _cold_typed_checkpoint(store, c, guard, models)
        targeted = spec.target(store, c, user, prefix.draft["project_id"], prefix.body.review.card_id,
            prefix.body.review.expected_goal_version, prefix.body.review.expected_goal_fingerprint,
            prefix.draft["runtime_id"], family=natural.VERSION, _graph_read=guard)
        _cold_typed_checkpoint(store, c, guard, models)
        material, goal = targeted
        target = dict(material=material, goal=_cold_model_dump(GoalCardRunSource, goal))
        guard.add(prefix.key + ":target", target)
        models.append((GoalCardRunSource, goal, target["goal"]))
        reviewed = _review_from_facts(user, prefix.draft["project_id"], prefix.body.review, prefix.limits,
            source_facts.binding, source_facts.proof, material, goal,
            _graph_read=guard, _graph_key=prefix.key + ":review")
        _cold_typed_checkpoint(store, c, guard, models)
        checked, material, goal = reviewed
        facts = _ColdExtractionReview(prefix, source_facts, prefix.key + ":review", checked, material, goal)
        guard.add(facts.key, facts.fields())
        return facts
    except BaseException:
        _invalidate_cold_inputs(guard, prefix, source_facts)
        raise


def _cold_verify_from_review(store, c, user, prefix, review_facts):
    guard = None
    try:
        require(type(prefix) is _ColdExtractionPrefix and type(review_facts) is _ColdExtractionReview)
        guard = prefix.guard
        require(guard is prefix._origin_guard, "Cold extraction read scope cannot be replaced")
        if guard is None:
            raise DomainError("VERSION_CONFLICT", "Exact Cold graph read scope required")
        _cold_fields(store, c, guard, prefix.key, prefix.fields())
        _cold_fields(store, c, guard, review_facts.key, review_facts.fields())
        require(review_facts.prefix is prefix and user == prefix.user)
        models: list[tuple[type[Strict], Strict, dict]] = [(ExtractInput, prefix.body, guard.inputs[prefix.key]["body"]),
                  (Metadata, prefix.meta, guard.inputs[prefix.key]["meta"]),
                  (GoalCardRunSource, review_facts.goal, guard.inputs[review_facts.key]["goal"])]
        value = _verify_from_review(store, c, user, prefix.draft, prefix.limits,
            prefix.marker, prefix.body, prefix.frozen, prefix.meta,
            review_facts.checked, review_facts.material, review_facts.goal,
            _graph_read=guard, _typed_models=models)
        _cold_typed_checkpoint(store, c, guard, models)
        manifest, report, material, goal = value
        guard.add(prefix.key + ":verified", dict(manifest=manifest.model_dump(),
            report=report, material=material, goal=goal))
        return value
    except BaseException:
        _invalidate_cold_inputs(guard, prefix, review_facts)
        raise


def _cold_verify_facet_from_review(store, c, user, prefix, review_facts, limits, source_facts, *, role=None):
    """Recompile a new Limits facet over the same full metadata and target facts.

    Fresh original scope/authority gates remain root-owned at the role edge.
    Complete new Source proof is required; no earlier compile/review digest is
    used as a substitute for this Limits facet's complete comparison/compile.
    """
    guard = None
    try:
        require(type(prefix) is _ColdExtractionPrefix and type(review_facts) is _ColdExtractionReview
            and type(source_facts) is _ColdSourceFacts
            and type(source_facts.typed) is _ColdSourceTyped
            and type(source_facts.typed.prefix) is _ColdSourcePrefix)
        guard = prefix.guard
        require(guard is prefix._origin_guard, "Cold extraction read scope cannot be replaced")
        if guard is None:
            raise DomainError("VERSION_CONFLICT", "Exact Cold graph read scope required")
        _cold_fields(store, c, guard, prefix.key, prefix.fields())
        _cold_fields(store, c, guard, review_facts.key, review_facts.fields())
        _cold_fields(store, c, guard, source_facts.key, source_facts.fields())
        source_prefix = source_facts.typed.prefix
        facet_role = prefix.role if role is None else role
        require(user == prefix.user == source_prefix.user and review_facts.prefix is prefix
            and type(limits) is Limits and facet_role in {"source", "generate", "cold"}
            and guard is source_prefix.guard and source_prefix.guard is source_prefix._origin_guard
            and limits is source_prefix.limits
            and facet_role == source_prefix.role
            and prefix.draft["project_id"] == source_prefix.pid
            and prefix.body.review.source_run_id == source_prefix.rid)
        key = ":".join(("pb-extraction", facet_role, user, prefix.draft["id"],
                        fingerprint(limits.model_dump())))
        facet = _ColdExtractionPrefix(guard, key, user, prefix.draft, limits, facet_role,
            prefix.marker, prefix.body, prefix.frozen, prefix.meta)
        guard.add(facet.key, facet.fields())
        guard.add(facet.key + ":limits", limits)
        models: list[tuple[type[Strict], Strict, dict]] = [(ExtractInput, prefix.body, guard.inputs[prefix.key]["body"]),
                  (Metadata, prefix.meta, guard.inputs[prefix.key]["meta"]),
                  (GoalCardRunSource, review_facts.goal, guard.inputs[review_facts.key]["goal"])]
        _review_source_from_facts(facet.body.review, source_facts.proof)
        _cold_typed_checkpoint(store, c, guard, models)
        # Original complete target bytes and Goal identity; no repeated target IO.
        material, goal = review_facts.material, review_facts.goal
        guard.add(facet.key + ":target", dict(material=material, goal=_cold_model_dump(GoalCardRunSource, goal)))
        reviewed = _review_from_facts(user, facet.draft["project_id"], facet.body.review, limits,
            source_facts.binding, source_facts.proof, material, goal,
            _graph_read=guard, _graph_key=facet.key + ":review")
        _cold_typed_checkpoint(store, c, guard, models)
        checked, material, goal = reviewed
        review = _ColdExtractionReview(facet, source_facts, facet.key + ":review", checked, material, goal)
        guard.add(review.key, review.fields())
        # Shared exact AND order retains the name scalar at the original point.
        value = _cold_verify_from_review(store, c, user, facet, review)
        _checkpoint_graph(store, c, guard)
        return facet, review, value
    except BaseException:
        _invalidate_cold_inputs(guard, prefix, review_facts, source_facts)
        raise


def _audit_prefix(store, c, user, draft, *, _graph_read=None):
    from . import pa_spec_apps as spec

    _checkpoint_graph(store, c, _graph_read)
    scoped = spec.scope_gate(store, c, user, draft["id"],
        **({"_graph_read": _graph_read} if _graph_read is not None else {}))
    _checkpoint_graph(store, c, _graph_read)
    require(scoped)
    paired = (pair(c, user, draft["id"], META, "scope", Metadata)
        if _graph_read is None else _cold_persisted_pair(store, c, user,
            draft["id"], META, "scope", Metadata, _graph_read))
    _checkpoint_graph(store, c, _graph_read)
    meta, meta_seal = paired
    result = c.execute(select(task_extractions).where(task_extractions.c.app_id == draft["id"]))
    _checkpoint_graph(store, c, _graph_read)
    marker = result.mappings().one()
    paired = (pair(c, user, draft["id"], EXTRACT, marker["request_key"], ExtractInput)
        if _graph_read is None else _cold_extract_pair(store, c, user,
            draft["id"], marker["request_key"], _graph_read))
    _checkpoint_graph(store, c, _graph_read)
    body, frozen = paired
    result = c.execute(select(app_drafts).where(app_drafts.c.id == draft["id"],
        app_drafts.c.project_id == draft["project_id"], app_drafts.c.runtime_id == draft["runtime_id"]))
    _checkpoint_graph(store, c, _graph_read)
    actual = result.mappings().one()
    return meta, meta_seal, marker, body, frozen, actual


def _audit_from_source(meta, meta_seal, marker, body, frozen, actual, source_digest, *, _audit_out=None):
    digest = fingerprint(dict(source_audit=source_digest,
        metadata=meta.model_dump(), metadata_seal=meta_seal,
        marker=dict(marker), request=body.model_dump(), frozen=frozen, draft=dict(actual)))
    if _audit_out is not None:
        _audit_out.update(base=copy.deepcopy(dict(actual)), digest=digest)
    return digest


def audit_fingerprint(store, c, user, draft, *, _audit_out=None):
    meta, meta_seal, marker, body, frozen, actual = _audit_prefix(store, c, user, draft)
    source_digest = source_audit(store, c, user, draft["project_id"], meta.source_run_id)
    return _audit_from_source(meta, meta_seal, marker, body, frozen, actual, source_digest,
                              _audit_out=_audit_out)


@dataclass(frozen=True)
class _ColdExtractionAuditPrefix:
    guard: Any
    key: str
    user: str
    draft: Any
    meta: Metadata
    meta_seal: dict
    marker: Any
    body: ExtractInput
    frozen: dict
    actual: Any
    _origin_guard: Any = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, "_origin_guard", self.guard)

    def fields(self):
        return dict(user=self.user, draft=dict(self.draft), metadata=_cold_model_dump(Metadata, self.meta),
                    metadata_seal=self.meta_seal, marker=dict(self.marker), body=_cold_model_dump(ExtractInput, self.body),
                    frozen=self.frozen, actual=dict(self.actual))


def _cold_audit_prefix(store, c, user, draft, guard):
    """Stop at the original Source audit field before collecting that dependency."""
    try:
        if guard is None:
            raise DomainError("VERSION_CONFLICT", "Exact Cold graph read scope required")
        _checkpoint_graph(store, c, guard)
        meta, meta_seal, marker, body, frozen, actual = _audit_prefix(store, c, user, draft, _graph_read=guard)
        prefix = _ColdExtractionAuditPrefix(guard, "pb-extraction-audit:" + user + ":" + draft["id"],
            user, draft, meta, meta_seal, marker, body, frozen, actual)
        guard.add(prefix.key, prefix.fields())
        return prefix
    except BaseException:
        _invalidate_cold_inputs(guard)
        raise


def _cold_audit_from_source(store, c, user, prefix, source_facts, *, _audit_out=None):
    guard = None
    try:
        require(type(prefix) is _ColdExtractionAuditPrefix
            and type(source_facts) is _ColdSourceAuditFacts
            and type(source_facts.prefix) is _ColdSourceAuditPrefix)
        guard = prefix.guard
        require(guard is prefix._origin_guard, "Cold extraction read scope cannot be replaced")
        if guard is None:
            raise DomainError("VERSION_CONFLICT", "Exact Cold graph read scope required")
        _cold_fields(store, c, guard, prefix.key, prefix.fields())
        _cold_fields(store, c, guard, source_facts.key, source_facts.fields())
        require(user == prefix.user == source_facts.prefix.user and guard is source_facts.prefix.guard
                and source_facts.prefix.guard is source_facts.prefix._origin_guard
                and prefix.draft["project_id"] == source_facts.prefix.pid
                and prefix.meta.source_run_id == source_facts.prefix.rid)
        digest = _audit_from_source(prefix.meta, prefix.meta_seal, prefix.marker, prefix.body,
            prefix.frozen, prefix.actual, source_facts.digest, _audit_out=_audit_out)
        _checkpoint_graph(store, c, guard)
        return digest
    except BaseException:
        _invalidate_cold_inputs(guard, prefix, source_facts)
        raise


def receipt(body, checked, frozen):
    return dict(namespace=VERSION, id=frozen["app_id"], **frozen, request=body.model_dump(),
        reviewed=checked, new_model_requests=0, project_writes=0,
        semantic_status="UNKNOWN", owner_acceptance="PENDING", formal_publication_enabled=False)


@controlled
def extract(store, user, pid, rid, body, limits):
    # Match explicit key closure's bounded SQLite wait for the shared write group.
    with store.tx(wait_seconds=30) as c:
        return _extract(store, c, user, pid, rid, body, limits)


@controlled
def _extract(store, c, user, pid, rid, body, limits):
    """Original extraction write group, shared with the bounded trial controller."""
    from .apps import load_draft

    require(c.in_transaction())
    store.lock_project(c, user, pid)
    require(body.review.source_run_id == rid)
    from .pb_extraction_terminals import fenced

    source_gate(store, c, user, pid, rid)
    require(not fenced(c, rid, body.review.request_key),
            "Original P-B extraction key is permanently closed or its closure evidence is incomplete")
    checked, material, _ = review(store, c, user, pid, body.review, limits)
    require(checked["review_fingerprint"] == body.expected_review_fingerprint)
    prior = c.execute(select(task_extractions.c.app_id).where(task_extractions.c.task_id == rid,
        task_extractions.c.principal_id == user, task_extractions.c.request_key == body.review.request_key)).scalar()
    if prior:
        draft, _, _, _ = load_draft(store, c, user, prior, limits)
        old, frozen = pair(c, user, prior, EXTRACT, body.review.request_key, ExtractInput)
        require(old.model_dump() == body.model_dump())
        return receipt(body, checked, frozen)
    if len(c.execute(select(task_extractions.c.app_id).where(task_extractions.c.task_id == rid,
        task_extractions.c.principal_id == user)).all()) >= MAX:
        raise DomainError("BUDGET_EXHAUSTED", "Finite P-B source extraction capacity exhausted")
    aid, runtime = checked["app_id"], checked["runtime_id"]
    frozen = frozen_for(user, pid, body, checked)
    c.execute(insert(principals).values(id=runtime, name="P-B natural spec target runtime"))
    for ref, tool in [(material["resource_id"], natural.READ), (pid, natural.SAVE)]:
        c.execute(insert(grants).values(id=new_id("grant"), principal_id=runtime, project_id=pid,
            resource_id=ref, tool_ref=tool, expires_at=time.time() + 86400, revision=1, revoked=False))
    c.execute(insert(app_drafts).values(id=aid, project_id=pid, runtime_id=runtime, name=body.review.name,
        candidate=checked["candidate"], fingerprint=checked["candidate_fingerprint"], created_at=time.time()))
    c.execute(insert(task_extractions).values(task_id=rid, principal_id=user,
        request_key=body.review.request_key, request_fingerprint=fingerprint(body.model_dump()),
        app_id=aid, snapshot=frozen))
    meta = Metadata(app_id=aid, principal_id=user, project_id=pid, runtime_id=runtime,
                    resource_id=material["resource_id"], source_run_id=rid)
    remember(c, user, aid, META, "scope", meta, meta.model_dump())
    remember(c, user, aid, EXTRACT, body.review.request_key, body, frozen)
    # Fresh final origin, target, seals, budget and exact candidate verification.
    draft, _, _, _ = load_draft(store, c, user, aid, limits)
    verify(store, c, user, draft, limits)
    return receipt(body, checked, frozen)

def mount(app, store, limits, identity):
    from . import pb_extraction_terminals as terminals

    user_dependency = Depends(identity)

    @app.get("/api/projects/{pid}/natural-spec-task-runs/{rid}/extraction-options")
    def options(pid: str, rid: str, user=user_dependency):
        with store.tx() as c:
            binding, proof = source(store, c, user, pid, rid, limits)
            return dict(namespace=VERSION, principal_id=user, project_id=pid, source_run_id=rid,
                source_proof=proof, source_proof_fingerprint=fingerprint(proof),
                recipe=copy.deepcopy(binding["draft"]["candidate"]["spec_recipe"]),
                recipe_fingerprint=proof["recipe_fingerprint"],
                approved_source_limits=binding["draft"]["candidate"]["manifest"]["runtime_limits"],
                new_model_requests=0, project_writes=0, semantic_status="UNKNOWN",
                owner_acceptance="PENDING", formal_publication_enabled=False)

    @app.post("/api/projects/{pid}/natural-spec-task-runs/{rid}/extraction-reviews")
    def preview(pid: str, rid: str, body: ReviewInput, user=user_dependency):
        with store.tx() as c:
            store.lock_project(c, user, pid)
            require(body.source_run_id == rid)
            checked, _, _ = review(store, c, user, pid, body, limits)
            return checked

    @app.post("/api/projects/{pid}/natural-spec-task-runs/{rid}/extractions", status_code=201)
    def create(pid: str, rid: str, body: ExtractInput, user=user_dependency):
        return extract(store, user, pid, rid, body, limits)

    @app.post("/api/projects/{pid}/natural-spec-task-runs/{rid}/extractions/by-key/{key}/close")
    def close_unused(pid: str, rid: str, key: str, body: terminals.CloseInput, user=user_dependency):
        return terminals.close(store, user, pid, rid, key, body, limits)

    @app.get("/api/projects/{pid}/natural-spec-task-runs/{rid}/extractions/by-key/{key}")
    def recover(pid: str, rid: str, key: str, user=user_dependency):
        from .apps import load_draft

        with store.tx() as c:
            source_gate(store, c, user, pid, rid)
            terminal = terminals.read(store, c, user, pid, rid, key)
            if terminal is not None:
                return terminal
            aid = c.execute(select(task_extractions.c.app_id).where(task_extractions.c.task_id == rid,
                task_extractions.c.principal_id == user, task_extractions.c.request_key == key)).scalar()
            if aid is None:
                raise DomainError("OUTCOME_UNKNOWN", "Only read this original extraction key; do not resend")
            draft, _, _, _ = load_draft(store, c, user, aid, limits)
            body, frozen = pair(c, user, aid, EXTRACT, key, ExtractInput)
            require(draft["project_id"] == pid and body.review.source_run_id == rid)
            checked, _, _ = review(store, c, user, pid, body.review, limits, draft["runtime_id"])
            verify(store, c, user, draft, limits)
            return receipt(body, checked, frozen)


# The owned Source producer/consumer closure is fixed before any read callback.
from . import _cold_source_packet as _source_fact_code
_source_fact_code.register(6,globals(),(
    '_owned_source_enabled','_checkpoint_graph','_checkpoint_graph_owner','_cold_fields','_cold_model_dump',
    '_cold_typed_checkpoint','_source_audit_prefix','_source_audit_rows',
    '_cold_source_audit_prefix','_cold_source_audit_from_original',
    '_source_prefix','_source_typed','_source_from_audit','_source_proof_fields',
    '_cold_source_prefix','_cold_source_typed','_cold_source_from_audit',
    '_cold_source_facet_from_source','_cold_review_from_source',
    '_cold_verify_from_review','_cold_verify_facet_from_review','_cold_audit_from_source',
    '_audit_prefix','_cold_audit_prefix','_cold_extract_pair',
    '_review_source_from_facts','_review_from_facts','_verify_from_review','_audit_from_source',
    '_check_review_read','_cold_persisted_pair','_persisted_pair_input','_persisted_extract_input',
    '_review_preview','candidate','frozen_for','_extraction_name','_invalidate_cold_inputs',
    'source_gate','require','fingerprint'),
    (_ColdSourcePrefix,_ColdSourceTyped,_ColdSourceFacts,_ColdSourceAuditPrefix,
     _ColdSourceAuditFacts,_ColdExtractionReview,_ColdReviewRead,_ColdExtractionAuditPrefix,
     Metadata,ExtractInput,ReviewInput),
    constants=('natural','_source_fact_code','app_drafts','task_extractions','select','copy',
        'Metadata','ExtractInput','ReviewInput','GoalCardRunSource','Limits','META','EXTRACT'))
