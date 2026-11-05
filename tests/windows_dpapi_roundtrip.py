"""Actual Windows user DPAPI with synthetic values only; no real credentials."""
import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sim2act.windows_credentials import write_dpapi,read_dpapi
from sim2act.desktop_protocol import ProtocolError
checks=[]
with tempfile.TemporaryDirectory(prefix='sim2act-dpapi-test-') as folder:
    file=Path(folder)/'synthetic.dpapi'
    value='SYNTHETIC-ONLY-中文-credential'
    write_dpapi(file,value)
    assert read_dpapi(file)==value and value.encode() not in file.read_bytes()
    checks.append('current-user encrypted roundtrip preserves Unicode')
    before=file.read_bytes()
    try:write_dpapi(file,'replacement')
    except ProtocolError:pass
    else:raise AssertionError('Existing credential replaced')
    assert file.read_bytes()==before and read_dpapi(file)==value
    checks.append('existing credential remains byte-identical on replacement attempt')
    corrupt=Path(folder)/'corrupt.dpapi';corrupt.write_text('00112233')
    try:read_dpapi(corrupt)
    except ProtocolError:checks.append('corrupt ciphertext rejected')
    else:raise AssertionError('Corrupt credential accepted')
print({'status':'PASS','checks':checks,'scope':'synthetic Windows DPAPI files, no UI or database'})
