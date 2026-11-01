"""Actual Linux POSIX-signal callback boundaries; not a performance score."""
import signal, types
import pytest
from sim2act import _cold_graph_structure as native,natural_spec_runtime as r
from test_cold_dictionary_versions import scope,counters


def fixture_row(callback):
    class Row:pass
    marker=r._cold_graph_pickle_marker
    class Pickler:
        def reducer_override(self,value):
            callback()
            return marker,('synthetic unchanged row',)
    namespace=dict(vars(r));namespace['_ColdGraphPickler']=Pickler
    reader=types.FunctionType(r._cold_graph_row_storage.__code__,namespace)
    return Row,reader


def test_actual_signal_during_capture_restored_value_cannot_arm_old_interval():
    changed=[]
    leaf={'value':tuple(range(30000))}
    original=leaf['value']
    before=counters()
    def arm():signal.setitimer(signal.ITIMER_REAL,.0001)
    Row,reader=fixture_row(arm)
    value=[Row(),leaf];identity=scope()
    def handler(number,frame):
        changed.append(counters()['complete_capsules']==before['complete_capsules'])
        leaf['value']=tuple([1])
        leaf['value']=original
    prior=signal.signal(signal.SIGALRM,handler)
    try:
        saved=native.snapshot(value,Row,r.Limits,r._ColdGraphQuotedName,reader,r._cold_graph_limit_values,identity)
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,prior)
    assert saved is not native.UNSUPPORTED
    assert changed==[True]  # Handler ran before this C capture completed.
    assert counters()['armed_dictionary_versions']==before['armed_dictionary_versions']


@pytest.mark.parametrize('action',['mutate-earlier','raise-original'])
def test_actual_signal_after_fast_read_refuses_stale_data_or_keeps_original_error(action):
    leaves=[{'index':i,'value':7} for i in range(5000)]
    armed=[False]
    def arm():
        if armed[0]:signal.setitimer(signal.ITIMER_REAL,.0001)
    Row,reader=fixture_row(arm)
    value=[Row(),*leaves];identity=scope()
    saved=native.snapshot(value,Row,r.Limits,r._ColdGraphQuotedName,reader,r._cold_graph_limit_values,identity)
    assert saved is not native.UNSUPPORTED
    before=counters();seen=[]
    original=RuntimeError('synthetic exact pending signal error')
    def handler(number,frame):
        now=counters()
        seen.append((now['match_calls']>before['match_calls'],now['flat_dictionary_hits']>before['flat_dictionary_hits']))
        if action=='raise-original':raise original
        leaves[0]['value']=8
    prior=signal.signal(signal.SIGALRM,handler)
    armed[0]=True
    try:
        if action=='raise-original':
            with pytest.raises(RuntimeError) as error:native.matches_fast(saved,value,identity)
            assert error.value is original
        else:
            assert native.matches_fast(saved,value,identity) is not True
        assert seen==[(True,True)]  # Real callback after an indexed read.
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,prior)
