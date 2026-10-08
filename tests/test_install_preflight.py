"""Synthetic, offline checks runnable without pytest or installed Sim2Act."""

import contextlib
import importlib.metadata
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install_preflight.py"
SPEC = importlib.util.spec_from_file_location("install_preflight", SCRIPT)
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)

SECRET = "SYNTHETIC_PRIVATE_SENTINEL"
VALID_CONFIG = (
    "# local synthetic config\n"
    "SIM2ACT_DATABASE_URL=postgresql+psycopg://user:" + SECRET + "@localhost/test\n"
    "SIM2ACT_DATA_DIR=" + SECRET + "\n"
    "SIM2ACT_INTERN_TOKEN=" + SECRET + "\n"
)


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / ".env"
        self.config.write_text(VALID_CONFIG, encoding="utf-8")
        (self.root / "pyproject.toml").write_text("", encoding="utf-8")
        for name in ("requirements.lock", "requirements-windows.lock"):
            (self.root / name).write_text("example-package==1.0\n", encoding="utf-8")

    def test_missing_unreadable_and_invalid_encoding_are_safe(self):
        for path in (self.root / "absent", self.root):
            checks = preflight.config_checks(path)
            self.assertEqual(checks[0]["status"], "BLOCKED")
        self.config.write_bytes(b"\xff" + SECRET.encode())
        self.assertNotIn(SECRET, json.dumps(preflight.config_checks(self.config)))

    def test_bom_and_equals_in_values_match_loader(self):
        self.config.write_text(
            "\ufeff" + VALID_CONFIG + "INTERN_API_TOKEN=a=b=c\n", encoding="utf-8"
        )
        checks = preflight.config_checks(self.config)
        self.assertTrue(all(item["status"] == "PASS" for item in checks))
        self.assertNotIn(SECRET, json.dumps(checks))

    def test_malformed_lines_and_empty_required_values(self):
        self.config.write_text(" export " + SECRET + "\nSIM2ACT_DATABASE_URL=\n", encoding="utf-8")
        checks = preflight.config_checks(self.config)
        self.assertTrue(all(item["status"] == "BLOCKED" for item in checks))
        self.assertNotIn(SECRET, json.dumps(checks))

    def test_config_limit(self):
        self.config.write_text("#" + "x" * 65536, encoding="utf-8")
        self.assertEqual(preflight.config_checks(self.config)[0]["status"], "BLOCKED")

    def test_setup_does_not_read_package_metadata(self):
        with patch.object(preflight, "dependency_checks", side_effect=AssertionError):
            checks = preflight.collect("setup", ".env", self.root, "Linux", lambda _: "/synthetic")
        self.assertTrue(all(item["status"] == "PASS" for item in checks))
        self.assertFalse(any(item["check"] == "powershell" for item in checks))

    def test_windows_missing_commands_actionable(self):
        checks = preflight.collect("setup", ".env", self.root, "Windows", lambda _: None)
        by_name = {item["check"]: item for item in checks}
        for name in ("git", "powershell", "python_launcher"):
            self.assertEqual(by_name[name]["status"], "BLOCKED")
            self.assertNotEqual(by_name[name]["next_step"], "None.")

    def test_wrong_python_or_architecture_blocks(self):
        with (
            patch.object(preflight.sys, "version_info", (3, 11)),
            patch.object(preflight.struct, "calcsize", return_value=4),
        ):
            checks = preflight.collect("setup", ".env", self.root, "Windows", lambda _: "present")
        self.assertEqual([item["status"] for item in checks[:2]], ["BLOCKED", "BLOCKED"])

    def test_start_uses_platform_lock_and_requires_repo_venv(self):
        with patch.object(preflight, "dependency_checks", return_value=[]) as dependencies:
            checks = preflight.collect("start", ".env", self.root, "Windows", lambda _: "present")
        dependencies.assert_called_once_with(self.root / "requirements-windows.lock")
        self.assertEqual(
            next(c for c in checks if c["check"] == "virtual_environment")["status"], "BLOCKED"
        )
        with (
            patch.object(preflight.sys, "prefix", str(self.root / ".venv")),
            patch.object(preflight, "dependency_checks", return_value=[]),
        ):
            checks = preflight.collect("start", ".env", self.root, "Linux", lambda _: "present")
        self.assertTrue(all(c["status"] == "PASS" for c in checks))

    def test_missing_mismatched_and_valid_packages(self):
        lock = self.root / "requirements.lock"

        def missing(name):
            raise importlib.metadata.PackageNotFoundError(SECRET)

        self.assertEqual(preflight.dependency_checks(lock, missing)[0]["status"], "BLOCKED")
        self.assertEqual(
            preflight.dependency_checks(lock, lambda _: "wrong")[0]["status"], "BLOCKED"
        )
        self.assertEqual(preflight.dependency_checks(lock, lambda _: "1.0")[0]["status"], "PASS")
        self.assertNotIn(SECRET, json.dumps(preflight.dependency_checks(lock, missing)))

    def test_bad_lock_or_metadata_never_echoes_error(self):
        lock = self.root / "requirements.lock"

        def broken(name):
            raise ValueError(SECRET)

        self.assertNotIn(SECRET, json.dumps(preflight.dependency_checks(lock, broken)))
        for text in ("", "package @ https://" + SECRET):
            lock.write_text(text, encoding="utf-8")
            checks = preflight.dependency_checks(lock, lambda _: "1.0")
            self.assertEqual(checks[0]["status"], "BLOCKED")
            self.assertNotIn(SECRET, json.dumps(checks))

    def test_cli_output_exit_codes_redaction_and_no_changes(self):
        before = self.config.read_bytes()
        for ok in (True, False):
            checks = [preflight.result("synthetic", ok, "Safe fixed message.", "Safe action.")]
            for args in ([], ["--json"]):
                output = io.StringIO()
                with (
                    patch.object(preflight, "collect", return_value=checks),
                    contextlib.redirect_stdout(output),
                ):
                    code = preflight.main(args)
                self.assertEqual(code, 0 if ok else 1)
                self.assertNotIn(SECRET, output.getvalue())
                if args:
                    self.assertEqual(
                        json.loads(output.getvalue())["status"], "PASS" if ok else "BLOCKED"
                    )
        self.assertEqual(self.config.read_bytes(), before)

    def test_real_cli_reads_only_explicit_config_and_redacts_secrets(self):
        # Keep the real CLI rooted in the synthetic repository, independent of
        # whether the caller uses the actual checkout's valid .venv.
        script = self.root / "scripts" / "install_preflight.py"
        script.parent.mkdir()
        script.write_bytes(SCRIPT.read_bytes())
        before = self.config.read_bytes()
        inventory = sorted(path.name for path in self.root.iterdir())
        for stage in ("setup", "start"):
            child = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--stage",
                    stage,
                    "--config",
                    str(self.config),
                    "--json",
                ],
                cwd=self.root,
                env={**os.environ, "INTERN_API_TOKEN": SECRET},
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertNotIn(SECRET, child.stdout + child.stderr)
            report = json.loads(child.stdout)
            self.assertEqual(child.returncode, 0 if report["status"] == "PASS" else 1)
            checks = {item["check"]: item["status"] for item in report["checks"]}
            for name in ("config_format", "sim2act_database_url", "sim2act_data_dir"):
                self.assertEqual(checks[name], "PASS")
            if stage == "start":
                self.assertEqual(checks["virtual_environment"], "BLOCKED")
                self.assertEqual(child.returncode, 1)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), inventory)

    def test_explicit_config_is_repo_relative_not_cwd(self):
        alternate = self.root / "private.env"
        alternate.write_text(VALID_CONFIG, encoding="utf-8")
        self.config.unlink()
        checks = preflight.collect("setup", "private.env", self.root, "Linux", lambda _: "present")
        self.assertTrue(all(c["status"] == "PASS" for c in checks))


if __name__ == "__main__":
    unittest.main()
