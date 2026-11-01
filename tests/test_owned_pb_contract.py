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


def legacy_binding():
    from sim2act.spec_production import ProductionTrialBinding
    previous=sys.getprofile()
    sys.setprofile(lambda *args: None)
    try:
        return ProductionTrialBinding(contract(), 'approval', 'synthetic-account')
    finally:
        sys.setprofile(previous)


def test_legacy_binding_and_unregistered_owned_root_are_distinct():
    from sim2act.spec_production import ProductionTrialBinding
    binding=legacy_binding()
    assert owned.bound(binding) is None
    value=owned.issue_data(binding.contract)
    object.__setattr__(binding,'contract',value)
    with pytest.raises(ValueError,match='ownership or lifecycle'):
        owned.bound(binding)


def test_direct_install_cannot_borrow_constructor_code_or_checked():
    from sim2act.spec_production import ProductionTrialBinding
    binding=legacy_binding()
    checked=binding.contract;value=owned.issue_data(checked)
    with pytest.raises(ValueError,match='ownership or lifecycle'):
        source.native.install_contract_binding(binding,value,checked,binding.approval_key,binding.account_id)
    assert owned.bound(binding) is None


def test_legacy_unregistered_binding_foreign_key_never_dispatches():
    from sim2act.spec_production import ProductionTrialBinding
    binding=legacy_binding();calls=[]
    class ForeignKey:
        def __hash__(self):return hash('contract')
        def __eq__(self,other):calls.append(True);return False
    fields={ForeignKey():None}
    object.__setattr__(binding,'__dict__',fields)
    with pytest.raises(ValueError,match='ownership or lifecycle'):
        owned.bound(binding)
    assert calls==[]


def test_default_binding_retirement_exact_identity_and_no_raw_downgrade():
    from sim2act.spec_production import ProductionTrialBinding
    a=ProductionTrialBinding(contract(),'approval','synthetic-account')
    b=ProductionTrialBinding(a.contract,'approval','synthetic-account')
    assert owned.is_owned(a.contract) and owned.is_owned(b.contract)
    assert gate._contract_same(owned.bound(a),a.contract)
    assert not gate._contract_same(a.contract,b.contract)
    assert gate._contract_recipe(a.contract)==gate._contract_recipe(b.contract)
    original=a.contract;raw=gate.PBTrialContract.model_validate(original.model_dump())
    object.__setattr__(a,'contract',raw)
    with pytest.raises(DomainError,match='ownership or lifecycle'):
        gate._contract_graph(a)
    object.__setattr__(a,'contract',b.contract)
    with pytest.raises((ValueError,DomainError),match='ownership or lifecycle'):
        owned.bound(a)
    object.__setattr__(a,'contract',original)
    assert gate._contract_same(gate._contract_graph(a),original)


def test_original_exclude_none_model_fields_and_repeated_aliases():
    from sim2act.contracts import FieldSource
    model=contract()
    nested=FieldSource(source='input',field='resource_id')
    inputs=model.extraction_recipe.steps[0].inputs
    inputs['extra1']=nested;inputs['extra2']=nested
    value=owned.issue_data(model)
    assert owned.is_owned(value)
    assert value.model_dump(exclude_none=True)==model.model_dump(exclude_none=True)
    assert value.extraction_recipe.model_dump(exclude_none=True)==model.extraction_recipe.model_dump(exclude_none=True)
    assert 'extra2' in value.extraction_recipe.model_dump(exclude_none=True)['steps'][0]['inputs']
    assert 'ref' not in value.extraction_recipe.model_dump(exclude_none=True)['steps'][0]['inputs']['extra2']
    assert gate._contract_recipe_equal(model.extraction_recipe,value.extraction_recipe)
    assert gate._contract_validated(value)
    with pytest.raises(TypeError):value.model_dump(exclude_none=object())


