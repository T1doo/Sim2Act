from pathlib import Path
import ast,gzip,hashlib,json,os,re,sqlite3,subprocess,tempfile
roots=['docs/evidence/cloud-fresh-encoding-20261028','docs/evidence/cloud-core-20261028','docs/evidence/cloud-settlement-20261028','docs/evidence/cloud-mapping-20261028']
constants=set()
for p in (*Path('tests').rglob('*.py'),*Path('src/sim2act').glob('*.py')):
 try:
  constants.update(n.value for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,ast.Constant) and isinstance(n.value,str))
 except (ValueError,UnicodeError):pass
materials=set(constants)
for p in Path('tests/fixtures').rglob('*'):
 if p.is_file():
  try:materials.add(p.read_text())
  except UnicodeError:pass
secrets=[v.encode() for k,v in os.environ.items() if re.search(r'(?:TOKEN|PASSWORD|SECRET|API_KEY)$',k,re.I) and len(v)>8]
known={None}|{hashlib.sha256(v.encode()).hexdigest() for v in ('synthetic-test-A','synthetic-test-B')}
rows=[];findings=[]
for name in subprocess.check_output(['git','ls-files',*roots],text=True).splitlines():
 p=Path(name);raw=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
 if any(v in raw for v in secrets):findings.append(dict(path=name,type='configured secret match'))
 if not raw.startswith(b'SQLite format 3'):continue
 with tempfile.NamedTemporaryFile(dir='/workspace/scratch') as f:
  f.write(raw);f.flush();c=sqlite3.connect('file:'+f.name+'?mode=ro',uri=True)
  principals=list(c.execute('select name,token_hash from principals'))
  principal_ok=all(n in constants and h in known for n,h in principals)
  exact=derived=unknown=0
  for content, in c.execute('select content from resources'):
   if content in materials:exact+=1;continue
   try:
    value=json.loads(content)
    assert type(value) is dict and value['source_content'] in materials
    source=value['source_content'];assert all(cite['quote']==source[cite['start']:cite['end']] for item in value['items'] for cite in item['citations'])
    derived+=1
   except (ValueError,TypeError,KeyError,AssertionError):unknown+=1
  if not principal_ok or unknown:findings.append(dict(path=name,type='unclassified principal or resource'))
  rows.append(dict(path=name,synthetic_principals_verified=principal_ok,exact_test_resources=exact,derived_synthetic_checklists=derived,unclassified_resources=unknown));c.close()
report=dict(status='PASS' if not findings else 'REVIEW_REQUIRED',scope=roots,findings=findings,databases=rows,limits='Configured secret values scanned in every tracked artifact including decompressed bytes. Material/identity provenance verified against source/test literals and test fixtures. No claim that pattern scanning alone proves absence of all conceivable private information. Prior unknown token-hash flags were null project-runtime identities, now explicitly classified.')
Path('/workspace/scratch/published-evidence-audit-final.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],databases=len(rows),findings=findings)))
