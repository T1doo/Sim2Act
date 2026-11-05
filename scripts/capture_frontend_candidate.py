"""Capture a read-only frontend candidate, without credentials or Git mutations."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.local' / 'review-packages' / 'r0-plan-baseline-20261105'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    previous = json.loads((ROOT / 'docs/evidence/frontend-review-followup-20261105/verification-summary.json').read_text(encoding='utf-8'))
    compared = []
    for name, expected in previous['sources'].items():
        actual = digest((ROOT / name).read_bytes())
        compared.append(dict(path=name, expected=expected, actual=actual, matches=actual == expected))
    files = sorted((ROOT / 'src/sim2act/web').rglob('*'))
    files += [ROOT / 'tests/frontend_result_identity.cjs']
    files = [p for p in files if p.is_file()]
    manifest = {
        'branch': git('branch', '--show-current').decode().strip(),
        'head': git('rev-parse', 'HEAD').decode().strip(),
        'main_local': git('rev-parse', 'main').decode().strip(),
        'remote_not_fetched': True,
        'status_before_capture': git('status', '--porcelain').decode(),
        'prior_source_comparison': compared,
        'files': {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in files},
        'scope': 'Frontend byte snapshot plus tracked diff; not a qualified desktop package',
        'ui_ready': 'NOT_RUN: full states, native zoom, touch and accessibility gates remain open',
        'r0_ready': 'NOT_RUN: same-version Windows/PostgreSQL/model/AT acceptance remains open',
    }
    (OUT / 'tracked.patch').write_bytes(git('diff', '--binary', 'HEAD'))
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    with zipfile.ZipFile(OUT / 'frontend-source.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for p in files:
            archive.write(p, p.relative_to(ROOT).as_posix())
    print(json.dumps({'output': str(OUT), 'source_files': len(files), 'prior_hashes_match': all(x['matches'] for x in compared), 'archive_sha256': digest((OUT / 'frontend-source.zip').read_bytes())}, ensure_ascii=False))


if __name__ == '__main__':
    main()
