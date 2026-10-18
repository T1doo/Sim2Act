"""Read the stopped synthetic fixture without invoking product, Worker, or model."""
from pathlib import Path
import sqlite3,hashlib,json,datetime,subprocess
OUT=Path(__file__).parent;REPO=Path('/workspace/Sim2Act');FIXTURE=Path('/workspace/local-record-state-evidence-20261018/shared-d5eadc70/test_natural_spec_page_actual_0/fixture.db')
def utc(x):return datetime.datetime.fromtimestamp(x,datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(FIXTURE);stat=FIXTURE.stat();c=sqlite3.connect('file:'+str(FIXTURE)+'?mode=ro&immutable=1',uri=True);c.row_factory=sqlite3.Row
queries={
'runs':"select id,principal_id,project_id,runtime_id,status,request_key,created_at,lease_until,fence,version,json_extract(context,'$.kind') as kind,json_extract(context,'$.requests') as requests,json_extract(context,'$.tools') as tools,json_extract(context,'$.spec_family') as spec_family from runs",
'operations':"select id,run_id,call_id,tool_ref,status from operations",
'app_runs':"select id,instance_id,release_id,status,result_version from internal_app_runs",
'instances':"select id,source_app_id,release_id,revision,data_version from internal_instances",
'events':"select run_id,created_at,kind,json_extract(data,'$.step_id') as step_id,json_extract(data,'$.status') as status from events order by created_at,id",
'resources':"select id,project_id,format,length(content) as characters,hash from resources",
'attempts':"select id,run_id,status,created_at,reserved_tokens from attempts order by created_at,id",
}
rows={k:[dict(r) for r in c.execute(q)] for k,q in queries.items()}
for r in rows['events']:r['utc']=utc(r['created_at'])
counts={r[0]:c.execute('select count(*) from "'+r[0]+'"').fetchone()[0] for r in c.execute("select name from sqlite_master where type='table'").fetchall()};c.close()
result={'classification':'NON_AUTHOR_READ_ONLY_ORIGINAL_SYNTHETIC_FIXTURE_METADATA_NO_PRODUCT_EXECUTION','uri_mode':'ro&immutable=1','fixture':str(FIXTURE),'sha256_before':before,'sha256_after':sha(FIXTURE),'unchanged':before==sha(FIXTURE),'file_size':stat.st_size,'mtime':stat.st_mtime,'mtime_utc':utc(stat.st_mtime),'rows':rows,'table_counts':counts,'directory_files':sorted(p.name for p in FIXTURE.parent.iterdir())}
(OUT/'original-fixture-metadata.json').write_text(json.dumps(result,indent=2)+'\n')
source_files=['tests/test_pa_natural_spec_ui.py','tests/pa_natural_spec_ui.cjs','src/sim2act/web/internal.js','src/sim2act/web/owner-review.js','src/sim2act/internal_api.py','src/sim2act/lifecycle.py','src/sim2act/app_jobs.py','src/sim2act/db.py','src/sim2act/worker.py','src/sim2act/goal_applications.py','src/sim2act/pa_spec_apps.py','src/sim2act/pa_material_bindings.py','src/sim2act/natural_spec_runtime.py','src/sim2act/csv_logic_reuse.py','src/sim2act/text_workflows.py']
manifest={'head':subprocess.check_output(['git','-c','core.fsmonitor=false','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'files':{p:{'bytes':(REPO/p).stat().st_size,'sha256':sha(REPO/p)} for p in source_files},'node_path':{'configured':'/workspace/node-tools/node_modules','realpath':str(Path('/workspace/node-tools/node_modules').resolve()),'exists':Path('/workspace/node-tools/node_modules/jsdom/package.json').is_file()}}
(OUT/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'head':manifest['head'],'fixture_unchanged':result['unchanged'],'fixture_sha':before,'runs':[(r['id'],r['status']) for r in rows['runs']],'last_event':rows['events'][-1],'file_mtime':result['mtime_utc'],'original_directory_files':result['directory_files']}))
