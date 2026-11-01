"""Build a complete same-revision portable directory; never execute its desktop EXE."""

import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

import httpx

from candidate_wheel import MODULES, record
from package_windows_portable import build
from windows_pe import inspect

ROOT = Path(__file__).resolve().parents[1]


def main():
    assert sys.platform == "win32" and sys.version_info[:3] == (3, 12, 10)
    out = Path(os.environ["RUNNER_TEMP"]) / ("sim2act-full-" + os.environ["GITHUB_RUN_ID"])
    out.mkdir(exist_ok=False)
    payload = out / "payload"
    payload.mkdir()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert commit == os.environ["GITHUB_SHA"]
    report = dict(source_commit=commit, status="STARTED", desktop_executed=False,
                  real_model_requests=0, database="SYNTHETIC_SQLITE_ONLY", stages=[])
    until = time.monotonic() + 210
    target = os.environ.get("GITHUB_ENV")
    if target:
        with open(target, "a", encoding="utf-8") as output:
            output.write("SIM2ACT_FULL_PAYLOAD=" + str(payload) + "\n")

    def save():
        (payload / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def run(name, command, timeout=120):
        report["stages"].append(dict(name=name, state="RUNNING"))
        save()
        print("START " + name, flush=True)
        remaining = until - time.monotonic()
        if remaining <= 0:
            raise RuntimeError("Finite build-step budget exhausted; no new process started")
        try:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=min(timeout, remaining))
        except subprocess.TimeoutExpired as error:
            (payload / (name + ".stdout.log")).write_bytes(error.stdout or b"")
            (payload / (name + ".stderr.log")).write_bytes(error.stderr or b"")
            report["stages"][-1].update(state="TIMED_OUT", returncode=None)
            save()
            raise
        (payload / (name + ".stdout.log")).write_bytes(result.stdout)
        (payload / (name + ".stderr.log")).write_bytes(result.stderr)
        report["stages"][-1].update(state="COMPLETED", returncode=result.returncode)
        save()
        assert result.returncode == 0, (name, result.returncode)
        print("PASS " + name, flush=True)

    try:
        candidate = out / "candidate"
        run("build-four-extension-wheel", [sys.executable, "scripts/package_local_candidate.py", "--output", str(candidate)], 210)
        manifest = candidate / "candidate-manifest.json"
        candidate_data = json.loads(manifest.read_bytes())
        assert candidate_data["source_commit"] == commit
        assert len(candidate_data["wheel_profile"]["native_artifacts"]) == 4
        wheel = candidate / candidate_data["wheel_profile"]["filename"]
        assert wheel.name == "sim2act-0.1.0-cp312-cp312-win_amd64.whl"
        # Keep genuine built bytes even if a later native check or protocol fails.
        shutil.copyfile(wheel, payload / wheel.name)
        shutil.copyfile(manifest, payload / "candidate-manifest.json")
        shutil.copyfile(candidate / "build.log", payload / "wheel-build.log")
        run("install-actual-wheel", [sys.executable, "-m", "pip", "install", "--no-index", "--no-deps", "--force-reinstall", str(wheel)], 30)
        # This script lives under scripts/, not src; imports must be the installed wheel.
        import sim2act
        assert Path(sim2act.__file__).is_relative_to(Path(sys.prefix))
        inputs = ROOT / "src/sim2act"
        groups = {
            "_raw_snapshot": ("_raw_snapshot.c",), "_cold_graph_structure": ("_cold_graph_structure.c",),
            "_cold_typed_cohort": ("_cold_typed_cohort.c", "_cold_typed_native_impl.c", "_raw_snapshot.c", "_cold_cohort_backend.py"),
            "_cold_source_owned_impl": ("_cold_source_owned_impl.c", "_cold_source_live_match.h", "_cold_source_code.h", "_cold_source_view.h", "_cold_source_shape.h"),
        }
        native = {}
        for name in MODULES:
            module = importlib.import_module("sim2act." + name)
            path = Path(module.__file__)
            assert path.is_relative_to(Path(sys.prefix)) and path.name == name + ".cp312-win_amd64.pyd"
            assert module.SOURCE_SHA256 == hashlib.sha256(b"".join((inputs / n).read_bytes() for n in groups[name])).hexdigest()
            pe = inspect(path.read_bytes())
            assert pe["machine"] == "0x8664" and pe["pe32plus"] and pe["dll"]
            assert "PyInit_" + name in pe["exports"] and "python312.dll" in [v.lower() for v in pe["imports"]]
            native[name] = dict(file=path.name, **record(path.read_bytes()), pe=pe, source_sha256=module.SOURCE_SHA256)
        from sim2act import natural_spec_runtime, _cold_source_packet, _cold_typed_cohort
        from sim2act.production_trial_admission import _qualified
        _qualified()
        assert _cold_source_packet.available()
        _cold_source_packet.current()
        report["native"] = native
        report["cohort_abi_witness"] = _cold_typed_cohort.build_identity()
        save()
        run("exact-installed-dependencies", [sys.executable, "scripts/windows_ci_dependencies.py"], 20)
        run("ordinary-offline-protocols", [sys.executable, "-m", "pytest", "--assert=plain", "-o", "pythonpath=",
            "tests/test_lease_control_primitives.py", "tests/test_lease_control_native_entry.py",
            "tests/test_lease_control_main_receipts.py", "tests/test_desktop_control.py",
            "tests/test_desktop_origin.py::test_origin_publication_concurrency_and_replacement_fail_closed",
            "tests/test_desktop_origin.py::test_same_bytes_replacement_during_first_publication_is_not_adopted",
            "tests/test_desktop_origin.py::test_invalid_origin_never_rewritten",
            "-q", "--junitxml=" + str(payload / "protocol-tests.xml"), "--basetemp=" + str(out / "test-data")], 100)
        import xml.etree.ElementTree as ET
        suite = ET.parse(payload / "protocol-tests.xml").find("testsuite")
        assert all(suite.attrib[k] == "0" for k in ("failures", "errors", "skipped"))
        specification = json.loads((ROOT / "deliverables/windows-afternoon-20261023/portable-inputs.json").read_bytes())
        specification["product_commit"] = commit
        specification_file = out / "inputs.json"
        specification_file.write_text(json.dumps(specification), encoding="utf-8")
        stage_zip = out / "stage.zip"
        build(specification_file, out, wheel, stage_zip, candidate_manifest=manifest,
              runtime_image=ROOT / "deliverables/windows-afternoon-20261023/Sim2Act-preview-win64-7794748c.zip")
        with zipfile.ZipFile(stage_zip) as z:
            z.extractall(out / "stage")
        stage = out / "stage/Sim2Act-preview"
        sdk = out / "webview2.nupkg"
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get("https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/1.0.4314.35/microsoft.web.webview2.1.0.4314.35.nupkg")
            response.raise_for_status()
            assert record(response.content) == dict(bytes=9818548, sha256="90778deb1b77e36292828b4b5833c9255c27533f40e0ddd55891ae718944edc4")
            sdk.write_bytes(response.content)
        run("compile-native-desktop", ["pwsh", "-NoProfile", "-File", str(stage / "desktop-build/Build-Desktop.ps1"),
            "-CandidateRoot", str(stage), "-SdkPackage", str(sdk), "-SourceCommit", commit], 40)
        host_pe = inspect((stage / "Sim2Act.exe").read_bytes())
        assert host_pe["machine"] == "0x8664" and host_pe["pe32plus"] and not host_pe["dll"] and host_pe["subsystem"] == 2
        report["host_pe"] = host_pe
        expected_runtime = {w["name"]: w["version"] for w in specification["wheels"]
                            if w["name"].replace("_", "-") not in ("psycopg", "psycopg-binary")}
        expected_runtime["sim2act"] = "0.1.0"
        (payload / "expected-native.json").write_text(json.dumps(dict(native=native,
            dependencies=expected_runtime)), encoding="utf-8")
        private_check = """
import hashlib,importlib,importlib.metadata,json,re,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve();expected=json.loads(Path(sys.argv[2]).read_bytes());actual={}
for name,record in expected['native'].items():
 module=importlib.import_module('sim2act.'+name);path=Path(module.__file__).resolve()
 assert path.is_relative_to(root) and path.name==record['file']
 assert module.SOURCE_SHA256==record['source_sha256']
 assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
 actual[name]=dict(file=str(path),source_sha256=module.SOURCE_SHA256,sha256=record['sha256'])
from sim2act import natural_spec_runtime,_cold_source_packet,_cold_typed_cohort
from sim2act.production_trial_admission import _qualified
_qualified();assert _cold_source_packet.available();_cold_source_packet.current()
canonical=lambda value:re.sub(r'[-_.]+','-',value).lower()
dependencies={}
for dist in importlib.metadata.distributions():
 name=canonical(dist.metadata['Name']);assert name not in dependencies
 dependencies[name]=dist.version
assert dependencies=={canonical(k):v for k,v in expected['dependencies'].items()}
print(json.dumps(dict(native=actual,dependencies=dependencies,cohort_abi=_cold_typed_cohort.build_identity(),desktop_executed=False,model_requests=0)))
"""
        run("private-runtime-four-native-qualification", [str(stage / "runtime/python.exe"), "-I", "-B", "-c",
            private_check, str(stage / "runtime"), str(payload / "expected-native.json")], 30)
        graph = {str(p.relative_to(stage)).replace("\\", "/"): inspect(p.read_bytes())["imports"]
                 for p in stage.rglob("*") if p.is_file() and p.suffix.lower() in (".pyd", ".dll", ".exe")}
        bundled = {p.name.lower() for p in stage.rglob("*") if p.is_file()}
        external = sorted({name.lower() for values in graph.values() for name in values if name.lower() not in bundled})
        report["native_import_graph"] = graph
        report["unbundled_native_imports_to_resolve_on_target"] = external
        run("packaged-backend-reopen", [sys.executable, "scripts/windows_portable_backend_check.py",
            "--python", str(stage / "runtime/python.exe"), "--root", str(out / "backend-check")], 75)
        shutil.copyfile(out / "backend-check/report.json", payload / "packaged-backend-report.json")
        (stage / "WINDOWS-BUILD-STATUS.md").write_text(
            "# Same-source compiled Windows package\n\nSource: `" + commit + "`.\n\n"
            "Four Windows CPython extensions and the independent WinForms/WebView2 EXE are built. "
            "The private Python backend is checked with synthetic SQLite/CSV only; the desktop EXE/WebView2 window is NOT executed. "
            "This is an internal engineering build, not a final product acceptance or Release. "
            "Old portable-manifest labels describe the unchanged input assembly stage; full-package-manifest.json is the final inventory.\n\n"
            "Target prerequisites: Windows x64/UCRT, existing .NET Framework 4.6.2+, existing WebView2 Runtime. "
            "No system runtime/security setting is installed. Any additional unbundled native import is recorded below "
            "and must be resolved on the target before calling it a clean-machine acceptance. "
            "Do not bypass security refusals or substitute old application binaries.\n\n"
            + json.dumps(external, indent=2) + "\n", encoding="utf-8")
        files = {str(p.relative_to(stage)).replace("\\", "/"): record(p.read_bytes()) for p in stage.rglob("*") if p.is_file()}
        full = dict(format="sim2act-complete-portable-build.v1", source_commit=commit,
            status="ASSEMBLED_BACKEND_CHECKED_DESKTOP_NOT_EXECUTED", desktop_executed=False,
            model_requests=0, files=files, native=report["native"], host_pe=host_pe, native_import_graph=graph,
            unbundled_native_imports_to_resolve_on_target=external,
            dependency_image_role="ONLY_UNCHANGED_RUNTIME_DEPENDENCIES")
        (stage / "full-package-manifest.json").write_text(json.dumps(full, indent=2) + "\n", encoding="utf-8")
        archive = payload / ("Sim2Act-win64-" + commit[:12] + ".zip")
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as z:
            for p in sorted(stage.rglob("*")):
                if p.is_file():
                    z.write(p, "Sim2Act/" + str(p.relative_to(stage)).replace("\\", "/"))
        shutil.copyfile(stage / "full-package-manifest.json", payload / "full-package-manifest.json")
        report.update(status="PASS_ASSEMBLY_AND_BACKEND_ONLY", archive=dict(name=archive.name, **record(archive.read_bytes())),
                      exe=record((stage / "Sim2Act.exe").read_bytes()), tests=dict(suite.attrib))
        print("PACKAGE_RESULT=" + json.dumps(report), flush=True)
    except BaseException as error:
        report.update(status="FAILED_NOT_ACCEPTED", error_type=type(error).__name__)
        raise
    finally:
        for source, name in [(out / "candidate/build.log", "wheel-build.log"),
                             (out / "backend-check/report.json", "packaged-backend-report.json")]:
            if source.is_file():
                shutil.copyfile(source, payload / name)
        for source in (out / "backend-check").glob("start-*.log"):
            shutil.copyfile(source, payload / ("backend-" + source.name))
        save()


if __name__ == "__main__":
    main()
