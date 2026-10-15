"""Typed synthetic archives only: no real LIVE origin, network or credentials."""

import copy
import hashlib
import json
import time
from dataclasses import replace

import pytest

from sim2act.db import fingerprint
from sim2act.errors import DomainError
from sim2act.natural_live_admission import (
    CONSENT,
    ApproveInput,
    MaterialGoal,
    PBTrialContract,
    StageKeys,
)
from sim2act.pb_live_source_contract import (
    LivePBSourceContract,
    ResponseEvidence,
    SourceEvidence,
    SourceSlotEvidence,
    SyntheticSourceResolver,
    UsageEvidence,
    extraction_fingerprint,
    resolve_source,
)


def recipe(style="ordered"):
    # Pure finite Recipe fixture: no importing executor fixtures or archived gold.
    source = {k: dict(source="step", ref="read", field=k)
        for k in ("resource_id", "content", "hash", "format")}
    return dict(version="natural-spec-recipe.v1", steps=[
        dict(step_id="read", operator="resource.read", depends_on=[],
            inputs=dict(resource_id=dict(source="data", ref="source", field="resource_id"))),
        dict(step_id="infer", operator="model.spec.all" if style == "single"
            else "model.spec.requirements", depends_on=["read"], inputs=source),
        dict(step_id="check", operator="spec.verify_citations", depends_on=["read", "infer"],
            inputs={**source, "items": dict(source="step", ref="infer", field="items")}),
        dict(step_id="save", operator="artifact.save_text", depends_on=["check"],
            inputs=dict(text=dict(source="step", ref="check", field="text")))])


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def material(n):
    rid = 'res_' + str(n) * 32
    content = f'Independent material {n}'
    source = sha(content.encode())
    snapshot = dict(schema_version='F2-goal-card.v1', content=dict(title='T', goal='G', known=[],
        assumptions=[], unresolved=[], constraints=[], acceptance_checks=['check'], resource_refs=[rid]),
        resource_snapshots=[dict(resource_id=rid, hash=source, format='txt')])
    return MaterialGoal(resource_id=rid, content=content, source_hash=source,
        card_id='goal_' + str(n) * 32, goal_version=1, goal_fingerprint=fingerprint(snapshot),
        goal_snapshot=snapshot)


