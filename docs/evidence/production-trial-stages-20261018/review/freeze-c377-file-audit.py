from pathlib import Path
import ast
import hashlib
import json
import subprocess

repo = Path('/workspace/Sim2Act')
out = Path('/workspace/production-trial-stages-review-20261018')
head = 'c37736161c69562745078cbc8ee59d95c1f6d287'
previous = '99f112228755b86cce6090941332d8e3a40f1bdc'
base = '4bb3c26f5f67511795771c9187537aee4e852590'
def git(*args):
    return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', *args], cwd=repo).decode()
def source(ref, path):
    return git('show', f'{ref}:{path}')
def functions(text):
    return {n.name: n for n in ast.parse(text).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
def tree(ref):
    entries = git('ls-tree', '-r', ref, '--', 'src/').splitlines()
    return {line.split('\t', 1)[1]: line.split()[2] for line in entries}
assert git('rev-parse', 'HEAD').strip() == head
assert not git('status', '--porcelain')
changed = git('diff', '--name-only', previous, head).splitlines()
assert changed == ['src/sim2act/production_trial_sender.py', 'tests/test_production_trial_stages.py']
all_changed = git('diff', '--name-only', base, head).splitlines()
assert len(all_changed) == 7
sender_path = 'src/sim2act/production_trial_sender.py'
sender = source(head, sender_path)
fns = functions(sender)
old_fns = functions(source(previous, sender_path))
assert {k: ast.dump(v.args) for k, v in fns.items() if not k.startswith('_')} == {k: ast.dump(v.args) for k, v in old_fns.items() if not k.startswith('_')}
derive_calls = [n for n in ast.walk(ast.parse(sender)) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == '_derive']
assert len(derive_calls) == 3
for call in derive_calls:
    matching = [k.value for k in call.keywords if k.arg == '_generation']
    assert len(matching) == 1
    assert ast.dump(matching[0]) == ast.dump(ast.parse("item.stage == 'generate'", mode='eval').body)
checker = functions(source(head, 'src/sim2act/pa_spec_apps.py'))['check_envelope']
assert {n.func.id for n in ast.walk(checker) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)} == {'isinstance', 'set', 'DomainError'}
assert 'parse_response(raw, {CHECK_TOOL: check_envelope})' in source(head, 'src/sim2act/goal_applications.py')
assert 'schemas = {CHECK_TOOL: check_envelope}' in sender
current_tree, base_tree = tree(head), tree(base)
changed_production = [p for p in current_tree if current_tree[p] != base_tree.get(p)]
assert len(current_tree) == len(base_tree)
assert sorted(changed_production) == sorted(p for p in all_changed if p.startswith('src/'))
protected = ['production_trial_journal.py', 'production_trial_policy.py', 'production_trial_source.py', 'production_evidence.py', 'production_trial_admission.py', 'model.py', 'goal_applications.py', 'natural_trial_runs.py', 'natural_trial_budget.py', 'natural_spec_runtime.py', 'config.py']
for name in protected:
    p = 'src/sim2act/' + name
    assert current_tree[p] == base_tree[p]
record = {
    'review': 'STATIC_FILE_GIT_AST_ONLY', 'qualification': 'PENDING_ROOT_RUN_3_NO_EXECUTION_ARTIFACTS_READ',
    'head': head, 'previous': previous, 'base': base, 'git_status_clean_at_read': True,
    'previous_to_head_changed_paths': changed, 'base_to_head_changed_paths': all_changed,
    'production_tracked_paths': len(current_tree), 'production_changed_paths': changed_production,
    'protected_baseline_blob_equal_paths': ['src/sim2act/' + n for n in protected],
    'fixed_generation_schema_matches_original_controller': True,
    'derive_call_sites_same_stage_rule': len(derive_calls),
    'public_sender_signatures_equal_previous': True,
    'checker_envelope_only_no_compile_execute_calls': True,
    'production_blobs': {p: current_tree[p] for p in changed_production},
    'files': [{'path': p, 'bytes': (repo/p).stat().st_size, 'sha256': hashlib.sha256((repo/p).read_bytes()).hexdigest()} for p in all_changed],
    'limits': ['No product imports or tests executed', 'No DB/SQL/HTTP/network or model operations', 'No active run-3 artifacts read', 'No repository or sealed-directory writes', 'Raw run-1/run-2 failure counts not independently audited in this static step']
}
(out/'freeze-c377-static-verification.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'status':'STATIC_PASS_PENDING_EXECUTION', 'head':head, 'production_paths':len(current_tree), 'changed_production_paths':len(changed_production), 'protected_equal_paths':len(protected), 'derive_call_sites':len(derive_calls)}, ensure_ascii=False))
