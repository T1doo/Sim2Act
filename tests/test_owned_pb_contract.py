"""Complete PB DATA handoff. No model, DB, permit or business clock replacement."""
import json
import sys
import time

import pytest

from test_pb_live_source_contract import material, recipe
from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime
from sim2act import _owned_pb_contract as owned
from sim2act import _cold_source_packet as source
from sim2act.db import fingerprint
from sim2act.errors import DomainError
from sim2act.production_trial_admission import canonical_quota_subject


def contract(*, plain=False, title='synthetic contract', expires=None):
    materials=[]
    for i in (1,2):
        data=material(i).model_dump()
        data['goal_snapshot']['content']['title']=title
        data['goal_fingerprint']=fingerprint(data['goal_snapshot'])
        materials.append(gate.MaterialGoal.model_validate(data))
    return gate.PBTrialContract(trial_key='synthetic-owned-contract',project_id='proj_'+'a'*32,
        principal_id='user_'+'b'*32,runtime_id='runtime_'+'c'*32,
        quota_subject=canonical_quota_subject('synthetic-account'),software_fingerprint='d'*64,
        authorization_fingerprint='e'*64,bindings=materials,
        stage_keys=dict(generate='g',source='s',cold='c'),
        expires_at=time.time()+300 if expires is None else expires,
        path='P-B',extraction_request_key='x',extraction_recipe=recipe(),
        caps=gate.TrialCaps() if plain else gate.SQLiteSettlementCaps())


@pytest.mark.parametrize('plain',[False,True])
def test_complete_retirement_deep_readonly_and_exact_caps_type(plain):
    original=contract(plain=plain);raw=original.model_dump();value=owned.issue_data(original)
    assert owned.is_owned(value)
    assert type(value) is not gate.PBTrialContract and owned.model_type(value) is gate.PBTrialContract
    assert owned.model_type(value.caps) is (gate.TrialCaps if plain else gate.SQLiteSettlementCaps)
    original.caps.__dict__['max_output_tokens']=1
    original.bindings[0].goal_snapshot.content.known.append('retired producer changed')
    original.extraction_recipe.steps[0].inputs.clear()
    assert value.model_dump()==raw
    with pytest.raises((TypeError,AttributeError)):value.caps.max_output_tokens=1
    with pytest.raises((TypeError,AttributeError)):value.bindings[0]=None
    exported=value.model_dump();exported['bindings'][0]['goal_snapshot']['content']['known'].append('copy only')
    assert value.model_dump()==raw


