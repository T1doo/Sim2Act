"""Controlled process-identity refusals; never starts or stops a database."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sim2act.private_postgres import PrivatePostgres, verify_process
from sim2act.desktop_protocol import ProtocolError

identity=dict(pid=12345,created=123.5,executable=str(Path('owned/postgres.exe').resolve()),
              data_dir=str(Path('owned/data').resolve()),port=55432)
verify_process(identity,**identity)
checks=['exact observed ownership accepted']
for key,value in [('pid',54321),('created',124.0),('executable',str(Path('other/postgres.exe').resolve())),
                  ('data_dir',str(Path('other/data').resolve())),('port',5432)]:
    changed={**identity,key:value}
    controlled=PrivatePostgres.__new__(PrivatePostgres)
    controlled.identity=identity
    controlled._observed=lambda:changed
    called=[]
    controlled._command=lambda *args:called.append(args)
    try:controlled.stop()
    except ProtocolError:pass
    else:raise AssertionError('Mismatch accepted: '+key)
    assert not called
    checks.append(key+' mismatch refuses before issuing stop')
controlled=PrivatePostgres.__new__(PrivatePostgres)
controlled.identity=None
try:controlled.stop()
except ProtocolError:checks.append('unowned controller cannot stop a database')
else:raise AssertionError('Unowned stop accepted')
print({'status':'PASS','checks':checks,'scope':'controlled identity guards only; real PG lifecycle NOT_RUN'})
