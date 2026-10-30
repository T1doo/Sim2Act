"""Bounded WAL lifecycle checks on private copies of the completed synthetic DB.

Usage: python diagnose.py COMPLETED_CASE_DIR NEW_PRIVATE_OUTPUT_DIR
The supplied original database/proof are never opened for writing or changed.
"""
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

source=Path(sys.argv[1]).resolve()
output=Path(sys.argv[2]).resolve()
output.mkdir(exist_ok=False)
evidence=Path(__file__).resolve().parent.parent/'pb-use-response-first-producer-20261030'
original=evidence/'check-reopen-original.py'
fixed=evidence/'check-reopen.py'

def state(root):
    result={}
    for suffix in ('','-wal'):
        path=root/('fixture.db'+suffix)
        data=path.read_bytes() if path.exists() else None
        result[suffix or 'main']=dict(exists=data is not None,
            size=None if data is None else len(data),
            sha256=None if data is None else hashlib.sha256(data).hexdigest())
    return result

def clone(name):
    case=output/name
    case.mkdir()
    shutil.copy2(source/'fixture.db',case/'fixture.db')
    shutil.copy2(source/'pb-controller-proof.json',case/'pb-controller-proof.json')
    return case

def invoke(checker,case,*,tamper=False):
    command=[sys.executable,str(checker),str(case),str(case/'reopen.json')]
    if tamper:
        # Only this disposable copy: mutate the WAL after business reads close.
        # The checker must reject a changed nonempty file, not normalize it.
        program="""
import sys,runpy
from pathlib import Path
checker,case,out=sys.argv[1:]
line=next(i for i,s in enumerate(Path(checker).read_text().splitlines(),1)
    if s.startswith('wal_after=wal_state'))
def trace(frame,event,arg):
    if event=='line' and frame.f_code.co_filename==checker and frame.f_lineno==line:
        with Path(case,'fixture.db-wal').open('ab') as f:f.write(b'SYNTHETIC_CHANGED_WAL')
    return trace
sys.argv=[checker,case,out]
sys.settrace(trace)
runpy.run_path(checker,run_name='__main__')
"""
        command=[sys.executable,'-c',program,*command[1:]]
    result=subprocess.run(command,capture_output=True,text=True,timeout=15)
    (case/'checker.stderr').write_text(result.stderr)
    return result

before_original=state(source)
assert before_original['-wal']['size'] in (None,0), 'Original WAL has frames: do not copy main alone'
rows=[]
for index in range(3):
    for name,checker,expected in [('old',original,1),('fixed',fixed,0)]:
        case=clone(f'{name}-{index}');before=state(case)
        result=invoke(checker,case);after=state(case)
        assert result.returncode==expected,result.stderr
        assert before['main']==after['main']==before_original['main']
        assert not before['-wal']['exists'] and after['-wal']['size']==0
        if name=='old':assert 'assert wal_after==wal_before' in result.stderr
        else:
            proof=json.loads((case/'reopen.json').read_text())
            assert proof['database_content_unchanged'] and proof['empty_wal_lifecycle_transition']
            assert proof['physical_main_and_wal_identity'] is False
        rows.append(dict(case=case.name,returncode=result.returncode,before=before,after=after))

case=clone('nonempty-real-committed-wal')
writer=sqlite3.connect(case/'fixture.db')
try:
    assert writer.execute('PRAGMA journal_mode').fetchone()[0]=='wal'
    writer.execute('PRAGMA wal_autocheckpoint=0')
    writer.execute('CREATE TABLE reopen_probe(value INTEGER)')
    writer.execute('INSERT INTO reopen_probe VALUES(2)');writer.commit()
    before=state(case);assert before['-wal']['size']>32
    result=invoke(fixed,case);after=state(case)
    assert result.returncode==0,result.stderr
    assert before==after
    # Independently compute every table from the actual committed WAL view.
    digest=hashlib.sha256()
    for table, in writer.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
        data=writer.execute('SELECT * FROM "'+table.replace('"','""')+'" ORDER BY rowid').fetchall()
        digest.update(json.dumps([table,data],ensure_ascii=True,separators=(',',':')).encode())
    assert json.loads((case/'reopen.json').read_text())['logical_database_sha256']==digest.hexdigest()
    rows.append(dict(case=case.name,returncode=0,before=before,after=after,committed_wal_read=True))
finally:writer.close()

case=clone('changed-wal-after-read');before=state(case)
result=invoke(fixed,case,tamper=True);after=state(case)
assert result.returncode==1 and 'WAL content changed during read-only verification' in result.stderr
assert before['main']==after['main'] and after['-wal']['size']>0
assert not (case/'reopen.json').exists()
rows.append(dict(case=case.name,returncode=1,before=before,after=after,changed_nonempty_wal_rejected=True))
assert state(source)==before_original
record=dict(status='PASS',classification='ACTUAL_COMPLETED_SYNTHETIC_DB_COPIES_REAL_SQLITE_NO_MODEL_CALLS',
    original_unchanged=True,cases=rows,
    checker_sha256=hashlib.sha256(fixed.read_bytes()).hexdigest(),
    original_checker_sha256=hashlib.sha256(original.read_bytes()).hexdigest())
(output/'result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(status=record['status'],cases=len(rows),original_unchanged=True,
    reproduced_old_absent_empty_failure=3,fresh_reopen_fixed=3,
    nonempty_committed_wal_read=True,changed_nonempty_wal_rejected=True)))
