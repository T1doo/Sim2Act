"""Shared sealed per-Run binding engine; distinct saved P-A/P-B provenance."""
import copy
import time
from dataclasses import dataclass
from typing import Any, Literal

from fastapi import Depends
from pydantic import Field
from sqlalchemy import bindparam, insert, select

from . import natural_specs as natural
from . import pb_natural_specs as pb
from .contracts import GoalCardRunSource, Limits, Strict
from .db import (
    delivery_graph_requests,
    fingerprint,
    grants,
    internal_app_runs,
    internal_run_bindings,
    new_id,
    runs,
)
from .delivery_graph_apps import HASH, controlled
from .errors import DomainError
from .text_logic_reuse import KEY, pair, remember, require
from .text_workflows import RunScopeInput

VERSION = "pb-natural-per-run.v1"
USE, META = "pb_natural_use", "pb_natural_use_scope"
CONSENT = "RUN_THIS_SAVED_PB_LOGIC_WITH_THIS_EXACT_GOAL_MATERIAL_AND_READ_GRANT"
MAX = 64


class ReviewInput(Strict):
    expected_revision: int = Field(strict=True, ge=1)
    expected_release_fingerprint: str = Field(pattern=HASH)
    expected_app_fingerprint: str = Field(pattern=HASH)
    expected_recipe_fingerprint: str = Field(pattern=HASH)
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    card_id: str = Field(pattern=r"^goal_[a-f0-9]{32}$")
    expected_goal_version: int = Field(strict=True, ge=1)
    expected_goal_fingerprint: str = Field(pattern=HASH)
    expected_source_hash: str = Field(pattern=HASH)
    request_key: str = Field(pattern=KEY)


class CommitInput(Strict):
    review: ReviewInput
    expected_review_fingerprint: str = Field(pattern=HASH)
    consent: Literal["RUN_THIS_SAVED_PB_LOGIC_WITH_THIS_EXACT_GOAL_MATERIAL_AND_READ_GRANT"]


PA_CONSENT = "RUN_THIS_SAVED_PA_LOGIC_WITH_THIS_EXACT_GOAL_MATERIAL_AND_READ_GRANT"


class PACommitInput(Strict):
    review: ReviewInput
    expected_review_fingerprint: str = Field(pattern=HASH)
    consent: Literal["RUN_THIS_SAVED_PA_LOGIC_WITH_THIS_EXACT_GOAL_MATERIAL_AND_READ_GRANT"]


@dataclass(frozen=True)
class Family:
    field: str
    namespace: str
    use: str
    meta: str
    consent: str
    body_type: type[CommitInput] | type[PACommitInput]
    route: str


PB = Family("pb_use", VERSION, USE, META, CONSENT, CommitInput, "pb-use")
PA = Family("pa_use", "pa-natural-per-run.v1", "pa_natural_use", "pa_natural_use_scope",
    PA_CONSENT, PACommitInput, "pa-use")
FAMILIES = (PB, PA)
_USE_FAMILY_STATES=tuple((value,vars(value),tuple(vars(value).items())) for value in FAMILIES)


def _use_family_current():
    """Fresh fixed routing configuration, never historical permissions."""
    for value,storage,items in _USE_FAMILY_STATES:
        require(type(value) is Family, 'Exact per-use family configuration required')
        current=object.__getattribute__(value,'__dict__')
        require(current is storage and type(current) is dict and len(current)==len(items)
            and all(key is old_key and value is old_value
                for (key,value),(old_key,old_value) in zip(current.items(),items,strict=True)),
            'Per-use family configuration changed')

# Reuse immutable SQL syntax, never query results or per-use authorities.
_HINT_LEDGER = select(delivery_graph_requests.c.app_id).where(
    delivery_graph_requests.c.app_id == bindparam("hint_run_id", type_=delivery_graph_requests.c.app_id.type),
    delivery_graph_requests.c.kind.in_(bindparam("hint_kinds", expanding=True, type_=delivery_graph_requests.c.kind.type)))
_HINT_BINDINGS = {family.field: select(internal_run_bindings.c.snapshot[family.field]["review"]["resource_id"].as_string())
    .where(internal_run_bindings.c.run_id == bindparam("hint_run_id", type_=internal_run_bindings.c.run_id.type))
    for family in FAMILIES}
_HINT_RESPONSE = select(delivery_graph_requests.c.app_id).where(
    delivery_graph_requests.c.kind == bindparam("hint_kind", type_=delivery_graph_requests.c.kind.type),
    delivery_graph_requests.c.snapshot["response"]["run_id"].as_string() == bindparam("hint_run_id", type_=internal_run_bindings.c.run_id.type))


# Publish the strict input models before the spec module bootstraps its fixed
# schema catalogue. This keeps direct CLI imports independent of API preload.
from . import pa_spec_apps as spec  # noqa: E402


def saved_family(candidate):
    if not natural.is_candidate(candidate):
        return None
    if candidate.get("spec_task", {}).get("kind") == pb.KIND:
        return PB
    if "spec_task" not in candidate and ("goal_application" in candidate or
            candidate.get("spec_binding", {}).get("kind") == spec.KIND):
        return PA
    return None


def base_audit(store, c, user, base, family, *, _audit_out=None):
    if family == PB and _audit_out is not None:
        return pb.audit_fingerprint(store, c, user, base, _audit_out=_audit_out)
    return (pb.audit_fingerprint if family == PB else spec.audit_fingerprint)(store, c, user, base)


def _bound_fingerprint(value):
    draft, manifest, report, material, goal = value
    return fingerprint([draft, manifest.model_dump(), report, material, goal])


def _invalidate_use_reads(*values):
    """Invalidate only known local packets or the exact read scope; never duck type."""
    if all(value is None for value in values):
        return
    from .natural_spec_runtime import _ColdGraphRead

    for value in values:
        guard = None
        if type(value) is _ColdGraphRead:
            guard = value
        elif type(value) in (_ColdUseReviewPrefix, _ColdUseBoundPrefix, _ColdUseAuditPrefix):
            guard = getattr(value, "guard", None)
        elif type(value) is _ColdUseReviewFacts:
            prefix = getattr(value, "prefix", None)
            if type(prefix) is _ColdUseReviewPrefix:
                guard = getattr(prefix, "guard", None)
        if type(guard) is _ColdGraphRead:
            _ColdGraphRead.invalidate(guard)


def _use_read_checkpoint(store, c, guard):
    try:
        if guard is not None:
            from .natural_spec_runtime import _cold_read_checkpoint
            _cold_read_checkpoint(store, c, guard)
            _use_family_current()
    except BaseException:
        _invalidate_use_reads(guard)
        raise


def _use_own_checkpoint(guard):
    try:
        if guard is not None:
            from .natural_spec_runtime import _ColdGraphRead
            require(type(guard) is _ColdGraphRead, "Exact Cold graph read scope required")
            _use_read_checkpoint(guard.store, guard.connection, guard)
    except BaseException:
        _invalidate_use_reads(guard)
        raise


def _use_read_inputs(store, c, guard, key, fields, *, start=False):
    try:
        if guard is not None:
            if start:
                from .natural_spec_runtime import _ColdGraphRead
                require(type(guard) is _ColdGraphRead, "Exact Cold graph read scope required")
                guard.add(key, fields)
            else:
                _use_read_checkpoint(store, c, guard)
                require(key in guard.inputs and fields == guard.inputs[key],
                    "Cold per-use complete inputs changed")
    except BaseException:
        _invalidate_use_reads(guard)
        raise


def _use_dump(expected, model, guard):
    """Only strict owned fixed classes; defaults keep their original serializer."""
    if guard is None:
        return model.model_dump()
    try:
        require(any(expected is kind for kind in (ReviewInput, CommitInput, RunScopeInput, GoalCardRunSource))
            and type(model) is expected, "Exact fixed per-use typed fact required")
        if expected is CommitInput:
            require(type(model.review) is ReviewInput, "Exact nested per-use review required")
        return expected.model_dump(model)
    except BaseException:
        _invalidate_use_reads(guard)
        raise


def _use_typed_current(guard, expected, model, raw):
    try:
        if guard is not None:
            from .natural_live_admission import _trial_typed_equal
            require(type(raw) is dict and _trial_typed_equal(_use_dump(expected, model, guard), raw),
                "Typed per-use fact changed after its complete raw proof")
    except BaseException:
        _invalidate_use_reads(guard)
        raise


@controlled
def _use_pair_model_validate(expected, raw):
    """Only persisted fixed-schema parsing is normalized; no IO/checkpoint here."""
    require(any(expected is kind for kind in (CommitInput, RunScopeInput)),
        "Exact owned per-use persisted schema required")
    return expected.model_validate(raw)


