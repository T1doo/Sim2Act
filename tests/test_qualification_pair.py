"""One exact reviewed byte set closes both qualification literals, without a callback."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from sim2act import production_trial_admission as production
from sim2act import text_continuations as continuation
from sim2act.errors import DomainError


@pytest.fixture
def target(tmp_path, monkeypatch):
    root = Path(production.__file__).parent
    for path in root.iterdir():
        if path.suffix in {".py", ".c", ".h", ".json"}:
            shutil.copyfile(path, tmp_path / path.name)
    monkeypatch.setattr(production, "__file__", str(tmp_path / "production_trial_admission.py"))
    monkeypatch.setattr(continuation, "__file__", str(tmp_path / "text_continuations.py"))
    return tmp_path


def repin_text(root, raw):
    path = root / "text_software_qualification.json"
    old = hashlib.sha256(path.read_bytes()).hexdigest()
    path.write_bytes(raw)
    source = root / "text_continuations.py"
    literal = ('QUALIFICATION_HASH = "' + old + '"').encode()
    assert source.read_bytes().count(literal) == 1
    source.write_bytes(source.read_bytes().replace(literal,
        ('QUALIFICATION_HASH = "' + hashlib.sha256(raw).hexdigest() + '"').encode()))


def test_same_complete_target_qualifies_both_without_delegated_verdict(target, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Production cannot delegate to a replaceable continuation verdict")
    monkeypatch.setattr(continuation, "qualified_target", forbidden)
    monkeypatch.setattr(continuation, "known", forbidden)
    production._qualified()


@pytest.mark.parametrize("fault", ["missing-file", "extra-file", "changed-file", "sources",
    "anchor", "baseline", "candidate", "normalization", "duplicate-top", "duplicate-files"])
def test_resealed_text_manifest_cannot_escape_the_same_reviewed_target(target, fault):
    path = target / "text_software_qualification.json"
    proof = json.loads(path.read_bytes())
    if fault == "missing-file":
        proof["files"].pop("worker.py")
    elif fault == "extra-file":
        proof["files"]["unreviewed.py"] = "0" * 64
    elif fault == "changed-file":
        proof["files"]["worker.py"] = "0" * 64
    elif fault == "sources":
        proof["sources"].append("f" * 64)
    elif fault == "anchor":
        proof["anchor_hash"] = "0" * 64
    elif fault in {"baseline", "candidate"}:
        proof["review_" + fault] = "0" * 40
    elif fault == "normalization":
        proof["normalization"] = "skip-more-files"
    raw = json.dumps(proof, indent=2, sort_keys=True).encode()
    if fault == "duplicate-top":
        raw = raw.replace(b'{\n', b'{\n  "version": "literal-software-qualification.v1",\n', 1)
    elif fault == "duplicate-files":
        raw = raw.replace(b'"files": {', b'"files": {"worker.py": "' + proof["files"]["worker.py"].encode() + b'",', 1)
    repin_text(target, raw)
    with pytest.raises(DomainError):
        production._qualified()


@pytest.mark.parametrize("fault", ["top", "files"])
def test_duplicate_production_fields_rejected_even_with_synthetic_repin(target, monkeypatch, fault):
    path = target / "production_software_qualification.json"
    raw = path.read_bytes()
    if fault == "top":
        raw = raw.replace(b'{\n', b'{\n  "version": "production-software-qualification.v2",\n', 1)
    else:
        digest = json.loads(raw)["files"]["worker.py"].encode()
        raw = raw.replace(b'"files": {', b'"files": {"worker.py": "' + digest + b'",', 1)
    path.write_bytes(raw)
    pin = hashlib.sha256(raw).hexdigest()
    source = target / "production_trial_admission.py"
    source.write_text(source.read_text().replace(
        'PRODUCTION_QUALIFICATION_HASH = "' + production.PRODUCTION_QUALIFICATION_HASH + '"',
        'PRODUCTION_QUALIFICATION_HASH = "' + pin + '"', 1))
    monkeypatch.setattr(production, "PRODUCTION_QUALIFICATION_HASH", pin)
    with pytest.raises(DomainError, match="Duplicate software qualification field"):
        production._qualified()


@pytest.mark.parametrize("file", ["worker.py", "text_continuations.py", "production_trial_admission.py",
    "_owned_sql_catalog.json", "_raw_snapshot.c"])
def test_any_other_reviewed_byte_change_is_rejected(target, file):
    path = target / file
    path.write_bytes(path.read_bytes() + b"\n ")
    with pytest.raises(DomainError):
        production._qualified()


@pytest.mark.parametrize("name", ["text_continuations.py", "production_trial_admission.py"])
@pytest.mark.parametrize("fault", ["nested", "computed", "duplicate", "wrong-value"])
def test_both_normalized_roles_are_exact_single_top_level_literals(target, name, fault):
    path = target / name
    variable = "QUALIFICATION_HASH" if name.startswith("text_") else "PRODUCTION_QUALIFICATION_HASH"
    value = (continuation.QUALIFICATION_HASH if name.startswith("text_")
             else production.PRODUCTION_QUALIFICATION_HASH)
    assignment = variable + ' = "' + value + '"'
    replacement = {"nested": "if True:\n    " + assignment,
        "computed": variable + ' = ("' + value + '")',
        "duplicate": assignment + "\n" + assignment,
        "wrong-value": variable + ' = "' + "0" * 64 + '"'}[fault]
    path.write_text(path.read_text().replace(assignment, replacement, 1))
    with pytest.raises(DomainError):
        production._qualified()


def test_single_captured_python_set_binds_both_proofs(target, monkeypatch):
    reads = {}
    anchor_reads = []
    original = Path.read_bytes
    def observed(path):
        if path == target / "text_software_anchors.json":
            anchor_reads.append(path)
            assert len(anchor_reads) == 1, "Anchor parsing must use the same hash-verified bytes"
        if path.parent == target and path.suffix == ".py":
            reads[path.name] = reads.get(path.name, 0) + 1
            assert reads[path.name] == 1, "A later scan could describe different bytes"
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", observed)
    production._qualified()
    assert len(reads) == len(list(target.glob("*.py"))) - 1  # Original config.py exception only.
    assert len(anchor_reads) == 1
