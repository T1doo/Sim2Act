"""Page-level control binding while complete detail is still pending."""

import json
import subprocess


def test_owner_stop_remains_available_during_full_detail_read(tmp_path):
    output=tmp_path/'stop-control.json'
    result=subprocess.run(['node','tests/internal_stop_control.cjs',str(output)],
        capture_output=True,text=True,timeout=30)
    (tmp_path/'driver.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stdout+result.stderr
    proof=json.loads(output.read_text())
    assert proof['status']=='PASS'
