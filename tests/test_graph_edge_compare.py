"""First visits, alias changes and mutable reducer types remain checked."""

import gc
import sys

import pytest

from sim2act import _cold_graph_structure as native
from sim2act import natural_spec_runtime as r
from sim2act.contracts import Limits


def limit():
    return Limits(max_requests=2,max_tools=4,max_repairs=0,
        max_total_tokens=64000,max_output_tokens=1024,run_seconds=300)


def arguments():
    return (r._ColdGraphRowMapping,Limits,r._ColdGraphQuotedName,
        r._cold_graph_row_storage,r._cold_graph_limit_values)


@pytest.mark.parametrize('kind',['r','c','u'])
def test_already_visited_reducer_owner_still_rechecks_current_class(monkeypatch,kind):
    class OtherLimits(Limits):pass
    classes={'r':(Limits,OtherLimits,r._ColdGraphQuotedName),
        'c':(r._ColdGraphRowMapping,Limits,r._ColdGraphQuotedName),
        'u':(r._ColdGraphRowMapping,OtherLimits,Limits)}[kind]
    first,second=limit(),limit();value=[first,second,first]
    scope=(object(),object(),'reducer-class',0,'post')
    cap=native.snapshot(value,*classes,r._cold_graph_row_storage,r._cold_graph_limit_values,scope)
    assert cap is not native.UNSUPPORTED
    original=r._cold_graph_limit_values
    def changed(model):
        if model is second:object.__setattr__(first,'__class__',OtherLimits)
        return original(model)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(r,'_cold_graph_limit_values',changed)
            assert native.matches_fast(cap,value,scope) is False
    finally:object.__setattr__(first,'__class__',Limits)
    assert native.matches_fast(cap,value,scope) is True


def test_callback_changes_future_alias_and_original_constraint_rejects(monkeypatch):
    shared={'value':[1]};other={'value':[1]};value=[shared,limit(),other]
    scope=(object(),object(),'later-alias',0,'post')
    cap=native.snapshot(value,*arguments(),scope)
    original=r._cold_graph_limit_values
    def changed(model):
        value[2]=shared
        return original(model)
    with monkeypatch.context() as patch:
        patch.setattr(r,'_cold_graph_limit_values',changed)
        assert native.matches_fast(cap,value,scope) is False
    value[2]=other
    assert native.matches_fast(cap,value,scope) is True


def test_reentry_and_exception_after_memo_hits_leave_independent_state(monkeypatch):
    model=limit();value=[{'memo':[1]},model,model]
    scope=(object(),object(),'memo-reentry',0,'post')
    cap=native.snapshot(value,*arguments(),scope)
    original=r._cold_graph_limit_values;inside=False;nested=[]
    def reentrant(actual):
        nonlocal inside
        if not inside:
            inside=True
            try:nested.append(native.matches_fast(cap,value,scope))
            finally:inside=False
        return original(actual)
    with monkeypatch.context() as patch:
        patch.setattr(r,'_cold_graph_limit_values',reentrant)
        assert native.matches_fast(cap,value,scope) is True and nested and all(nested)
    references=sys.getrefcount(model)
    def failed(actual):raise RuntimeError('Synthetic edge comparator callback')
    with monkeypatch.context() as patch:
        patch.setattr(r,'_cold_graph_limit_values',failed)
        with pytest.raises(RuntimeError,match='Synthetic edge comparator callback'):
            native.matches_fast(cap,value,scope)
    gc.collect()
    assert sys.getrefcount(model)==references
    assert native.matches_fast(cap,value,scope) is True
