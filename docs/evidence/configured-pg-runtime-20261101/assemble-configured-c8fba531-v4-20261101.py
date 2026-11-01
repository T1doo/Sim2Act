"""Single frozen offline internal assembly. No Windows/PG/model execution."""
from pathlib import Path
import hashlib,json,zipfile,subprocess,re
from email.parser import BytesParser
repo=Path('/workspace/Sim2Act');source='c8fba5316043264bdfb7d761a49d3e96995f5aaa'
scratch=Path('/workspace/scratch');stage=scratch/'Sim2Act-configured-c8fba531-stage.zip'
host=scratch/'sim2act-configured-desktop-c8fba531-20261101'
out=scratch/'Sim2Act-internal-win64-c8fba5316043-reviewed.zip';assert not out.exists()
def record(v):return dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest())
assert record(stage.read_bytes())==dict(bytes=26949178,sha256='93cb3aa7072ee02b2cedd8467266acc467fc3ecf02c28ec46c9f46204ac3f418')
with zipfile.ZipFile(stage) as z:
 assert len(z.namelist())==len(set(z.namelist()))
 files={n.removeprefix('Sim2Act-preview/'):z.read(n) for n in z.namelist()}
manifest=json.loads(files['portable-manifest.json']);assert manifest['product_commit']==source and manifest['omitted']==[]
assert set(files)==set(manifest['files'])|{'portable-manifest.json'}
for n,expected in manifest['files'].items():assert record(files[n])==expected
app=json.loads(files['app-build-provenance.json']);assert app['source_commit']==source
assert app['native_reuse']['status']=='REUSED_UNCHANGED_NATIVE_NOT_CURRENT_WINDOWS_EXECUTED'
# Complete current source inventory, not only matching filenames or old hashes.
candidate=json.loads((scratch/'sim2act-configured-c8fba531-input-20261101/candidate-manifest.json').read_bytes())
count=0
for name,expected in candidate['files'].items():
 if not name.startswith('src/sim2act/'):continue
 data=files['runtime/Lib/site-packages/'+name[4:]]
 assert record(data)==expected and data==subprocess.check_output(['git','show',source+':'+name],cwd=repo)
 count+=1
host_manifest=json.loads((host/'host-manifest.json').read_bytes());assert host_manifest['source_commit']==source
assert host_manifest['status']=='CROSS_COMPILED_NOT_WINDOWS_EXECUTED'
host_build=json.loads((host/'build-result.json').read_bytes())
host_zip=host/host_build['archive']['name']
assert record(host_zip.read_bytes())=={k:host_build['archive'][k] for k in ('bytes','sha256')}
with zipfile.ZipFile(host_zip) as h:
 host_files={n:h.read(n) for n in h.namelist()}
for name,expected in host_manifest['files'].items():
 assert record(host_files[name])==expected
 if (host/name).exists():assert (host/name).read_bytes()==host_files[name]
assert (host/'Sim2ActDesktop.cs').read_bytes()==subprocess.check_output(['git','show',source+':scripts/windows/Sim2ActDesktop.cs'],cwd=repo)
for name in ('Sim2Act.exe','Microsoft.Web.WebView2.Core.dll','Microsoft.Web.WebView2.WinForms.dll','WebView2Loader.dll','WEBVIEW2-SDK-LICENSE.txt'):
 assert name not in files
 files[name]=host_files[name]
archive_name='host-build-provenance/'+host_zip.name
files[archive_name]=host_zip.read_bytes()
files['desktop-manifest.json']=(json.dumps(dict(format='sim2act-assembled-configured-desktop.v1',
 source_commit=source,status='CROSS_COMPILED_NOT_CURRENT_WINDOWS_EXECUTED',
 host='WINFORMS_WEBVIEW2_NO_BROWSER_FALLBACK',build_archive=dict(file=archive_name,**record(files[archive_name])),
 files={n:record(files[n]) for n in ('Sim2Act.exe','Microsoft.Web.WebView2.Core.dll','Microsoft.Web.WebView2.WinForms.dll','WebView2Loader.dll','WEBVIEW2-SDK-LICENSE.txt')}),indent=2)+'\n').encode()
