"""Exact target qualification never adds a filename exemption or instance grant."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from sim2act import text_continuations as cont
from sim2act.errors import DomainError

ROOT = Path(cont.__file__).parent
SOURCES = sorted(json.loads((ROOT / "text_software_anchors.json").read_text()))


@pytest.fixture
def software(tmp_path, monkeypatch):
    for p in ROOT.glob("*.py"):
        shutil.copyfile(p, tmp_path / p.name)
    for name in ("text_software_anchors.json", "text_software_qualification.json"):
        shutil.copyfile(ROOT / name, tmp_path / name)
    monkeypatch.setattr(cont, "__file__", str(tmp_path / "text_continuations.py"))
    return tmp_path


@pytest.mark.parametrize("fp", SOURCES)
def test_exact_two_sources_qualify_without_changing_old_anchor_or_whitelist(software, fp):
    old = json.loads((software / "text_software_anchors.json").read_text())
    assert cont.known(fp) == old[fp]
    assert cont.CHANGED == {"api.py", "app_jobs.py", "internal_api.py", "owner_acceptance.py",
        "app_owner_goals.py", "apps.py", "lifecycle.py", "text_logic_reuse.py",
        "text_continuations.py", "text_run_checks.py", "text_workflows.py"}
    assert hashlib.sha256((software / "text_software_anchors.json").read_bytes()).hexdigest() == cont.ANCHOR_HASH


@pytest.mark.parametrize("name", ["generation_approvals.py", "pa_material_bindings.py", "contracts.py",
    "db.py", "goal_applications.py", "text_apps.py", "worker.py", "api.py",
    "text_logic_reuse.py", "text_continuations.py"])
def test_unreviewed_byte_change_including_original_changed_names_is_closed(software, name):
    p = software / name
    p.write_bytes(p.read_bytes() + b"\n# synthetic unreviewed change\n")
    for fp in SOURCES:
        with pytest.raises(DomainError) as caught:
            cont.known(fp)
        assert caught.value.code == "VERSION_CONFLICT"


@pytest.mark.parametrize("fault", ["extra-file", "missing-file", "missing-qualification",
    "changed-qualification", "changed-anchor", "changed-pin-literal", "computed-pin", "nested-pin"])
def test_unknown_file_set_manifest_anchor_or_nonliteral_pin_never_qualifies(software, fault):
    p = software / "text_continuations.py"
    assignment = 'QUALIFICATION_HASH = "' + cont.QUALIFICATION_HASH + '"'
    if fault == "extra-file":
        (software / "synthetic_unreviewed.py").write_text("x = 1\n")
    elif fault == "missing-file":
        (software / "worker.py").unlink()
    elif fault == "missing-qualification":
        (software / "text_software_qualification.json").unlink()
    elif fault == "changed-qualification":
        p = software / "text_software_qualification.json"
        p.write_bytes(p.read_bytes() + b"\n")
    elif fault == "changed-anchor":
        p = software / "text_software_anchors.json"
        p.write_bytes(p.read_bytes() + b"\n")
    elif fault == "changed-pin-literal":
        p.write_text(p.read_text().replace(assignment, 'QUALIFICATION_HASH = "' + 'f' * 64 + '"'))
    elif fault == "computed-pin":
        p.write_text(p.read_text().replace(assignment, 'QUALIFICATION_HASH = ("' + cont.QUALIFICATION_HASH + '")'))
    else:
        p.write_text(p.read_text().replace(assignment, "if True:\n    " + assignment))
    for fp in SOURCES:
        with pytest.raises(DomainError) as caught:
            cont.known(fp)
        assert caught.value.code == "VERSION_CONFLICT"


def test_duplicate_manifest_field_is_rejected_even_in_synthetic_repinned_document(software, monkeypatch):
    p = software / "text_software_qualification.json"
    raw = p.read_text().replace('{\n', '{\n  "version": "literal-software-qualification.v1",\n', 1)
    p.write_text(raw)
    pin = hashlib.sha256(raw.encode()).hexdigest()
    code = software / "text_continuations.py"
    code.write_text(code.read_text().replace('QUALIFICATION_HASH = "' + cont.QUALIFICATION_HASH + '"',
                                           'QUALIFICATION_HASH = "' + pin + '"'))
    monkeypatch.setattr(cont, "QUALIFICATION_HASH", pin)
    with pytest.raises(DomainError, match="Duplicate software qualification field"):
        cont.known(SOURCES[0])


def test_unknown_source_has_no_qualification_contract(software):
    with pytest.raises(DomainError) as caught:
        cont.known("f" * 64)
    assert caught.value.code == "UNSUPPORTED_CAPABILITY"