@pytest.fixture
def source():
    trial = PBTrialContract(trial_key='trial-original', project_id='proj_' + '1' * 32,
        principal_id='user_' + '2' * 32, runtime_id='runtime_' + '3' * 32,
        quota_subject='server-quota', software_fingerprint='a' * 64,
        authorization_fingerprint='b' * 64, bindings=[material(1), material(2)],
        stage_keys=StageKeys(generate='generate', source='source', cold='cold'),
        expires_at=time.time() + 300, path='P-B', extraction_request_key='extract',
        extraction_recipe=recipe('ordered'))
    tfp = fingerprint(trial.model_dump())
    afp = fingerprint(ApproveInput(expected_contract_fingerprint=tfp,
        request_key="approved-original", consent=CONSENT).model_dump())
    attempts = []
    for n in (1, 2):
        wire = json.dumps(dict(model=trial.model, stream=False, max_tokens=1024,
            messages=[dict(role='user', content=trial.bindings[0].content)])).encode()
        tokens = dict(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        raw = json.dumps(dict(id=f'response-{n}', model=trial.model, usage=tokens,
            choices=[dict(message=dict(content='synthetic result'))])).encode()
        usage = UsageEvidence('known', 'PROVIDER_RESPONSE', sha(raw), **tokens)
        attempts.append(ResponseEvidence(tfp, afp, 'attempt_' + str(n) * 32, trial.trial_key,
            'synthetic-provider', 'server-account', 'run_' + '4' * 32, 'LIVE', 'VERIFIED',
            f'provider-request-{n}', f'response-{n}', wire, sha(wire), raw, sha(raw), usage))
    slots = tuple(SourceSlotEvidence(tfp, afp, len(p.wire) + 1024, trial.trial_key, p.source_run_id, p.attempt_id, 'source',
        True, p.wire_sha256, p.response_sha256, p.usage) for p in attempts)
    evidence = SourceEvidence(tfp, afp, trial.trial_key, trial.project_id, trial.principal_id, trial.runtime_id,
        'synthetic-provider', 'server-account', trial.quota_subject, 'run_' + '4' * 32,
        'app_' + '5' * 32, trial.stage_keys.source, 'SUCCEEDED', trial.bindings[0], trial.bindings[1],
        tuple(attempts), slots, trial.extraction_request_key, attempts[1].attempt_id,
        attempts[1].response_sha256, trial.extraction_recipe, '')
    evidence = replace(evidence, extraction_fingerprint=extraction_fingerprint(evidence))
    contract = LivePBSourceContract(trial=trial, approval_key="approved-original", provider=evidence.provider,
        account_id=evidence.account_id, source_run_id=evidence.source_run_id,
        source_app_id=evidence.source_app_id, source_attempt_ids=tuple(p.attempt_id for p in attempts),
        response_attempt_id=attempts[1].attempt_id, extraction_request_key=trial.extraction_request_key,
        expected_extraction_fingerprint=evidence.extraction_fingerprint)
    return contract, evidence


def test_fixed_synthetic_source_only_never_grants_live(source):
    contract, evidence = source
    before = copy.deepcopy((contract, evidence))
    receipt = resolve_source(contract, SyntheticSourceResolver(evidence))
    assert receipt.verification == 'NOT_LIVE_VERIFIED' and receipt.evidence_scope == 'SYNTHETIC'
    assert receipt.live_allowed is False and receipt.actual_model_requests == 0
    assert receipt.account_id == 'server-account' and receipt.quota_subject == 'server-quota'
    assert receipt.trial_fingerprint == fingerprint(contract.trial.model_dump())
    assert (contract, evidence) == before


def test_default_and_unknown_resolver_deny_without_calling_callback(source):
    class Foreign:
        def resolve(self, contract):
            pytest.fail('Unregistered callback executed')
    contract, _ = source
    for resolver in (None, Foreign(), {'authority': 'trusted', 'free': True}):
        with pytest.raises(DomainError, match='No trusted production') as error:
            resolve_source(contract, resolver)
        assert error.value.code == 'LIVE_BLOCKED'


@pytest.mark.parametrize('field,value', [
    ('trial_fingerprint', '9' * 64), ('approval_fingerprint', '9' * 64),
    ('trial_key', 'other'), ('project_id', 'proj_' + '9' * 32),
    ('principal_id', 'user_' + '9' * 32), ('runtime_id', 'runtime_' + '9' * 32),
    ('provider', 'other'), ('account_id', 'other'), ('quota_subject', 'other'),
    ('source_run_id', 'run_' + '9' * 32), ('source_app_id', 'app_' + '9' * 32),
    ('source_request_key', 'other'), ('source_status', 'RUNNING'),
    ('extraction_request_key', 'other'), ('extraction_response_attempt_id', 'attempt_' + '9' * 32),
    ('extraction_response_sha256', '9' * 64), ('extraction_fingerprint', '9' * 64),
])
def test_cross_scope_and_extraction_anchor_fail_closed(source, field, value):
    contract, evidence = source
    with pytest.raises(DomainError):
        resolve_source(contract, SyntheticSourceResolver(replace(evidence, **{field: value})))


@pytest.mark.parametrize('field,value', [
    ('trial_fingerprint', '9' * 64), ('approval_fingerprint', '9' * 64),
    ('mode', 'MOCK'), ('status', 'RECEIVED'), ('trial_key', 'other'), ('account_id', 'other'),
    ('provider', 'other'), ('source_run_id', 'run_' + '9' * 32),
    ('wire_sha256', '9' * 64), ('response_sha256', '9' * 64),
    ('provider_request_id', ''), ('provider_response_id', 'other'),
    ('wire', b'{}'), ('raw_response', b'[]'),
])
def test_mock_relabel_and_response_archive_mismatch_denied(source, field, value):
    contract, evidence = source
    changed = replace(evidence.attempts[0], **{field: value})
    with pytest.raises(DomainError):
        resolve_source(contract, SyntheticSourceResolver(replace(evidence,
            attempts=(changed, evidence.attempts[1]))))


@pytest.mark.parametrize('field,value', [
    ('status', 'unknown'), ('source', 'caller'), ('response_sha256', '9' * 64),
    ('prompt_tokens', -1), ('completion_tokens', True), ('total_tokens', 0),
])
def test_unknown_partial_or_forged_usage_denied(source, field, value):
    contract, evidence = source
    proof = evidence.attempts[0]
    changed = replace(proof, usage=replace(proof.usage, **{field: value}))
    with pytest.raises(DomainError):
        resolve_source(contract, SyntheticSourceResolver(replace(evidence,
            attempts=(changed, evidence.attempts[1]))))


@pytest.mark.parametrize('damage', ['recipe', 'cold', 'goal', 'same_cold', 'expired', 'attempts',
    'slot_trial', 'slot_unknown', 'slot_usage', 'slot_stage', 'slot_missing', 'duplicate_provider'])
def test_recipe_material_goal_and_original_two_slot_binding(source, damage):
    contract, evidence = source
    if damage == 'recipe':
        evidence = replace(evidence, extraction_recipe=recipe('single'))
    elif damage == 'cold':
        evidence = replace(evidence, cold_material=material(3))
    elif damage == 'goal':
        changed = evidence.cold_material.model_copy(update={'goal_version': 2})
        evidence = replace(evidence, cold_material=changed)
    elif damage == 'same_cold':
        trial = contract.trial.model_copy(update={'bindings': [evidence.source_material] * 2})
        contract = contract.model_copy(update={'trial': trial})
    elif damage == 'expired':
        contract = contract.model_copy(update={'trial': contract.trial.model_copy(update={'expires_at': 1.0})})
    elif damage == 'attempts':
        evidence = replace(evidence, attempts=(evidence.attempts[0], evidence.attempts[0]))
    elif damage == 'slot_missing':
        evidence = replace(evidence, source_slots=())
    elif damage == 'duplicate_provider':
        a, b = evidence.attempts
        evidence = replace(evidence, attempts=(a, replace(b, provider_request_id=a.provider_request_id)))
    else:
        a, b = evidence.source_slots
        updates = {'slot_trial': {'trial_key': 'other'}, 'slot_unknown': {'accepted': False},
            'slot_usage': {'usage': replace(a.usage, status='unknown')}, 'slot_stage': {'stage': 'cold'}}
        evidence = replace(evidence, source_slots=(replace(a, **updates[damage]), b))
    with pytest.raises(DomainError):
        resolve_source(contract, SyntheticSourceResolver(evidence))


@pytest.mark.parametrize("field,value", [("software_fingerprint", "f" * 64),
    ("authorization_fingerprint", "f" * 64), ("expires_at", 9999999999.0),
    ("stage_keys", StageKeys(generate="other-generation", source="source", cold="cold"))])
def test_same_trial_key_changed_original_trial_cannot_reuse_source(source, field, value):
    contract, evidence = source
    changed = contract.model_copy(update={"trial": contract.trial.model_copy(update={field: value})})
    with pytest.raises(DomainError):
        resolve_source(changed, SyntheticSourceResolver(evidence))


@pytest.mark.parametrize("damage", ["approval", "slot_trial_fingerprint", "slot_approval_fingerprint",
    "slot_envelope", "total_over_envelope"])
def test_exact_approval_and_reserved_envelope(source, damage):
    contract, evidence = source
    if damage == "approval":
        contract = contract.model_copy(update={"approval_key": "different-approval"})
    elif damage == "total_over_envelope":
        a, b = evidence.attempts
        tokens = dict(prompt_tokens=100000, completion_tokens=20, total_tokens=100020)
        payload = json.loads(a.raw_response)
        payload["usage"] = tokens
        raw = json.dumps(payload).encode()
        usage = replace(a.usage, response_sha256=sha(raw), **tokens)
        evidence = replace(evidence, attempts=(replace(a, raw_response=raw,
            response_sha256=sha(raw), usage=usage), b))
    else:
        a, b = evidence.source_slots
        updates = {"slot_trial_fingerprint": {"trial_fingerprint": "9" * 64},
            "slot_approval_fingerprint": {"approval_fingerprint": "9" * 64},
            "slot_envelope": {"reserved_tokens": 64000}}
        evidence = replace(evidence, source_slots=(replace(a, **updates[damage]), b))
    with pytest.raises(DomainError):
        resolve_source(contract, SyntheticSourceResolver(evidence))


@pytest.mark.parametrize("damage", ["attempt_shape", "slot_shape", "raw_boolean_usage", "foreign_contract"])
def test_untyped_archive_shapes_and_boolean_provider_usage_fail_closed(source, damage):
    contract, evidence = source
    if damage == "attempt_shape":
        evidence = replace(evidence, attempts=("forged", evidence.attempts[1]))
    elif damage == "slot_shape":
        evidence = replace(evidence, source_slots=("forged", evidence.source_slots[1]))
    elif damage == "foreign_contract":
        contract = {"trial": contract.trial.model_dump()}
    else:
        a, b = evidence.attempts
        payload = json.loads(a.raw_response)
        payload["usage"]["prompt_tokens"] = True
        payload["usage"]["completion_tokens"] = 20
        payload["usage"]["total_tokens"] = 21
        raw = json.dumps(payload).encode()
        usage = replace(a.usage, response_sha256=sha(raw), prompt_tokens=1, total_tokens=21)
        evidence = replace(evidence, attempts=(replace(a, raw_response=raw,
            response_sha256=sha(raw), usage=usage), b))
    with pytest.raises(DomainError):
        resolve_source(contract, SyntheticSourceResolver(evidence))
