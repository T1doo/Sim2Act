"""Version-bound raw dictionary facts: full shape, aliases and real mutation.

No model/network/time substitution. Native false/unsupported is a MISS, never
final business refusal; product wrappers retain their original complete SHA.
"""
import gc
import types

import pytest

from sim2act import _cold_graph_structure as native
from sim2act import natural_spec_runtime as r
from test_cold_graph_structure import arguments


def scope():
    return (object(), object(), 'synthetic-dictionary-version', 0, 'post')


def capture(value, identity, stable=None):
    return native.snapshot(value, *arguments(), identity, r._SOURCE_VIEW_TYPE,
        r._SOURCE_OWNER_TYPE, value if stable is None else stable)


def counters():
    return native.read_structure_counts()['post']


def test_unchanged_original_flat_dictionary_uses_full_version_proof():
    identity=scope()
    value={'id':'synthetic','value':17,'nested':tuple([b'original',True,None,-0.0])}
    before=counters()
    saved=capture(value,identity)
    assert saved is not native.UNSUPPORTED
    for _ in range(3):assert native.matches_fast(saved,value,identity) is True
    after=counters()
    assert after['armed_dictionary_versions']>before['armed_dictionary_versions']
    assert after['flat_dictionary_hits']-before['flat_dictionary_hits']==3
    # A real write and restore must NEVER advance the old expectation/tag.
    value['value']=18
    assert native.matches_fast(saved,value,identity) is not True
    value['value']=17
    hits=counters()['flat_dictionary_hits']
    assert native.matches_fast(saved,value,identity) is True
    assert counters()['flat_dictionary_hits']==hits


@pytest.mark.parametrize('damage',['split-dict','merge-dict','split-tuple','merge-tuple','split-text','merge-text'])
def test_flat_dictionary_aliases_remain_in_complete_global_domain(damage):
    identity=scope()
    one=tuple([bytes(bytearray(b'synthetic immutable tuple'))])
    two=tuple([bytes(bytearray(b'synthetic immutable tuple'))])
    text='synthetic shared text '.encode().decode()
    other='synthetic shared text '.encode().decode()
    assert one is not two and text is not other
    leaf={'tuple':one,'text':text}
    if damage=='split-dict':
        value=[leaf,leaf]
        mutate=lambda:value.__setitem__(1,dict(leaf))
    elif damage=='merge-dict':
        value=[leaf,dict(leaf)]
        mutate=lambda:value.__setitem__(1,leaf)
    elif damage=='split-tuple':
        value={'leaf':leaf,'outside':one}
        mutate=lambda:value.__setitem__('outside',two)
    elif damage=='merge-tuple':
        value={'leaf':leaf,'outside':two}
        mutate=lambda:value.__setitem__('outside',one)
    elif damage=='split-text':
        value={'leaf':leaf,'outside':text}
        mutate=lambda:value.__setitem__('outside',other)
    else:
        value={'leaf':leaf,'outside':other}
        mutate=lambda:value.__setitem__('outside',text)
    original=r._cold_graph_bytes(value)
    saved=capture(value,identity)
    assert saved is not native.UNSUPPORTED
    assert native.matches_fast(saved,value,identity) is True
    mutate()
    assert r._cold_graph_bytes(value)!=original
    assert native.matches_fast(saved,value,identity) is not True


def test_nested_mutable_values_cannot_arm_a_dictionary():
    value={'mutable':[1,2]}
    identity=scope();before=counters()
    saved=capture(value,identity)
    assert saved is not native.UNSUPPORTED
    assert counters()['armed_dictionary_versions']==before['armed_dictionary_versions']
    value['mutable'].append(3)
    assert native.matches_fast(saved,value,identity) is not True


def test_projection_dictionaries_outside_live_inputs_stay_full_current_walks():
    identity=scope()
    live={'original':11}
    def projection():
        return {'inputs':live,'binding':{'contract':{'value':tuple([123])}}}
    value=projection();before=counters()
    saved=capture(value,identity,live)
    assert saved is not native.UNSUPPORTED
    assert counters()['armed_dictionary_versions']-before['armed_dictionary_versions']==1
    for _ in range(5):assert native.matches_fast(saved,projection(),identity) is True
    assert counters()['flat_dictionary_hits']-before['flat_dictionary_hits']==5


