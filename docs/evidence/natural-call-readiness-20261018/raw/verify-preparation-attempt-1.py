"""File/schema preparation checks only; no product execution or semantic scoring."""
import ast
import hashlib
import json
import sys
from pathlib import Path

repo = Path('/workspace/Sim2Act')
root = Path('/workspace/natural-semantic-preparation-20261018')
out = Path(__file__).parent
assert not (out / 'preparation-verification.json').exists()
forbidden = []


def audit(event, args):
    if event in {'socket.connect', 'sqlite3.connect', 'subprocess.Popen', 'os.system'}:
        forbidden.append(event)
        raise AssertionError('Preparation verification cannot use network, DB or subprocess')


sys.addaudithook(audit)
sys.path.insert(0, str(repo / 'src'))
from sim2act.goals import GoalCardInput

manifest_file = root / 'MANIFEST.json'
manifest_sha = hashlib.sha256(manifest_file.read_bytes()).hexdigest()
assert manifest_sha == '0d551c953b5c86e92b010ada120556dce51b22cc2f3c3e3706c700914dfa38f3'
manifest = json.loads(manifest_file.read_text())
assert manifest['entry_count'] == len(manifest['files']) == 9
assert manifest['total_pre_manifest_bytes'] == sum(e['bytes'] for e in manifest['files']) == 23481
entries = {}
for entry in manifest['files']:
    name = entry['path']
    assert not Path(name).is_absolute() and '..' not in Path(name).parts
    data = (root / name).read_bytes()
    assert len(data) == entry['bytes']
    assert hashlib.sha256(data).hexdigest() == entry['sha256']
    assert len(data.decode('utf-8').splitlines()) == entry['text_lines']
    entries[name] = dict(bytes=len(data), sha256=entry['sha256'], lines=entry['text_lines'])
tree = ast.parse((repo / 'tests/test_natural_spec_apps.py').read_text())
development = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and type(node.value.value) is str:
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in {'SOURCE', 'COLD'}:
                development[target.id] = hashlib.sha256(node.value.value.encode()).hexdigest()
assert len(development) == 2
materials = {}
for case in ('a', 'b'):
    name = 'material_' + case + '.txt'
    data = (root / name).read_bytes()
    text = data.decode('utf-8')
    assert 0 < len(data) <= 1024 and len(text.splitlines()) <= 20
    assert data.endswith(b'\n') and b'\r' not in data
    assert entries[name]['sha256'] not in development.values()
    materials[case] = entries[name]
assert materials['a']['sha256'] != materials['b']['sha256']
drafts = json.loads((root / 'goal_drafts.json').read_text())
assert drafts['status'] == 'UNBOUND_GOAL_DRAFTS_NOT_SUBMITTABLE' and drafts['binding_required']
assert len(drafts['goals']) == 2
for item in drafts['goals']:
    goal = GoalCardInput.model_validate(item['goal_card_draft'])
    assert goal.resource_refs == ['__UNBOUND_ACTUAL_MATERIAL_' + item['case'] + '_RESOURCE_ID__']
    assert item['material_file'] == 'material_' + item['case'].lower() + '.txt'
    assert all(getattr(goal, field) for field in ('known', 'assumptions', 'unresolved', 'constraints', 'acceptance_checks'))
for case in ('a', 'b'):
    sheet = (root / ('score_sheet_' + case + '.md')).read_text()
    assert all(marker in sheet for marker in ('NOT_SCORED', 'NOT_PRODUCED', 'OWNER_PENDING'))
assert not forbidden
result = dict(status='FILE_AND_DRAFT_SCHEMA_CHECKS_PASSED_ONLY', manifest_sha256=manifest_sha,
    manifest_entries=entries, materials=materials, development_fixture_sha256=development,
    goal_drafts_schema_valid=2, actual_resource_bindings=0, goals_submitted=0,
    score_sheets='EMPTY_NOT_SCORED', private_reference='HASHED_ONLY_BY_ROOT_NOT_USED_FOR_IMPLEMENTATION_OR_TEST',
    audit_forbidden_attempts=forbidden, product_or_api_execution=0, database_connections=0,
    model_calls=0, mock_model_calls=0, generated_answers=0, human_scores=0, live_permits=0,
    limitations=['byte novelty only, not blind qualification', 'Goal schema only, not authorization or frozen contract',
        'reference is an unaccepted draft', 'no semantic/owner acceptance', 'prior nine pytest cases not rerun'])
(out / 'preparation-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'manifest_entries'}))
