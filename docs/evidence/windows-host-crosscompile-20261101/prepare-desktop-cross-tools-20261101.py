import base64,hashlib,httpx,json,tarfile,zipfile,shutil
from pathlib import Path
root=Path('/workspace/scratch/sim2act-desktop-cross-tools-20261101');root.mkdir(exist_ok=False)
runtime=json.loads(Path('/workspace/scratch/desktop-cross-runtime-selection-20261101.json').read_text())
packages=json.loads(Path('/workspace/scratch/desktop-cross-nuget-selection-20261101.json').read_text())
report={'scope':'WORKSPACE_ONLY_BUILD_TOOLS_NO_WINDOWS_EXECUTION','downloads':[]}
def download(client,url,path,expected,max_bytes):
 h=hashlib.sha512();n=0
 with client.stream('GET',url) as response:
  response.raise_for_status()
  with path.open('xb') as out:
   for value in response.iter_bytes(65536):
    n+=len(value)
    if n>max_bytes:raise ValueError('Official download exceeded finite bound')
    h.update(value);out.write(value)
 assert h.digest()==expected,'Official SHA512 mismatch; do not execute'
 report['downloads'].append({'url':url,'bytes':n,'sha512':h.hexdigest(),'verified_official_metadata':True})
 (root/'tools-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report['downloads'][-1]),flush=True)
with httpx.Client(timeout=60,follow_redirects=True) as client:
 archive=root/'runtime.tar.gz';download(client,runtime['artifact']['url'],archive,bytes.fromhex(runtime['artifact']['hash']),64*1024*1024)
 target=root/'dotnet';target.mkdir()
 with tarfile.open(archive,'r:gz') as tar:
  assert sum(m.size for m in tar.getmembers())<150*1024*1024
  tar.extractall(target,filter='data')
 archive.unlink()
 for package,info in packages.items():
  archive=root/(package+'.nupkg');download(client,info['package_url'],archive,base64.b64decode(info['package_hash_base64']),info['package_size'])
  with zipfile.ZipFile(archive) as z:
   if package=='Microsoft.Net.Compilers.Toolset':
    names=[n for n in z.namelist() if n.startswith('tasks/netcore/bincore/') and '/' not in n[len('tasks/netcore/bincore/'):] and not ('VisualBasic' in n or Path(n).name.startswith('vbc'))]
    folder=root/'compiler'
   else:
    needed={'mscorlib.dll','System.dll','System.Core.dll','System.Drawing.dll','System.Windows.Forms.dll','System.Web.Extensions.dll','System.Xml.dll','Microsoft.CSharp.dll'}
    names=[n for n in z.namelist() if n.startswith('build/.NETFramework/v4.6.2/') and Path(n).name in needed]
    assert {Path(n).name for n in names}==needed
    folder=root/'net462'
   folder.mkdir()
   for name in names:
    (folder/Path(name).name).write_bytes(z.read(name))
   for name in z.namelist():
    if Path(name).name.lower() in {'license.txt','thirdpartynotices.rtf','thirdpartynotices.txt'}:
     (folder/Path(name).name).write_bytes(z.read(name))
  archive.unlink()
 print(json.dumps({'prepared':str(root),'free_MiB':shutil.disk_usage(root).free//1024//1024,'compiler_runtime':json.loads((root/'compiler/csc.runtimeconfig.json').read_text())}),flush=True)