def test_reducer_temporary_dictionaries_are_never_indexed():
    class Row:pass
    calls=[]
    marker=r._cold_graph_pickle_marker
    class Pickler:
        def reducer_override(self,value):
            calls.append(True)
            return marker,({'temporary':tuple([123])},)
    namespace=dict(vars(r));namespace['_ColdGraphPickler']=Pickler
    reader=types.FunctionType(r._cold_graph_row_storage.__code__,namespace)
    value={'row':Row()};identity=scope();before=counters()
    saved=native.snapshot(value,Row,r.Limits,r._ColdGraphQuotedName,reader,
        r._cold_graph_limit_values,identity)
    assert saved is not native.UNSUPPORTED
    for _ in range(5):assert native.matches_fast(saved,value,identity) is True
    assert len(calls)==6
    assert counters()['armed_dictionary_versions']==before['armed_dictionary_versions']


def test_later_original_reducer_cannot_change_an_already_indexed_dictionary():
    class Row:pass
    leaf={'value':7}
    armed=[False]
    marker=r._cold_graph_pickle_marker
    class Pickler:
        def reducer_override(self,value):
            if armed[0]:leaf['value']=8
            return marker,('unchanged synthetic row',)
    namespace=dict(vars(r));namespace['_ColdGraphPickler']=Pickler
    reader=types.FunctionType(r._cold_graph_row_storage.__code__,namespace)
    value=[leaf,Row()];identity=scope()
    saved=native.snapshot(value,Row,r.Limits,r._ColdGraphQuotedName,reader,
        r._cold_graph_limit_values,identity)
    assert saved is not native.UNSUPPORTED
    assert native.matches_fast(saved,value,identity) is True
    armed[0]=True
    before=counters()['flat_dictionary_hits']
    assert native.matches_fast(saved,value,identity) is not True
    assert counters()['flat_dictionary_hits']>before


def test_gc_change_and_restore_cannot_reuse_a_stale_dictionary_version():
    identity=scope()
    value={'value':tuple([b'synthetic capture',17])}
    original=value['value'];other=tuple([b'changed',18])
    args=(value,*arguments(),identity,r._SOURCE_VIEW_TYPE,r._SOURCE_OWNER_TYPE,value)
    before=counters()
    old_threshold=gc.get_threshold()
    held=[];changed=[]
    def collecting(phase,info):
        if phase=='start':
            # Read-only counters locate the actual post-capture/pre-arm
            # interval without replacing any product function or clock.
            if counters()['dictionary_capture_candidates']>before['dictionary_capture_candidates']:
                value['value']=other
                value['value']=original
                changed.append(counters()['complete_capsules']>before['complete_capsules'])
        elif phase=='stop':
            # Keep one tracked allocation after each collection so the next
            # native inventory allocation also reaches the real collector.
            held.append([])
    gc.collect()
    gc.callbacks.append(collecting)
    try:
        gc.set_threshold(1,old_threshold[1],old_threshold[2])
        saved=native.snapshot(*args)
    finally:
        gc.callbacks.remove(collecting)
        gc.set_threshold(*old_threshold)
    assert saved is not native.UNSUPPORTED
    assert changed
    # CPython may defer the collector until the native call has returned.
    # Whichever real callback point occurs, the old tag cannot be reused.
    assert all(type(after_capture) is bool for after_capture in changed)
    hits=counters()['flat_dictionary_hits']
    assert native.matches_fast(saved,value,identity) is True
    assert counters()['flat_dictionary_hits']==hits


@pytest.mark.parametrize('position',[1023,1024,1025,2047,2048,2049])
def test_logical_signal_boundary_work_does_not_change_full_content(position):
    # The scalar prefix places the same versioned leaf on either side of a
    # 1024 work boundary. This is correctness, never a timing benchmark.
    value=[0]*position+[{'synthetic':'original','value':7}]
    identity=scope();saved=capture(value,identity)
    assert saved is not native.UNSUPPORTED
    assert native.matches_fast(saved,value,identity) is True
    value[-1]['value']=8
    assert native.matches_fast(saved,value,identity) is not True
