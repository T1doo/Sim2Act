import hashlib,json,sys,time,gc
from pathlib import Path
import test_cold_snapshot_full_flow
from sim2act import _cold_source_packet as source
assert source.available()
source.current()
paths=['_cold_source_owned_impl.c','_cold_source_live_match.h','_cold_source_code.h','_cold_source_view.h','_cold_source_shape.h']
root=Path(source.__file__).parent
expected=hashlib.sha256(b''.join((root/n).read_bytes() for n in paths)).hexdigest()
assert source.native.SOURCE_SHA256==expected
batches=[]
for _ in range(400):source.current()
for _ in range(7):
 a=time.perf_counter_ns();b=time.process_time_ns()
 for _ in range(3000):source.current()
 batches.append(dict(calls=3000,wall_ns=time.perf_counter_ns()-a,process_ns=time.process_time_ns()-b))
print(json.dumps(dict(source_module=source.__file__,binary=str(source.native.__file__),binary_sha256=hashlib.sha256(Path(source.native.__file__).read_bytes()).hexdigest(),native_source_sha256=expected,gc_enabled=gc.isenabled(),batches=batches)))
