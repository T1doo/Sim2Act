import ast
import hashlib
import json
from pathlib import Path
import sqlite3

root=Path('/workspace/csv-full-report-instances-evidence-20261017/backend-negative')
out=Path('/tmp/csv-full-report-negative-sql-observer-20261017')
report=[]
for path in sorted(root.glob('test_current_source_effect_and*/actual-complete-report-negative.json')):
    if path.parent.name not in {f'test_current_source_effect_and{i}' for i in range(3)}:
        continue
    evidence=json.loads(path.read_text())
    denied=evidence.get('denied_private_body_reads',[])
    database=path.parent/'fixture.db'
    connection=sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=1)
    connection.execute('PRAGMA query_only=ON')
    queries=[]
    for item in denied:
        values=ast.literal_eval(item['parameters'])
        assert isinstance(values,tuple) and len(values)==4 and all(isinstance(value,str) for value in values)
        count=connection.execute('SELECT COUNT(*) FROM delivery_graph_requests WHERE app_id=? AND principal_id=? AND kind=? AND request_key=?',values).fetchone()[0]
        queries.append(dict(sql=item['sql'],parameters=list(values),exact_existing_rows=count))
    connection.close()
    assert denied and all(row['parameters'][2] in ('pa_spec_run_scope','pa_spec_run_scope_seal') and row['parameters'][3]=='accepted' and row['exact_existing_rows']==0 for row in queries)
    report.append(dict(original_evidence=str(path),evidence_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),database=str(database),recorded_denied_full_selects=len(denied),queries=queries,readonly_http={name:dict(status=evidence[name]['status'],database_unchanged=evidence[name]['database_before']==evidence[name]['database_after']) for name in ('delivery','approval','run','original_key','confirm')}))
(out/'raw-analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps([dict(evidence=entry['original_evidence'],denied_full_selects=entry['recorded_denied_full_selects'],exact_counts=[row['exact_existing_rows'] for row in entry['queries']],readonly_http=entry['readonly_http']) for entry in report],ensure_ascii=False))
