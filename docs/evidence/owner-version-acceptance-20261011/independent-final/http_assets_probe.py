"""Actual in-process HTTP static routes and bytes; no native browser or provider."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path

from fastapi.testclient import TestClient
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store

ROOT = Path('/workspace/Sim2Act')
OUT = Path('/tmp/owner-version-acceptance-review-20261011')


class Resources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'script' and a.get('src'):
            self.paths.append(a['src'])
        if tag == 'link' and a.get('rel') == 'stylesheet':
            self.paths.append(a['href'])


store = Store('sqlite:///' + str(OUT / 'assets-only.db'), test_only=True)
store.initialize()
client = TestClient(create_app(store, Settings(store.database_url, OUT, mode='mock')))
report = {'transport': 'actual FastAPI TestClient in-process HTTP', 'live_models': 0,
          'semantic_owner_signoff': 'NOT_RUN', 'native_browser': 'NOT_RUN', 'resources': []}
try:
    index = client.get('/')
    assert index.status_code == 200
    parser = Resources()
    parser.feed(index.text)
    assert '/owner-review.js' in parser.paths and '/goal-application.js' in parser.paths
    assert len(parser.paths) == len(set(parser.paths))
    for path in ['/', *parser.paths]:
        response = index if path == '/' else client.get(path)
        file = ROOT / 'src/sim2act/web' / ('index.html' if path == '/' else path.lstrip('/'))
        expected = file.read_bytes()
        ctype = response.headers.get('content-type', '')
        expected_type = 'text/html' if path == '/' else 'text/css' if path.endswith('.css') else 'text/javascript'
        row = {'path': path, 'status': response.status_code, 'content_type': ctype,
               'bytes': len(response.content), 'sha256': hashlib.sha256(response.content).hexdigest(),
               'disk_bytes': len(expected), 'disk_sha256': hashlib.sha256(expected).hexdigest()}
        report['resources'].append(row)
        assert response.status_code == 200, row
        assert ctype.startswith(expected_type), row
        assert response.content == expected, row
    missing = client.get('/owner-review-nonexistent-independent.js')
    report['unknown_route'] = {'path': '/owner-review-nonexistent-independent.js', 'status': missing.status_code}
    assert missing.status_code == 404
    report.update(status='PASS', resource_count=len(report['resources']), unexpected_routes=0)
finally:
    (OUT / 'sealed2-http-assets.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    client.close()
    store.engine.dispose()
print(json.dumps({'status': report.get('status'), 'resources': len(report['resources']), 'unknown_status': report.get('unknown_route', {}).get('status')}))