def _use_pair(c, user, lid, kind, key, expected, *, _graph_read=None):
    if _graph_read is None:
        return pair(c, user, lid, kind, key, expected)
    try:
        from . import delivery_graph_apps as graph
        from .natural_spec_runtime import _ColdGraphRead

        require(type(_graph_read) is _ColdGraphRead, "Exact Cold graph read scope required")
        require(any(expected is model for model in (CommitInput, RunScopeInput)),
            "Exact owned per-use persisted schema required")
        store = _graph_read.store
        _use_read_checkpoint(store, c, _graph_read)
        rows = []
        for paired_kind in (kind, kind + "_seal"):
            row = graph.lookup(c, user, lid, paired_kind, key)
            _use_read_checkpoint(store, c, _graph_read)
            rows.append(row)
        require(all(rows), "Independent text logic seals missing")
        checked = []
        for row in rows:
            spec._persisted_snapshot_finite(row['snapshot'])
            value = graph.checked(row)
            _use_read_checkpoint(store, c, _graph_read)
            checked.append(value)
        left, right = checked
        require(set(left) == {"request", "response"} and fingerprint(left) == fingerprint(right))
        body = _use_pair_model_validate(expected, left["request"])
        _use_read_checkpoint(store, c, _graph_read)
        require(all(row["request_fingerprint"] == fingerprint(_use_dump(expected, body, _graph_read))
            for row in rows))
        response=left['response']
        if expected is CommitInput and pb._owned_source_enabled():
            # Each original paired read has its own checked/deepcopy domain.
            # Transfer before :pair/:paired publishes any old mutable alias;
            # neither a prior response nor a permission result is reused.
            name='pb-use-response:'+str(len(vars(_graph_read).get('_source_fact_bindings',{})))
            response=_use_fact_code.own_fact(_graph_read,name,response)
        return body, response
    except BaseException:
        _invalidate_use_reads(_graph_read)
        raise


def _review_target_current(store, c, guard, key, material, goal):
    try:
        _use_read_checkpoint(store, c, guard)
        require(key in guard.inputs, "Complete per-use target pin required")
        _use_typed_current(guard, GoalCardRunSource, goal, guard.inputs[key]["goal"])
        require(dict(material=material, goal=_use_dump(GoalCardRunSource, goal, guard)) == guard.inputs[key],
            "Complete per-use target changed")
    except BaseException:
        _invalidate_use_reads(guard)
        raise


def _review_inputs(user, instance, release, body, limits, runtime, approved_grants, *, _graph_read=None):
    return dict(principal_id=user, instance=instance, release=release,
        request=_use_dump(ReviewInput, body, _graph_read), platform_limits=limits, runtime_id=runtime,
        approved_grant_state=approved_grants)


def _review_inputs_current(store, c, guard, key, user, instance, release, body, limits, runtime, approved_grants):
    try:
        _use_read_checkpoint(store, c, guard)
        require(key in guard.inputs, "Complete per-use request pin required")
        _use_typed_current(guard, ReviewInput, body, guard.inputs[key]["request"])
        require(key in guard.inputs and _review_inputs(user, instance, release, body, limits, runtime, approved_grants, _graph_read=guard) == guard.inputs[key], "Cold per-use complete review inputs changed")
    except BaseException:
        _invalidate_use_reads(guard)
        raise


def _scope_inputs_current(store, c, guard, key, header, meta, seal):
    try:
        _use_read_checkpoint(store, c, guard)
        require(key in guard.inputs, "Complete per-use scope pin required")
        _use_typed_current(guard, RunScopeInput, meta, guard.inputs[key]["meta"])
        require(key in guard.inputs and dict(header=header, meta=_use_dump(RunScopeInput, meta, guard), seal=seal)
            == guard.inputs[key], "Cold per-use accepted scope facts changed")
    except BaseException:
        _invalidate_use_reads(guard)
        raise


@dataclass(frozen=True)
class _ColdUseReviewPrefix:
    """Complete target/compile/Grant prefix, before the original base audit."""
    guard: Any
    key: str
    user: Any
    instance: Any
    release: Any
    body: Any
    limits: Any
    runtime: Any
    approved_grants: Any
    family: Family
    base: Any
    saved: Any
    logic_origin: Any
    material: Any
    goal: Any
    declared: Limits
    value: Any
    report: Any
    result: Any
    role: str = "per_use"

    def input_fields(self):
        return _review_inputs(self.user, self.instance, self.release, self.body, self.limits, self.runtime, self.approved_grants, _graph_read=self.guard)

    def fields(self):
        return dict(inputs=self.input_fields(), base=self.base, saved=self.saved,
            logic_origin=self.logic_origin, material=self.material, goal=_use_dump(GoalCardRunSource, self.goal, self.guard),
            declared_limits=self.declared, effective_candidate=self.value,
            report=self.report, result_prefix=self.result, role=self.role)

    def check(self, store, c, user):
        try:
            _use_read_checkpoint(store, c, self.guard)
            require(self.guard is not None and self.user == user and self.family is PB
                and self.logic_origin is None, "Exact plain P-B review prefix required")
            require(self.key in self.guard.inputs, "Complete review prefix pin required")
            raw = self.guard.inputs[self.key]
            _use_typed_current(self.guard, ReviewInput, self.body, raw["inputs"]["request"])
            _use_typed_current(self.guard, GoalCardRunSource, self.goal, raw["goal"])
            require(self.key in self.guard.inputs and self.fields() == self.guard.inputs[self.key],
                "Cold per-use complete review prefix changed")
        except BaseException:
            _invalidate_use_reads(self)
            raise


@dataclass(frozen=True)
class _ColdUseReviewFacts:
    """Full review output, with its complete base audit already consumed."""
    prefix: _ColdUseReviewPrefix
    base_digest: str
    value: Any

    def fields(self):
        checked, material, goal = self.value
        return dict(base_digest=self.base_digest, checked=checked,
            material=material, goal=_use_dump(GoalCardRunSource, goal, self.prefix.guard))

    def check(self, store, c, user):
        try:
            require(type(self.prefix) is _ColdUseReviewPrefix, "Exact complete per-use review provenance required")
            self.prefix.check(store, c, user)
            raw_key = self.prefix.key + ":review"
            require(raw_key in self.prefix.guard.inputs, "Complete review output pin required")
            _use_typed_current(self.prefix.guard, GoalCardRunSource, self.value[2],
                self.prefix.guard.inputs[raw_key]["goal"])
            _use_read_inputs(store, c, self.prefix.guard, self.prefix.key + ":review", self.fields())
        except BaseException:
            _invalidate_use_reads(self)
            raise


@dataclass(frozen=True)
class _ColdUseBoundPrefix:
    """Full accepted per-use pair and instance; review is still explicit."""
    guard: Any
    key: str
    user: Any
    job: Any
    snapshot: Any
    release: Any
    limits: Any
    body: Any
    frozen: Any
    instance: Any
    accepted_instance: Any
    role: str = "per_use"

    def input_fields(self):
        return dict(principal_id=self.user, job=self.job, snapshot=self.snapshot,
            release=self.release, platform_limits=self.limits)

    def fields(self):
        return dict(inputs=self.input_fields(), request=_use_dump(CommitInput, self.body, self.guard), frozen=self.frozen,
            instance=self.instance, accepted_instance=self.accepted_instance, role=self.role)

    def check(self, store, c, user):
        try:
            _use_read_checkpoint(store, c, self.guard)
            require(self.guard is not None and self.user == user, "Exact P-B bound prefix required")
            require(self.key in self.guard.inputs, "Complete bound prefix pin required")
            _use_typed_current(self.guard, CommitInput, self.body, self.guard.inputs[self.key]["request"])
            require(self.key in self.guard.inputs and self.fields() == self.guard.inputs[self.key],
                "Cold per-use complete binding prefix changed")
        except BaseException:
            _invalidate_use_reads(self)
            raise


@dataclass(frozen=True)
class _ColdUseAuditPrefix:
    """Complete scope/base/pair/marker prefix, before the original base audit."""
    guard: Any
    key: str
    user: Any
    draft: Any
    header: Any
    base: Any
    meta: Any
    seal_meta: Any
    snapshot: Any
    body: Any
    frozen: Any
    marker: Any

    def input_fields(self):
        return dict(principal_id=self.user, draft=self.draft)

    def fields(self):
        return dict(inputs=self.input_fields(), header=self.header, base=self.base,
            meta=_use_dump(RunScopeInput, self.meta, self.guard), scope_seal=self.seal_meta, snapshot=self.snapshot,
            request=_use_dump(CommitInput, self.body, self.guard), frozen=self.frozen, logic_marker=self.marker)

    def check(self, store, c, user):
        try:
            _use_read_checkpoint(store, c, self.guard)
            require(self.guard is not None and self.user == user and self.marker is None,
                "Exact plain P-B audit prefix required")
            require(self.key in self.guard.inputs, "Complete audit prefix pin required")
            raw = self.guard.inputs[self.key]
            _use_typed_current(self.guard, RunScopeInput, self.meta, raw["meta"])
            _use_typed_current(self.guard, CommitInput, self.body, raw["request"])
            require(self.key in self.guard.inputs and self.fields() == self.guard.inputs[self.key],
                "Cold per-use complete audit prefix changed")
        except BaseException:
            _invalidate_use_reads(self)
            raise


def _complete_base_digest(value):
    """Shape only: the caller must supply the completed full P-B base audit."""
    require(type(value) is str and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value),
        "A complete P-B base audit digest is required")


def use_hint(c, rid, family=None, *, _graph_read=None):
    try:
        read_store = _graph_read.store if _graph_read is not None else None
        _use_read_checkpoint(read_store, c, _graph_read)
        if family is None:
            return any(use_hint(c, rid, f,
                **({"_graph_read": _graph_read} if _graph_read is not None else {})) for f in FAMILIES)
        hinted = c.execute(_HINT_LEDGER, dict(hint_run_id=rid,
            hint_kinds=[family.meta, family.meta + "_seal"])).first()
        _use_read_checkpoint(read_store, c, _graph_read)
        # Independent scalar identifiers prevent deleting both dedicated seals from
        # downgrading a per-use Run to its saved default target's authorization.
        if not hinted:
            binding = _HINT_BINDINGS.get(family.field)
            if binding is None:
                # Keep the original dynamic lookup for internal callers with a
                # different Family; only the two established families are fixed.
                binding = select(internal_run_bindings.c.snapshot[family.field]["review"]["resource_id"].as_string()).where(
                    internal_run_bindings.c.run_id == bindparam("hint_run_id", type_=internal_run_bindings.c.run_id.type))
            hinted = c.execute(binding, {"hint_run_id": rid}).scalar_one_or_none()
            _use_read_checkpoint(read_store, c, _graph_read)
        if not hinted:
            hinted = c.execute(_HINT_RESPONSE, dict(hint_kind=family.use, hint_run_id=rid)).first()
            _use_read_checkpoint(read_store, c, _graph_read)
        return bool(hinted)
    except BaseException:
        _invalidate_use_reads(_graph_read)
        raise


