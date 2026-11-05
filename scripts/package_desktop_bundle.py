"""Allowlisted desktop + private PostgreSQL payload, excluding machine/user state.

This is an internal payload builder, not an installer or release qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_file(root,name,expected):
    path=PurePosixPath(name)
    blocked={'private','workspace data','webview-profile','configured-webview-profile','temp','exports','local-installation.json','desktop.log'}
    if (path.is_absolute() or str(path)!=name or '..' in path.parts or '\\' in name or ':' in name
            or PureWindowsPath(name).is_reserved() or any(p.casefold() in blocked or p.endswith((' ','.')) for p in path.parts)
            or name.lower().endswith(('.dpapi','.db','.env'))):
        raise ValueError('Private or unsafe payload member: '+name)
    file=root.joinpath(*path.parts)
    if any(p.is_symlink() or p.is_junction() for p in (file,*file.parents)):
        raise ValueError('Linked payload member')
    data=file.read_bytes()
    if len(data)!=expected['bytes'] or digest(data)!=expected['sha256']:
        raise ValueError('Payload bytes differ: '+name)
    return data


def build(app,postgres,output):
    if output.exists() or any(p.is_symlink() or p.is_junction() for p in (output,*output.parents)):
        raise ValueError('New ordinary output required')
    manifests={}
    for name in ('portable-manifest.json','desktop-manifest.json'):
        manifests[name]=(app/name).read_bytes()
    portable=json.loads(manifests['portable-manifest.json'].decode('utf-8-sig'))
    host=json.loads(manifests['desktop-manifest.json'].decode('utf-8-sig'))
    if (portable['format']!='sim2act-offline-windows-configured-build.v1'
            or host['format']!='sim2act-native-desktop.v1'
            or portable['product_commit']!=host['source_commit']
            or digest(manifests['portable-manifest.json'])!=host['portable_manifest_sha256']):
        raise ValueError('Desktop source/manifest mismatch')
    pg_raw=(postgres/'runtime-manifest.json').read_bytes()
    pg=json.loads(pg_raw)
    if pg['format']!='sim2act-private-postgres-runtime.v1':raise ValueError('Unknown database runtime')
    entries={}
    for inventory,root,prefix in [(portable['files'],app,''),(host['files'],app,''),(pg['files'],postgres,'postgresql/')]:
        for name,expected in inventory.items():
            key=prefix+name
            if key.casefold() in {k.casefold() for k in entries}:raise ValueError('Duplicate payload member')
            entries[key]=checked_file(root,name,expected)
    entries.update(manifests)
    entries['postgresql/runtime-manifest.json']=pg_raw
    summary={'format':'sim2act-combined-desktop-payload.v1','source_commit':host['source_commit'],
        'status':'ASSEMBLED_NOT_FIRST_USE_OR_RELEASE_ACCEPTED','first_use_ready':False,
        'distribution_license_review':'NOT_EVALUATED','private_credentials_included':False,
        'files':{name:{'bytes':len(data),'sha256':digest(data)} for name,data in sorted(entries.items())}}
    entries['bundle-manifest.json']=json.dumps(summary,indent=2).encode()
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(entries.items()):archive.writestr('Sim2Act/'+name,data)
    return {'archive':str(output),'sha256':digest(output.read_bytes()),'files':len(entries),'bytes':output.stat().st_size,'status':summary['status']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app',required=True,type=Path)
    parser.add_argument('--postgres',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps(build(args.app,args.postgres,args.output),indent=2))
