from pathlib import Path
import hashlib,json,re,subprocess,xml.etree.ElementTree as ET
from datetime import datetime,timezone
B=Path('docs/evidence/project-column-material-reuse-20261011')
def write(name,value):
    (B/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
freeze=json.loads((B/'frozen-before.json').read_text())
current={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in freeze['files']}
assert current==freeze['files'],'source changed during final tests'
write('frozen-after.json',{'base_head':freeze['base_head'],'files':current,'before_after_equal':True,'file_count':len(current)})
# Include the unchanged CSS and structured fixtures separately; they were not
# part of the explicit Python/JS/HTML freeze and must not be counted as frozen.
all_paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','--','src','tests'],text=True).splitlines()
extra={}
for p in all_paths:
    if p not in current:
        actual=Path(p).read_bytes()
        old=subprocess.check_output(['git','show',freeze['base_head']+':'+p])
        assert actual==old,p
        extra[p]=hashlib.sha256(actual).hexdigest()
write('other-source-fixtures-unchanged.json',{'base_head':freeze['base_head'],'not_in_314_freeze':True,'files':extra,'head_byte_equal':True})
selected=[s.strip() for s in (B/'final-collection.log').read_text().splitlines() if s.startswith('tests/') and '::' in s]
assert len(selected)==269 and len(set(selected))==269
allnodes=[];suites={}
for name,expected in [('final-core',15),('final-regression',254)]:
    root=ET.parse(B/(name+'.xml')).getroot()
    group=root.findall('testsuite') if root.tag=='testsuites' else [root]
    cases=[c for s in group for c in s.findall('testcase')]
    assert len(cases)==expected,(name,len(cases))
    rows=[]
    for c in cases:
        node=c.attrib['classname'].replace('.','/')+'.py::'+c.attrib['name']
        stop=next((k for k in ['failure','error','skipped'] if c.find(k) is not None),None)
        row={'node':node,'status':{'failure':'FAIL','error':'ERROR','skipped':'SKIP',None:'PASS'}[stop],'seconds':float(c.attrib['time'])}
        if stop: row['reason']=c.find(stop).attrib.get('message','')
        rows.append(row);allnodes.append(node)
    totals={s:sum(x['status']==s for x in rows) for s in ['PASS','FAIL','ERROR','SKIP']}
    assert totals['FAIL']==0 and totals['ERROR']==0,(name,totals)
    durations=[float(s.attrib['time']) for s in group]
    raw=(B/(name+'.log')).read_text()
    assert re.search(r'\d+ passed.* in [\d.]+s',raw),name+' no completion line'
    suites[name]={'counts':totals,'unique_nodes':len(rows),'junit_seconds':sum(durations),'nodes':rows,'completion_line':[s for s in raw.splitlines() if re.match(r'\d+ passed.* in [\d.]+s',s)][-1]}
assert len(set(allnodes))==269 and set(allnodes)==set(selected),'collection/JUnit mismatch'
write('final-validation.json',{'status':'LIMITED_PASS','base_head':freeze['base_head'],'validated_at_utc':datetime.now(timezone.utc).isoformat(),'selected':269,'deselected':2,'deselected_reason':'actual old-source upgrades explicitly not run','collection_junit_exact_equal':True,'all_source_test_hashes_equal':True,'freeze_file_count':len(current),'additional_unchanged_fixture_files':len(extra),'suites':suites,'counts':{s:sum(x['counts'][s] for x in suites.values()) for s in ['PASS','FAIL','ERROR','SKIP']},'independent':{'backend_actual_pass':13,'backend_not_rerun_final_js_only_byte_bridge':True,'fresh_final_ui_pass':16,'not_added_to_author_pytest_count':True},'not_run':['PostgreSQL/roles','Windows/native browser/visual','old source upgrade','real models/paid APIs','complete P-A/P-B/AT10','human semantic/owner acceptance','remote CI','deployment']})
print(json.dumps({name:{k:v for k,v in s.items() if k!='nodes'} for name,s in suites.items()},ensure_ascii=False,indent=2))
print('269 selected unique nodes match actual final JUnit; 314 frozen files unchanged; extra fixture files unchanged:',len(extra))
