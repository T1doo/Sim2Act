"""Synthetic pure CSV checks; never import sim2act or its business dependencies.

Only the two CSV functions, their three pure helpers, and DomainError are compiled
from AST. The independent oracle parses decimal text into scaled Python integers;
it never uses Decimal addition or any existing business/proof oracle.
Run directly: python3 tests/test_csv_precision.py -v
Functional tests use portable stdlib code. The AS/CPU resource probe is Linux-only
and unittest explicitly reports it as skipped elsewhere; that is not Windows
resource-limit validation. Direct --bounded-probe refuses unsupported platforms.
"""

import ast
import csv
import hashlib
import io
import json
import random
import re
import subprocess
import sys
import unittest
from unittest import mock
from decimal import Context, Decimal, DecimalException, DefaultContext, DivisionByZero, Inexact, InvalidOperation, Overflow, ROUND_DOWN, ROUND_HALF_EVEN, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS = {"_bounded_csv_reader", "_csv_decimal_context", "_exact_csv_sum", "csv_column_options", "aggregate_csv_content"}
tree = ast.parse((ROOT / "src/sim2act/tools.py").read_text())
nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS]
assert {node.name for node in nodes} == FUNCTIONS
error_tree = ast.parse((ROOT / "src/sim2act/errors.py").read_text())
error_node = next(node for node in error_tree.body if isinstance(node, ast.ClassDef) and node.name == "DomainError")
namespace = {"csv": csv, "hashlib": hashlib, "io": io, "Context": Context, "Decimal": Decimal,
             "DecimalException": DecimalException, "DivisionByZero": DivisionByZero, "Inexact": Inexact,
             "InvalidOperation": InvalidOperation, "Overflow": Overflow, "ROUND_HALF_EVEN": ROUND_HALF_EVEN}
exec(compile(ast.Module(body=[error_node, *nodes], type_ignores=[]), "<isolated-csv-functions>", "exec"), namespace)
aggregate = namespace["aggregate_csv_content"]
guidance = namespace["csv_column_options"]
DomainError = namespace["DomainError"]


def digits_integer(digits):
    # Chunking avoids Python's int/string conversion limit without changing it.
    value = 0
    for offset in range(0, len(digits), 9):
        chunk = digits[offset:offset + 9]
        value = value * 10 ** len(chunk) + int(chunk)
    return value


def fixed_number(text):
    match = re.fullmatch(r"\s*([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d+))?\s*", text)
    if not match:
        raise ValueError("non-decimal oracle input")
    sign, whole, fraction, fraction_only, exponent = match.groups()
    fraction = fraction if whole is not None else fraction_only
    fraction = fraction or ""
    coefficient = digits_integer((whole or "") + fraction)
    return (-coefficient if sign == "-" else coefficient), int(exponent or "0") - len(fraction)


def integer_oracle(content, column):
    rows = list(csv.reader(io.StringIO(content)))
    index = rows[0].index(column)
    numbers = [fixed_number(row[index]) for row in rows[1:] if row]
    scale = min([0] + [exponent for _, exponent in numbers])
    return sum(coefficient * 10 ** (exponent - scale) for coefficient, exponent in numbers), scale, len(numbers)


def csv_text(values, name="n"):
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([name])
    writer.writerows([[value] for value in values])
    return output.getvalue()


