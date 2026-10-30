"""Pointer-index acceleration must retain complete content and alias checks."""

import copy
import gc
import itertools
import sys
import weakref

import pytest
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.sql.elements import quoted_name

from sim2act import _cold_graph_structure as native
from sim2act import natural_spec_runtime as runtime
from sim2act.contracts import Limits


def arguments():
    return RowMapping,Limits,quoted_name,runtime._cold_graph_row_storage,runtime._cold_graph_limit_values


@pytest.mark.parametrize('kind',['dict','list','tuple'])
def test_mutable_original_clone_split_merge_reverse_alias_matrix(kind):
    def item():
        child={'value':[1001]}
        return child if kind=='dict' else ([child] if kind=='list' else (child,))
    originals=[item() for _ in range(3)]
    clones=copy.deepcopy(originals)
    choices=originals+clones
    scope=(object(),object(),'identity-matrix',0,'post')
    for before in itertools.product(range(3),repeat=3):
        root=[originals[i] for i in before]
        key=runtime._cold_graph_bytes(root)
        capsule=native.snapshot(root,*arguments(),scope)
        assert capsule is not native.UNSUPPORTED
        for after in itertools.product(range(6),repeat=3):
            current=[choices[i] for i in after]
            expected=runtime._cold_graph_bytes(current)==key
            assert native.matches_fast(capsule,current,scope) is expected,(kind,before,after)


def test_same_mutable_objects_are_not_content_verdicts_and_refs_stay_stable():
    root={'items':[[1],[2]]}
    scope=(object(),object(),'mutable-content',0,'post')
    capsule=native.snapshot(root,*arguments(),scope)
    refs=[sys.getrefcount(v) for v in [root,root['items'],*root['items']]]
    for _ in range(500):
        assert native.matches_fast(capsule,root,scope) is True
        root['items'][0].append(9)
        assert native.matches_fast(capsule,root,scope) is False
        root['items'][0].pop()
    assert [sys.getrefcount(v) for v in [root,root['items'],*root['items']]]==refs


def test_cloned_limits_and_temporary_reducer_results_are_released():
    original=Limits(max_requests=2,max_tools=4,max_repairs=0,
        max_total_tokens=64000,max_output_tokens=1024,run_seconds=300)
    scope=(object(),object(),'temporary-reducers',0,'post')
    capsule=native.snapshot([original],*arguments(),scope)
    initial=sys.getrefcount(original)
    for _ in range(100):
        current=original.model_copy(deep=True)
        ref=weakref.ref(current)
        assert native.matches_fast(capsule,[current],scope) is True
        del current
        assert ref() is None
    gc.collect()
    assert sys.getrefcount(original)==initial


def test_reducer_exception_cleans_borrowed_and_owned_references(monkeypatch):
    row=RowMapping(SimpleResultMetaData(['id']),None,{'id':0},('synthetic',))
    root=[row,{'nested':[1]}]
    scope=(object(),object(),'exception-cleanup',0,'post')
    capsule=native.snapshot(root,*arguments(),scope)
    refs=[sys.getrefcount(v) for v in [root,row,root[1],root[1]['nested']]]
    def fail(*args):
        raise RuntimeError('Synthetic reducer exception')
    with monkeypatch.context() as patch:
        patch.setattr(runtime,'_cold_graph_row_storage',fail)
        with pytest.raises(RuntimeError,match='Synthetic reducer exception'):
            native.matches_fast(capsule,root,scope)
    assert native.matches_fast(capsule,root,scope) is True
    assert [sys.getrefcount(v) for v in [root,row,root[1],root[1]['nested']]]==refs