def _scope_gate(store, c, user, rid, header, *, _graph_read=None, _scope_role="audit"):
    try:
        _use_read_checkpoint(store, c, _graph_read)
        hinted = use_hint(c, rid,
            **({"_graph_read": _graph_read} if _graph_read is not None else {}))
        _use_read_checkpoint(store, c, _graph_read)
        if not hinted:
            return False
        hints = []
        for f in FAMILIES:
            hinted = use_hint(c, rid, f,
                **({"_graph_read": _graph_read} if _graph_read is not None else {}))
            _use_read_checkpoint(store, c, _graph_read)
            if hinted:
                hints.append(f)
        require(len(hints) == 1, "Exact per-use family required")
        family = hints[0]
        if _graph_read is not None:
            require(family is PB, "Cold per-use scope requires the plain P-B family")
        meta, seal = _use_pair(c, user, rid, family.meta, 'accepted', RunScopeInput, _graph_read=_graph_read)
        _use_read_checkpoint(store, c, _graph_read)
        if _graph_read is not None:
            require(_scope_role in ("audit", "job"), "Fixed P-B scope caller required")
            expected_header = {"principal_id", "project_id", "runtime_id"}
            if _scope_role == "job":
                expected_header.add("request_key")
            require(set(header) == expected_header, "Exact P-B scope caller header required")
            key = "pb-use-scope:" + rid + ":" + _scope_role
            _use_read_inputs(store, c, _graph_read, key,
                dict(header=header, meta=_use_dump(RunScopeInput, meta, _graph_read), seal=seal),
                start=key not in _graph_read.inputs)
        require(fingerprint(_use_dump(RunScopeInput, meta, _graph_read)) == fingerprint(seal) and meta.run_id == rid
            and meta.principal_id == user == header["principal_id"]
            and meta.project_id == header["project_id"] and meta.runtime_id == header["runtime_id"])
        from .db import app_drafts
        accepted, accepted_seal = _use_pair(c, user, rid, spec.RUN_META, 'accepted', RunScopeInput, _graph_read=_graph_read)
        if _graph_read is not None:
            _scope_inputs_current(store, c, _graph_read, key, header, meta, seal)
        require(_use_dump(RunScopeInput, accepted, _graph_read) == _use_dump(RunScopeInput, meta, _graph_read) == accepted_seal)
        location = c.execute(select(app_drafts.c.candidate["namespace"].as_string().label("namespace"),
            app_drafts.c.candidate["spec_task"]["kind"].as_string().label("task"),
            app_drafts.c.candidate["spec_binding"]["kind"].as_string().label("binding"),
            app_drafts.c.candidate["goal_application"]["run_id"].as_string().label("generation"))
            .where(app_drafts.c.id == meta.app_id, app_drafts.c.project_id == meta.project_id,
            app_drafts.c.runtime_id == meta.runtime_id)).mappings().first()
        if _graph_read is not None:
            _scope_inputs_current(store, c, _graph_read, key, header, meta, seal)
        require(location is not None and location["namespace"] == natural.VERSION
            and (location["task"] == pb.KIND if family == PB else location["task"] is None
                 and (location["binding"] == spec.KIND or location["generation"] is not None)))
        if family == PA:
            from .db import internal_instance_data, internal_instances
            base = c.execute(select(internal_run_bindings.c.snapshot["pa_base_data_version"].as_integer())
                .where(internal_run_bindings.c.run_id == rid)).scalar_one_or_none()
            live = c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one()
            current = c.execute(select(internal_instances.c.data_version, internal_instances.c.source_app_id,
                internal_instances.c.project_id, internal_instances.c.runtime_id)
                .where(internal_instances.c.id == meta.instance_id, internal_instances.c.principal_id == user)).mappings().first()
            require(type(base) is int and base >= 0 and current is not None
                and current["source_app_id"] == meta.app_id and current["project_id"] == meta.project_id
                and current["runtime_id"] == meta.runtime_id)
            if live not in {"SUCCEEDED", "FAILED", "CANCELLED"} and current["data_version"] != base:
                own = c.execute(select(internal_app_runs.c.status, internal_app_runs.c.result_version)
                    .where(internal_app_runs.c.id == meta.app_run_id, internal_app_runs.c.instance_id == meta.instance_id,
                        internal_app_runs.c.principal_id == user)).mappings().first()
                typed = c.execute(select(internal_instance_data.c.version).where(
                    internal_instance_data.c.instance_id == meta.instance_id,
                    internal_instance_data.c.run_id == meta.app_run_id)).scalars().all()
                require(current["data_version"] == base + 1 and own is not None and own["status"] == "SUCCEEDED"
                    and own["result_version"] == base + 1 and typed == [base + 1], "Confirmed P-A result version competed")

        store.own_project(c, user, meta.project_id)
        if _graph_read is not None:
            _scope_inputs_current(store, c, _graph_read, key, header, meta, seal)
        store.authorize(c, user, meta.runtime_id, meta.project_id, meta.resource_id, natural.READ)
        if _graph_read is not None:
            _scope_inputs_current(store, c, _graph_read, key, header, meta, seal)
        store.authorize(c, user, meta.runtime_id, meta.project_id, meta.project_id, natural.SAVE)
        if _graph_read is not None:
            _scope_inputs_current(store, c, _graph_read, key, header, meta, seal)
        return True
    except BaseException:
        _invalidate_use_reads(_graph_read)
        raise


@controlled
def _scope_gate_default(*args, **kwargs):
    return _scope_gate(*args, **kwargs)


def scope_gate(*args, **kwargs):
    guard = kwargs.get("_graph_read")
    if guard is None:
        return _scope_gate_default(*args, **kwargs)
    try:
        return _scope_gate(*args, **kwargs)
    except BaseException:
        _invalidate_use_reads(guard)
        raise


def protected_instance(c, iid):
    """Independent identifier-only hints, never a material or result body."""
    from .db import app_drafts, internal_instances, internal_releases

    kind = c.execute(select(internal_releases.c.snapshot["draft"]["candidate"]["spec_task"]["kind"].as_string())
        .join(internal_instances, internal_instances.c.release_id == internal_releases.c.id)
        .where(internal_instances.c.id == iid)).scalar_one_or_none()
    app_kind = c.execute(select(app_drafts.c.candidate["spec_task"]["kind"].as_string())
        .join(internal_instances, internal_instances.c.source_app_id == app_drafts.c.id)
        .where(internal_instances.c.id == iid)).scalar_one_or_none()
    ledger = c.execute(select(delivery_graph_requests.c.app_id).where(
        ((delivery_graph_requests.c.app_id == iid) & delivery_graph_requests.c.kind.in_([f.use + suffix for f in FAMILIES for suffix in ("", "_seal")]))
        | (delivery_graph_requests.c.kind.in_([spec.RUN_META, spec.RUN_META + "_seal"])
           & (delivery_graph_requests.c.snapshot["request"]["instance_id"].as_string() == iid)))).first()
    overlay = c.execute(select(internal_run_bindings.c.run_id)
        .join(internal_app_runs, internal_app_runs.c.id == internal_run_bindings.c.app_run_id)
        .where(internal_app_runs.c.instance_id == iid,
            ((internal_run_bindings.c.snapshot["pb_use"]["review"]["resource_id"].as_string().is_not(None))
             | (internal_run_bindings.c.snapshot["pa_use"]["review"]["resource_id"].as_string().is_not(None))))).first()
    release_namespace = c.execute(select(internal_releases.c.snapshot["draft"]["candidate"]["namespace"].as_string())
        .join(internal_instances, internal_instances.c.release_id == internal_releases.c.id)
        .where(internal_instances.c.id == iid)).scalar_one_or_none()
    app_namespace = c.execute(select(app_drafts.c.candidate["namespace"].as_string())
        .join(internal_instances, internal_instances.c.source_app_id == app_drafts.c.id)
        .where(internal_instances.c.id == iid)).scalar_one_or_none()
    return release_namespace == natural.VERSION or app_namespace == natural.VERSION or kind == pb.KIND or app_kind == pb.KIND or bool(ledger or overlay)


