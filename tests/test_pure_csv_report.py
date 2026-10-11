"""Run directly: python tests/test_pure_csv_report.py -v.

AST isolation selects render, obj, original INPUT/OUTPUT declarations, two pure
contract validators, and DomainError. No business package or service is imported.
The render function's local import is replaced only by those selected validators.
"""

import ast
import copy
import math
import re
import sys
import unittest
from decimal import Decimal, DecimalException
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
namespace = {"math": math, "re": re, "Decimal": Decimal, "DecimalException": DecimalException}
error_tree = ast.parse((ROOT / "src/sim2act/errors.py").read_text())
error = next(node for node in error_tree.body if isinstance(node, ast.ClassDef) and node.name == "DomainError")
contract_tree = ast.parse((ROOT / "src/sim2act/contracts.py").read_text())
validators = [node for node in contract_tree.body if isinstance(node, ast.FunctionDef)
              and node.name in {"resource_id", "validate_value"}]
assert {node.name for node in validators} == {"resource_id", "validate_value"}
report_tree = ast.parse((ROOT / "src/sim2act/csv_reports.py").read_text())
selected = []
for node in report_tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in {"obj", "render"}:
        if node.name == "render":
            imports = [child for child in node.body if isinstance(child, ast.ImportFrom)]
            assert len(imports) == 1 and imports[0].module == "contracts"
            assert [alias.name for alias in imports[0].names] == ["resource_id", "validate_value"]
            node.body = [child for child in node.body if child is not imports[0]]
        selected.append(node)
    elif isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
            and target.id in {"FIELDS", "INPUT", "OUTPUT"} for target in node.targets):
        selected.append(node)
assert {node.name for node in selected if isinstance(node, ast.FunctionDef)} == {"obj", "render"}
exec(compile(ast.Module(body=[error, *validators, *selected], type_ignores=[]),
             "<isolated-csv-report>", "exec"), namespace)
render = namespace["render"]
validate = namespace["validate_value"]
DomainError = namespace["DomainError"]
INPUT, OUTPUT = namespace["INPUT"], namespace["OUTPUT"]


def fixture(total="3.50", column="n", count=1):
    return {"resource_id": "res_" + "1" * 32, "column": column, "count": count,
            "sum": total, "source_hash": "a" * 64}


