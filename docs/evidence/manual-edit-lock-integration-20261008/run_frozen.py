"""Own-resource source-provenance runner. Edit own paths, never use a user DB."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
BASE = "72563fa220c66dd142be5656c5468d177de8fede"
backend = sys.argv[1]
assert backend in {"sqlite", "pg"}
basetemp = Path(sys.argv[2])
assert str(basetemp).startswith("/tmp/sim2act-lock-integration-final-")
assert os.environ["LIVE"] == "0" and os.environ["SIM2ACT_LIVE_ENABLED"] == "false"
assert (backend == "pg") == bool(os.environ.get("SIM2ACT_TEST_DATABASE_URL"))
python = ROOT / ".venv/bin/python"
scope = json.loads((EVIDENCE / "scope.json").read_text())

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

def hashes():
    result = {}
    for name in ["src", "tests", "schemas", "scripts", ".github/workflows"]:
        for p in sorted((ROOT / name).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                result[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result

before = hashes()
source = git("rev-parse", "HEAD")
# Original assertions/scripts/locks/workflows must remain byte-identical.
old_files = git("ls-tree", "-r", "--name-only", BASE).splitlines()
preserved = {}
for name in old_files:
    if name.startswith(("tests/", "scripts/", ".github/workflows/")) or "lock" in Path(name).name and not name.startswith("docs/"):
        old = subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)
        assert (ROOT / name).read_bytes() == old, name
        preserved[name] = hashlib.sha256(old).hexdigest()
collection = subprocess.run([str(python), "-m", "pytest", "--collect-only", "-q", *scope],
    cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(EVIDENCE / f"{backend}-collection.log").write_text(collection.stdout)
assert collection.returncode == 0
nodes = [line for line in collection.stdout.splitlines() if line.startswith("tests/") and "::" in line]
assert len(nodes) == len(set(nodes))
(EVIDENCE / f"{backend}-collection.json").write_text(json.dumps(nodes, indent=2))
xml = EVIDENCE / f"{backend}-final.xml"
start = time.monotonic()
with (EVIDENCE / f"{backend}-final.log").open("w") as output:
    outcome = subprocess.run([str(python), "-m", "pytest", "-q", *scope, "--basetemp=" + str(basetemp), "--junitxml=" + str(xml)],
        cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
seconds = time.monotonic() - start
after = hashes()
assert after == before, "Executed source or tests changed during frozen run"
suite = ET.parse(xml).getroot().find("testsuite")
assert suite is not None and int(suite.attrib["tests"]) == len(nodes)
summary = dict(backend=backend, source_sha=source, base_sha=BASE, collection=len(nodes),
    tests=int(suite.attrib["tests"]), failures=int(suite.attrib["failures"]), errors=int(suite.attrib["errors"]),
    skipped=int(suite.attrib["skipped"]), seconds=seconds, returncode=outcome.returncode,
    source_unchanged=before == after, LIVE=0, native="NOT_RUN", independent_review="LIMITED_PASS_PER_PARENT_REPORT")
summary["passed"] = summary["tests"] - summary["failures"] - summary["errors"] - summary["skipped"]
(EVIDENCE / f"{backend}-summary.json").write_text(json.dumps(summary, indent=2))
(EVIDENCE / f"{backend}-provenance.json").write_text(json.dumps(dict(summary=summary,
    before=before, after=after, original_assertions_scripts_locks_workflows=preserved), indent=2))
proofs = EVIDENCE / f"{backend}-routing-traces"
proofs.mkdir(exist_ok=True)
for p in basetemp.rglob("routing-trace.json"):
    shutil.copyfile(p, proofs / (p.parent.name + ".json"))
for proof_name in ["results.json", "upgrade-proof.json"]:
    target = EVIDENCE / f"{backend}-actual-proofs"
    target.mkdir(exist_ok=True)
    for p in basetemp.rglob(proof_name):
        folder = target / p.parent.name
        folder.mkdir(exist_ok=True)
        shutil.copyfile(p, folder / proof_name)
        for extra in ["driver.log", "info.json"]:
            if (p.parent / extra).exists(): shutil.copyfile(p.parent / extra, folder / extra)
print(json.dumps(summary), flush=True)
sys.exit(outcome.returncode)