@controlled
def data_scope_gate(store, c, user, iid, *, app_run_id=None):
    if not protected_instance(c, iid):
        return False
    if store is None or user is None:
        raise DomainError("PERMISSION_DENIED", "Protected history requires current target authority")
    from .db import internal_instance_data, internal_instances

    i = c.execute(select(internal_instances).where(internal_instances.c.id == iid,
        internal_instances.c.principal_id == user)).mappings().first()
    if i is None:
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c, user, i["project_id"])
    scope = internal_app_runs.c.instance_id == iid
    records_scope = internal_instance_data.c.instance_id == iid
    if app_run_id is not None:
        scope = scope & (internal_app_runs.c.id == app_run_id)
        records_scope = records_scope & (internal_instance_data.c.run_id == app_run_id)
    app_headers = c.execute(select(internal_app_runs.c.id, internal_app_runs.c.instance_id,
        internal_app_runs.c.principal_id, internal_app_runs.c.release_id, internal_app_runs.c.status,
        internal_app_runs.c.result_version).where(scope)).mappings().all()
    require(all(a["principal_id"] == user and a["instance_id"] == iid for a in app_headers))
    covered = {a["id"]: a for a in app_headers}
    record_headers = c.execute(select(internal_instance_data.c.run_id, internal_instance_data.c.release_id,
        internal_instance_data.c.version).where(records_scope)).mappings().all()
    require(all(r["run_id"] in covered and covered[r["run_id"]]["status"] == "SUCCEEDED"
        and covered[r["run_id"]]["release_id"] == r["release_id"]
        and covered[r["run_id"]]["result_version"] == r["version"] for r in record_headers),
        "Typed history is outside the accepted instance scope")
    spec.instance_scope_gate(store, c, user, i, app_run_id=app_run_id)
    return True


