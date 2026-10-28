import cProfile,pstats,time,hashlib,io,json
from pathlib import Path
import pytest
@pytest.fixture(autouse=True)
def diagnostic(monkeypatch):
 from cold_semantic_clock import SemanticClock
 from sim2act import natural_spec_runtime as r
 SemanticClock(monkeypatch)
 original=r._cold_graph_bytes
 def encoded(values):
  data=original(values)
  if len(data)>400000:
   prof=cProfile.Profile();prof.enable()
   for _ in range(40):original(values)
   prof.disable();out=io.StringIO();pstats.Stats(prof,stream=out).sort_stats('tottime').print_stats(25)
   timings={}
   for name,fn in [('sha256',lambda:hashlib.sha256(data).hexdigest()),('blake2b',lambda:hashlib.blake2b(data,digest_size=32).hexdigest())]:
    start=time.perf_counter()
    for _ in range(100):fn()
    timings[name]=time.perf_counter()-start
   def chunkhash():
    h=hashlib.sha256();v=memoryview(data)
    for i in range(0,len(data),2047):h.update(v[i:i+2047])
    return h.hexdigest()
   assert chunkhash()==hashlib.sha256(data).hexdigest()
   start=time.perf_counter()
   for _ in range(100):chunkhash()
   timings['sha256_chunk']=time.perf_counter()-start
   Path('/workspace/scratch/codec-benchmark.txt').write_text('bytes='+str(len(data))+' '+json.dumps(timings)+'\n'+out.getvalue())
   raise KeyboardInterrupt('OWNED DIAGNOSTIC STOP after codec measurement; not acceptance')
  return data
 monkeypatch.setattr(r,'_cold_graph_bytes',encoded)
