"""Diagnostic only: virtual business clock, passive owner stack samples."""
import json, sys, threading, time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
import pytest

@pytest.fixture(autouse=True)
def diagnostic_clock(monkeypatch):
    from cold_semantic_clock import SemanticClock
    from sim2act import natural_spec_runtime as runtime
    clock = SemanticClock(monkeypatch)
    owner = threading.get_ident()
    finished = threading.Event()
    state = {'phase': None}
    samples = Counter()
    records = []
    def sample():
        while not finished.wait(.005):
            phase = state['phase']
            if phase:
                frame = sys._current_frames().get(owner)
                stack = []
                while frame:
                    if '/src/sim2act/' in frame.f_code.co_filename:
                        stack.append((frame.f_code.co_filename.rsplit('/',1)[-1], frame.f_code.co_name, frame.f_lineno))
                    frame = frame.f_back
                samples[(phase, tuple(stack))] += 1
    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    for name, phase in [('_cold_model_before','G0'),('_model_settlement_read','G1')]:
        original = getattr(runtime,name)
        @contextmanager
        def observed(*args, original=original, phase=phase, **kwargs):
            begin=time.monotonic(); state['phase']=phase
            rec={'phase':phase,'completed':False}
            try:
                with original(*args,**kwargs) as value:
                    yield value
                rec['completed']=True
            finally:
                state['phase']=None
                rec['wall_seconds']=time.monotonic()-begin
                records.append(rec)
        monkeypatch.setattr(runtime,name,observed)
    try:
        yield
    finally:
        finished.set();thread.join(2)
        Path('/workspace/scratch/settlement-sampling.json').write_text(json.dumps({'classification':'DIAGNOSTIC_VIRTUAL_BUSINESS_CLOCK_NOT_ACCEPTANCE','records':records,'samples':[{'phase':k[0],'stack':k[1],'count':v} for k,v in samples.most_common()]},indent=2))