class CsvPrecisionTests(unittest.TestCase):
    def exact(self, content, column="n"):
        result = aggregate(content, "synthetic-resource", column)
        coefficient, scale, count = integer_oracle(content, column)
        actual, actual_scale = fixed_number(result["sum"])
        common_scale = min(scale, actual_scale)
        self.assertEqual(actual * 10 ** (actual_scale - common_scale), coefficient * 10 ** (scale - common_scale))
        self.assertEqual(result, {"resource_id": "synthetic-resource", "column": column, "count": count,
                                  "sum": result["sum"], "source_hash": hashlib.sha256(content.encode()).hexdigest()})
        guide = guidance(content)
        self.assertEqual(guide["row_count"], count)
        self.assertIsNone(guide["error"])
        self.assertTrue(next(item for item in guide["columns"] if item["name"] == column)["numeric"])
        return result

    def invalid(self, content, column="n"):
        with self.assertRaises(DomainError) as raised:
            aggregate(content, "synthetic-resource", column)
        self.assertEqual(raised.exception.code, "INVALID_INPUT")
        return guidance(content)

    def test_reproduced_big_integer_plus_one(self):
        result = self.exact("n\n10000000000000000000000000000\n1\n")
        self.assertEqual(result["sum"], "10000000000000000000000000001")

    def test_normal_result_contract_and_empty_column(self):
        for values, expected in [(["1.20", "2.30"], "3.50"), (["1e2", "2e2"], "300"),
                                 (["1e30"], "1.000000000000000000000000000E+30"),
                                 (["-0.00", "0.00"], "0.00"), (["1000.00", "-1000.00"], "0.00"), ([], "0")]:
            with self.subTest(values=values):
                self.assertEqual(self.exact(csv_text(values))["sum"], expected)

    def test_fractional_digits_beyond_default_precision(self):
        for values in [["0." + "0" * 35 + "1", "0." + "0" * 35 + "2"],
                       ["12345678901234567890.12345678901234567890", "0.00000000000000000001"],
                       ["-0.000000000000000000000000000001", "2.000000000000000000000000000002"]]:
            with self.subTest(values=values):
                self.exact(csv_text(values))

    def test_positive_negative_cancellation_and_order(self):
        for values in [["1e30", "1", "-1e30"], ["1e30", "-1e30", "1"],
                       ["-1e100", "-1", "1e100"], ["1e1000", "0.125", "-1e1000"]]:
            with self.subTest(values=values):
                self.exact(csv_text(values))

    def test_large_and_small_exponents_with_exact_oracle(self):
        for values in [["1e1000", "1"], ["1e-1000", "2e-1000"],
                       ["1e300", "-1e300", "1e-300"], [" +1.5E+2 ", ".25e-2", "5."]]:
            with self.subTest(values=values):
                self.exact(csv_text(values))

    def test_nonfinite_and_missing_values_rejected_consistently(self):
        for value in ["NaN", "sNaN", "Infinity", "-Infinity", "text", ""]:
            with self.subTest(value=value):
                guide = self.invalid(csv_text(["1", value]))
                self.assertEqual(guide["row_count"], 2)
                self.assertFalse(guide["columns"][0]["numeric"])
                self.assertIsNotNone(guide["columns"][0]["reason"])
        guide = self.invalid("other\n")  # Missing requested column.
        self.assertEqual(guide["row_count"], 0)

    def test_structural_errors_and_independent_column_guidance(self):
        for content in ["n,n\n1,2\n", "n\n1,2\n", "n,other\n1\n"]:
            with self.subTest(content=content):
                # The final CSV has a valid n but a missing requested other.
                self.invalid(content, "other" if content.startswith("n,other") else "n")
        guide = guidance("good,bad,large\n1,text,1e1000000000\n2,3,1\n")
        self.assertEqual([item["numeric"] for item in guide["columns"]], [True, False, False])
        self.exact("good,bad,large\n1,text,1e1000000000\n2,3,1\n", "good")

    def test_exponent_amplification_has_explicit_bounded_failure(self):
        for value in ["1e32767", "1e-32768", "1e1000000000", "1e-1000000000", "0e1000000000", "1e999999999999999999999"]:
            with self.subTest(value=value):
                guide = self.invalid(csv_text([value]))
                self.assertFalse(guide["columns"][0]["numeric"])
        # Cancellation cannot require unbounded intermediate precision either.
        self.invalid(csv_text(["1e1000000000", "1", "-1e1000000000"]))

    def test_maximum_input_length_and_working_precision_boundary(self):
        content = "n\n" + "9" * 32765 + "\n"
        self.assertEqual(len(content), 32768)
        self.assertEqual(len(self.exact(content)["sum"]), 32765)
        self.assertEqual(len(self.exact(csv_text(["-1e32766", "-1"]))["sum"]), 32768)

    def test_oversized_or_nontext_content_rejected_before_parsing(self):
        for content in ["n\n" + "9" * 32766 + "\n", None, 123, b"n\n1\n"]:
            with self.subTest(kind=type(content).__name__):
                guide = self.invalid(content)
                self.assertIsNone(guide["row_count"])
                self.assertEqual(guide["columns"], [])
                self.assertIn("32768", guide["error"])

    def test_thousand_rows_and_explicit_row_limit(self):
        content = csv_text(["1.2345678901234567890123456789"] * 1000)
        self.assertLessEqual(len(content), 32768)
        self.exact(content)
        guide = self.invalid(csv_text(["1"] * 1001))
        self.assertEqual(guide["columns"], [])
        self.assertIn("1000", guide["error"])

    def test_ambient_decimal_context_cannot_round_or_change_context_flags(self):
        with localcontext() as ambient:
            ambient.prec = 2
            ambient.rounding = ROUND_DOWN
            ambient.Emax = 2
            ambient.Emin = -2
            ambient.traps[Inexact] = True
            ambient.clear_flags()
            before = (ambient.prec, ambient.rounding, ambient.Emax, ambient.Emin, dict(ambient.flags))
            self.exact(csv_text(["1e100", "1", "1e-100"]))
            self.assertEqual((ambient.prec, ambient.rounding, ambient.Emax, ambient.Emin, dict(ambient.flags)), before)

    def test_serialization_ignores_ambient_capitals_without_rounding(self):
        for values in [["1e30"], ["1e-30"], ["1e30", "1"], [], ["1.20", "2.30"],
                       ["1.23456789012345678901234567890123456789e-50", "1e-90"]]:
            with self.subTest(values=values):
                results = []
                for capitals in [0, 1]:
                    with localcontext() as ambient:
                        ambient.capitals = capitals
                        ambient.prec = 1
                        ambient.Emax = 2
                        ambient.Emin = -2
                        ambient.traps[Inexact] = True
                        ambient.clear_flags()
                        results.append(self.exact(csv_text(values)))
                        self.assertEqual(ambient.capitals, capitals)
                        self.assertFalse(any(ambient.flags.values()))
                self.assertEqual(results[0], results[1])
                self.assertNotIn("e", results[0]["sum"])
                if values == ["1e30"]:
                    self.assertEqual(results[0]["sum"], "1.000000000000000000000000000E+30")
        self.assertFalse(any(name == "sim2act" or name.startswith("sim2act.") or name == "sqlalchemy" for name in sys.modules))

    def test_resource_probe_refuses_unsupported_platform_explicitly(self):
        # Simulate the guard only, never simulate Windows execution or limits.
        with mock.patch.object(sys, "platform", "win32"):
            with self.assertRaisesRegex(RuntimeError, "Linux-only"):
                bounded_probe()

    def test_mutated_default_context_cannot_change_results_or_error_contract(self):
        contents = [csv_text(values) for values in [["1e30"], ["1e30", "1"],
                    ["1.23456789012345678901234567890123456789e-50", "1e-90"], []]]
        baseline = [(aggregate(content, "synthetic-resource", "n"), guidance(content)) for content in contents]
        invalid_contents = [csv_text(["1e1000000000"]), csv_text(["NaN"]), csv_text(["text"])]
        invalid_baseline = [self.invalid(content) for content in invalid_contents]
        def rejection_contract(content):
            try:
                aggregate(content, "synthetic-resource", "n")
            except DomainError as error:
                return error.public()
            self.fail("expected INVALID_INPUT")
        error_baseline = [rejection_contract(content) for content in invalid_contents]
        original = DefaultContext.copy()
        try:
            DefaultContext.prec = 1
            DefaultContext.rounding = ROUND_DOWN
            DefaultContext.Emin = -1
            DefaultContext.Emax = 1
            DefaultContext.capitals = 0
            DefaultContext.clamp = 1
            for mapping in [DefaultContext.flags, DefaultContext.traps]:
                for signal in mapping:
                    mapping[signal] = True
            configured_flags = DefaultContext.flags.copy()
            configured_traps = DefaultContext.traps.copy()
            self.assertEqual([(aggregate(content, "synthetic-resource", "n"), guidance(content)) for content in contents], baseline)
            self.assertEqual([self.invalid(content) for content in invalid_contents], invalid_baseline)
            self.assertEqual([rejection_contract(content) for content in invalid_contents], error_baseline)
            self.assertEqual(DefaultContext.flags, configured_flags)
            self.assertEqual(DefaultContext.traps, configured_traps)
            self.assertEqual((DefaultContext.prec, DefaultContext.Emin, DefaultContext.Emax, DefaultContext.capitals, DefaultContext.clamp), (1, -1, 1, 0, 1))
        finally:
            for option in ["prec", "rounding", "Emin", "Emax", "capitals", "clamp"]:
                setattr(DefaultContext, option, getattr(original, option))
            DefaultContext.flags = original.flags.copy()
            DefaultContext.traps = original.traps.copy()

    def test_seeded_synthetic_cases_against_independent_integer_oracle(self):
        generator = random.Random(771)
        for case in range(250):
            values = []
            for _ in range(generator.randint(1, 20)):
                digits = "".join(str(generator.randrange(10)) for _ in range(generator.randint(1, 80)))
                values.append(("-" if generator.randrange(2) else "") + digits + "e" + str(generator.randint(-100, 100)))
            with self.subTest(case=case):
                self.exact(csv_text(values))

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux-only AS/CPU resource probe; portable functional tests remain executable")
    def test_resource_bounded_subprocess_and_no_business_imports(self):
        child = subprocess.run([sys.executable, __file__, "--bounded-probe"], capture_output=True, text=True, timeout=10)
        self.assertEqual(child.returncode, 0, child.stderr)
        report = json.loads(child.stdout)
        self.assertEqual(report["memory_limit_bytes"], 128 * 1024 * 1024)
        self.assertEqual(report["cpu_limit_seconds"], 5)
        self.assertEqual(report["probes"], 8)
        self.assertEqual(report["business_imports"], [])
        self.assertTrue(report["platform"].startswith("linux"))
        self.assertFalse(any(name == "sim2act" or name.startswith("sim2act.") or name == "sqlalchemy" for name in sys.modules))


def bounded_probe():
    if not sys.platform.startswith("linux"):
        raise RuntimeError("Linux-only AS/CPU resource probe; run portable functional tests instead")
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    inputs = ["n\n" + "9" * 32765 + "\n", csv_text(["1.2345678901234567890123456789"] * 1000),
              csv_text(["-1e32766", "-1"]), csv_text(["1e1000000000"]), csv_text(["1e-1000000000"]),
              csv_text(["1e999999999999999999999"]), csv_text(["0e1000000000"]), "n\n" + "9" * 32766 + "\n"]
    for content in inputs:
        guidance(content)
        try:
            aggregate(content, "synthetic-resource", "n")
        except DomainError as error:
            assert error.code == "INVALID_INPUT"
    print(json.dumps({"platform": sys.platform, "memory_limit_bytes": 128 * 1024 * 1024, "cpu_limit_seconds": 5,
                      "probes": len(inputs), "business_imports": [name for name in sys.modules if name == "sim2act" or name.startswith("sim2act.") or name == "sqlalchemy"]}))


if __name__ == "__main__":
    if sys.argv[1:] == ["--bounded-probe"]:
        bounded_probe()
    else:
        unittest.main()
