"""Complete native audit first publication, scoped seeds and real alias checks."""
import copy
import pytest
from test_cold_generation_facts import generated,scope
from sim2act import natural_spec_runtime as runtime,goal_applications as generation
from sim2act import pa_spec_apps as spec,_cold_source_packet as owned
from sim2act.errors import DomainError


def test_first_native_audit_has_no_mutable_original_root_and_keeps_all_rows(generated):
    f=generated
    with f.store.tx() as c,scope(f,c) as guard:
        raw=spec._native_audit_facts(f.store,c,f.user,f.draft,_graph_read=guard)
        expected=copy.deepcopy(raw)
        fact=runtime._cold_native_audit_fact(guard,raw)
        assert owned.image.is_kind(fact,'d')
        key='original-native-audit:'+raw['original']['id']
        assert owned.image.same(owned.fact(guard,key),fact)
        assert guard.inputs[key][0]==owned.FACT_TAG
        assert owned.image.compat(fact)==expected
        seed=generation._ColdGenerationRawSeed(f.store,c,f.user,fact,guard)
        seed.check(f.store,c,f.user,f.run)
        raw['attempts'].clear()
        raw['run']['context']['requests']+=1
        assert owned.image.compat(fact)==expected
        seed.check(f.store,c,f.user,f.run)


@pytest.mark.parametrize('damage',['equal-other-owner','root-rebind','another-guard'])
def test_native_seed_rejects_replacement_scope_and_equal_clone(generated,damage):
    f=generated;reached=False
    with pytest.raises(DomainError),f.store.tx() as c,scope(f,c) as guard:
        raw=spec._native_audit_facts(f.store,c,f.user,f.draft,_graph_read=guard)
        fact=runtime._cold_native_audit_fact(guard,raw)
        seed=generation._ColdGenerationRawSeed(f.store,c,f.user,fact,guard)
        seed.check(f.store,c,f.user,f.run)
        if damage=='equal-other-owner':
            seed.rows=owned.own_fact(guard,'native-audit:equal-clone',owned.image.compat(fact))
        elif damage=='root-rebind':guard.inputs['original-native-audit:'+raw['original']['id']]=dict(raw)
        else:
            # An unrelated object cannot substitute the exact originally bound
            # guard, even if it copies every visible instance field.
            other=object.__new__(type(guard));vars(other).update(vars(guard));seed.guard=other
        reached=True
        seed.check(f.store,c,f.user,f.run)
    assert reached and not guard.active


def test_native_audit_retains_real_outside_mutable_alias(generated):
    f=generated;reached=False
    with pytest.raises(DomainError),f.store.tx() as c,scope(f,c) as guard:
        raw=spec._native_audit_facts(f.store,c,f.user,f.draft,_graph_read=guard)
        shared=raw['run']['context']
        guard.add('native-audit:shared-original-context',shared)
        fact=runtime._cold_native_audit_fact(guard,raw)
        guard.check(f.store,c)
        assert fact['run']['context']['requests']==shared['requests']
        shared['requests']+=1
        reached=True
        guard.check(f.store,c)
    assert reached


@pytest.mark.parametrize('module,name',[(spec,'_native_audit_facts'),(generation,'source_scope_gate')])
def test_native_audit_producer_replacement_is_not_executed(monkeypatch,module,name):
    observed=[]
    def replaced(*args,**kwargs):observed.append(True);return {}
    monkeypatch.setattr(module,name,replaced)
    with pytest.raises(DomainError):owned.current()
    assert not observed
