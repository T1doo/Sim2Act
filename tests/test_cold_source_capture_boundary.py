"""Outside traversal retains the full admission domain and alias closure."""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.sql.elements import quoted_name
from sim2act import _cold_source_image as image


def test_completed_capture_releases_recursive_walker_without_later_gc():
    import gc,sys,types,weakref
    code=next(c for c in image.capture.__code__.co_consts
        if isinstance(c,types.CodeType) and c.co_name=='visit')
    monitor=sys.monitoring
    slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
    walkers=[]
    def entered(target,offset):
        if walkers:return
        frame=sys._getframe(1)
        walkers.append(weakref.ref(frame.f_locals['recur']))
        gc.collect()  # Reset prior garbage; never disable or alter GC policy.
    monitor.use_tool_id(slot,'Capture temporary lifetime regression')
    try:
        monitor.register_callback(slot,monitor.events.PY_START,entered)
        monitor.set_local_events(slot,code,monitor.events.PY_START)
        image.capture({'kept':['synthetic']},{'outside':[1,2,3]})
        assert len(walkers)==1 and walkers[0]() is None
    finally:
        monitor.set_local_events(slot,code,0)
        monitor.register_callback(slot,monitor.events.PY_START,None)
        monitor.free_tool_id(slot)


def test_shared_parent_marks_all_incoming_descendants_and_leaf_identity():
    leaf=''.join(('shared ', 'carrier'))
    child={'leaf':leaf}
    parent=[child,child]
    data,anchors=image.capture({'parent':parent}, {'outside':[parent,parent]})
    assert len(anchors)==2
    assert anchors[0] is parent and anchors[1] is child
    assert len(data[3])==2
    assert len(data[6])==2  # The key and value leaves in the shared subtree.


@pytest.mark.parametrize('bad',[(1<<63),-(1<<63)-1,{1},object()])
def test_outside_only_values_retain_original_type_and_range_gates(bad):
    with pytest.raises(image.Unsupported):image.capture({'valid':1},{'outside':bad})


def test_outside_cycle_is_rejected_even_after_an_alias_was_seen():
    child=[];outside=[child,child];child.append(outside)
    with pytest.raises(image.Unsupported,match='cycle'):image.capture((),outside)


@pytest.mark.parametrize('limit,value,maximum',[
    ('_MAX_LEAF',{'text':'large'},8),
    ('_MAX_EDGES',[1,2,3],3),
    ('_MAX_NODES',[1,2,3],3),
])
def test_outside_only_data_consumes_joint_capture_budgets(monkeypatch,limit,value,maximum):
    monkeypatch.setattr(image,limit,maximum)
    with pytest.raises(image.Bounds):image.capture((),value)


def test_sql_row_alias_and_quoted_name_hidden_storage_stay_in_boundary():
    engine=create_engine('sqlite://')
    try:
        with engine.connect() as connection:
            row=connection.execute(text('select 7 as number, :label as label'),{'label':'synthetic'}).mappings().one()
            data,anchors=image.capture({'row':row,'quote':quoted_name('quoted',True)},[row])
            assert any(anchor is row for anchor in anchors)
            assert any(node[0]=='r' for node in data[1])
            assert any(node[0]=='u' for node in data[1])
            assert data[3] and data[5]
    finally:engine.dispose()


@pytest.mark.parametrize('shape',['row','limits','float'])
def test_outside_helper_failure_retains_original_exception(monkeypatch,shape):
    from sim2act import natural_spec_runtime as runtime
    from sim2act.contracts import Limits
    original=ValueError('outside helper original failure')
    def fail(*args,**kwargs):raise original
    engine=None
    try:
        if shape=='row':
            engine=create_engine('sqlite://')
            with engine.connect() as connection:
                value=connection.execute(text('select 1 as number')).mappings().one()
            monkeypatch.setattr(runtime,'_cold_graph_row_storage',fail)
        elif shape=='limits':
            value=Limits(max_requests=1,max_tools=1,max_repairs=0,
                max_total_tokens=100,max_output_tokens=20,run_seconds=60)
            monkeypatch.setattr(runtime,'_cold_graph_limit_values',fail)
        else:
            value=1.25
            monkeypatch.setattr(image,'_PACK',fail)
        with pytest.raises(ValueError) as caught:image.capture(None,[value])
        assert caught.value is original
    finally:
        if engine is not None:engine.dispose()
