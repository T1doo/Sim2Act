"""Same passive, low-frequency stage profiler for two frozen source exports."""
import hashlib,json,os,platform,resource,sqlite3,sys,threading,time,importlib.util,weakref
from pathlib import Path
import pytest

def host_snapshot():
    result=dict(loadavg=os.getloadavg(),affinity=sorted(os.sched_getaffinity(0)))
    for key,name in (('cpu_max','cpu.max'),('cpu_stat','cpu.stat'),('memory_max','memory.max'),('cpuset','cpuset.cpus.effective')):
        p=Path('/sys/fs/cgroup')/name
        result[key]=p.read_text().strip() if p.exists() else None
    return result

@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    if item.name!='test_same_large_cold_snapshot_control[complete]':
        yield;return
    from sim2act import natural_spec_runtime as r,natural_live_admission as gate
    from sim2act import _cold_accounted_native as native,_cold_accounted_receipts as receipt
    from sim2act import _cold_source_packet as source,pa_spec_apps as spec,_sqlite_run_control as control
    from sim2act import _cold_graph_structure_guard as structural
    diagpath=next(Path('/workspace/scratch/use-effective-shape-20261031').glob('*.so'))
    ds=importlib.util.spec_from_file_location('_use_effective_shape._cold_graph_structure',diagpath);diag=importlib.util.module_from_spec(ds);ds.loader.exec_module(diag)
    diagnostic_source=diagpath.with_name('_cold_graph_structure.c')
    assert diag.SOURCE_SHA256==hashlib.sha256(diagnostic_source.read_bytes()).hexdigest(), 'Diagnostic binary/source mismatch'
    production_text=Path(r.__file__).with_name('_cold_graph_structure.c').read_text();diagnostic_text=diagnostic_source.read_text()
    for suffix in ('Entry;','Map;','Encoder;','Node;','Tree;'):
        assert next(line for line in production_text.splitlines() if line.startswith('typedef struct') and line.endswith(suffix))==next(line for line in diagnostic_text.splitlines() if line.startswith('typedef struct') and line.endswith(suffix)), 'Diagnostic Tree layout mismatch'
    shape_targets={structural.select.__code__:'select',structural.select_frontier.__code__:'select_frontier'}
    shape_graphs={};shape_rows=[];shape_ns=0;transfers=[]
    timed={r._ColdTrialGraph._prepare.__code__:'prepare',r._ColdTrialGraph.commit.__code__:'trial.commit',
        native._NativeCandidate.qualify.__code__:'native.qualify',receipt._ReceiptClosure.preload.__code__:'receipt.preload',
        receipt._ReceiptClosure.budget.__code__:'receipt.budget',spec._cold_receipts.__code__:'receipts',r._prove_node.__code__:'prove_node'}
    absent=[]
    for name in ('_budget_admin','_publish_admin'):
        fn=getattr(receipt._ReceiptClosure,name,None)
        if fn is None:absent.append('receipt.'+name)
        else:timed[fn.__code__]='receipt.'+name
    counted={source.current.__code__:'source.current',r._ColdGraphRead._check_dynamic.__code__:'graph.dynamic',
        receipt._receipt_for_frontier.__code__:'receipt.current',structural.select.__code__:'select',
        structural.select_frontier.__code__:'select_frontier',gate._trial_typed_values.__code__:'typed_values'}
    ctor=control.Epoch.__init__.__code__;post=control.Epoch.postwrite.__code__
    close=control.Registry.settlement.__wrapped__.__code__;encoding=r._cold_graph_bytes.__code__
    choice=native._NativeCandidate.choose.__code__;monitor=sys.monitoring
    slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
    epochs=[];tracked=None;owner_thread=None;stack=[];rows={};counts={};phases=[];selections=[];errors=[]
    phase_start=None;epoch_start=None;host_before=host_snapshot()
    def stamp():
        u=resource.getrusage(resource.RUSAGE_SELF)
        return dict(wall_ns=time.monotonic_ns(),thread_ns=time.thread_time_ns(),process_cpu=u.ru_utime+u.ru_stime)
    def delta(a,b):return {key:b[key]-a[key] for key in a}
    def record_phase(phase):
        phases.append(dict(epoch=len(epochs),phase=phase,elapsed=delta(phase_start,stamp()),host=host_snapshot()))
    def enabled():return tracked is not None and not tracked.closed and threading.get_ident()==owner_thread
    def entered(code,offset):
        try:
            if not enabled():return
            key=(len(epochs),tracked.phase)
            if code in counted:
                n=counted[code];counts.setdefault(key,{}).setdefault(n,0);counts[key][n]+=1
            if code in timed:
                stack.append([id(sys._getframe(1)),key,timed[code],time.monotonic_ns(),time.thread_time_ns(),0,0])
        except Exception as e:errors.append(type(e).__name__)
    def returned(code,offset,value,unwound=False,actual_frame=None):
        nonlocal tracked,owner_thread,phase_start,epoch_start,shape_ns
        try:
            frame=sys._getframe(1) if actual_frame is None else actual_frame
            if code is ctor:
                e=frame.f_locals['self']
                if e.worker.store.engine.url.database!=item.funcargs['env'][0].engine.url.database:return
                if tracked is not None and not tracked.closed:errors.append('overlapping epochs')
                tracked=e;owner_thread=threading.get_ident();epochs.append(e)
                epoch_start=phase_start=stamp();return
            if tracked is None or threading.get_ident()!=owner_thread:return
            if code is post:
                if frame.f_locals['self'] is tracked:
                    record_phase('G0');phase_start=stamp()
                return
            if code is close:
                if frame.f_locals.get('epoch') is tracked and tracked.closed:
                    record_phase('G1');tracked=None
                return
            if not enabled():return
            key=(len(epochs),tracked.phase)
            if code is encoding:
                row=counts.setdefault(key,{})
                row['encoding_calls']=row.get('encoding_calls',0)+1
                if type(value) is bytes:row['encoded_bytes']=row.get('encoded_bytes',0)+len(value)
            elif code is choice:
                candidate=frame.f_locals['self']
                selections.append(dict(epoch=len(epochs),phase=tracked.phase,record=candidate.selection_record()))
            if code is source.own_fact.__code__ and type(frame.f_locals.get('name')) is str and frame.f_locals['name'].endswith((':effective-candidate',':expanded')):
                if type(value) is source.image.View:
                    data=source.native.owned_data(value.owner())
                    transfers.append(dict(epoch=len(epochs),phase=tracked.phase,name=frame.f_locals['name'],owned_nodes=len(data[1]),carrier_leaves=len(data[2]),boundary_anchors=len(data[3])))
            if code in shape_targets and value is True:
                graph=frame.f_locals.get('graph');state=frame.f_locals.get('state');scope=frame.f_locals.get('scope')
                if graph is not None and state is not None and state.capsule is not None:
                    entry=shape_graphs.get(id(graph))
                    if entry is None or entry[0]() is not graph:
                        maps={};shape_graphs[id(graph)]=(weakref.ref(graph),maps)
                    else:maps=entry[1]
                    sk=(len(epochs),tracked.phase,scope[2],shape_targets[code])
                    row=maps.get(sk)
                    if row is None:
                        a=time.monotonic_ns();shape=diag.shape(state.capsule);shape_ns+=time.monotonic_ns()-a
                        row=dict(epoch=len(epochs),phase=tracked.phase,selector=shape_targets[code],calls=0,shape=shape,
                            effective_candidate_roots=sum(name.endswith((':effective-candidate',':expanded')) for name in vars(graph).get('_source_fact_bindings',{})))
                        maps[sk]=row;shape_rows.append(row)
                    row['calls']+=1
            if code not in timed:return
            ident=id(frame)
            if not stack or stack[-1][0]!=ident:
                errors.append('unmatched timed return');return
            entry=stack.pop();wall=time.monotonic_ns()-entry[3];cpu=time.thread_time_ns()-entry[4]
            row=rows.setdefault((entry[1],entry[2]),dict(calls=0,partial_calls=0,inclusive_wall_ns=0,exclusive_wall_ns=0,inclusive_thread_ns=0,exclusive_thread_ns=0))
            row['partial_calls']+=int(unwound)
            row['calls']+=1;row['inclusive_wall_ns']+=wall;row['exclusive_wall_ns']+=wall-entry[5]
            row['inclusive_thread_ns']+=cpu;row['exclusive_thread_ns']+=cpu-entry[6]
            if stack:stack[-1][5]+=wall;stack[-1][6]+=cpu
        except Exception as e:errors.append(type(e).__name__)
    def unwound(code,offset,error):
        if code in timed or code is close:returned(code,offset,None,True,sys._getframe(1))
    events={}
    for code in counted:events[code]=monitor.events.PY_START
    for code in timed:events[code]=monitor.events.PY_START|monitor.events.PY_RETURN
    for code in (ctor,post,close,encoding,choice,source.own_fact.__code__,*shape_targets):events[code]=events.get(code,0)|monitor.events.PY_RETURN
    monitor.use_tool_id(slot,'Paired low-frequency stages and count-only hot calls')
    try:
        monitor.register_callback(slot,monitor.events.PY_START,entered);monitor.register_callback(slot,monitor.events.PY_RETURN,returned)
        monitor.register_callback(slot,monitor.events.PY_UNWIND,unwound)
        monitor.set_events(slot,monitor.events.PY_UNWIND)
        for code,mask in events.items():monitor.set_local_events(slot,code,mask)
        yield
    finally:
        for code in events:monitor.set_local_events(slot,code,0)
        monitor.set_events(slot,0)
        for event in (monitor.events.PY_START,monitor.events.PY_RETURN,monitor.events.PY_UNWIND):monitor.register_callback(slot,event,None)
        monitor.free_tool_id(slot)
        # Original business/lease intervals have ended. Do not insert extra
        # validation or replay Graph/PASS inside either real transaction.
        batch=[]
        try:
            for _ in range(10):source.current()
            for _ in range(3):
                a=time.perf_counter_ns();b=time.process_time_ns()
                for _ in range(200):source.current()
                batch.append(dict(calls=200,wall_ns=time.perf_counter_ns()-a,process_ns=time.process_time_ns()-b))
        except Exception as e:errors.append('outside-lease qualification batch:'+type(e).__name__)
        binaries={}
        for name in ('sim2act._raw_snapshot','sim2act._cold_graph_structure','sim2act._cold_source_owned_impl'):
            module=sys.modules.get(name)
            if module is not None and getattr(module,'__file__',None):
                p=Path(module.__file__);binaries[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
        report=dict(classification='PAIRED_ORIGINAL_LARGE_FIXED_MOCK_SQLITE_PASSIVE_COARSE_PROFILE_NOT_SLA',
            python=sys.version,sqlite=sqlite3.sqlite_version,platform=platform.platform(),hash_seed=os.environ.get('PYTHONHASHSEED'),
            runtime_module=r.__file__,profiler_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),binaries=binaries,
            host_before=host_before,host_after=host_snapshot(),epochs=[dict(phase=e.phase,seconds=e.seconds,g0_seconds=e.g0_seconds,closed=e.closed,finished=e.finished_normally) for e in epochs],
            phase_intervals=phases,coarse=[dict(epoch=k[0][0],phase=k[0][1],function=k[1],**v) for k,v in rows.items()],
            counts=[dict(epoch=k[0],phase=k[1],**v) for k,v in counts.items()],selections=selections,absent_timing_targets=absent,
            shapes=shape_rows,shape_metadata_read_ns=shape_ns,effective_candidate_transfers=transfers,
            diagnostic_binary_sha256=hashlib.sha256(diagpath.read_bytes()).hexdigest(),diagnostic_source_sha256=hashlib.sha256(diagnostic_source.read_bytes()).hexdigest(),production_graph_source_sha256=hashlib.sha256(Path(r.__file__).with_name('_cold_graph_structure.c').read_bytes()).hexdigest(),
            outside_lease_source_qualification_batches=batch,errors=errors,open_timed_stack=len(stack),
            limits='Same profiler both frozen exports, no data/callee/clock/SQL edits; hot calls count-only, no active_epochs scan. Wall/threadCPU include observer overhead. Coarse exclusives subtract only other timed coarse children. Count-only function costs not individually timed. Batch outside leases, not whole-flow extrapolation; real UUIDs and clocks, not byte-identical datasets.')
        (item.funcargs['tmp_path']/'use-effective-profile.json').write_text(json.dumps(report,indent=2)+'\n')
