"""Full DOM/real use.js with synthesized API; not HTTP or PG evidence."""
import hashlib
import json
import subprocess
from pathlib import Path


def test_catalog_use_routing_synthesized_api(tmp_path):
    source = Path(__file__).parents[1] / "src/sim2act/web/use.js"
    result = subprocess.run(
        ["node", "tests/catalog_use_routing.cjs", str(tmp_path), str(source)],
        capture_output=True, text=True, timeout=30,
    )
    (tmp_path / "driver.log").write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads((tmp_path / "results.json").read_text())
    assert receipt["status"] == "PASS" and len(receipt["checks"]) == 24
    assert receipt["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
