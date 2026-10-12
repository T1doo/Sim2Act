from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path('/workspace/Sim2Act')
OUT = Path('/tmp/pb-cold-recovery-review-20261011')
sha = lambda b: hashlib.sha256(b).hexdigest()

def write(name, value):
    path = OUT / name
    assert not path.exists(), path
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def xml_counts(name):
    root = ET.parse(OUT / name).getroot()
    cases = list(root.iter('testcase'))
    named = [c for c in cases if c.get('name')]
    def count(tag):
        return sum(c.find(tag) is not None for c in named)
    return {'file': name, 'named': len(named), 'passed': sum(all(c.find(t) is None for t in ['failure','error','skipped']) for c in named), 'failures': count('failure'), 'errors': count('error'), 'skipped': count('skipped'), 'anonymous_records_excluded': len(cases) - len(named), 'time': root.find('testsuite').get('time')}

def metrics(folder):
    rows = []
    for f in sorted((OUT / folder).glob('*.json')):
        if f.name.endswith('-private.json'):
            continue
        obj = json.loads(f.read_text())
        assert isinstance(obj, dict), f
        assets = obj['static_resource_loads']
        mismatches = []
        for asset in assets:
            path = ROOT / 'src/sim2act/web' / (asset['path'].lstrip('/') or 'index.html')
            data = path.read_bytes()
            mime = {'/':'text/html; charset=utf-8', '/app.css':'text/css; charset=utf-8'}.get(asset['path'], 'text/javascript; charset=utf-8')
            if asset['status'] != 200 or asset['content_type'] != mime or asset['bytes'] != len(data) or asset['sha256'] != sha(data):
                mismatches.append(asset)
        actions = obj['actions']
        gesture = [a for a in actions if a.get('event') == 'DOM dispatch' and a.get('visible') is True and a.get('enabled') is True]
        requests = obj['requests']
        post = lambda suffix: sum(r['method']=='POST' and r['path'].split('?')[0].endswith(suffix) for r in requests)
        row = {'file': str(f.relative_to(OUT)), 'status': obj['status'], 'scenario': obj.get('scenario'), 'phase': obj.get('phase'), 'process_id': obj.get('process_id'), 'checks': len(obj['checks']), 'visible_enabled_dom_gestures': len(gesture), 'other_action_records': len(actions)-len(gesture), 'boots':len(set(a['boot'] for a in assets)), 'actual_http_assets':len(assets), 'asset_status_mime_bytes_hash_mismatches':mismatches, 'prepare_posts':post('/extraction-requests'), 'extract_posts':post('/extract'), 'close_posts':post('/extraction-request-close'), 'storage_attempts':obj.get('storage_attempts'), 'other_actor_requests':len(obj.get('other_actor_requests',[]))}
        rows.append(row)
    for row in rows:
        assert row['status']=='PASS' and not row['asset_status_mime_bytes_hash_mismatches'], row
    pair_proofs = []
    if rows and all(r['phase'] for r in rows):
        scenarios = sorted(set(r['scenario'] for r in rows))
        for scenario in scenarios:
            pair = [r for r in rows if r['scenario']==scenario]
            assert len(pair)==2 and set(r['phase'] for r in pair)=={'first','cold'}, pair
            assert len(set(r['process_id'] for r in pair))==2, pair
            pair_proofs.append({'scenario':scenario,'distinct_first_and_cold_processes':True,'process_ids':[r['process_id'] for r in pair]})
    return {'folder':folder,'page_outputs':len(rows),'checks':sum(r['checks'] for r in rows),'visible_enabled_dom_gestures':sum(r['visible_enabled_dom_gestures'] for r in rows),'other_action_records':sum(r['other_action_records'] for r in rows),'boots':sum(r['boots'] for r in rows),'actual_http_assets':sum(r['actual_http_assets'] for r in rows),'all_status_mime_bytes_hash_match':True,'pair_proofs':pair_proofs,'rows':rows}

manifest_path = ROOT / 'docs/evidence/pb-cold-recovery-20261011/candidate3-source-freeze.json'
manifest = json.loads(manifest_path.read_text())
actual = {name:sha((ROOT/name).read_bytes()) for name in manifest['sha256']}
differences = [name for name in actual if actual[name] != manifest['sha256'][name]]
assert not differences and len(actual)==369
write('candidate3-source-after.json', {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_count':len(actual),'manifest_file_sha256':sha(manifest_path.read_bytes()),'source_map_sha256':manifest['source_map_sha256'],'differences':differences,'sha256':actual})

old = Path('/tmp/pb-text-extraction-review-20261011')
old_manifest_path = old / 'archive-manifest.json'
old_manifest = json.loads(old_manifest_path.read_text())
assert len(old_manifest['files'])==224
old_differences = []
for entry in old_manifest['files']:
    if not (old/entry['path']).exists() or sha((old/entry['path']).read_bytes())!=entry['sha256']:
        old_differences.append(entry['path'])
assert not old_differences
write('old-pb-independent224-preservation.json', {'scope':'Only the prior independent224 sealed archive, not the root496 tracked PB evidence or193 top-level tree/blob bridge; no old tests rerun.', 'file_count':224,'manifest_file_sha256':sha(old_manifest_path.read_bytes()),'differences':old_differences})

groups = [metrics(name) for name in ['candidate3-cold-pages','candidate3-existing-pages','candidate3-final-independent-cold-pages','candidate3-final-independent-latest-pages']]
assert groups[0]['page_outputs']==36 and groups[1]['page_outputs']==9 and groups[2]['page_outputs']==groups[3]['page_outputs']==2
write('candidate3-final-http-page-metrics.json', {'classification':'ACTUAL_SQLITE_TESTCLIENT_IPC_HTTP_NEW_JSDOM_SOURCE_ASSETS; external scheduling is controlled, upstream model synthetic, no native browser','groups':groups,'scope':'Cold phase fresh Node, fresh Store/API; JSDOM DOM gestures and cache/no-store/storage interception are controlled, no claim of native OS browser cache/persistence or cross-device atomic installation.'})

names = ['candidate1-new.xml','candidate1-existing.xml','candidate1-independent-gates.xml','candidate1-independent-cold-poison.xml','candidate2-new.xml','candidate2-existing.xml','candidate2-independent-gates.xml','candidate2-independent-latest.xml','candidate3-independent.xml','candidate3-final-independent.xml','candidate3-new.xml','candidate3-existing.xml']
counts = [xml_counts(name) for name in names]
write('all-independent-test-history.json', {'counts':counts,'final_groups':['candidate3-new.xml','candidate3-existing.xml','candidate3-final-independent.xml'],'withdrawn':['candidate1*','candidate2*','candidate3-independent.xml (output fixture error; 5 named passed before exact SIGINT)'],'anonymous_not_pass':True,'do_not_add_withdrawn_history_to_final_coverage':True})
active = []
for line in subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines():
    if str(OUT) in line and ('-m pytest' in line or 'node ' in line) and 'ps -eo' not in line:
        active.append(line.strip())
assert not active, active
write('candidate3-final-health.json', {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'active_owned_pytest_or_node':active,'maintenance_results':[json.loads((OUT/name).read_text()) for name in ['candidate3-new-result.json','candidate3-existing-result.json']], 'external_final_exit_code':0,'external_final_junit':'candidate3-final-independent.xml'})
print(json.dumps({'source369_differences':differences,'groups':[{k:g[k] for k in ['folder','page_outputs','checks','visible_enabled_dom_gestures','other_action_records','boots','actual_http_assets']} for g in groups],'final_counts':counts[-3:],'old224_differences':old_differences,'active':active},indent=2))
