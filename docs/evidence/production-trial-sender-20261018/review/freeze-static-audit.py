"""Pure file/Git/AST audit. No product import, database, pytest or network."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

repo = Path('/workspace/Sim2Act')
out = Path('/workspace/production-trial-sender-review-20261018')
base = '94fa765de11e1e3cc42dac9070a28ec9c2b47647'
expected = 'c6f946d4d5c90652dbc6ad9945499dc529cc8e4d'
def git(*args):
    return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', *args], cwd=repo)
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def dump(node):
    return ast.dump(node, include_attributes=False)
def statements(nodes):
    return [dump(n) for n in nodes]
def functions(tree):
    return {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

head = git('rev-parse', 'HEAD').decode().strip()
status = git('status', '--porcelain=v1').decode()
changed = git('diff', '--name-status', base, head).decode().splitlines()
path = 'src/sim2act/production_trial_journal.py'
old = functions(ast.parse(git('show', base + ':' + path)))
new = functions(ast.parse((repo / path).read_bytes()))
old_apply = old['_apply']
with_index = next(i for i, node in enumerate(old_apply.body) if isinstance(node, ast.With))
prefix = old_apply.body[:with_index]
old_tx = old_apply.body[with_index].body
helper = new['_apply_in_transaction'].body
old_read_tx = next(n for n in old['read'].body if isinstance(n, ast.With)).body
checks = {
    'exact_expected_head': head == expected,
    'clean_worktree': status == '',
    'only_three_expected_paths': changed == [
        'M\tsrc/sim2act/production_trial_journal.py',
        'A\tsrc/sim2act/production_trial_sender.py',
        'A\ttests/test_production_trial_sender.py',
    ],
    'old_apply_validation_ast_exact_after_new_transaction_assertion':
        statements(prefix) == statements(helper[1:1 + len(prefix)]),
    'old_apply_transaction_body_ast_exact':
        statements(old_tx) == statements(helper[1 + len(prefix):]),
    'old_read_scalar_anchor_ast_exact':
        statements(old_read_tx[1:3]) == statements(new['_history_anchor'].body),
    'all_other_existing_journal_functions_ast_exact': all(
        dump(node) == dump(new[name]) for name, node in old.items() if name not in {'read', '_apply'}
    ),
}
source_paths = [line.split('\t', 1)[1] for line in changed]
files = {}
for name in source_paths:
    raw = (repo / name).read_bytes()
    blob = git('show', head + ':' + name)
    files[name] = {'bytes': len(raw), 'sha256': sha(raw), 'matches_frozen_git_blob': raw == blob}
checks['all_changed_files_match_frozen_git_blobs'] = all(x['matches_frozen_git_blob'] for x in files.values())
legacy = git('ls-tree', '-r', '--name-only', base, 'src').decode().splitlines()
current = git('ls-tree', '-r', '--name-only', head, 'src').decode().splitlines()
legacy_blobs = git('ls-tree', '-r', base, 'src').decode().splitlines()
current_blobs = git('ls-tree', '-r', head, 'src').decode().splitlines()
old_map = dict(line.split('\t', 1)[::-1] for line in legacy_blobs)
new_map = dict(line.split('\t', 1)[::-1] for line in current_blobs)
legacy_other = [p for p in legacy if p != path]
checks['all_legacy_production_except_journal_git_blobs_identical'] = all(old_map[p] == new_map.get(p) for p in legacy_other)
checks['sender_uninstalled_from_other_production_modules'] = not any(
    b'production_trial_sender' in (repo / name).read_bytes()
    for name in current if name != 'src/sim2act/production_trial_sender.py'
)
test_tree = functions(ast.parse((repo / 'tests/test_production_trial_sender.py').read_bytes()))
empty = test_tree['test_cancel_between_committed_marker_and_guard_never_reaches_transport']
empty_source = ast.get_source_segment((repo / 'tests/test_production_trial_sender.py').read_text(), empty)
checks['empty_oracle_has_capture_and_journal_corruption_same_e64'] = (
    'sender.CAPTURE' in empty_source and 'journal.KIND' in empty_source
    and empty_source.count('response_sha256="e" * 64') == 2
    and 'damaged = snapshot' in empty_source
)
design_path = Path('/workspace/production-trial-sender-20261018/minimal-design-v3.md')
design_raw = design_path.read_bytes()
record = {
    'status': 'STATIC_NO_REMAINING_DEFINITE_P1_P2' if all(checks.values()) else 'STATIC_CHECK_REQUIRES_REVIEW',
    'baseline': base, 'freeze': head, 'checks': checks, 'changed_paths': changed,
    'production_tree': {'baseline_files': len(legacy), 'frozen_files': len(current),
                        'legacy_unchanged_except_journal': len(legacy_other)},
    'files': files,
    'design_v3': {'path': str(design_path), 'bytes': len(design_raw), 'sha256': sha(design_raw)},
    'qualification': 'PENDING_AUTHOR_CLOSED_ARTIFACTS; no running DB or result read',
    'explicit_difference': 'Existing _apply primitive validation now executes inside caller transaction, preceded by new c.in_transaction() assertion. Existing validation expressions and original transaction body AST are identical.',
    'limits': ['No product/pytest/HTTP/SQL/database/network/model execution by reviewer',
               'No API/Worker installation; strict test_only SQLite + exact MockTransport only',
               'No real source authority or LIVE permit; all receipts false',
               'DB guard to IO cancellation window remains possible and is explicitly disclosed',
               'Generic response protocol validity does not qualify business/source/cold semantics'],
    'sealed': False,
}
(out / 'freeze-static-review.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, ensure_ascii=False, indent=2))