class PureCsvReportTests(unittest.TestCase):
    def accepted(self, value, expected_text):
        before = copy.deepcopy(value)
        result = render(value)
        self.assertEqual(value, before)
        self.assertIsNot(result, value)
        self.assertEqual(result, {**before, "text": expected_text})
        self.assertIsNone(validate(OUTPUT, result, "output"))
        self.assertLessEqual(len(result["text"]), 32768)
        return result

    def rejected(self, value, code, message=None):
        before = copy.deepcopy(value)
        with self.assertRaises(DomainError) as raised:
            render(value)
        self.assertEqual(value, before)
        self.assertEqual(raised.exception.code, code)
        if message is not None:
            self.assertEqual(raised.exception.message, message)

    def test_original_input_output_declarations_are_unchanged(self):
        fields = {"resource_id": {"type": "string"}, "column": {"type": "string"},
                  "count": {"type": "integer"}, "sum": {"type": "string"},
                  "source_hash": {"type": "string"}}
        self.assertEqual(INPUT, {"type": "object", "properties": fields,
                         "required": list(fields), "additionalProperties": False})
        output_fields = {**fields, "text": {"type": "string"}}
        self.assertEqual(OUTPUT, {"type": "object", "properties": output_fields,
                         "required": list(output_fields), "additionalProperties": False})

    def test_old_short_text_is_verbatim_for_positive_negative_decimal_scientific(self):
        for total in ("3.50", "-3.50", "+1.20", "-0.00", "1E+30", "1e-30", " 2.00 "):
            with self.subTest(total=total):
                self.accepted(fixture(total), "列 n；行数 1；合计 " + total)

    def test_256_and_reproduced_257_digit_sums_keep_complete_text(self):
        for size in (256, 257):
            with self.subTest(size=size):
                total = "9" * size
                self.accepted(fixture(total), "列 n；行数 1；合计 " + total)

    def test_full_text_exactly_32768_is_not_summarized(self):
        prefix = "列 n；行数 1；合计 "
        total = "9" * (32768 - len(prefix))
        expected = prefix + total
        self.assertEqual(len(expected), 32768)
        self.accepted(fixture(total), expected)

    def test_full_text_over_limit_by_one_is_explicit_summary(self):
        prefix = "列 n；行数 1；合计 "
        total = "9" * (32769 - len(prefix))
        self.assertEqual(len(prefix + total), 32769)
        self.accepted(fixture(total), "列 n；行数 1；合计摘要：完整合计见sum字段")

    def test_maximum_sum_length_is_preserved_in_its_original_field(self):
        total = "9" * 32768
        result = self.accepted(fixture(total), "列 n；行数 1；合计摘要：完整合计见sum字段")
        self.assertEqual(len(result["sum"]), 32768)

    def test_long_positive_negative_fraction_and_scientific_text_are_not_rewritten(self):
        totals = ("9" * 32760, "-" + "9" * 32759,
                  "0." + "1" * 32758, "1." + "0" * 32753 + "E+30")
        for total in totals:
            with self.subTest(prefix=total[:3]):
                self.assertGreater(len("列 n；行数 1；合计 " + total), 32768)
                self.accepted(fixture(total), "列 n；行数 1；合计摘要：完整合计见sum字段")

    def test_200_character_column_1000_rows_and_text_boundary(self):
        column = "列" * 200
        prefix = "列 " + column + "；行数 1000；合计 "
        total = "9" * (32768 - len(prefix))
        self.accepted(fixture(total, column, 1000), prefix + total)
        self.accepted(fixture(total + "9", column, 1000),
                      "列 " + column + "；行数 1000；合计摘要：完整合计见sum字段")

    def test_empty_and_whitespace_columns_keep_original_policy_and_text(self):
        self.accepted(fixture("0", "", 0), "列 ；行数 0；合计 0")
        self.accepted(fixture("1", " \t "), "列  \t ；行数 1；合计 1")

    def test_oversized_sum_rejects_at_original_input_limit(self):
        self.rejected(fixture("9" * 32769), "INVALID_INPUT", "String exceeds limit")

    def test_nonfinite_and_non_decimal_sum_rejection_is_unchanged(self):
        for total in ("NaN", "sNaN", "Infinity", "-Infinity", "", "text"):
            with self.subTest(total=total):
                self.rejected(fixture(total), "VERIFICATION_FAILED", "Invalid typed CSV report provenance")

    def test_count_type_and_range_checks_are_unchanged(self):
        for count in (-1, 1001, 10**400):
            self.rejected(fixture(count=count), "VERIFICATION_FAILED")
        for count in (True, 1.0, "1"):
            self.rejected(fixture(count=count), "INVALID_INPUT")
        self.accepted(fixture("0", count=0), "列 n；行数 0；合计 0")

    def test_resource_id_hash_and_column_checks_are_unchanged(self):
        value = fixture(); value["resource_id"] = "bad"
        self.rejected(value, "INVALID_INPUT", "Expected logical resource ID")
        for digest in ("a" * 63, "a" * 65, "A" * 64, "g" * 64):
            value = fixture(); value["source_hash"] = digest
            self.rejected(value, "VERIFICATION_FAILED")
        self.rejected(fixture(column="n" * 201), "VERIFICATION_FAILED")

    def test_required_fields_unknown_fields_and_types_are_unchanged(self):
        for field in fixture():
            value = fixture(); del value[field]
            self.rejected(value, "INVALID_INPUT")
        value = fixture(); value["extra"] = "x"
        self.rejected(value, "INVALID_INPUT")
        for field in ("resource_id", "column", "sum", "source_hash"):
            value = fixture(); value[field] = 1
            self.rejected(value, "INVALID_INPUT")

    def test_no_business_imports(self):
        self.assertEqual([name for name in sys.modules if name == "sim2act" or name.startswith("sim2act.")
                          or name in {"pydantic", "sqlalchemy"}], [])


if __name__ == "__main__":
    unittest.main()
