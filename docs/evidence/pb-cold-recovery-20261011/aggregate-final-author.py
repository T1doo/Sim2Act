"""Read-only aggregation of the completed actual author round; never runs tests."""
from pathlib import Path
import json, xml.etree.ElementTree as ET, hashlib
root = Path(__file__).resolve().parent
result = json.loads((root / "candidate4-exit.json").read_text())
assert result["exit"] == 0 and not result["source_changes"]
nodes = ET.parse(root / "candidate4.xml").findall(".//testcase")
assert all(n.get("name") for n in nodes), "No unnamed interrupted records in final round"
assert not any(n.find("failure") is not None or n.find("error") is not None for n in nodes)
report = {"actual_round": "candidate4", "result": result, "named_unique_nodes": len({(n.get("classname"), n.get("name")) for n in nodes}), "skip": [{"class": n.get("classname"), "name": n.get("name"), "reason": n.find("skipped").get("message"), "text": n.find("skipped").text} for n in nodes if n.find("skipped") is not None], "pages": {}}
freeze = json.loads((root / "candidate4-source-freeze.json").read_text())["sha256"]
before = json.loads((root / "candidate4-source-before.json").read_text())
after = json.loads((root / "candidate4-source-after.json").read_text())
assert before == after == freeze
report["frozen_source_count"] = len(freeze)
report["source_map_sha256"] = hashlib.sha256(json.dumps(freeze, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
for label, directory in [("cold", "candidate4-cold-pages"), ("existing_text", "candidate4-pb-pages")]:
    pages=[]
    for p in sorted(root.joinpath(directory).rglob("*.json")):
        value=json.loads(p.read_text())
        if isinstance(value,dict) and "static_resource_loads" in value:
            assert value["status"] == "PASS", p
            actions=value.get("actions",[])
            if label == "cold":
                assert all(a["visible"] and a["enabled"] and a["event"] == "DOM dispatch" for a in actions)
                assert len(value["static_resource_loads"]) == 19
                assert not value["storage_attempts"]
            pages.append({"path":str(p.relative_to(root)), "checks":len(value.get("checks",[])), "actions":len(actions), "static_resources":len(value["static_resource_loads"]), "boots":value.get("boots",1), "process_id":value.get("process_id"), "phase":value.get("phase"), "scenario":value.get("scenario")})
    report["pages"][label]={"scenario_or_phase_records":len(pages), "actual_page_boots":sum(p["boots"] for p in pages), "checks":sum(p["checks"] for p in pages), "actions":sum(p["actions"] for p in pages), "static_resources":sum(p["static_resources"] for p in pages), "pages":pages}
root.joinpath("final-author-summary.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({k:v for k,v in report.items() if k not in {"skip","pages"}}))
print(json.dumps({k:{x:y for x,y in v.items() if x!="pages"} for k,v in report["pages"].items()}))
