"""Controlled shutdown-order/deadline checks; no database or child is spawned."""
import io,json,sys,tempfile,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sim2act.desktop_protocol import Supervisor,TEST_ONLY

checks=[]
with tempfile.TemporaryDirectory() as folder:
    for case in ('success','failure','timeout','undrained'):
        output=io.StringIO();calls=[];release=threading.Event()
        def cleanup(remaining):
            calls.append(remaining)
            if case=='timeout':release.wait(1)
            return case=='success'
        service=Supervisor(Path(folder)/case,TEST_ONLY,'a'*64,lambda *args:[],{},
            stop_seconds=.08,input_stream=io.StringIO(),output_stream=output,owned_cleanup=cleanup)
        service.root.mkdir();service.claim=service.claim_file.open('x+b');service._write_claim()
        if case=='undrained':service._drained=lambda:False
        service._shutdown()
        receipt=json.loads(output.getvalue().splitlines()[-1])
        release.set()
        if case=='success':
            assert receipt['clean'] and not service.claim_file.exists() and len(calls)==1
            checks.append('dependency success precedes clean receipt and claim release')
        else:
            assert not receipt['clean'] and service.claim_file.exists()
            if case=='undrained':assert not calls
            checks.append(case+' preserves claim and refuses clean receipt')
print({'status':'PASS','checks':checks,'scope':'controlled Supervisor cleanup cases only'})
