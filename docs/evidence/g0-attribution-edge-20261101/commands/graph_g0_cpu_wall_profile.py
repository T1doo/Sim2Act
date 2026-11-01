"""Read-only real-clock coarse/fresh-code profile of the original Cold tests.

No data, core callee, clock, query or deadline is replaced. Times include the
same observer overhead in both frozen comparisons; not an uninstrumented SLA.
"""
import hashlib,json,os,platform,sys,threading,time,types
from pathlib import Path
import pytest
from sqlalchemy import event

@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    names=('test_original_thirty_large_goal_or_safe_budget_refusal',
           'test_same_large_cold_snapshot_control[complete]')
    if item.name not in names:
        yield;return
    from sim2act import natural_spec_runtime as rt,natural_live_admission as typed
    from sim2act import _cold_graph_versions as versions,_cold_source_packet as source
    from sim2act import _cold_graph_structure_guard as structural,_sqlite_run_control as control
    from sim2act import _sqlite_model_snapshot as snapshot,model_settlement as settlement
    from sim2act import _cold_accounted_native as accounted,pa_spec_apps as spec
    from sqlalchemy.engine import Connection
    profile_path=item.funcargs['tmp_path']/'graph-g0-cpu-wall-profile.json'
    timed=[(rt._ColdTrialGraph._prepare,'trial.prepare'),(rt._ColdTrialGraph.commit,'trial.commit'),
        (rt._ColdGraphRead.check,'graph.check'),(rt._ColdGraphRead._check_dynamic,'graph.dynamic'),
        (rt._ColdGraphRead.content_version,'graph.version'),(rt._ColdGraphRead._content_matches,'graph.fallback'),
        (rt._ColdGraphRead.input_bytes,'graph.input_bytes'),(rt._cold_graph_bytes,'graph.encode'),
        (versions.current,'version.current'),(versions._code,'version.code'),(versions._scope,'version.scope'),
        (source.current,'source.code'),(structural.select,'selector.graph'),(structural.select_frontier,'selector.frontier'),
        (rt._ModelSettlementRead.check,'proof.check'),(rt._cold_binding_limits_facet,'binding'),
        (spec._cold_receipts,'receipts'),(snapshot._Read.promote,'writer.promote'),(Connection.commit,'sql.commit')]
    from sim2act import _cold_typed_stream as stream,natural_source_archives as archive
    timed.extend((getattr(rt._ColdTrialGraph,n),'trial.'+n) for n in (
        '_base','_typed_parameter_models','_typed_values_from_models','_check_links','check'))
    timed.extend([(typed._trial_typed_values,'typed.values'),
        (typed._trial_typed_storage,'typed.storage'),(typed._trial_typed_equal,'typed.equal'),
        (stream._stream_values,'typed.stream'),(rt._graph_run_context,'run.context'),
        (archive._graph_resolve_trial_source,'source.resolve'),
        (typed._graph_trial_stage_parent_pin,'stage.parent')])
    codes={fn.__code__:label for fn,label in timed}
    for code in typed._trial_typed_guard.__code__.co_consts:
        if type(code) is types.CodeType and code.co_name=='checked':codes[code]='typed.guard'
    caller_codes={rt._ColdGraphRead.check.__code__,rt._ColdGraphRead.input_bytes.__code__,
        rt._ColdTrialGraph._base.__code__,typed._trial_typed_values.__code__,
        typed._trial_typed_storage.__code__,rt._cold_graph_bytes.__code__}
    callers={}
    epoch_cpu={}
    ctor=control.Epoch.__init__.__code__;post=control.Epoch.postwrite.__code__
    close=control.Registry.settlement.__wrapped__.__code__;checkpoint=settlement.checkpoint.__code__
    postproof=rt._model_settlement_read.__wrapped__.__code__
    commit_code=rt._ColdTrialGraph.commit.__code__;graph_ctor=rt._ColdGraphRead.__init__.__code__
    monitor=sys.monitoring;slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
    epochs=[];active=None;thread=None;stack=[];aggregates={};bounds={};exceptions=[];errors=[];sql={};attached=[];counts={}
    native_codes={versions.current.__code__,versions._code.__code__,versions._scope.__code__,source.current.__code__,rt._ColdGraphRead.content_version.__code__}
    native_codes.add(rt._ColdGraphRead.check.__code__)
    native_codes.update((structural.select.__code__,structural.select_frontier.__code__,structural._qualified.__code__,structural._fixed_classes.__code__))
    native_entries={value:'native.'+name for name,value in versions._ENTRIES}
    native_entries[structural._NATIVE_MATCH]='native.full_match'
    native_entries[structural._NATIVE_SNAPSHOT]='native.full_capture'
    native_entries[structural._NATIVE_CLASSES]='native.class_config'
    if source.native is not None:native_entries[source.native.verify_code]='native.verify_code'
    def row():return bounds[len(epochs)]
    def enabled():return active is not None and not active.closed and threading.get_ident()==thread
    def aggregate(key,name,elapsed,child,cpu=0,cpu_child=0):
        d=aggregates.setdefault((key,name),dict(calls=0,inclusive_ns=0,exclusive_among_targets_ns=0,inclusive_cpu_ns=0,exclusive_among_targets_cpu_ns=0))
        d['calls']+=1;d['inclusive_ns']+=elapsed;d['exclusive_among_targets_ns']+=elapsed-child
        d['inclusive_cpu_ns']+=cpu;d['exclusive_among_targets_cpu_ns']+=cpu-cpu_child
    def push(token,name):
        if enabled():stack.append([token,name,(len(epochs),active.phase),time.monotonic_ns(),0,time.thread_time_ns(),0])
    def pop(token):
        if stack and stack[-1][0]==token:
            _,name,key,start,child,cpu_start,cpu_child=stack.pop();cpu=time.thread_time_ns()-cpu_start;elapsed=time.monotonic_ns()-start
            aggregate(key,name,elapsed,child,cpu,cpu_child)
            if stack:stack[-1][4]+=elapsed;stack[-1][6]+=cpu
    def before(c,cursor,statement,parameters,context,many):
        if not enabled():return
        verb=statement.lstrip().split(None,1)[0].upper() if statement.strip() else ''
        sql[id(context)]=(len(epochs),active.phase,verb,time.monotonic_ns(),time.thread_time_ns())
        if verb in ('INSERT','UPDATE','DELETE'):
            row().setdefault('first_dml_attempt_mono',time.monotonic())
            row().setdefault('first_dml_verb',verb)
    def after(c,cursor,statement,parameters,context,many):
        old=sql.pop(id(context),None)
        if old:
            aggregate((old[0],old[1]),'sql.'+old[2],time.monotonic_ns()-old[3],0,time.thread_time_ns()-old[4],0)
            if old[2] in ('INSERT','UPDATE','DELETE'):
                bounds[old[0]].setdefault('first_dml_completed_mono',time.monotonic())
                bounds[old[0]].setdefault('first_dml_rowcount',cursor.rowcount)
    def sql_error(context):sql.pop(id(context.execution_context),None)
    def start(code,offset):
        try:
            if code is postproof and enabled():row().setdefault('postproof_entered_mono',time.monotonic())
            if code is snapshot._Read.promote.__code__ and enabled():row().setdefault('promotion_started_mono',time.monotonic())
            if code is Connection.commit.__code__ and enabled():row().setdefault('commit_started_mono',time.monotonic())
            if code in caller_codes and enabled():
                f=sys._getframe(1);parent=f.f_back
                if parent is not None:
                    pc=parent.f_code
                    key=(len(epochs),active.phase,codes[code],Path(pc.co_filename).name,pc.co_qualname,pc.co_firstlineno)
                    callers[key]=callers.get(key,0)+1
                del parent,f
            if code in codes:push(code,codes[code])
        except Exception as e:errors.append('start:'+type(e).__name__)
    def end(code,offset,value=None,unwound=False,frame=None):
        nonlocal active,thread
        try:
            frame=sys._getframe(1) if frame is None else frame
            if code is ctor:
                epoch=frame.f_locals['self']
                if not epoch.worker.store._local_model_snapshots:return
                active=epoch;thread=threading.get_ident();epochs.append(epoch);epoch_cpu[len(epochs)]=dict(start_cpu_ns=time.thread_time_ns())
                bounds[len(epochs)]=dict(start_mono=epoch.started,start_wall=time.time(),run_id=epoch.header['id'],g1_phase_entered=False,g1_postproof_entered=False)
                engine=epoch.worker.store.engine
                if not any(old[0] is engine for old in attached):
                    for name,fn in [('before_cursor_execute',before),('after_cursor_execute',after),('handle_error',sql_error)]:
                        event.listen(engine,name,fn);attached.append((engine,name,fn))
                return
            if active is None or threading.get_ident()!=thread:return
            if code is post and frame.f_locals.get('self') is active:
                row()['g1_phase_entered']=True;row()['postwrite_mono']=time.monotonic()
            if code is close and frame.f_locals.get('epoch') is active and active.closed:
                epoch_cpu[len(epochs)]['end_cpu_ns']=time.thread_time_ns();row()['end_mono']=time.monotonic();row()['g1_postproof_entered']='postproof_entered_mono' in row();active=None
            if code is snapshot._Read.promote.__code__ and enabled() and not unwound:row()['promotion_completed_mono']=time.monotonic()
            if code is Connection.commit.__code__ and enabled() and not unwound:row()['commit_completed_mono']=time.monotonic()
            if code is graph_ctor and enabled() and not unwound:
                graph=frame.f_locals['self'];row().setdefault('graph_phases',[]).append(graph.phase)
            if code is rt._cold_graph_bytes.__code__ and enabled():
                d=counts.setdefault((len(epochs),active.phase),dict(encoding_calls=0,encoded_bytes=0,projection_returns=0))
                d['encoding_calls']+=1
                if type(value) is bytes:d['encoded_bytes']+=len(value)
            if code is rt._ColdGraphRead.input_bytes.__code__ and enabled() and type(value) is dict:
                counts.setdefault((len(epochs),active.phase),dict(encoding_calls=0,encoded_bytes=0,projection_returns=0))['projection_returns']+=1
            if code in codes:pop(code)
        except Exception as e:errors.append('end:'+type(e).__name__)
    def unwind(code,offset,exc):
        if code in codes or code is close:end(code,offset,None,True,sys._getframe(1))
    def raised(code,offset,error):
        try:
            if code is not checkpoint or not enabled() or type(error) is not settlement.DomainError:return
            f=sys._getframe(1);frames=[];boundary=None
            while f is not None and len(frames)<24:
                frames.append(dict(file=Path(f.f_code.co_filename).name,method=f.f_code.co_qualname,line=f.f_lineno))
                if f.f_code is commit_code:
                    prefix=f.f_locals.get('prefix');boundary=getattr(prefix,'key',None)
                f=f.f_back
            worker=sys._getframe(1).f_locals.get('worker');token=vars(worker).get('_settlement_interval')
            now_mono,now_wall=time.monotonic(),time.time()
            exceptions.append(dict(epoch=len(epochs),phase=active.phase,error=error.public(),boundary=boundary,
                mono=now_mono,wall=now_wall,interval=list(token) if type(token) is tuple else None,
                observed_mono_expired=type(token) is tuple and now_mono>=token[0],observed_wall_expired=type(token) is tuple and now_wall>=token[1],
                first_dml_attempted='first_dml_attempt_mono' in row(),first_dml_completed='first_dml_completed_mono' in row(),
                postproof_entered='postproof_entered_mono' in row(),stack=frames))
        except Exception as e:errors.append('raise:'+type(e).__name__)
    def call(code,offset,callee,arg0):
        try:
            name=native_entries.get(callee)
            if name:push((code,offset),name)
        except Exception as e:errors.append('native-call:'+type(e).__name__)
    def cret(code,offset,callee,arg0):
        try:
            if callee in native_entries:pop((code,offset))
        except Exception as e:errors.append('native-return:'+type(e).__name__)
    monitor.use_tool_id(slot,'Graph immutable versions real-clock bounded observation')
    events={code:monitor.events.PY_START|monitor.events.PY_RETURN for code in codes}
    for code in (ctor,post,close,graph_ctor):events[code]=events.get(code,0)|monitor.events.PY_RETURN
    events[postproof]=events.get(postproof,0)|monitor.events.PY_START
    for code in native_codes:events[code]=events.get(code,0)|monitor.events.CALL
    try:
        monitor.register_callback(slot,monitor.events.PY_START,start);monitor.register_callback(slot,monitor.events.PY_RETURN,end)
        monitor.register_callback(slot,monitor.events.PY_UNWIND,unwind);monitor.register_callback(slot,monitor.events.RAISE,raised)
        monitor.register_callback(slot,monitor.events.CALL,call);monitor.register_callback(slot,monitor.events.C_RETURN,cret);monitor.register_callback(slot,monitor.events.C_RAISE,cret)
        for code,mask in events.items():monitor.set_local_events(slot,code,mask)
        monitor.set_events(slot,monitor.events.PY_UNWIND|monitor.events.RAISE)
        yield
    finally:
        monitor.set_events(slot,0)
        for code in events:monitor.set_local_events(slot,code,0)
        for kind in (monitor.events.PY_START,monitor.events.PY_RETURN,monitor.events.PY_UNWIND,monitor.events.RAISE,monitor.events.CALL,monitor.events.C_RETURN,monitor.events.C_RAISE):monitor.register_callback(slot,kind,None)
        monitor.free_tool_id(slot)
        for engine,name,fn in attached:event.remove(engine,name,fn)
        report=dict(classification='REAL_WALL_CLOCK_ORIGINAL_COLD_FIXED_MOCK_FILE_SQLITE_OBSERVER_INCLUDED_NOT_LIVE_NOT_PG',
            test_nodeid=item.nodeid,case=item.name,observer_probe=Path(item.module.__file__).name=='test_graph_clock_observer_probe.py',python=sys.version,platform=platform.platform(),loadavg=os.getloadavg(),affinity=sorted(os.sched_getaffinity(0)),
            observer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            epochs=[dict(ordinal=i+1,seconds=e.seconds,g0_seconds=e.g0_seconds,finished=e.finished_normally,closed=e.closed,final_phase=e.phase,**bounds.get(i+1,{})) for i,e in enumerate(epochs)],
            timed=[dict(epoch=k[0][0],phase=k[0][1],function=k[1],**v) for k,v in aggregates.items()],
            cpu_epochs=epoch_cpu,caller_counts=[dict(epoch=k[0],phase=k[1],function=k[2],caller_file=k[3],caller=k[4],caller_line=k[5],calls=v) for k,v in callers.items()],
            counts=[dict(epoch=k[0],phase=k[1],**v) for k,v in counts.items()],budget_failures=exceptions,errors=errors,pending_frames=len(stack),pending_sql=len(sql),
            limits='THREAD_CPU_AND_WALL_TARGETED_ORIGINAL30; includes added observer overhead; cutoff workload may differ from lighter observers. No uninstrumented SLA or eliminable-share claim. Times include observation; nested inclusive overlap. Only tracked children subtracted. G1 phase begins before writer admission; postproof separately marks actual post-write G1. First DML attempt/return bound real SQLite lock acquisition, not an exact instant. Exception samples do not uniquely infer checkpoint short-circuit branch.')
        profile_path.write_text(json.dumps(report,indent=2)+'\n')