files['READ-ME-FIRST.txt']=('Sim2Act - INTERNAL CONFIGURED DESKTOP QA INPUT\n\n'
 'The current matching independent WinForms/WebView2 EXE is already compiled and included. You do not need a C# compiler to start it.\n'
 'This package has NOT been executed as a complete package on Windows or PostgreSQL and is not a final R0/Release delivery.\n'
 'Existing Windows x64, .NET Framework 4.6.2+ and WebView2 Runtime are required; no system runtime installer or browser fallback.\n'
 'Default Start-Sim2Act.cmd opens the explicitly synthetic local SQLite workspace.\n'
 'Start-Configured-Sim2Act.cmd requires the existing explicit PostgreSQL application-role config and optionally the existing approved trial selection.\n'
 'It does not create a database, role, grant, credential or approval. Existing configured login is required in the application.\n'
 'Current Python source, original unchanged four native extensions and original pinned PostgreSQL drivers have byte provenance in the manifests.\n'
 'Host source/compiler logs are inside the referenced original host component ZIP in host-build-provenance, not claimed as root runtime files.\n'
 'Licensing and full redistribution review remain unresolved; no project license has been selected here.\n'
 'Preserve data/profile/claims on unknown stop; do not bypass OS or application refusals.\n').encode()
expected=json.loads((scratch/'sim2act-pg-original-dependencies-20261101/configured-inputs.json').read_bytes())
canonical=lambda s:re.sub(r'[-_.]+','-',s).lower()
versions={}
for name,data in files.items():
 if name.startswith('runtime/Lib/site-packages/') and name.endswith('.dist-info/METADATA'):
  metadata=BytesParser().parsebytes(data);key=canonical(metadata['Name']);assert key not in versions
  versions[key]=metadata['Version']
assert versions=={canonical(w['name']):w['version'] for w in expected['wheels']}|{'sim2act':'0.1.0'}
assert len(versions)==24
for module,item in app['native_reuse']['modules'].items():assert record(files['runtime/Lib/site-packages/'+item['file']])=={k:item[k] for k in ('bytes','sha256')}
patterns=[rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{40,}',rb'(?<![A-Za-z0-9_])sk-[A-Za-z0-9_-]{30,}']
assert not any(re.search(p,data) for data in files.values() for p in patterns)
assert not any(n.endswith(('.db','.sqlite','.env')) for n in files)
report=dict(format='sim2act-configured-internal-full-package.v1',source_commit=source,
 status='ASSEMBLED_NOT_CURRENT_WINDOWS_POSTGRESQL_OR_RELEASE_ACCEPTED',current_source_files=count,
 native_reuse=app['native_reuse'],host=record(files['Sim2Act.exe']),installed_dependencies=versions,
 runtime_input='exact original CPython3.12.10/dependency image plus original pinned PG wheels',
 secrets='bounded standalone hosted-token/private-key marker and private-config/database-name scan: no matches; initial substring false positive is unchanged original psutil constant (571c6cd7919971df4c1381cfd514808ff934f7f7fc79c312b52278fcd0c7dd10)',
 model_calls=0,windows_executed=False,postgresql_executed=False,distribution_review='NOT_EVALUATED',
 files={n:record(v) for n,v in sorted(files.items())})
files['full-package-manifest.json']=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
with zipfile.ZipFile(out,'x') as z:
 for name,data in sorted(files.items()):
  item=zipfile.ZipInfo('Sim2Act/'+name,(2026,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;item.external_attr=0o100644<<16;z.writestr(item,data)
with zipfile.ZipFile(out) as z:
 assert len(z.namelist())==len(files)==len(set(z.namelist()))
 for name,data in files.items():assert z.read('Sim2Act/'+name)==data
summary=dict(source_commit=source,archive=dict(file=str(out),**record(out.read_bytes())),
 wheel=record((scratch/'sim2act-configured-c8fba531-input-20261101/sim2act-0.1.0-cp312-cp312-win_amd64.whl').read_bytes()),
 source_files=count,files=len(files),installed_packages=len(versions),host=record(files['Sim2Act.exe']),
 status=report['status'],native='REUSED_UNCHANGED_NATIVE',Windows='NOT_RUN',PostgreSQL='NOT_RUN',models=0)
(scratch/'configured-full-assembly-c8fba531-reviewed-20261101.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
