import sys,json,io,zipfile,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('scripts').resolve()))
from candidate_wheel import reuse_windows_native,wheel_profile
root=Path('.local/windows-build-20261105')
pure=root/'source-check/sim2act-0.1.0-py3-none-any.whl'
image=Path('deliverables/windows-full-20261101/Sim2Act-win64-042ab21c4fa9.zip')
setup=subprocess.check_output(['git','show','HEAD:setup.py'])
proof=Path('docs/evidence/windows-full-package-20261101/attempt-2/report.json')
name,data,provenance=reuse_windows_native(pure.name,pure.read_bytes(),image,setup,proof,native_image=True)
(root/name).write_bytes(data)
checks=['Exact image, unchanged native source groups, actual-import witness and PE ABI accepted']
for label,source,recipe in [('changed setup',pure.read_bytes(),setup+b'\n')]:
    try:reuse_windows_native(pure.name,source,image,recipe,proof,native_image=True)
    except ValueError:checks.append(label+' rejected')
    else:raise AssertionError(label)
modified=io.BytesIO()
with zipfile.ZipFile(pure) as src,zipfile.ZipFile(modified,'w') as dst:
    for member in src.namelist():
        content=src.read(member)
        if member=='sim2act/_raw_snapshot.c':content+=b'\n'
        dst.writestr(member,content)
try:reuse_windows_native(pure.name,modified.getvalue(),image,setup,proof,native_image=True)
except ValueError:checks.append('changed native source rejected')
else:raise AssertionError('changed native source accepted')
result={'status':'PASS_INPUT_REUSE_NOT_CURRENT_WINDOWS_EXECUTION','checks':checks,'profile':wheel_profile(name,data,target='windows'),'provenance':provenance}
Path('docs/evidence/r0-convergence-20261105/native-image-reuse.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'checks':checks,'wheel':name,'bytes':len(data)}))
