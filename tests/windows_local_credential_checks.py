"""Compile the actual credential-reader method into a console-only fixture.

Uses synthetic current-user DPAPI data; never opens a window or real credentials.
"""
import json,subprocess,sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]
source=(root/'scripts/windows/Sim2ActDesktop.cs').read_text(encoding='utf-8')
method=source[source.index('    string ReadLocalUiToken()'):source.index('    Dictionary<string,object> ProfileIdentity()')]
method=method.replace('    string ReadLocalUiToken()', '    public string ReadLocalUiToken()',1)
paths_start=source.index('static class Paths {')
paths=source[paths_start:source.index('sealed class ',paths_start)]
helper=next(line.strip() for line in source.splitlines() if line.strip().startswith('static string TextValue('))
folder=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'.local/windows-build-20261105/credential-checks'
folder.mkdir(exist_ok=False)
harness=r'''
class Reader {
 public string managedFile,managedSnapshot,expectedData;
 METHOD
 HELPER
}
class Probe {
 static int Main(string[] args) {
  string root=args[0];Directory.CreateDirectory(root);
  string file=Path.Combine(root,"selection.json"),secret=Path.Combine(root,"test.dpapi"),data=Path.Combine(root,"data");
  var serializer=new JavaScriptSerializer();int count=0;
  foreach(string scenario in new[]{"valid","changed-selection","wrong-workspace","wrong-data","missing-token","bad-token","corrupt-blob"}) {
   string config=serializer.Serialize(new Dictionary<string,object>{{"format","sim2act.local-installation.v1"},{"workspace",root},{"credentials",secret},{"data",data}});
   File.WriteAllText(file,config);
   var credentials=new Dictionary<string,object>{{"data_dir",scenario=="wrong-data"?root:data}};
   if(scenario!="missing-token")credentials["ui_token"]=scenario=="bad-token"?"invalid":new string('a',64);
   byte[] encrypted=ProtectedData.Protect(Encoding.Unicode.GetBytes(serializer.Serialize(credentials)),null,DataProtectionScope.CurrentUser);
   File.WriteAllText(secret,scenario=="corrupt-blob"?"00000000":BitConverter.ToString(encrypted).Replace("-",""));
   var reader=new Reader{managedFile=file,managedSnapshot=scenario=="changed-selection"?config+" ":config,expectedData=scenario=="wrong-workspace"?data:root};
   bool accepted=false;
   try {accepted=reader.ReadLocalUiToken()==new string('a',64);}catch(Exception){}
   if(accepted!=(scenario=="valid"))throw new Exception("Unexpected outcome: "+scenario);
   Console.WriteLine("PASS "+scenario);count++;
  }
  Console.WriteLine("CHECKS="+count);return 0;
 }
}
'''.replace('METHOD',method).replace('HELPER',helper)
header='using System;using System.IO;using System.Text;using System.Text.RegularExpressions;using System.Collections.Generic;using System.Web.Script.Serialization;using System.Security.Cryptography;using Microsoft.Win32;\n'
code=folder/'Probe.cs';code.write_text(header+paths+harness,encoding='utf-8')
exe=folder/'Probe.exe'
subprocess.run([r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe','/nologo','/langversion:5','/codepage:65001','/reference:System.Security.dll,System.Web.Extensions.dll','/out:'+str(exe),str(code)],check=True)
result=subprocess.run([str(exe),str(folder/'fixture')],capture_output=True,text=True)
(folder/'result.json').write_text(json.dumps({'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'scope':'synthetic DPAPI console fixture, no native UI'},indent=2))
print(result.stdout)
if result.returncode:raise RuntimeError('Credential boundary checks failed; preserve report')
