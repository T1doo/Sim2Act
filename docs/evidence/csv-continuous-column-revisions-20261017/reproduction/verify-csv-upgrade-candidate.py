import hashlib,io,json,sqlite3,subprocess,tarfile,xml.etree.ElementTree as ET
from pathlib import Path
repo=Path('/workspace/Sim2Act');out=Path('/workspace/csv-continuous-column-evidence-20261017/author-upgrade-candidate');before=json.loads((out/'inputs-before.json').read_text());root=Path(before['snapshot']);sha='b589809375c89b4d93617d91c780a1e0f7f704e2'
after={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in before['files']};assert after==before['files']
(out/'inputs-after.json').write_text(json.dumps(dict(verified_git_sha=sha,files=after),indent=2))
blob=subprocess.check_output(['git','archive',sha,'src','tests','schemas','pyproject.toml','docs/evidence/bounded-agent-offline-20261006','docs/evidence/model-protocol-preparation-20261006/materials','docs/evidence/protocol-store-loop-20261006/evaluation'],cwd=repo)
with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
 expected={m.name:hashlib.sha256(tar.extractfile(m).read()).hexdigest() for m in tar.getmembers() if m.isfile()}
assert all(expected[p]==h for p,h in after.items())
assert set(expected)-set(after)=={'tests/test_csv_derive_receipt.py'}
node=Path('/tmp/csv-continuous-upgrade-page-data-20261017/test_visible_current_effective0')
if not node.exists():
 candidates=list(Path('/tmp/csv-continuous-upgrade-page-data-20261017').glob('test_*/page-result.json'));assert len(candidates)==1;node=candidates[0].parent
page=json.loads((node/'page-result.json').read_text());assert page['status']=='PASS'
requests=page['requests'];derive=[r for r in requests if r['method']=='POST' and r['path'].endswith('/delivery-graph/derive')];assert len(derive)==1 and derive[0]['status']==201 and derive[0]['delivery']=='ACTUAL_DERIVE_201_LOST'
recover=[r for r in requests if r['method']=='GET' and r['path'].endswith('/derive-requests/'+derive[0]['body']['request_key'])];assert len(recover)==1 and recover[0]['status']==200
pending=[r for r in requests if r['method']=='GET' and r['path'].endswith('/csv-owner-review')];assert pending[-1]['status']==200 and pending[-1]['response']['owner_acceptance']=='PENDING'
with sqlite3.connect((node/'fixture.db').as_uri()+'?mode=ro&immutable=1',uri=True) as c:
 attempts=c.execute('select count(*) from attempts').fetchone()[0];assert attempts==0
 runs=c.execute('select status,count(*) from runs group by status').fetchall();assert runs==[('SUCCEEDED',5)]
 cases=list(ET.parse(out/'junit.xml').iter('testcase'));assert len(cases)==1 and not cases[0].findall('failure') and not cases[0].findall('error') and not cases[0].findall('skipped')
report=dict(status='PASS_BOUNDED',verified_git_sha=sha,candidate_origin='d74 exact Git plus four recorded overlays, all selected inputs later byte-matched to b589 Git',input_count=len(after),inputs_unchanged=True,all_input_bytes_equal_git=True,git_extra_unexecuted_test_files=['tests/test_csv_derive_receipt.py'],unique_cases=1,passes=1,failures=0,skips=0,seconds=cases[0].attrib['time'],page_checks=len(page['checks']),actual_page_requests=len(requests),static_assets=len(page['assets']),expected_http_errors=[dict(path=r['path'],status=r['status']) for r in requests if r['status']>=400],model_attempts=attempts,run_statuses=runs,derive_posts=1,exact_derive_recovery_gets=1,full_database_path=str(node/'fixture.db'),limitation='Synthetic prior software registry; not actual ce3 binary upgrade. No real model, PG, Windows, native browser, remote CI or deployment.')
(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
