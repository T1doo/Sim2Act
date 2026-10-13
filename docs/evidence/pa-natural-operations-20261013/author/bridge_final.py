"""Compare current complete source closure and exact unique test denominators."""
from pathlib import Path
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).parent
REPO = Path('/workspace/Sim2Act-pa-provider')
EVIDENCE = ROOT.parent
labels = ['frozen-backend', 'frozen-ui']
maps = []
for label in labels:
    result = json.loads((ROOT / f'{label}-result.json').read_text())
    assert result['returncode'] == 0 and not result['source_changes']
    for side in ['before', 'after']:
        maps.append(ROOT / f'{label}-source-{side}.json')
maps += [EVIDENCE / 'independent/selected-source-before.json',
         EVIDENCE / 'independent/selected-source-after.json']
reference = json.loads(maps[0].read_text())
rows = []
for path in maps:
    current = json.loads(path.read_text())
    assert current['files'] == reference['files'] and current['head'] == reference['head']
    rows.append({'path': str(path.relative_to(EVIDENCE)), 'files': len(current['files']),
                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'exact': True})
names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard',
                                 'src', 'tests', 'pyproject.toml'], cwd=REPO, text=True).splitlines()
current = {n: hashlib.sha256((REPO / n).read_bytes()).hexdigest() for n in sorted(set(names))}
assert current == reference['files']


def nodes(path):
    cases = ET.parse(path).getroot().findall('.//testcase')
    result = {(c.attrib['classname'], c.attrib['name']) for c in cases}
    assert len(result) == len(cases)
    return result


backend = nodes(ROOT / 'frozen-backend.xml')
ui = nodes(ROOT / 'frozen-ui.xml')
independent = nodes(EVIDENCE / 'independent/selected.xml')
assert not backend & ui
author = backend | ui
assert independent <= author
report = {'tested_head': reference['head'], 'source_files': len(current),
          'current_exact': True, 'source_changes': [], 'maps': rows,
          'author_unique': len(author), 'author_backend_unique': len(backend),
          'author_ui_unique': len(ui), 'independent_unique': len(independent),
          'intersection': len(author & independent), 'union_unique': len(author | independent),
          'independent_not_added_to_author_denominator': True}
(ROOT / 'author-independent-final-bridge.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
