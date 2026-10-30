"""Build the uninstalled candidate explicitly into a caller-selected directory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import sysconfig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--cc', default='/usr/bin/cc')
    args = parser.parse_args()
    if sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 12):
        parser.error('This uninstalled candidate is qualified only for CPython 3.12.')
    source_dir = Path(__file__).resolve().parent
    files = [source_dir / '_source_owned_proto.c', source_dir / 'source_live_match.h']
    source_sha = hashlib.sha256(b''.join(path.read_bytes() for path in files)).hexdigest()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    binary = output_dir / ('_source_owned_proto' + sysconfig.get_config_var('EXT_SUFFIX'))
    command = [args.cc, '-shared', '-fPIC', '-O3', '-DNDEBUG', '-Wall', '-Wextra',
               '-Werror', '-DSOURCE_SHA="' + source_sha + '"',
               '-I' + sysconfig.get_paths()['include'], str(files[0]), '-o', str(binary)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    (output_dir / 'build.log').write_text(result.stdout + result.stderr)
    identity = dict(status='UNINSTALLED_NOT_PRODUCTION', returncode=result.returncode,
                    source_sha256=source_sha,
                    source_files={path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
                    binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest()
                    if result.returncode == 0 else None)
    (output_dir / 'build.json').write_text(json.dumps(identity, indent=2) + '\n')
    print(json.dumps(identity))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
