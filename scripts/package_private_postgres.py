"""Stage a private PostgreSQL runtime; never install a service or initialize data."""
import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath


def stage(archive: Path, expected_sha256: str, output: Path):
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise ValueError('PostgreSQL archive digest mismatch')
    if output.exists() or any(p.is_symlink() or p.is_junction() for p in (output, *output.parents)):
        raise ValueError('New ordinary output directory required')
    records = {}
    with zipfile.ZipFile(archive) as bundle:
        names = set()
        selected = []
        for member in bundle.infolist():
            name = PurePosixPath(member.filename)
            if name.is_absolute() or '..' in name.parts or '\\' in member.filename or ':' in member.filename:
                raise ValueError('Unsafe archive path')
            if str(name) != member.filename.rstrip('/') or PureWindowsPath(member.filename).is_reserved() or any(p.endswith((' ','.')) for p in name.parts):
                raise ValueError('Ambiguous Windows archive path')
            if stat.S_ISLNK(member.external_attr >> 16):
                raise ValueError('Archive link refused')
            if member.is_dir():
                continue
            if member.filename.casefold() in names:
                raise ValueError('Duplicate Windows archive path')
            names.add(member.filename.casefold())
            runtime = member.filename.startswith(('pgsql/bin/', 'pgsql/lib/', 'pgsql/share/'))
            notice = any(word in member.filename.lower() for word in ('copyright', 'license', 'notice'))
            if runtime or notice:
                selected.append(member)
        required = {'pgsql/bin/'+n+'.exe' for n in ('postgres', 'pg_ctl', 'initdb', 'psql', 'pg_isready')}
        if not required.issubset({m.filename for m in selected}):
            raise ValueError('Incomplete PostgreSQL runtime')
        if not any(any(w in m.filename.lower() for w in ('copyright', 'license')) for m in selected):
            raise ValueError('Original distribution notices required')
        if sum(m.file_size for m in selected) > 2_000_000_000:
            raise ValueError('Unexpected runtime size')
        # Complete name/inventory validation precedes any writes. A CRC failure
        # during extraction preserves the partial candidate for diagnosis.
        output.mkdir(parents=True)
        for member in selected:
            data = bundle.read(member)
            target = output.joinpath(*PurePosixPath(member.filename).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            records[member.filename] = {'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()}
    report = {'format':'sim2act-private-postgres-runtime.v1', 'archive_sha256':digest,
              'status':'STAGED_NOT_EXECUTED_OR_INITIALIZED', 'files':records,
              'service_installed':False, 'startup_registered':False,
              'data_initialized':False, 'distribution_license_review':'NOT_EVALUATED'}
    (output/'runtime-manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=stage(args.archive,args.sha256,args.output)
    print(json.dumps({'status':report['status'],'files':len(report['files'])}))