@pytest.mark.parametrize('attack',['reentry','wrong-origin','retire-tamper'])
def test_constructor_real_callbacks_keep_exact_private_origin_and_lifecycle(attack):
    import inspect
    from sim2act.spec_production import ProductionTrialBinding
    publish=owned.publish
    line=next(number for number,text in enumerate(inspect.getsource(publish).splitlines(),publish.__code__.co_firstlineno)
        if '_NATIVE.install_contract_binding' in text)
    captured=[];errors=[];triggered=[]
    tool=3
    sys.monitoring.use_tool_id(tool,'pb-constructor-real-callback')
    class Retired:
        def __init__(self,local):self.local=local
        def __del__(self):
            local=self.local
            try:source.native.install_contract_binding(local['binding'],local['value'],local['checked'],local['approval_key'],local['account_id'])
            except ValueError:errors.append('pending-refused')
            captured.append(local['binding'])
            object.__setattr__(local['binding'],'account_id','late-different-account')
    def monitor(code,number):
        if code is not publish.__code__ or number!=line or triggered:return
        triggered.append(True);local=dict(sys._getframe(1).f_locals)
        if attack=='reentry':
            source.native.install_contract_binding(local['binding'],local['value'],local['checked'],local['approval_key'],local['account_id']);captured.append(local['binding'])
        elif attack=='wrong-origin':
            checked=gate.PBTrialContract.model_validate(local['checked'].model_dump())
            other=owned.issue_data(checked)
            for origin in (checked,local['checked']):
                try:source.native.install_contract_binding(local['binding'],other,origin,local['approval_key'],local['account_id'])
                except ValueError:errors.append('origin-refused')
                else:errors.append('unexpected-install')
        else:
            object.__setattr__(local['binding'],'contract_fingerprint',Retired(local))
    sys.monitoring.register_callback(tool,sys.monitoring.events.LINE,monitor)
    sys.monitoring.set_local_events(tool,publish.__code__,sys.monitoring.events.LINE)
    try:
        if attack=='wrong-origin':
            result=ProductionTrialBinding(contract(),'approval','synthetic-account')
        else:
            with pytest.raises(ValueError,match='ownership or lifecycle'):
                ProductionTrialBinding(contract(),'approval','synthetic-account')
    finally:
        sys.monitoring.set_local_events(tool,publish.__code__,0)
        sys.monitoring.register_callback(tool,sys.monitoring.events.LINE,None)
        sys.monitoring.free_tool_id(tool)
    assert triggered==[True]
    if attack=='reentry':
        assert errors==[] and len(captured)==1
        assert gate._contract_same(owned.bound(captured[0]),captured[0].contract)
    elif attack=='wrong-origin':
        assert errors==['origin-refused','origin-refused']
        assert owned.is_owned(result.contract) and owned.bound(result) is not None
    else:
        assert errors==['pending-refused'] and len(captured)==1
        with pytest.raises(ValueError,match='ownership or lifecycle'):
            owned.bound(captured[0])


def test_recipe_dictionary_imitation_cannot_borrow_model_equality():
    value=owned.issue_data(contract());actual=gate.Recipe.model_validate(value.extraction_recipe.model_dump())
    step=actual.steps[0]
    for key,field in tuple(step.inputs.items()):
        step.inputs[key]=field.model_dump()
    assert actual != gate.Recipe.model_validate(value.extraction_recipe.model_dump())
    assert gate._contract_recipe_equal(actual,value.extraction_recipe) is False


def test_owned_producer_canonical_raw_is_readonly_and_same_full_owner():
    from sim2act.spec_production import ProductionTrialBinding
    binding=ProductionTrialBinding(contract(),'approval','synthetic-account')
    raw=gate._contract_raw(binding.contract)
    assert source.image.plain(raw)==binding.contract.model_dump()
    assert source.native.View.owner(raw) is source.native.View.owner(binding.contract)
    cohort=[]
    gate._trial_typed_hold(cohort,gate.PBTrialContract,binding.contract,raw)
    assert cohort==[]
    gate._trial_typed_values([(gate.PBTrialContract,binding.contract,raw)])
    with pytest.raises(TypeError):raw['trial_key']='changed'
    with pytest.raises((DomainError,TypeError)):
        gate._trial_typed_hold([],gate.PBTrialContract,binding.contract,binding.contract.model_dump())


@pytest.mark.parametrize('path',['caps','extraction_recipe'])
def test_owned_nested_schema_cannot_claim_pb_typed_expectation(path):
    value=getattr(owned.issue_data(contract()),path)
    raw=gate._contract_raw(value)
    with pytest.raises(DomainError,match='Exact PB root schema'):
        gate._trial_typed_hold([],gate.PBTrialContract,value,raw)
    with pytest.raises(DomainError,match='Exact PB root schema'):
        gate._trial_typed_values([(gate.PBTrialContract,value,raw)])


def test_c_read_keeps_fresh_pb_roles_and_schema(monkeypatch):
    from sim2act.spec_production import ProductionTrialBinding
    b=ProductionTrialBinding(contract(),'approval','synthetic-account');calls=[]
    with monkeypatch.context() as patch:
        patch.setattr(owned,'_TYPE',lambda *args:calls.append(True))
        with pytest.raises(ValueError,match='ownership or lifecycle'):
            source.native.contract_binding_current(b)
    assert calls==[] and owned.bound(b) is not None
    schema=gate.PBTrialContract.__pydantic_core_schema__
    with monkeypatch.context() as patch:
        patch.setitem(schema,'custom-late-schema',True)
        with pytest.raises(ValueError,match='ownership or lifecycle'):
            source.native.contract_binding_current(b)
    assert owned.bound(b) is not None
