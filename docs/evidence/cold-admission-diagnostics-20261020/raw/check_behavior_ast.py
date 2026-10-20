"""Read-only statement-tree projection; does not import/execute product code.

Projection removes only the explicitly added diagnostic statements/wrappers
and inlines the once-materialized stop value at its original expression.
This is an order check, not proof of zero timing overhead or PB qualification.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

BASE = 'a952866022a3976eedf045408778ea901760646b'
PATH = 'src/sim2act/natural_spec_runtime.py'
before = subprocess.check_output(['git', 'show', BASE + ':' + PATH])
after = Path(PATH).read_bytes()


def method(tree, cls, name):
    return next(n for c in tree.body if isinstance(c, ast.ClassDef) and c.name == cls
        for n in c.body if isinstance(n, ast.FunctionDef) and n.name == name)


class DiagnosticProjection(ast.NodeTransformer):
    def visit_Assign(self, node):
        if any(isinstance(t, ast.Name) and t.id in {'diagnostic', 'finite_names', 'stopped'}
                for t in node.targets):
            return None
        if any(isinstance(t, ast.Attribute) and t.attr == '_diagnostic_counts' for t in node.targets):
            return None
        return self.generic_visit(node)

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
            f = node.value.func
            if isinstance(f.value, ast.Name) and f.value.id in {'finite_names', 'diagnostic'}:
                return None
        return self.generic_visit(node)

    def visit_With(self, node):
        call = node.items[0].context_expr
        if (len(node.items) == 1 and isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute) and call.func.attr == 'stage'
                and isinstance(call.func.value, ast.Name) and call.func.value.id == 'diagnostic'):
            return [self.visit(n) for n in node.body]
        return self.generic_visit(node)

    def visit_Try(self, node):
        if (len(node.body) == 1 and isinstance(node.body[0], ast.AugAssign)
                and isinstance(node.body[0].target, ast.Subscript)
                and isinstance(node.body[0].target.value, ast.Attribute)
                and node.body[0].target.value.attr == '_diagnostic_counts'):
            return None
        if (len(node.handlers) == 1 and isinstance(node.handlers[0].type, ast.Name)
                and node.handlers[0].type.id == 'DomainError'):
            assert len(node.body) == 1
            return [self.visit(node.body[0])]
        return self.generic_visit(node)

    def visit_Name(self, node):
        if node.id == 'stopped' and isinstance(node.ctx, ast.Load):
            return ast.parse('self.worker.stop.is_set()', mode='eval').body
        return node


old, new = ast.parse(before), ast.parse(after)
checks = []
for cls, name in [('_ColdGraphRead', '__init__'), ('_ColdGraphRead', 'check'),
        ('_ColdGraphRead', 'input_key'), ('_ColdTrialGraph', 'commit')]:
    original = ast.dump(method(old, cls, name), include_attributes=False)
    projected = ast.dump(DiagnosticProjection().visit(method(new, cls, name)), include_attributes=False)
    assert original == projected, (cls, name)
    checks.append(dict(method=cls + '.' + name, statement_tree_equal=True))
print(json.dumps(dict(classification='STATIC_DIAGNOSTIC_PROJECTION_NOT_RUNTIME_EQUIVALENCE_PROOF',
    baseline=BASE, before_sha256=hashlib.sha256(before).hexdigest(),
    after_sha256=hashlib.sha256(after).hexdigest(), checks=checks,
    product_executions=0, new_graph_calls=0), indent=2))
