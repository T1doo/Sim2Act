"""Build only the explicit experimental component, with the installed toolchain.

No pip, SDK installation, build isolation or production enablement. The caller
chooses an isolated output directory; the source tree receives no binary.
"""

import argparse
import json
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    if sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 12):
        raise SystemExit('Requires the qualified CPython 3.12 toolchain')
    compiler = shutil.which('cc')
    include = Path(sysconfig.get_path('include'))
    if compiler is None or not (include / 'Python.h').is_file() or not (include / 'pyconfig.h').is_file():
        raise SystemExit('Missing installed cc, Python.h or pyconfig.h; nothing installed')
    source = Path(__file__).resolve().parents[1] / 'src/sim2act/_cold_typed_native_impl.c'
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / ('_cold_typed_native_impl' + sysconfig.get_config_var('EXT_SUFFIX'))
    command = [compiler, '-shared', '-fPIC', '-O2', '-Wall', '-Wextra', '-Werror',
        '-I' + str(include), str(source), '-o', str(target)]
    subprocess.run(command, check=True)
    print(json.dumps(dict(command=command, output=str(target), python=sys.version,
        soabi=sysconfig.get_config_var('SOABI'))))


if __name__ == '__main__':
    main()
