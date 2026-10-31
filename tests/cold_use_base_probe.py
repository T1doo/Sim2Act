"""Test-only observers at the real first SQL row/ownership boundary."""
import copy
import sys
from contextlib import contextmanager


@contextmanager
def observe_base(patch, probe):
    if probe is None:
        yield
        return
    from sqlalchemy.engine import RowMapping
    from sim2act import pb_natural_uses as use, _cold_source_packet as owned
    monitor=sys.monitoring
    slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
    checkpoint=use._use_read_checkpoint.__code__
    publish=owned.own_fact.__code__
    probe['unknown_callbacks']=[]
    def poison():
        probe['unknown_callbacks'].append(True)
        raise AssertionError('Unknown configuration callback executed')
    class Flag:
        def __bool__(self):poison()
    class Holder:
        def __iter__(self):poison()
    def entering(code,offset):
        frame=sys._getframe(1)
        if not frame.f_locals['name'].endswith(':base-row'):
            return
        probe['raw']=frame.f_locals['value']
        probe['graph']=frame.f_locals['graph']
        probe['name']=frame.f_locals['name']
        assert type(probe['raw']) is RowMapping
        probe['expected']=copy.deepcopy(dict(probe['raw']))
    def returned(code,offset,value):
        frame=sys._getframe(1)
        if code is checkpoint:
            caller=frame.f_back
            if (probe.get('injected') or caller is None or caller.f_code is not use._audit_prefix.__code__
                    or type(caller.f_locals.get('base')) is not RowMapping
                    or probe['mode'] not in ('flag','holder')):
                return
            probe['injected']=True
            patch.setattr(use,'_USE_OWNED_ENABLED',Flag()) if probe['mode']=='flag' else patch.setattr(use,'_USE_OWNED_CHECK',Holder())
            return
        if not frame.f_locals['name'].endswith(':base-row'):
            return
        graph=frame.f_locals['graph'];raw=frame.f_locals['value']
        assert owned.image.is_kind(value,'r')
        assert owned.image.plain(value)==probe['expected']
        # The native selected-node check includes hidden SQL storage, index,
        # quoted names, field order and full alias metadata, not only dict(row).
        assert owned.native.match_node(value.owner(),value.ref(),raw,owned._config(graph))
        probe['complete_hidden_storage_checked']=True
        if probe.get('injected'):
            return
        probe['injected']=True
        if probe['mode']=='producer-alias':
            raw['candidate']['old_alias_probe']='synthetic old producer mutation'
            assert owned.image.plain(value)==probe['expected']
            graph.check(graph.store,graph.connection)
        elif probe['mode']=='pin-rebind':
            key=frame.f_locals['name'];root=graph.inputs[key]
            graph.inputs[key]=(root[0],tuple(list(root[1])))
            graph.check(graph.store,graph.connection)
        elif probe['mode']=='late-bounds':
            raise probe['error']
    monitor.use_tool_id(slot,'Real Use audit first-owner boundary probe')
    try:
        monitor.register_callback(slot,monitor.events.PY_START,entering)
        monitor.register_callback(slot,monitor.events.PY_RETURN,returned)
        monitor.set_local_events(slot,publish,monitor.events.PY_START|monitor.events.PY_RETURN)
        monitor.set_local_events(slot,checkpoint,monitor.events.PY_RETURN)
        yield
    finally:
        for code in (publish,checkpoint):monitor.set_local_events(slot,code,0)
        for event in (monitor.events.PY_START,monitor.events.PY_RETURN):monitor.register_callback(slot,event,None)
        monitor.free_tool_id(slot)
