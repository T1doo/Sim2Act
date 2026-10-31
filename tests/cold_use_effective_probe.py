"""Observe the actual expanded JSON transfer without replacing business code."""
import copy
import sys
from contextlib import contextmanager


@contextmanager
def observe_effective(probe):
    if probe is None:
        yield
        return
    from sim2act import _cold_source_packet as owned
    monitor = sys.monitoring
    slot = next(i for i in (3, 5, 4) if monitor.get_tool(i) is None)
    publish = owned.own_fact.__code__
    probe['transfers'] = []

    def entering(code, offset):
        frame = sys._getframe(1)
        if not frame.f_locals['name'].endswith(':effective-candidate'):
            return
        raw = frame.f_locals['value']
        assert type(raw) is dict
        probe['graph'] = frame.f_locals['graph']
        probe['expected'] = copy.deepcopy(raw)
        probe['raw'] = raw
        if probe['mode'] == 'pre-bounds' and not probe.get('injected'):
            probe['injected'] = True
            raise owned.image.Bounds('synthetic prepublication candidate capacity')

    def returned(code, offset, view):
        frame = sys._getframe(1)
        name = frame.f_locals['name']
        if not name.endswith(':effective-candidate'):
            return
        graph, raw = frame.f_locals['graph'], frame.f_locals['value']
        assert owned.image.is_kind(view, 'd')
        assert owned.image.plain(view) == probe['expected']
        steps = raw['spec_recipe']['steps']
        for index, step in enumerate(steps):
            workflow = raw['manifest']['workflow'][index]
            for key in ('inputs', 'depends_on'):
                if workflow[key] is step[key]:
                    assert owned.image.same(view['manifest']['workflow'][index][key],
                                            view['spec_recipe']['steps'][index][key])
        probe['transfers'].append(dict(graph=graph, name=name, view=view))
        if probe.get('injected'):
            return
        probe['injected'] = True
        if probe['mode'] == 'producer-alias':
            raw['manifest']['name'] = 'retired synthetic producer mutation'
            assert owned.image.plain(view) == probe['expected']
            graph.check(graph.store, graph.connection)
        elif probe['mode'] == 'pin-rebind':
            root = graph.inputs[name]
            graph.inputs[name] = (root[0], tuple(list(root[1])))
            graph.check(graph.store, graph.connection)
        elif probe['mode'] == 'late-bounds':
            raise probe['error']

    monitor.use_tool_id(slot, 'Actual effective-candidate first-owner boundary')
    try:
        monitor.register_callback(slot, monitor.events.PY_START, entering)
        monitor.register_callback(slot, monitor.events.PY_RETURN, returned)
        monitor.set_local_events(slot, publish, monitor.events.PY_START | monitor.events.PY_RETURN)
        yield
    finally:
        monitor.set_local_events(slot, publish, 0)
        for event in (monitor.events.PY_START, monitor.events.PY_RETURN):
            monitor.register_callback(slot, event, None)
        monitor.free_tool_id(slot)


def check_effective(binding, graph, probe):
    if probe is None:
        return
    from sim2act import _cold_source_packet as owned
    value = binding.use_review.prefix.value
    consumers = (binding.use_review.value[0]['effective_candidate'],
                 binding.use_value[0]['candidate'], binding.binding['draft']['candidate'],
                 binding.binding['plan']['definition'])
    if type(value) is dict:
        assert probe['mode'] == 'pre-bounds'
        assert all(consumer is value for consumer in consumers)
    else:
        assert all(owned.image.same(consumer, value) for consumer in consumers)
        assert owned.image.same(owned.fact(graph,
            binding.use_review.prefix.key + ':effective-candidate'), value)
    probe['consumers_checked'] = True
