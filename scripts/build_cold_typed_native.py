"""Build only the explicit experimental component, with the installed toolchain.

No pip, SDK installation, build isolation or production enablement. The caller
chooses an isolated output directory; the source tree receives no binary.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--sanitize-address', action='store_true')
    parser.add_argument('--component', choices=('typed', 'row'), default='typed')
    args = parser.parse_args()
    if (sys.implementation.name != 'cpython' or sys.version !=
            '3.12.14 (main, Aug 25 2026, 14:00:49) [Clang 22.1.3 ]'
            or sysconfig.get_config_var('SOABI') != 'cpython-312-x86_64-linux-gnu'):
        raise SystemExit('Requires the exact qualified CPython 3.12.14 build/ABI')
    compiler = shutil.which('cc')
    include = Path(sysconfig.get_path('include'))
    if compiler is None or not (include / 'Python.h').is_file() or not (include / 'pyconfig.h').is_file():
        raise SystemExit('Missing installed cc, Python.h or pyconfig.h; nothing installed')
    stem = '_cold_typed_native_impl' if args.component == 'typed' else '_cold_row_native_impl'
    source = Path(__file__).resolve().parents[1] / ('src/sim2act/' + stem + '.c')
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / (stem + sysconfig.get_config_var('EXT_SUFFIX'))
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    command = [compiler, '-shared', '-fPIC', '-O2', '-Wall', '-Wextra', '-Werror',
        '-DSIM2ACT_VISITOR_SOURCE_SHA="' + source_sha + '"',
        '-I' + str(include), str(source), '-o', str(target)]
    if args.sanitize_address:
        command[command.index('-O2')] = '-O1'
        command += ['-g', '-fsanitize=address', '-fno-omit-frame-pointer']
    subprocess.run(command, check=True)
    receipt = dict(command=command, output=str(target), python=sys.version,
        soabi=sysconfig.get_config_var('SOABI'), source_sha256=source_sha,
        executable_sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        sanitizer='address' if args.sanitize_address else None,
        headers={name: hashlib.sha256((include / name).read_bytes()).hexdigest()
            for name in ('Python.h', 'pyconfig.h', 'cpython/pystate.h', 'internal/pycore_ceval.h')})
    target.with_suffix(target.suffix + '.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
