"""Run directly: python tests/test_pure_value_validation.py -v.

Compile only validate_value and DomainError from AST. Never import sim2act,
Pydantic, a service, database, dispatcher, proof or recovery module.
Literal schemas and explicit expected outcomes provide the independent oracle.
"""

import ast
import math
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / "src/sim2act/contracts.py").read_text())
nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "validate_value"]
assert len(nodes) == 1
error_tree = ast.parse((ROOT / "src/sim2act/errors.py").read_text())
error = next(node for node in error_tree.body if isinstance(node, ast.ClassDef) and node.name == "DomainError")
namespace = {"math": math}
exec(compile(ast.Module(body=[error, *nodes], type_ignores=[]), "<isolated-value-validation>", "exec"), namespace)
validate = namespace["validate_value"]
DomainError = namespace["DomainError"]


class PureValueValidationTests(unittest.TestCase):
    def accepted(self, schema, value):
        self.assertIsNone(validate(schema, value))

    def rejected(self, schema, value, message, path="input"):
        with self.assertRaises(DomainError) as raised:
            validate(schema, value, path)
        self.assertEqual(raised.exception.public(), {
            "code": "INVALID_INPUT", "message": message, "safe_retry": False,
            "effect_known": True, "user_action": "Check status, configuration and permissions",
        })

    def test_unbounded_positive_and_negative_integers_without_float_conversion(self):
        with mock.patch.object(math, "isfinite", side_effect=AssertionError("integer converted to float")):
            for kind in ("integer", "number"):
                for value in (10**400, -(10**400), 0, 1, -1):
                    with self.subTest(kind=kind, sign=value > 0):
                        self.accepted({"type": kind}, value)

    def test_large_integer_rejected_as_other_scalar_types_without_overflow(self):
        for kind in ("string", "array", "object", "boolean", "null"):
            for value in (10**400, -(10**400)):
                with self.subTest(kind=kind, sign=value > 0):
                    self.rejected({"type": kind}, value, "input has wrong type")

    def test_bool_never_counts_as_integer_or_number(self):
        for kind in ("integer", "number"):
            for value in (False, True):
                with self.subTest(kind=kind, value=value):
                    self.rejected({"type": kind}, value, "input has wrong type")

    def test_finite_floats_remain_numbers_but_not_integers(self):
        for value in (0.0, -0.0, 1.0, -1.5, 1e308, -1e308, 5e-324):
            with self.subTest(value=value):
                self.accepted({"type": "number"}, value)
                self.rejected({"type": "integer"}, value, "input has wrong type")

    def test_nonfinite_floats_reject_with_existing_error_contract(self):
        for value in (float("nan"), float("inf"), -float("inf")):
            for kind in ("number", "integer", "string"):
                with self.subTest(kind=kind, value=value):
                    self.rejected({"type": kind}, value, "input has wrong type")

    def test_numeric_bounds_including_large_integers_remain_exact(self):
        for kind in ("integer", "number"):
            schema = {"type": kind, "minimum": -2, "maximum": 2}
            for value in (-2, 0, 2):
                self.accepted(schema, value)
            for value in (-3, 3, -(10**400), 10**400):
                self.rejected(schema, value, "Number outside bounds")
        self.accepted({"type": "number", "minimum": 0, "maximum": 1}, 0.5)
        self.rejected({"type": "number", "maximum": 1}, 1.5, "Number outside bounds")

    def test_numeric_enum_preserves_exact_type_identity(self):
        self.accepted({"type": "integer", "enum": [10**400]}, 10**400)
        self.rejected({"type": "integer", "enum": [10**400]}, -(10**400), "input outside enum")
        self.accepted({"type": "number", "enum": [1]}, 1)
        self.rejected({"type": "number", "enum": [1]}, 1.0, "input outside enum")
        self.accepted({"type": "number", "enum": [1.0]}, 1.0)
        self.rejected({"type": "number", "enum": [1.0]}, 1, "input outside enum")

    def test_string_type_enum_and_explicit_limits(self):
        self.accepted({"type": "string", "enum": ["csv", "txt"]}, "csv")
        self.rejected({"type": "string", "enum": ["csv", "txt"]}, "other", "input outside enum")
        self.accepted({"type": "string", "maxLength": 2}, "汉字")
        self.rejected({"type": "string", "maxLength": 2}, "汉字文", "String exceeds limit")
        self.accepted({"type": "string", "maxLength": 0}, "")
        self.rejected({"type": "string", "maxLength": 0}, "a", "String exceeds limit")

    def test_default_string_resource_limit_remains_32768(self):
        self.accepted({"type": "string"}, "x" * 32768)
        self.rejected({"type": "string"}, "x" * 32769, "String exceeds limit")

    def test_array_types_explicit_limits_and_recursive_errors(self):
        schema = {"type": "array", "items": {"type": "integer"}, "maxItems": 2}
        self.accepted(schema, [10**400, -(10**400)])
        self.rejected(schema, [1, 2, 3], "Array exceeds limit")
        self.rejected(schema, [1, True], "input[] has wrong type")
        self.rejected(schema, (1, 2), "input has wrong type")
        self.accepted({"type": "array", "items": {"type": "string"}, "maxItems": 0}, [])
        self.rejected({"type": "array", "items": {"type": "string"}, "maxItems": 0}, ["x"], "Array exceeds limit")

    def test_default_array_resource_limit_remains_1000(self):
        schema = {"type": "array", "items": {"type": "integer"}}
        self.accepted(schema, [1] * 1000)
        self.rejected(schema, [1] * 1001, "Array exceeds limit")

    def test_closed_objects_required_fields_and_nested_values(self):
        schema = {"type": "object", "properties": {
            "count": {"type": "integer"}, "kind": {"type": "string", "enum": ["csv"]}},
            "required": ["count"], "additionalProperties": False}
        self.accepted(schema, {"count": 10**400})
        self.accepted(schema, {"count": 1, "kind": "csv"})
        self.rejected(schema, {}, "input has unknown or missing field")
        self.rejected(schema, {"count": 1, "extra": 2}, "input has unknown or missing field")
        self.rejected(schema, {"count": True}, "input.count has wrong type")
        self.rejected(schema, {"count": 1, "kind": "txt"}, "input.kind outside enum")

    def test_boolean_and_null_types(self):
        for value in (True, False):
            self.accepted({"type": "boolean"}, value)
        for value in (0, 1, "true", None):
            self.rejected({"type": "boolean"}, value, "input has wrong type")
        self.accepted({"type": "null"}, None)
        for value in (False, 0, "", []):
            self.rejected({"type": "null"}, value, "input has wrong type")

    def test_nullable_values_and_enum_rules_unchanged(self):
        for kind in ("integer", "boolean"):
            self.accepted({"type": kind, "nullable": True}, None)
            self.accepted({"type": kind, "nullable": True, "enum": [None]}, None)
            self.rejected({"type": kind, "nullable": False}, None, "input has wrong type")
        self.rejected({"type": "integer", "nullable": True, "enum": [1]}, None, "input outside enum")
        self.accepted({"type": "integer", "nullable": True}, 10**400)

    def test_custom_error_path_and_public_error_contract(self):
        self.rejected({"type": "integer"}, "1", "output.count has wrong type", "output.count")

    def test_no_business_imports(self):
        self.assertEqual([name for name in sys.modules if name == "sim2act" or name.startswith("sim2act.")
                          or name in {"pydantic", "sqlalchemy"}], [])


if __name__ == "__main__":
    unittest.main()