@controlled
def control_scope(store, c, user, rid, *, iid=None, lock=False):
    """Owner stop authority uses accepted identifiers, never protected bodies.

    Current resource authority is deliberately required by resume's job gate;
    pause/cancel remain possible after revocation or expiry.
    """
    from .db import events, internal_instances

    hint = c.execute(select(delivery_graph_requests.c.app_id).where(
        delivery_graph_requests.c.app_id == rid,
        delivery_graph_requests.c.kind.in_([spec.RUN_META, spec.RUN_META + "_seal"]))).first()
    association = c.execute(select(internal_run_bindings.c.snapshot["instance_id"].as_string())
        .where(internal_run_bindings.c.run_id == rid)).scalar_one_or_none()
    protected = association is not None and protected_instance(c, association)
    if not hint and not use_hint(c, rid) and not protected:
        return None
    q = select(runs.c.id, runs.c.principal_id, runs.c.project_id, runs.c.runtime_id,
        runs.c.request_key, runs.c.fingerprint, runs.c.status, runs.c.version, runs.c.cancel_intent)
    header = c.execute((q.with_for_update() if lock else q).where(runs.c.id == rid)).mappings().first()
    if header is None or header["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c, user, header["project_id"])
    meta, seal_meta = pair(c, user, rid, spec.RUN_META, "accepted", RunScopeInput)
    require(meta.model_dump() == seal_meta and meta.run_id == rid
        and meta.principal_id == user and meta.project_id == header["project_id"]
        and meta.runtime_id == header["runtime_id"] and header["request_key"] == "internal:" + meta.app_run_id)
    if iid is not None and meta.instance_id != iid:
        raise DomainError("PERMISSION_DENIED")
    if use_hint(c, rid):
        hints = [f for f in FAMILIES if use_hint(c, rid, f)]
        require(len(hints) == 1)
        own, own_seal = pair(c, user, rid, hints[0].meta, "accepted", RunScopeInput)
        require(own.model_dump() == own_seal == meta.model_dump())
    instance = c.execute(select(internal_instances.c.project_id, internal_instances.c.runtime_id,
        internal_instances.c.source_app_id).where(internal_instances.c.id == meta.instance_id,
        internal_instances.c.principal_id == user)).mappings().first()
    require(instance is not None and instance["project_id"] == meta.project_id
        and instance["runtime_id"] == meta.runtime_id and instance["source_app_id"] == meta.app_id)
    fields = ["run_id", "app_run_id", "instance_id", "release_id", "principal_id", "project_id", "runtime_id", "request_fingerprint"]
    binding = c.execute(select(internal_run_bindings.c.fingerprint,
        *(internal_run_bindings.c.snapshot[k].as_string().label(k) for k in fields))
        .where(internal_run_bindings.c.run_id == rid, internal_run_bindings.c.app_run_id == meta.app_run_id)).mappings().first()
    app_run = c.execute(select(internal_app_runs.c.id, internal_app_runs.c.fingerprint,
        internal_app_runs.c.instance_id, internal_app_runs.c.principal_id, internal_app_runs.c.release_id)
        .where(internal_app_runs.c.id == meta.app_run_id)).mappings().first()
    require(binding is not None and app_run is not None and binding["fingerprint"] == header["fingerprint"]
        and all(binding[k] == getattr(meta, k) for k in fields if k != "request_fingerprint")
        and app_run["instance_id"] == meta.instance_id and app_run["principal_id"] == user
        and app_run["release_id"] == meta.release_id and app_run["fingerprint"] == binding["request_fingerprint"])
    accepted = c.execute(select(events.c.data["instance_id"].as_string().label("iid"),
        events.c.data["app_run_id"].as_string().label("aid")).where(events.c.run_id == rid,
        events.c.kind == "ACCEPTED", events.c.data["namespace"].as_string() == "INTERNAL_APPRUN")).mappings().all()
    require(len(accepted) == 1 and accepted[0]["iid"] == meta.instance_id and accepted[0]["aid"] == meta.app_run_id)
    from .project_natural_revalidation import control_binding

    control_binding(store, c, user, header, meta)
    return dict(header), dict(app_run)


def _review_identity_from_facts(instance, release, body, base, saved, family):
    """Pure original predicates; caller retains all preceding scope/IO gates."""
    require(saved_family(base["candidate"]) == family
        and instance["source_app_id"] == base["id"] and instance["runtime_id"] == base["runtime_id"]
        and instance["revision"] == body.expected_revision
        and release["fingerprint"] == body.expected_release_fingerprint
        and base["fingerprint"] == body.expected_app_fingerprint
        and fingerprint(saved["spec_recipe"]) == body.expected_recipe_fingerprint)


def _bound_pair_from_facts(job, snapshot, family, body, frozen, *, _graph_read=None):
    require(_use_dump(CommitInput, body, _graph_read) == snapshot[family.field] and frozen["run_id"] == job["id"]
        and frozen["app_run_id"] == snapshot["app_run_id"])


def _accepted_instance_from_facts(instance, snapshot, release, family):
    accepted_instance = {**dict(instance), "revision": snapshot["expected_revision"],
                         "runtime_id": snapshot["runtime_id"], "source_app_id": release["snapshot"]["draft"]["id"]}
    if family == PA:
        accepted_instance["data_version"] = snapshot["pa_base_data_version"]
    return accepted_instance


def _bound_review_identity_from_facts(snapshot, family, body, frozen, checked, *, _graph_read=None):
    require(body.expected_review_fingerprint == checked["review_fingerprint"]
        and frozen["reviewed"] == checked and frozen["request_fingerprint"] == fingerprint(_use_dump(CommitInput, body, _graph_read))
        and snapshot["pb_effective_fingerprint" if family == PB else "pa_effective_fingerprint"] == checked["effective_fingerprint"])


def _bound_review_from_facts(job, snapshot, release, limits, family, body, frozen, checked, *, _graph_read=None):
    """Pure original predicates; caller retains all preceding scope/IO gates."""
    try:
        _use_own_checkpoint(_graph_read)
        _bound_review_identity_from_facts(snapshot, family, body, frozen, checked, _graph_read=_graph_read)
        draft = {**copy.deepcopy(release["snapshot"]["draft"]), "candidate": checked["effective_candidate"],
            "fingerprint": checked["effective_fingerprint"], family.field + "_run_id": job["id"]}
        manifest, _, report = natural.compile_candidate(draft["candidate"], limits)
        _use_own_checkpoint(_graph_read)
        return draft, manifest, report
    except BaseException:
        _invalidate_use_reads(_graph_read)
        raise


def _audit_from_facts(base_digest, meta, seal_meta, body, frozen, *, _graph_read=None):
    """Digest complete paired facts, after the original current scope/base audit."""
    return fingerprint(dict(base=base_digest, meta=_use_dump(RunScopeInput, meta, _graph_read),
        scope_seal=seal_meta, request=_use_dump(CommitInput, body, _graph_read), frozen=frozen))


def _review_effective_from_target(store, c, user, instance, release, body, limits, base, saved,
        logic_origin, material, goal, *, runtime=None, approved_grants=None, family=PB,
        _graph_read=None, key=""):
    try:
        _use_read_checkpoint(store, c, _graph_read)
        require(material["hash"] == body.expected_source_hash and material["resource_id"] == body.resource_id)
        declared = Limits(**saved["manifest"]["runtime_limits"])
        value = natural.expand(saved["spec_recipe"], base["id"], goal.card_id,
            base["project_id"], material["hash"], material["resource_id"], goal.snapshot["content"],
            declared, base["candidate"]["model_sample_check"]["sample_fingerprint"])
        if _graph_read is not None:
            _review_inputs_current(store, c, _graph_read, key + ":inputs", user,
                instance, release, body, limits, runtime, approved_grants)
        if _graph_read is not None:
            _review_target_current(store, c, _graph_read, key + ":target", material, goal)
        if logic_origin is not None:
            value["logic_revision"] = copy.deepcopy(saved["logic_revision"])
            revision = saved["manifest"]["revision"]
            value["manifest"]["revision"] = revision
            value["actions"][2]["revision"] = revision
            value["manifest"]["action_bindings"][2]["revision"] = revision
        elif family == PB:
            value["manifest"]["origin"] = "task_run"
            value["manifest"]["source_run_ref"] = base["candidate"]["manifest"]["source_run_ref"]
            value["spec_task"] = {**base["candidate"]["spec_task"], "target_goal_fingerprint": goal.fingerprint}
        else:
            spec.verify_origin(store, c, user, base, limits)
            for marker in ("goal_application", "spec_binding"):
                if marker in base["candidate"]:
                    value[marker] = copy.deepcopy(base["candidate"][marker])
        if _graph_read is not None:
            _graph_read.add(key + ":expanded", dict(effective_candidate=value, declared_limits=declared))
        _, _, report = natural.compile_candidate(value, limits)
        if _graph_read is not None:
            _review_inputs_current(store, c, _graph_read, key + ":inputs", user,
                instance, release, body, limits, runtime, approved_grants)
        if _graph_read is not None:
            _review_target_current(store, c, _graph_read, key + ":target", material, goal)
        if _graph_read is not None:
            _use_read_inputs(store, c, _graph_read, key + ":compile",
                dict(effective_candidate=value, declared_limits=declared, report=report), start=True)
        return declared, value, report
    except BaseException:
        _invalidate_use_reads(_graph_read)
        raise


def _review_result_prefix(user, instance, release, body, base, grant_state, family):
    return dict(approved_grant_state=grant_state, namespace=family.namespace, principal_id=user, project_id=instance["project_id"],
        app_id=base["id"], runtime_id=base["runtime_id"], instance_id=instance["id"],
        release_id=release["id"], release_fingerprint=release["fingerprint"],
        saved_app_fingerprint=base["fingerprint"], recipe_fingerprint=body.expected_recipe_fingerprint,
        source_run_id=base["candidate"]["manifest"]["source_run_ref"])


def _review_prefix(store, c, user, instance, release, body, limits, *, runtime=None, approved_grants=None, family=PB, _logic_out=None, _audit_out=None, _graph_read=None):
    key = ""
    if _graph_read is not None:
        _use_read_checkpoint(store, c, _graph_read)
        require(family is PB and type(body) is ReviewInput and type(limits) is Limits,
            "Cold per-use review supports the exact plain P-B family")
        key = "pb-use-review:" + instance["id"] + ":" + fingerprint(_use_dump(ReviewInput, body, _graph_read)) + ":" + fingerprint(limits.model_dump()) + ":" + str(runtime)
        if _graph_read is not None:
            _use_read_inputs(store, c, _graph_read, key + ":inputs",
                _review_inputs(user, instance, release, body, limits, runtime, approved_grants, _graph_read=_graph_read), start=True)
    base = release["snapshot"]["draft"]
    saved = base["candidate"]
    logic_origin = release["snapshot"].get("natural_logic_source")
    if _graph_read is not None:
        require(logic_origin is None, "Cold per-use review requires an unpatched saved P-B app")
    if logic_origin is not None:
        from .natural_logic_patches import release_bound
        if (_logic_out is not None and _logic_out.get("_call_connection") is c
                and _logic_out.get("_call_transaction") is c.get_transaction()
                and c.get_transaction() is not None and _logic_out.get("principal_id") == user
                and _logic_out.get("platform_limits") == limits.model_dump()
                and _logic_out.get("release_id") == release["id"]
                and _logic_out.get("release_fingerprint") == release["fingerprint"]):
            saved = _logic_out["value"]["effective_candidate"]
        else:
            saved = release_bound(store,c,user,release,limits)[0]["candidate"]
    _review_identity_from_facts(instance, release, body, base, saved, family)
    if _graph_read is not None:
        _review_inputs_current(store, c, _graph_read, key + ":inputs", user,
            instance, release, body, limits, runtime, approved_grants)
    material, goal = spec.target(store, c, user, instance["project_id"], body.card_id,
        body.expected_goal_version, body.expected_goal_fingerprint, runtime, family=natural.VERSION,
        **({"_graph_read": _graph_read} if _graph_read is not None else {}))
    if _graph_read is not None:
        _review_inputs_current(store, c, _graph_read, key + ":inputs", user,
            instance, release, body, limits, runtime, approved_grants)
    if _graph_read is not None:
        _use_read_inputs(store, c, _graph_read, key + ":target",
            dict(material=material, goal=_use_dump(GoalCardRunSource, goal, _graph_read)), start=True)
    declared, value, report = _review_effective_from_target(store, c, user, instance, release,
        body, limits, base, saved, logic_origin, material, goal, runtime=runtime,
        approved_grants=approved_grants, family=family, _graph_read=_graph_read, key=key)
    grant_state = approved_grants
    if grant_state is None:
        grant_rows = c.execute(select(grants).where(
            grants.c.principal_id == instance["runtime_id"],
            grants.c.project_id == instance["project_id"],
            grants.c.resource_id == material["resource_id"], grants.c.tool_ref == natural.READ)
            .order_by(grants.c.id)).mappings()
        if _graph_read is not None:
            _review_inputs_current(store, c, _graph_read, key + ":inputs", user,
                instance, release, body, limits, runtime, approved_grants)
        grant_state = [{**dict(row), "effective": not row["revoked"] and row["expires_at"] > time.time()} for row in grant_rows]
    result = _review_result_prefix(user, instance, release, body, base, grant_state, family)
    if _graph_read is not None:
        _review_inputs_current(store, c, _graph_read, key + ":inputs", user,
            instance, release, body, limits, runtime, approved_grants)
    if _graph_read is not None:
        _review_target_current(store, c, _graph_read, key + ":target", material, goal)
    if _graph_read is not None:
        _use_read_inputs(store, c, _graph_read, key + ":compile",
            dict(effective_candidate=value, declared_limits=declared, report=report))
    prefix = _ColdUseReviewPrefix(_graph_read, key, user, instance, release, body, limits,
        runtime, approved_grants, family, base, saved, logic_origin, material, goal,
        declared, value, report, result)
    if _graph_read is not None:
        _use_read_inputs(store, c, _graph_read, key, prefix.fields(), start=True)
    return prefix


def _review_from_audit(prefix, base_digest, *, store=None, c=None):
    user, instance, body = prefix.user, prefix.instance, prefix.body
    family, base, saved, logic_origin = prefix.family, prefix.base, prefix.saved, prefix.logic_origin
    material, goal, declared, value, report = prefix.material, prefix.goal, prefix.declared, prefix.value, prefix.report
    if prefix.guard is not None:
        prefix.check(store, c, user)
    result = dict(**prefix.result, source_audit_fingerprint=base_digest,
        request=_use_dump(ReviewInput, body, prefix.guard), target_goal=_use_dump(GoalCardRunSource, goal, prefix.guard),
        variable_bindings=dict(resource_id=material["resource_id"], source_hash=material["hash"],
            format=material["format"], goal_id=goal.card_id, goal_version=goal.version),
        effective_candidate=value, effective_fingerprint=fingerprint(value), report=report,
        required_permissions=[dict(tool_ref=natural.READ, resource_ref=material["resource_id"]),
            dict(tool_ref=natural.SAVE, resource_ref=instance["project_id"])],
    )
    preview = natural.preview(material, value, {})
    if prefix.guard is not None:
        prefix.check(store, c, user)
    result.update(preview=preview, consent=family.consent,
        new_model_requests=0, artifact_writes=0, semantic_status="UNKNOWN", owner_acceptance="PENDING",
        formal_publication_enabled=False)
    if logic_origin is not None:
        result["source_audit_fingerprint"] = fingerprint(dict(original=result["source_audit_fingerprint"],
            logic_origin=logic_origin,effective_fingerprint=fingerprint(saved)))
        result["saved_logic_source"] = dict(origin=copy.deepcopy(logic_origin),
            effective_fingerprint=fingerprint(saved),recipe_fingerprint=fingerprint(saved["spec_recipe"]))
    if family == PA:
        result.update(instance_data_version=instance["data_version"],
            saved_origin={k: copy.deepcopy(base["candidate"][k]) for k in ("goal_application", "spec_binding") if k in base["candidate"]},
            proposed_limits=declared.model_dump(), proposed_model_nodes=declared.max_requests,
            proposed_artifact_writes_at_most=1, real_model_allowance=0)
    return {**result, "review_fingerprint": fingerprint(result)}, material, goal


def _cold_review_prefix(store, c, user, instance, release, body, limits, guard, *, runtime=None, approved_grants=None):
    from .natural_spec_runtime import _ColdGraphRead

    try:
        require(type(guard) is _ColdGraphRead, "Cold per-use review requires its exact local read scope")
        return _review_prefix(store, c, user, instance, release, body, limits,
            runtime=runtime, approved_grants=approved_grants, family=PB, _graph_read=guard)
    except BaseException:
        _invalidate_use_reads(guard)
        raise


def _cold_review_from_audit(store, c, user, prefix, base_digest):
    try:
        require(type(prefix) is _ColdUseReviewPrefix,
            "Exact Cold per-use review prefix required")
        prefix.check(store, c, user)
        _complete_base_digest(base_digest)
        prefix.guard.add(prefix.key + ":base-audit", dict(base=prefix.base, digest=base_digest))
        value = _review_from_audit(prefix, base_digest, store=store, c=c)
        prefix.check(store, c, user)
        facts = _ColdUseReviewFacts(prefix, base_digest, value)
        prefix.guard.add(prefix.key + ":review", facts.fields())
        return facts
    except BaseException:
        _invalidate_use_reads(prefix)
        raise


@controlled
def review(store, c, user, instance, release, body, limits, *, runtime=None, approved_grants=None, family=PB, _logic_out=None, _audit_out=None):
    prefix = _review_prefix(store, c, user, instance, release, body, limits,
        runtime=runtime, approved_grants=approved_grants, family=family, _logic_out=_logic_out, _audit_out=_audit_out)
    base_digest = base_audit(store, c, user, prefix.base, family,
        **({"_audit_out": _audit_out} if _audit_out is not None else {}))
    return _review_from_audit(prefix, base_digest)


@controlled
def approve(store, c, user, instance, release, body, limits, *, family=PB):
    checked, material, goal = review(store, c, user, instance, release, body.review, limits, family=family)
    require(checked["review_fingerprint"] == body.expected_review_fingerprint)
    existing = c.execute(select(delivery_graph_requests.c.request_key).where(
        delivery_graph_requests.c.app_id == instance["id"], delivery_graph_requests.c.principal_id == user,
        delivery_graph_requests.c.kind == family.use)).all()
    if len(existing) >= MAX:
        raise DomainError("BUDGET_EXHAUSTED", "Finite per-instance use capacity exhausted")
    if c.execute(select(grants.c.id).where(grants.c.principal_id == instance["runtime_id"],
        grants.c.project_id == instance["project_id"], grants.c.resource_id == material["resource_id"],
        grants.c.tool_ref == natural.READ, grants.c.revoked.is_(False), grants.c.expires_at > time.time())).first() is None:
        c.execute(insert(grants).values(id=new_id("grant"), principal_id=instance["runtime_id"],
            project_id=instance["project_id"], resource_id=material["resource_id"], tool_ref=natural.READ,
            expires_at=time.time() + 86400, revision=1, revoked=False))
    checked_again, _, _ = review(store, c, user, instance, release, body.review, limits,
                                runtime=instance["runtime_id"], approved_grants=checked["approved_grant_state"], family=family)
    require(checked_again == checked)
    return checked, material, goal


def seal(c, user, base, snapshot, body, checked, *, family=PB):
    frozen = dict(run_id=snapshot["run_id"], app_run_id=snapshot["app_run_id"], reviewed=checked,
        request_fingerprint=fingerprint(body.model_dump()), review_fingerprint=checked["review_fingerprint"])
    remember(c, user, snapshot["instance_id"], family.use, body.review.request_key, body, frozen)
    meta = RunScopeInput(app_id=base["id"], principal_id=user, project_id=base["project_id"],
        runtime_id=base["runtime_id"], resource_id=checked["variable_bindings"]["resource_id"],
        run_id=snapshot["run_id"], instance_id=snapshot["instance_id"],
        app_run_id=snapshot["app_run_id"], release_id=snapshot["release_id"])
    remember(c, user, snapshot["run_id"], family.meta, "accepted", meta, meta.model_dump())


def _bound_prefix(store, c, user, job, snapshot, release, limits, *, family=PB, _logic_out=None, _read_out=None, _graph_read=None):
    from .db import internal_instances
    key = ""
    if _graph_read is not None:
        _use_read_checkpoint(store, c, _graph_read)
        require(family is PB and type(limits) is Limits
            and "natural_logic_source" not in release["snapshot"],
            "Cold per-use binding supports the exact plain P-B family")
        key = "pb-use-bound:" + job["id"] + ":" + fingerprint(limits.model_dump())
        if _graph_read is not None:
            _use_read_inputs(store, c, _graph_read, key + ":inputs",
                dict(principal_id=user, job=job, snapshot=snapshot, release=release, platform_limits=limits), start=True)
    body, frozen = _use_pair(c, user, snapshot['instance_id'], family.use, snapshot[family.field]['review']['request_key'], family.body_type, _graph_read=_graph_read)
    _use_read_checkpoint(store, c, _graph_read)
    if _graph_read is not None:
        _use_read_inputs(store, c, _graph_read, key + ":pair",
            dict(request=_use_dump(CommitInput, body, _graph_read), frozen=frozen), start=True)
    _bound_pair_from_facts(job, snapshot, family, body, frozen, _graph_read=_graph_read)
    instance = c.execute(select(internal_instances).where(internal_instances.c.id == snapshot["instance_id"],
        internal_instances.c.principal_id == user, internal_instances.c.project_id == job["project_id"])).mappings().one()
    _use_read_checkpoint(store, c, _graph_read)
    if _graph_read is not None:
        _use_typed_current(_graph_read, CommitInput, body, _graph_read.inputs[key + ":pair"]["request"])
    # Historic results retain their accepted revision; the existing commit guard
    # separately requires the live revision for any new side effect.
    accepted_instance = _accepted_instance_from_facts(instance, snapshot, release, family)
    prefix = _ColdUseBoundPrefix(_graph_read, key, user, job, snapshot, release, limits,
        body, frozen, instance, accepted_instance)
    if _graph_read is not None:
        if _graph_read is not None:
            _use_read_inputs(store, c, _graph_read, key + ":inputs", prefix.input_fields())
        if _graph_read is not None:
            _use_read_inputs(store, c, _graph_read, key + ":pair", dict(request=_use_dump(CommitInput, body, _graph_read), frozen=frozen))
        if _graph_read is not None:
            _use_read_inputs(store, c, _graph_read, key, prefix.fields(), start=True)
    return prefix


def _cold_bound_prefix(store, c, user, job, snapshot, release, limits, guard):
    from .natural_spec_runtime import _ColdGraphRead

    try:
        require(type(guard) is _ColdGraphRead, "Cold per-use binding requires its exact local read scope")
        return _bound_prefix(store, c, user, job, snapshot, release, limits, family=PB, _graph_read=guard)
    except BaseException:
        _invalidate_use_reads(guard)
        raise


def _cold_review_for_bound(store, c, user, prefix, review_facts):
    try:
        require(type(prefix) is _ColdUseBoundPrefix and type(review_facts) is _ColdUseReviewFacts,
            "Exact Cold per-use bound and complete review facts required")
        prefix.check(store, c, user)
        review_facts.check(store, c, user)
        reviewed = review_facts.prefix
        require(reviewed.guard is prefix.guard and reviewed.limits is prefix.limits
            and reviewed.role == prefix.role
            and reviewed.instance == prefix.accepted_instance and reviewed.release is prefix.release
            and reviewed.body is prefix.body.review and reviewed.runtime == prefix.job["runtime_id"]
            and reviewed.approved_grants == prefix.frozen["reviewed"]["approved_grant_state"],
            "Per-use review does not match the accepted binding and full Limits")
    except BaseException:
        _invalidate_use_reads(prefix, review_facts)
        raise


def _cold_bound_from_review(store, c, user, prefix, review_facts):
    try:
        require(type(prefix) is _ColdUseBoundPrefix,
            "Exact Cold per-use bound prefix required")
        _cold_review_for_bound(store, c, user, prefix, review_facts)
        checked, material, goal = review_facts.value
        result = _bound_review_from_facts(prefix.job, prefix.snapshot, prefix.release,
            prefix.limits, PB, prefix.body, prefix.frozen, checked, _graph_read=prefix.guard)
        prefix.check(store, c, user)
        review_facts.check(store, c, user)
        draft, manifest, report = result
        bound = draft, manifest, report, material, _use_dump(GoalCardRunSource, goal, prefix.guard)
        prefix.guard.add(prefix.key + ":bound", dict(draft=draft, manifest=manifest.model_dump(),
            report=report, material=material, goal=bound[4]))
        return bound
    except BaseException:
        _invalidate_use_reads(prefix, review_facts)
        raise


def _cold_facet_inputs(store, c, user, prefix, review_facts, limits, role):
    """Full same-epoch raw inputs; never refresh or infer an authority here."""
    from .natural_spec_runtime import _ColdGraphRead

    try:
        require(type(prefix) is _ColdUseBoundPrefix and type(review_facts) is _ColdUseReviewFacts
            and type(limits) is Limits and type(role) is str,
            "Exact per-use facts, role and complete Limits required")
        _cold_review_for_bound(store, c, user, prefix, review_facts)
        guard = prefix.guard
        require(type(guard) is _ColdGraphRead and role in {"source", "generate", "platform", "trial", "per_use"}
            and guard.role_limits[role] is limits,
            "Per-use facet must use its exact pinned role Limits")
        _bound_pair_from_facts(prefix.job, prefix.snapshot, PB, prefix.body, prefix.frozen, _graph_read=guard)
        accepted = _accepted_instance_from_facts(prefix.instance, prefix.snapshot, prefix.release, PB)
        require(accepted == prefix.accepted_instance,
            "Per-use facet accepted instance identity changed")
        _bound_review_identity_from_facts(prefix.snapshot, PB, prefix.body, prefix.frozen, review_facts.value[0], _graph_read=guard)
        prefix.check(store, c, user)
        review_facts.check(store, c, user)
        return guard
    except BaseException:
        _invalidate_use_reads(prefix, review_facts)
        raise


def _cold_review_facet_from_review(store, c, user, prefix, review_facts, limits, *, role):
    """Re-expand/recompile a full new Limits facet from complete original raw facts."""
    try:
        guard = _cold_facet_inputs(store, c, user, prefix, review_facts, limits, role)
        old = review_facts.prefix
        instance, release, body = prefix.accepted_instance, prefix.release, prefix.body.review
        base, saved = old.base, old.saved
        material, goal, approved_grants = old.material, old.goal, old.approved_grants
        runtime = prefix.job["runtime_id"]
        key = "pb-use-review-facet:" + prefix.job["id"] + ":" + role + ":" + fingerprint(limits.model_dump())
        guard.add(key + ":inputs", _review_inputs(user, instance, release, body, limits, runtime, approved_grants, _graph_read=guard))
        guard.add(key + ":provenance", dict(bound=prefix.fields(), review=review_facts.fields(),
            old_role=prefix.role, role=role, limits=limits))
        _review_identity_from_facts(instance, release, body, base, saved, PB)
        _review_inputs_current(store, c, guard, key + ":inputs", user,
            instance, release, body, limits, runtime, approved_grants)
        guard.add(key + ":target", dict(material=material, goal=_use_dump(GoalCardRunSource, goal, guard)))
        declared, value, report = _review_effective_from_target(store, c, user, instance, release,
            body, limits, base, saved, None, material, goal, runtime=runtime,
            approved_grants=approved_grants, family=PB, _graph_read=guard, key=key)
        review_facts.check(store, c, user)
        result = _review_result_prefix(user, instance, release, body, base,
            old.result["approved_grant_state"], PB)
        current = _ColdUseReviewPrefix(guard, key, user, instance, release, body, limits,
            runtime, approved_grants, PB, base, saved, None, material, goal,
            declared, value, report, result, role=role)
        guard.add(key, current.fields())
        complete = _cold_review_from_audit(store, c, user, current, review_facts.base_digest)
        prefix.check(store, c, user)
        review_facts.check(store, c, user)
        complete.check(store, c, user)
        return complete
    except BaseException:
        _invalidate_use_reads(prefix, review_facts)
        raise


def _cold_bound_facet(store, c, user, prefix, review_facts, facet_review, *, role):
    """Consume the explicit new review and original full paired/instance raw facts."""
    try:
        require(type(prefix) is _ColdUseBoundPrefix and type(review_facts) is _ColdUseReviewFacts
            and type(facet_review) is _ColdUseReviewFacts,
            "Exact original per-use facts and a complete new review facet are required")
        facet_review.check(store, c, user)
        newer = facet_review.prefix
        guard = _cold_facet_inputs(store, c, user, prefix, review_facts, newer.limits, role)
        old = review_facts.prefix
        require(newer.guard is guard and newer.role == role and newer.user == user
            and newer.release is prefix.release and newer.body is prefix.body.review
            and newer.instance == prefix.accepted_instance and newer.runtime == prefix.job["runtime_id"]
            and newer.material is old.material and newer.goal is old.goal
            and newer.approved_grants is old.approved_grants and newer.base is old.base
            and newer.saved is old.saved and facet_review.base_digest == review_facts.base_digest,
            "New per-use facet changed its complete raw provenance or role")
        key = "pb-use-bound-facet:" + prefix.job["id"] + ":" + role + ":" + fingerprint(newer.limits.model_dump())
        guard.add(key + ":inputs", dict(principal_id=user, job=prefix.job,
            snapshot=prefix.snapshot, release=prefix.release, platform_limits=newer.limits))
        _bound_pair_from_facts(prefix.job, prefix.snapshot, PB, prefix.body, prefix.frozen, _graph_read=guard)
        accepted = _accepted_instance_from_facts(prefix.instance, prefix.snapshot, prefix.release, PB)
        current = _ColdUseBoundPrefix(guard, key, user, prefix.job, prefix.snapshot, prefix.release,
            newer.limits, prefix.body, prefix.frozen, prefix.instance, accepted, role=role)
        guard.add(key + ":pair", dict(request=_use_dump(CommitInput, current.body, guard), frozen=current.frozen))
        guard.add(key, current.fields())
        value = _cold_bound_from_review(store, c, user, current, facet_review)
        prefix.check(store, c, user)
        review_facts.check(store, c, user)
        facet_review.check(store, c, user)
        return current, value
    except BaseException:
        _invalidate_use_reads(prefix, review_facts, facet_review)
        raise


@controlled
def bound(store, c, user, job, snapshot, release, limits, *, family=PB, _logic_out=None, _read_out=None):
    prefix = _bound_prefix(store, c, user, job, snapshot, release, limits,
        family=family, _logic_out=_logic_out, _read_out=_read_out)
    body, frozen, accepted_instance = prefix.body, prefix.frozen, prefix.accepted_instance
    audit_out: dict[str, Any] = {}
    checked, material, goal = review(store, c, user, accepted_instance, release, body.review, limits, runtime=job["runtime_id"], approved_grants=frozen["reviewed"]["approved_grant_state"], family=family,_logic_out=_logic_out,
        **({"_audit_out": audit_out} if _read_out is not None and family == PB else {}))
    draft, manifest, report = _bound_review_from_facts(job, snapshot, release, limits, family, body, frozen, checked)
    if (_read_out is not None and family == PB and "natural_logic_source" not in release["snapshot"]
            and audit_out.get("digest") == checked["source_audit_fingerprint"]
            and pb._source_reads_current(store, c, c.info.get("pb_source_reads"))):
        _read_out.update(principal_id=user, job_fingerprint=fingerprint(dict(job)),
            snapshot_fingerprint=fingerprint(snapshot), release_id=release["id"],
            release_fingerprint=release["fingerprint"], base=copy.deepcopy(release["snapshot"]["draft"]),
            platform_limits=limits.model_dump(), limits_ref=limits,
            token=c.info["pb_source_reads"], base_audit=checked["source_audit_fingerprint"],
            audit_base=audit_out.get("base"))
    return draft, manifest, report, material, goal.model_dump()


def _audit_prefix(store, c, user, draft, *, family=PB, _logic_out=None, _release=None, _use_proof=None, _graph_read=None):
    key = ""
    if _graph_read is not None:
        _use_read_checkpoint(store, c, _graph_read)
        require(family is PB, "Cold per-use audit supports only the exact plain P-B family")
        key = "pb-use-audit:" + draft["pb_use_run_id"] + ":" + fingerprint(draft)
        if _graph_read is not None:
            _use_read_inputs(store, c, _graph_read, key + ":inputs",
                dict(principal_id=user, draft=draft), start=True)
    rid = draft[family.field + "_run_id"]
    header = c.execute(select(runs.c.principal_id, runs.c.project_id, runs.c.runtime_id).where(runs.c.id == rid)).mappings().one()
    _use_read_checkpoint(store, c, _graph_read)
    scoped = scope_gate(store, c, user, rid, header,
        **({"_graph_read": _graph_read} if _graph_read is not None else {}))
    _use_read_checkpoint(store, c, _graph_read)
    require(scoped)
    from .db import app_drafts, internal_releases
    base = c.execute(select(app_drafts).where(app_drafts.c.id == draft["id"],
        app_drafts.c.project_id == draft["project_id"])).mappings().one()
    _use_read_checkpoint(store, c, _graph_read)
    if _graph_read is not None:
        require(type(_USE_OWNED_ENABLED) is bool
            and _USE_OWNED_ENABLED is _use_fact_code._SOURCE_OK
            and type(_USE_OWNED_CHECK) is tuple and len(_USE_OWNED_CHECK)==3,
            'Exact Use audit ownership configuration required')
    if _graph_read is not None and _USE_OWNED_ENABLED:
        check,code,defaults=_USE_OWNED_CHECK
        if (type(check) is not _UseFunctionType or _use_fact_code.current is not check or check.__code__ is not code
                or check.__defaults__ is not defaults):
            raise DomainError('VERSION_CONFLICT','Use audit ownership qualifier changed')
        check()
        # This independent complete SQL row has not escaped into :paired or
        # a prefix. Keep its full hidden RowMapping storage and alias domain;
        # later audit readers consume this same immutable value.
        try:
            base=_use_fact_code.own_fact(_graph_read,key+':base-row',base)
        except (_use_fact_code.image.Bounds,_use_fact_code.image.Unsupported):
            # Only bounded representation/capacity refusal before publication
            # can retain the original independently read row. Never replay SQL
            # or catch native match, authority, callback or postpublish errors.
            fields=vars(_graph_read)
            inputs=fields.get('inputs')
            registry=fields.get('_source_fact_bindings',{})
            if (fields.get('active') is not True or type(inputs) is not dict
                    or type(registry) is not dict
                    or not all(type(k) is str for k in inputs)
                    or not all(type(k) is str for k in registry)
                    or key+':base-row' in inputs or key+':base-row' in registry):
                raise  # Late/native/callback errors keep their exact identity.
            check()
            _use_read_checkpoint(store,c,_graph_read)
    meta, seal_meta = _use_pair(c, user, rid, family.meta, 'accepted', RunScopeInput, _graph_read=_graph_read)
    _use_read_checkpoint(store, c, _graph_read)
    snapshot = c.execute(select(internal_run_bindings.c.snapshot).where(internal_run_bindings.c.run_id == rid)).scalar_one()
    _use_read_checkpoint(store, c, _graph_read)
    body, frozen = _use_pair(c, user, meta.instance_id, family.use, snapshot[family.field]['review']['request_key'], family.body_type, _graph_read=_graph_read)
    _use_read_checkpoint(store, c, _graph_read)
    if _graph_read is not None:
        _use_read_inputs(store, c, _graph_read, key + ":paired",
            dict(header=header, base=base, meta=_use_dump(RunScopeInput, meta, _graph_read), scope_seal=seal_meta,
                snapshot=snapshot, request=_use_dump(CommitInput, body, _graph_read), frozen=frozen), start=True)
    # A reverse R2 recipe can equal R0 while its independently checked version
    # provenance remains mandatory. Discover the owned Release marker, never
    # infer proof presence from recipe inequality. The branch below validates
    # that exact Release and complete source/check chain afresh.
    marker = c.execute(select(internal_releases.c.snapshot["natural_logic_source"]["namespace"].as_string())
        .where(internal_releases.c.id == meta.release_id, internal_releases.c.principal_id == user)).scalar_one()
    _use_read_checkpoint(store, c, _graph_read)
    if _graph_read is not None:
        _use_read_inputs(store, c, _graph_read, key + ":paired",
            dict(header=header, base=base, meta=_use_dump(RunScopeInput, meta, _graph_read), scope_seal=seal_meta,
                snapshot=snapshot, request=_use_dump(CommitInput, body, _graph_read), frozen=frozen))
    if _graph_read is not None:
        paired_raw = _graph_read.inputs[key + ":paired"]
        _use_typed_current(_graph_read, RunScopeInput, meta, paired_raw["meta"])
        _use_typed_current(_graph_read, CommitInput, body, paired_raw["request"])
    require(("saved_logic_source" in frozen["reviewed"]) == (marker is not None),
        "Logic version requires its independent source proof")
    if _graph_read is not None:
        require(marker is None, "Cold per-use audit requires an unpatched saved P-B app")
    if marker is None:
        require(body.review.expected_recipe_fingerprint == fingerprint(base["candidate"]["spec_recipe"]))
    if "saved_logic_source" in frozen["reviewed"]:
        from .lifecycle import read_release
        current: dict[str, Any] = {}
        # Entry binding has just validated this exact Release in the same read-only
        # call. Commit guards omit these private values and validate it afresh.
        if (_logic_out is not None and _release is not None
                and _logic_out.get("_call_connection") is c
                and _logic_out.get("_call_transaction") is c.get_transaction()
                and c.get_transaction() is not None and _logic_out.get("principal_id") == user
                and _logic_out.get("platform_limits") == Limits(**snapshot["limits"]).model_dump()
                and _logic_out.get("release_id") == meta.release_id == _release["id"]
                and _logic_out.get("release_fingerprint") == _release["fingerprint"]
                and fingerprint(_release["snapshot"]) == _release["fingerprint"]):
            release, current = _release, _logic_out
        else:
            release = read_release(store,c,user,meta.release_id,Limits(**snapshot["limits"]),_logic_out=current)
        require(release["fingerprint"] == frozen["reviewed"]["release_fingerprint"]
            == snapshot["expected_release_fp"])
        saved = current["value"]["effective_candidate"]
        require(frozen["reviewed"]["saved_logic_source"] == dict(
            origin=release["snapshot"]["natural_logic_source"],effective_fingerprint=fingerprint(saved),
            recipe_fingerprint=fingerprint(saved["spec_recipe"])), "Current logic source proof changed")
    prefix = _ColdUseAuditPrefix(_graph_read, key, user, draft, header, base, meta,
        seal_meta, snapshot, body, frozen, marker)
    if _graph_read is not None:
        if _graph_read is not None:
            _use_read_inputs(store, c, _graph_read, key + ":inputs", prefix.input_fields())
        if _graph_read is not None:
            _use_read_inputs(store, c, _graph_read, key + ":paired",
                dict(header=header, base=base, meta=_use_dump(RunScopeInput, meta, _graph_read), scope_seal=seal_meta,
                    snapshot=snapshot, request=_use_dump(CommitInput, body, _graph_read), frozen=frozen))
        if _graph_read is not None:
            _use_read_inputs(store, c, _graph_read, key, prefix.fields(), start=True)
    return prefix


def _cold_audit_prefix(store, c, user, draft, guard):
    from .natural_spec_runtime import _ColdGraphRead

    try:
        require(type(guard) is _ColdGraphRead, "Cold per-use audit requires its exact local read scope")
        return _audit_prefix(store, c, user, draft, family=PB, _graph_read=guard)
    except BaseException:
        _invalidate_use_reads(guard)
        raise


def _cold_audit_from_base(store, c, user, prefix, base_digest):
    try:
        require(type(prefix) is _ColdUseAuditPrefix,
            "Exact Cold per-use audit prefix required")
        prefix.check(store, c, user)
        _complete_base_digest(base_digest)
        prefix.guard.add(prefix.key + ":base-audit", dict(base=prefix.base, digest=base_digest))
        value = _audit_from_facts(base_digest, prefix.meta, prefix.seal_meta, prefix.body, prefix.frozen, _graph_read=prefix.guard)
        prefix.check(store, c, user)
        prefix.guard.add(prefix.key + ":audit", dict(digest=value))
        return value
    except BaseException:
        _invalidate_use_reads(prefix)
        raise


@controlled
def audit(store, c, user, draft, *, family=PB, _logic_out=None, _release=None, _use_proof=None):
    prefix = _audit_prefix(store, c, user, draft, family=family,
        _logic_out=_logic_out, _release=_release, _use_proof=_use_proof)
    base, meta, seal_meta, snapshot, body, frozen = (prefix.base, prefix.meta,
        prefix.seal_meta, prefix.snapshot, prefix.body, prefix.frozen)
    base_digest = None
    def same_read():
        return (_use_proof is not None and family == PB
            and _use_proof.get("principal_id") == user and _use_proof.get("audit_base") == dict(base)
            and _use_proof.get("bound_fingerprint") == _bound_fingerprint(_use_proof["bound"])
            and _use_proof["bound"][0] == draft
            and _use_proof.get("release_id") == meta.release_id
            and _use_proof.get("release_fingerprint") == snapshot["expected_release_fp"]
            and _use_proof.get("snapshot_fingerprint") == fingerprint(snapshot)
            and _use_proof["limits_ref"].model_dump() == _use_proof["platform_limits"]
            and _use_proof.get("base_audit") == frozen["reviewed"]["source_audit_fingerprint"]
            and pb._source_reads_current(store, c, _use_proof.get("token")))
    if same_read():
        # This bound call already completed the exact base audit in its first
        # per-use review. Keep the live per-use scope and paired reads above.
        store.recheck_proof_authorities(c, _use_proof)
        if same_read():
            base_digest = _use_proof["base_audit"]
    if base_digest is None:
        base_digest = base_audit(store, c, user, base, family)
    return _audit_from_facts(base_digest, meta, seal_meta, body, frozen)


def mount(app, store, limits, identity, *, family=PB):
    user_dep = Depends(identity)

    @app.post("/api/internal/instances/{iid}/" + family.route + "-reviews")
    def preview(iid: str, body: ReviewInput, user=user_dep):
        from .lifecycle import instance
        with store.tx() as c:
            i, release = instance(store, c, user, iid, limits)
            checked, _, _ = review(store, c, user, i, release, body, limits, family=family)
            return checked

    def run(iid: str, body: CommitInput | PACommitInput, user=user_dep):
        from .app_jobs import enqueue
        return enqueue(store, user, iid, body.review.expected_revision,
            body.review.expected_release_fingerprint, {}, body.review.request_key, limits, **{family.field: body},
            submission=dict(endpoint=family.route + "-runs", body=body.model_dump(exclude_unset=True)))

    # FastAPI receives the exact immutable family schema; the implementation has
    # an explicit static union rather than a variable used as a type annotation.
    run.__annotations__["body"] = family.body_type
    app.post("/api/internal/instances/{iid}/" + family.route + "-runs", status_code=202)(run)

    @app.get("/api/internal/instances/{iid}/" + family.route + "-requests/{key}")
    @controlled
    def recover(iid: str, key: str, user=user_dep):
        from .lifecycle import instance
        with store.tx() as c:
            i, release = instance(store, c, user, iid, limits)
            # Only the Run identifier is inspected before target authorization.
            rid = c.execute(select(delivery_graph_requests.c.snapshot["response"]["run_id"].as_string()).where(
                delivery_graph_requests.c.app_id == iid, delivery_graph_requests.c.principal_id == user,
                delivery_graph_requests.c.kind == family.use, delivery_graph_requests.c.request_key == key)).scalar_one_or_none()
            if rid is None:
                raise DomainError("OUTCOME_UNKNOWN", "No accepted use for this original key")
            require(spec.job_scope_gate(store, c, user, rid))
            body, frozen = pair(c, user, iid, family.use, key, family.body_type)
            require(frozen["run_id"] == rid)
            job = c.execute(select(runs).where(runs.c.id == rid, runs.c.principal_id == user,
                runs.c.project_id == i["project_id"])).mappings().one()
            binding, _, _ = spec.verify_job(store, c, user, job, limits)
            return dict(namespace=family.namespace, request=body.model_dump(), request_key=key,
                **frozen, principal_id=user, project_id=i["project_id"], app_id=i["source_app_id"],
                instance_id=iid, release_id=binding["release"]["id"], status=job["status"],
                effective_fingerprint=binding["draft"]["fingerprint"], new_model_requests=0,
                semantic_status="UNKNOWN", owner_acceptance="PENDING", formal_publication_enabled=False)


# Register only the fixed private graph path and its actual public forwarding
# leaves. Public no-Graph review/bound/audit retain their original protocol.
from types import FunctionType as _UseFunctionType
from . import _cold_source_packet as _use_fact_code
from . import delivery_graph_apps as _use_pair_code
_USE_OWNED_CHECK=_use_fact_code.CHECK
_USE_OWNED_ENABLED=_use_fact_code._SOURCE_OK
_use_fact_code.register(8,globals(),tuple(name for name,value in tuple(globals().items())
    if type(value) is _UseFunctionType and value.__module__==__name__
    and (name.startswith('_') or name in ('scope_gate','use_hint','saved_family')))+('fingerprint','require'),
    (_ColdUseReviewPrefix,_ColdUseReviewFacts,_ColdUseBoundPrefix,_ColdUseAuditPrefix,Family),
    constants=('PB','PA','FAMILIES','_USE_FAMILY_STATES','Family','CommitInput','ReviewInput','RunScopeInput',
        'GoalCardRunSource','Limits','natural','pb','spec','copy','_use_fact_code','_use_pair_code',
        '_USE_OWNED_CHECK','_USE_OWNED_ENABLED'),
    helpers=((vars(_use_pair_code),('lookup','checked')),))
