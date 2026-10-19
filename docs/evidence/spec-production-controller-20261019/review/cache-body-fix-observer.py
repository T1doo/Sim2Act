from pathlib import Path
import ast,hashlib,json
root=Path('/workspace/Sim2Act'); before=Path('/workspace/spec-production-controller-audit-20261019/qualified-second/inputs')
def nodes(path):
    return {n.name:n for n in ast.parse(path.read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
def dump(n): return ast.dump(n,include_attributes=False)
def sha(p):
    data=p.read_bytes();return {'path':str(p),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def same_functions(rel,names):
    old=nodes(before/rel);new=nodes(root/rel)
    return {name:dump(old[name])==dump(new[name]) for name in names}
def strip_production_eligibility(node):
    node=ast.parse(ast.unparse(node)).body[0]
    node.body=[n for n in node.body if not(isinstance(n,ast.ImportFrom) and n.module=='spec_production')]
    class Restore(ast.NodeTransformer):
        def visit_Compare(self,n):
            self.generic_visit(n)
            if (isinstance(n.left,ast.Name) and n.left.id=='versions' and len(n.ops)==1 and isinstance(n.ops[0],ast.NotIn)
                and len(n.comparators)==1 and isinstance(n.comparators[0],ast.Tuple)):
                n.ops=[ast.NotEq()];n.comparators=[n.comparators[0].elts[0]]
            return n
    return Restore().visit(node)
rel='src/sim2act/goal_applications.py';old=nodes(before/rel);new=nodes(root/rel)
results={'scope':'Readonly stdlib AST/hash; closed qualified-second inputs and current source only. No running third outputs, product imports, tests, DB or network.',
 'unchanged_proof_functions':same_functions(rel,['source_scope_gate','_source_scope_gate','_verified_candidate']),
 'only_exact_production_marker_eligibility_changed':{n:dump(old[n])==dump(strip_production_eligibility(new[n])) for n in ['_journal_scope_anchor','verified_candidate']},
 'unchanged_existing_source_reads_file':(before/'src/sim2act/pb_natural_specs.py').read_bytes()==(root/'src/sim2act/pb_natural_specs.py').read_bytes(),
 'unchanged_PB_archive_functions':same_functions('src/sim2act/natural_source_archives.py',['_source_prefix','_source_bodies','_resolve_source_before_extraction']),
 'unchanged_default_resolver_body':same_functions('src/sim2act/production_evidence.py',['resolve_account']),
 'source_observations':[sha(root/p) for p in [rel,'src/sim2act/natural_source_archives.py','src/sim2act/pb_natural_specs.py','src/sim2act/spec_production.py','src/sim2act/production_trial_sender.py','tests/test_spec_production_controller.py']],
 'runtime_third_status':'NOT_READ_IN_PROGRESS','runtime_qualification':'PENDING; no seven-request PASS established by qualified-second',
 'archive_provenance_review':'Owned receipt_owner mode selects both actual body and reconstructed request; read checks same expected provenance; synthetic default retained.',
 'caveat':'SourceReads underlying current token requires exact same Store/connection/driver transaction/thread/write epoch AND test_only SQLite; no PG lease or performance conclusion.'}
checks=[*results['unchanged_proof_functions'].values(),*results['only_exact_production_marker_eligibility_changed'].values(),results['unchanged_existing_source_reads_file'],*results['unchanged_PB_archive_functions'].values(),*results['unchanged_default_resolver_body'].values()]
results['static_bridge_pass']=all(checks)
print(json.dumps(results,ensure_ascii=False,indent=2))
if not all(checks):raise AssertionError('Static bridge mismatch')