@pytest.mark.parametrize('expires',[1e-20,1.0,1e20])
@pytest.mark.parametrize('title',['中文 \"\\\n\t\b\f\r\x00\x1f / é 😀','synthetic'])
def test_original_json_and_fingerprint_float_unicode_control_matrix(expires,title):
    original=contract(expires=expires,title=title);raw=original.model_dump()
    value=owned.issue_data(original)
    assert owned.is_owned(value)
    assert source.native.contract_json(value)==json.dumps(raw,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    assert source.native.contract_fingerprint(value)==fingerprint(raw)
    assert value.caps.model_dump()==original.caps.model_dump()
    before=original.extraction_recipe.steps[0].inputs['resource_id']
    after=value.extraction_recipe.steps[0].inputs['resource_id']
    assert owned.model_type(after) is type(before)
    assert after.ref==before.ref  # Real field; never the ordinary View.ref method.
    assert after.model_dump()==before.model_dump()
    with pytest.raises(TypeError):value.model_dump(warnings=object())


@pytest.mark.parametrize('role',['_TYPE','_ALL','_TUPLE','_VARS','_NEXT','_PROFILE','_TRACE'])
def test_changed_entry_role_refuses_before_foreign_call(monkeypatch,role):
    value=contract();called=[]
    def foreign(*args,**kwargs):called.append(True);raise AssertionError('foreign role executed')
    with monkeypatch.context() as patch:
        patch.setattr(owned,role,foreign)
        with pytest.raises(ValueError,match='entry code or role'):
            owned.issue_data(value)
    assert called==[]


def test_public_builtin_shadow_is_not_a_dispatch_role(monkeypatch):
    value=contract();called=[]
    with monkeypatch.context() as patch:
        patch.setattr(owned,'type',lambda *args:called.append(True),raising=False)
        assert owned.model_type(value) is gate.PBTrialContract
    assert called==[]


def test_ordinary_source_domain_cannot_issue_pb_and_false_catalog_is_refused():
    model=contract();raw=model.model_dump()
    data,anchors=source.image.capture((model,raw),(),_contract=True)
    assert not anchors and source.native.make_owned(data) is source.native.UNSUPPORTED
    catalog=tuple((ref,0 if kind==17 else kind) for ref,kind in data[7])
    forged=(*data[:7],catalog)
    assert source.native.make_contract_owned(forged,(model,raw),owned._config()) is source.native.UNSUPPORTED


def test_descriptor_role_mixing_cannot_hide_current_private_storage():
    model=contract();raw=model.model_dump()
    data,anchors=source.image.capture((model,raw),(),_contract=True)
    config=owned._config();models=list(config[0]);entry=list(models[17])
    entry[5]=entry[4]  # Private is NOT the extra descriptor, even if both were None.
    models[17]=tuple(entry);wrong=(tuple(models),*config[1:])
    object.__setattr__(model,'__pydantic_private__',{'synthetic_hidden_change':True})
    assert source.native.make_contract_owned(data,(model,raw),wrong) is source.native.UNSUPPORTED


def test_schema_change_after_early_eligibility_refuses_publication():
    value=contract();schema=gate.PBTrialContract.__pydantic_core_schema__
    metadata=schema['metadata'];key='synthetic_late_pb_schema_change';assert key not in metadata
    monitor=sys.monitoring;slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
    hit=[];code=owned._config.__code__
    def start(active,offset):
        if active is code and not hit:
            hit.append(True);metadata[key]=True
    monitor.use_tool_id(slot,'pb-late-schema')
    monitor.register_callback(slot,monitor.events.PY_START,start)
    monitor.set_local_events(slot,code,monitor.events.PY_START)
    try:
        with pytest.raises(DomainError) as error:owned.issue_data(value)
        assert error.value.code=='VERSION_CONFLICT' and hit==[True]
    finally:
        monitor.set_local_events(slot,code,0)
        monitor.register_callback(slot,monitor.events.PY_START,None)
        monitor.free_tool_id(slot);metadata.pop(key,None)
    assert source.native.contract_schema_current() is True


def test_legacy_binding_and_unregistered_owned_root_are_distinct():
    from sim2act.spec_production import ProductionTrialBinding
    binding=ProductionTrialBinding(contract(), 'approval', 'synthetic-account')
    assert owned.bound(binding) is None
    value=owned.issue_data(binding.contract)
    object.__setattr__(binding,'contract',value)
    with pytest.raises(ValueError,match='ownership or lifecycle'):
        owned.bound(binding)


def test_direct_install_cannot_borrow_constructor_code_or_checked():
    from sim2act.spec_production import ProductionTrialBinding
    binding=ProductionTrialBinding(contract(), 'approval', 'synthetic-account')
    checked=binding.contract;value=owned.issue_data(checked)
    with pytest.raises(ValueError,match='ownership or lifecycle'):
        source.native.install_contract_binding(binding,value,checked,binding.approval_key,binding.account_id)
    assert owned.bound(binding) is None


def test_legacy_unregistered_binding_foreign_key_never_dispatches():
    from sim2act.spec_production import ProductionTrialBinding
    binding=ProductionTrialBinding(contract(), 'approval', 'synthetic-account');calls=[]
    class ForeignKey:
        def __hash__(self):return hash('contract')
        def __eq__(self,other):calls.append(True);return False
    fields={ForeignKey():None}
    object.__setattr__(binding,'__dict__',fields)
    with pytest.raises(ValueError,match='ownership or lifecycle'):
        owned.bound(binding)
    assert calls==[]
