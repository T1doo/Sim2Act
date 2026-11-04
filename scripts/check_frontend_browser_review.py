"""Bounded real-HTTP check of the source-only readonly browser candidate; no browser."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ui-driver', type=Path)
    args = parser.parse_args()
    root = args.candidate.absolute()
    args.output.mkdir(parents=True, exist_ok=False)
    receipt = json.loads((root / 'fixture/receipt.json').read_text())
    manifest = json.loads((root / 'manifest.json').read_text())
    checks, requests, lines = [], [], queue.Queue()
    def check(value, name):
        if not value:
            raise AssertionError(name)
        checks.append(name)
    process = None
    result = {'status': 'FAIL', 'source_commit': manifest['source_commit'], 'checks': checks,
        'scope': 'ACTUAL_CURRENT_SOURCE_HTTP_AND_SQLITE_NO_BROWSER_OR_WINDOWS_EXECUTION',
        'requests': requests, 'browser_launches': 0, 'runtime_workers': 0, 'live_model_requests': 0,
        'ci_execution_seconds': 0, 'new_downloads': 0}
    try:
        check(not list((root / 'src/sim2act').glob('*.so')) and not list((root / 'src/sim2act').glob('*.pyd')), 'Application source has no native extension binaries')
        check(not any(p.name.lower().startswith('sim2act') for p in (root / 'windows-runtime/Lib/site-packages').iterdir()), 'Old Windows application and metadata are excluded')
        env = {k: v for k, v in os.environ.items() if k not in {'PYTHONPATH', 'PYTHONHOME'}}
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        errors = (args.output / 'server.stderr.log').open('w')
        process = subprocess.Popen([sys.executable, '-B', str(root / 'review_server.py'), 'serve',
            '--root', str(root), '--port', '0', '--control-stdin'], cwd=root, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True)
        def drain():
            with (args.output / 'server.stdout.log').open('w') as log:
                for line in process.stdout:
                    log.write(line);log.flush();lines.put(line)
        reader = threading.Thread(target=drain, daemon=True);reader.start()
        deadline = time.monotonic() + 30
        ready = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('Candidate exited before READY; preserve logs')
            try:
                row = json.loads(lines.get(timeout=.1))
            except queue.Empty:
                continue
            if row.get('event') == 'FRONTEND_REVIEW_READY':
                ready = row;break
        check(ready is not None, 'Source-only server starts within 30 seconds')
        check(ready['source_commit'] == manifest['source_commit'] and Path(ready['api_module']).is_relative_to(root / 'src'), 'Server imports exact frozen current source')
        origin = ready['url'];parsed = urlsplit(origin)
        check(parsed.hostname == '127.0.0.1' and parsed.scheme == 'http' and parsed.port, 'Only owned loopback URL is used')
        with httpx.Client(base_url=origin, timeout=5, trust_env=False,
            headers={'Authorization': 'Bearer public-synthetic-local-candidate'}) as client:
            def get(path, status=200):
                response = client.get(path);requests.append({'method': 'GET', 'path': path, 'status': response.status_code})
                check(response.status_code == status, 'Actual GET ' + path + ' returns ' + str(status))
                check(response.headers.get('X-Sim2Act-Review-Source') == manifest['source_commit'], 'Response is bound to source SHA: ' + path)
                return response
            get('/health')
            html = get('/').text
            check('前端只读验收' in html and '保存、执行、审批、发布均关闭' in html, 'Actual root page visibly labels the readonly synthetic profile')
            check(re.sub(r'<section id="synthetic-workspace-banner".*?</section>', '', html, count=1) == (root / 'src/sim2act/web/index.html').read_text(), 'HTML differs only by explicit synthetic review banner')
            assets = re.findall(r'<script[^>]+src="([^"]+)"|<link[^>]+href="([^"]+)"', html)
            for pair in assets:
                path = next(value for value in pair if value)
                check(path.startswith('/') and '/' not in path[1:], 'Static asset stays on owned origin: ' + path)
                response = get(path)
                check(hashlib.sha256(response.content).hexdigest() == hashlib.sha256((root / 'src/sim2act/web' / path[1:]).read_bytes()).hexdigest(), 'Actual static bytes match frozen source: ' + path)
            check(any('/app.js' in pair for pair in assets), 'Delivered HTML loads the real current app controller')
            projects = get('/api/projects').json();check(any(p['id'] == receipt['project_id'] for p in projects), 'Synthetic project is available through original authorization API')
            get('/api/projects/' + receipt['project_id'] + '/resources')
            get('/api/goal-cards/' + receipt['goal_id'])
            get('/api/apps/' + receipt['app_id'])
            saved = get(receipt['result_route']).json();check(saved['result']['sum'] == '30' and saved['result_version'] == 1, 'Nonempty saved CSV result is actual sum30/v1')
            get('/api/runs/' + receipt['run_id'])
            for path in ['/api/projects', '/api/projects/' + receipt['project_id'] + '/runs']:
                response = client.post(path, json={});requests.append({'method': 'POST', 'path': path, 'status': response.status_code})
                check(response.status_code == 405 and response.json()['error']['code'] == 'FRONTEND_REVIEW_READ_ONLY', 'All mutation attempts are refused: ' + path)
            response = client.get('/api/projects', headers={'Authorization': 'Bearer wrong-synthetic-login'})
            check(response.status_code == 403 and response.json()['error']['code'] == 'PERMISSION_DENIED', 'Original authentication still rejects a wrong login')
            response = client.get('/api/projects', headers={'Origin': 'https://not-this-loopback.invalid'})
            check(response.status_code == 403, 'Original cross-origin guard remains active')
        if args.ui_driver:
            ui = subprocess.run(['node', str(args.ui_driver.absolute()), origin, str(root / 'fixture/receipt.json')], env=os.environ, capture_output=True, text=True, timeout=30)
            (args.output / 'ui.stdout.json').write_text(ui.stdout)
            (args.output / 'ui.stderr.log').write_text(ui.stderr)
            check(ui.returncode == 0, 'Current delivered UI reads nonempty actual HTTP result and refuses mutation')
        process.stdin.close();check(process.wait(timeout=10) == 0, 'Owned readonly server exits normally within 10 seconds')
        reader.join(2);errors.close()
        records = [json.loads(line) for line in (args.output / 'server.stdout.log').read_text().splitlines()]
        stopped = next(row for row in records if row.get('event') == 'FRONTEND_REVIEW_STOPPED')
        check(stopped['database_unchanged'] and stopped['runtime_workers'] == 0, 'Actual fixture bytes remain unchanged after reads and denied mutations')
        result.update(status='PASS', source_url=origin, assets_verified=len(assets), windows_execution='NOT_RUN', screenshots=0)
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        if process is not None and process.poll() is None:
            if not process.stdin.closed:
                process.stdin.close()
            process.wait(timeout=10)
        (args.output / 'http-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
