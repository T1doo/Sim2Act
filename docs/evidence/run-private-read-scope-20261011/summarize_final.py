"""Check final JUnit node sets and preserved bytes without changing test results."""
import gzip
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def junit(name):
    root = ET.parse(OUT / name).getroot()
    results = {}
    for case in root.iter("testcase"):
        node = case.attrib["classname"].replace(".", "/") + ".py::" + case.attrib["name"]
        assert node not in results, (name, node)
        outcome = ("ERROR" if case.find("error") is not None else
                   "FAIL" if case.find("failure") is not None else
                   "SKIP" if case.find("skipped") is not None else "PASS")
        results[node] = outcome
    return results


if __name__ == "__main__":
    selection = json.loads((OUT / "selection.json").read_text())
    partition = json.loads((OUT / "partition.json").read_text())
    expected_main = set(partition["nodes"])
    expected_supplement = {line for line in (OUT / "supplement-collection.log").read_text().splitlines()
                           if line.startswith("tests/") and "::" in line}
    assert expected_main.isdisjoint(expected_supplement)
    main, supplement = {}, junit("supplement.xml")
    per_junit = {}
    for name in [*(f"full-{i}.xml" for i in range(4)), "full-ui.xml"]:
        results = junit(name)
        assert main.keys().isdisjoint(results), name
        main.update(results)
        per_junit[name] = {outcome: list(results.values()).count(outcome)
                           for outcome in ("PASS", "FAIL", "ERROR", "SKIP")}
    assert main.keys() == expected_main
    assert supplement.keys() == expected_supplement
    original = set(selection["original_nodes"])
    assert len(original) == 650 and original <= main.keys()
    before = json.loads((OUT / "frozen-before.json").read_text())
    after = json.loads((OUT / "frozen-after.json").read_text())
    assert before == after and len(before) == 401
    assert all(digest(ROOT / name) == sha for name, sha in before.items())
    baseline = json.loads((OUT / "baseline.json").read_text())
    preserved = baseline["old_evidence_files"]
    assert len(preserved) == 141
    assert all(digest(ROOT / name) == sha for name, sha in preserved.items())
    archive_checks = {}
    for directory in ("independent", "independent-performance"):
        transfers = json.loads((OUT / directory / "archive-transfer.json").read_text())
        for name, detail in transfers.items():
            path = OUT / directory / name
            assert digest(path) == detail["archived_sha256"], path
            raw = gzip.decompress(path.read_bytes()) if name.endswith(".gz") else path.read_bytes()
            assert hashlib.sha256(raw).hexdigest() == detail["original_sha256"], path
        archive_checks[directory] = {"files": len(transfers), "raw_and_archived_hashes_verified": True}
    combined = dict(main, **supplement)
    summary = {
        "author_unique_selected_nodes": len(combined),
        "author_final_outcomes": {outcome: list(combined.values()).count(outcome)
                                  for outcome in ("PASS", "FAIL", "ERROR", "SKIP")},
        "main_selected": len(main), "supplement_selected": len(supplement),
        "original_650_exactly_restored": True,
        "original_650_outcomes": {outcome: sum(main[n] == outcome for n in original)
                                  for outcome in ("PASS", "FAIL", "ERROR", "SKIP")},
        "per_junit": per_junit,
        "deselected": ["actual_50b_source_upgrade", "actual_fab_source_upgrade"],
        "frozen_files": len(before), "source_test_script_bytes_unchanged": True,
        "old_evidence_files": len(preserved), "original_evidence_bytes_unchanged": True,
        "archived_independent_hashes": archive_checks,
        "independent_59_checks_are_separate_from_pytest_nodes": True,
        "full_execution": json.loads((OUT / "full-exit.json").read_text()),
    }
    (OUT / "final-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (OUT / "final-node-outcomes.json").write_text(json.dumps(combined, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
