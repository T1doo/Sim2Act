"""Offline archive boundary tests; synthetic bytes are never executed."""
import hashlib
import importlib.util
import tempfile
import zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stage',root/'scripts/package_private_postgres.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
checks=[]
with tempfile.TemporaryDirectory() as folder:
    base=Path(folder)
    for case in ('good','traversal','duplicate','missing'):
        archive=base/(case+'.zip')
        with zipfile.ZipFile(archive,'w') as bundle:
            for name in ('postgres','pg_ctl','initdb','psql','pg_isready'):
                if case=='missing' and name=='initdb':continue
                bundle.writestr('pgsql/bin/'+name+'.exe',b'synthetic-not-executable')
            bundle.writestr('pgsql/COPYRIGHT',b'synthetic notice')
            bundle.writestr('pgsql/pgAdmin4/unneeded.txt',b'excluded')
            if case=='traversal':bundle.writestr('pgsql/bin/../../escape',b'no')
            if case=='duplicate':bundle.writestr('pgsql/bin/POSTGRES.exe',b'no')
        digest=hashlib.sha256(archive.read_bytes()).hexdigest()
        output=base/case
        try:report=module.stage(archive,digest,output)
        except ValueError:
            assert case!='good' and not output.exists()
            checks.append(case+' rejected before writing')
        else:
            assert case=='good' and not (output/'pgsql/pgAdmin4').exists()
            assert not report['service_installed'] and not report['data_initialized']
            checks.append('required runtime and notices staged without service/data or pgAdmin')
    try:module.stage(base/'good.zip','0'*64,base/'bad-digest')
    except ValueError:checks.append('wrong digest rejected')
    else:raise AssertionError('wrong digest accepted')
print({'status':'PASS','checks':checks,'scope':'offline synthetic archives only'})
