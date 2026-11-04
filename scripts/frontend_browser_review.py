"""Frozen real-API browser review; synthetic saved data, no runtime worker or model.

prepare uses existing local tools and an already frozen Windows dependency image.
serve does not install, discover configuration, open a browser or mutate API data.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import socket
import subprocess
import sys
import tarfile
import threading
import zipfile

sys.dont_write_bytecode = True
FORMAT = 'sim2act-readonly-browser-review.v1'
PUBLIC_TOKEN = 'public-synthetic-local-candidate'
DEPENDENCY_ZIP_SHA = 'cc177eeb8815194a4f1e973e146ce7dd95c2949350745a296c4d6a9bfcd38027'
CSP = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unlinked(path):
    path = Path(os.path.abspath(path))
    require(not any(p.is_symlink() or p.is_junction() for p in [path, *path.parents]), 'Linked path refused')
    return path


def put(root, relative, data):
    name = PurePosixPath(relative)
    require(not name.is_absolute() and '..' not in name.parts, 'Unsafe member path')
    target = root.joinpath(*name.parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(data)


def prepare(output, runtime_archive):
    import importlib.util
    repo = Path(__file__).resolve().parents[1]
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    subprocess.run(['git', 'diff', '--exit-code', source, '--', 'src'], cwd=repo, check=True, capture_output=True)
    require(digest(runtime_archive) == DEPENDENCY_ZIP_SHA, 'Existing dependency archive differs')
    root = unlinked(output)
    require(not root.exists(), 'New output directory required')
    root.mkdir(parents=True)
    archive = subprocess.check_output(['git', 'archive', '--format=tar', source, 'src'], cwd=repo)
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        for member in stream:
            if member.isdir():
                continue
            require(member.isfile() and member.name.startswith('src/'), 'Unexpected source member')
            put(root, member.name, stream.extractfile(member).read())
    put(root, 'review_server.py', Path(__file__).read_bytes())
    put(root, 'requirements.lock', (repo / 'requirements.lock').read_bytes())
    count = 0
    with zipfile.ZipFile(runtime_archive) as archive:
        prefix = 'Sim2Act/runtime/'
        for name in archive.namelist():
            if not name.startswith(prefix) or name.endswith('/'):
                continue
            relative = name[len(prefix):]
            # Reuse dependencies only. No old application, wheel or native app module.
            if relative.startswith('Lib/site-packages/sim2act'):
                continue
            put(root, 'windows-runtime/' + relative, archive.read(name))
            count += 1
        native = json.loads(archive.read('Sim2Act/full-package-manifest.json'))['native']['_raw_snapshot']
        c_hash = digest(root / 'src/sim2act/_raw_snapshot.c')
        require(c_hash == native['source_sha256'], 'Existing raw dependency has different C source')
        raw = archive.read('Sim2Act/runtime/Lib/site-packages/sim2act/' + native['file'])
        require(hashlib.sha256(raw).hexdigest() == native['sha256'], 'Existing raw dependency differs')
        put(root, 'native/windows/' + native['file'], raw)
        linux = list((repo / 'src/sim2act').glob('_raw_snapshot.cpython-312-*-linux-gnu.so'))
        require(len(linux) == 1, 'Existing local raw dependency required; no build is performed')
        put(root, 'native/linux/' + linux[0].name, linux[0].read_bytes())
    fixture = root / 'fixture'
    fixture.mkdir()
    spec = importlib.util.spec_from_file_location('existing_local_demo', repo / 'scripts/local_candidate_demo.py')
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    settings = demo.settings_for(fixture)
    store = demo.Store(settings.database_url, test_only=True)
    try:
        store.initialize()
        store.user('PUBLIC synthetic browser-review identity', PUBLIC_TOKEN)
        with demo.loopback(store, settings) as (client, _):
            driver = demo.Demo(store, settings, client, fixture)
            project = driver.request('POST', '/api/projects', {'name': '合成前端验收 · 当前源码只读快照'}, 201)['id']
            material = driver.request('POST', f'/api/projects/{project}/resources', {
                'name': '合成报名金额与人数核对_完整中文名称.csv', 'format': 'csv',
                'content': '城市,金额,人数\n杭州,10,2\n成都,20,3\n'}, 201)
            text = driver.request('POST', f'/api/projects/{project}/resources', {
                'name': '合成说明_保留原文与待确认事项.md', 'format': 'md',
                'content': '# 合成核对说明\n\n只读浏览验收，不是真实业务数据。\n- 金额合计应为30。\n- 人数合计应为5。\n- 时间与负责人仍待人工确认。\n'}, 201)
            goal = driver.request('POST', f'/api/projects/{project}/goal-cards', {
                'title': '合成目标：核对金额并保留未决信息', 'goal': '核对已保存合成CSV金额，原文和未决信息保持可读。',
                'known': ['仅供前端浏览验收'], 'assumptions': [], 'unresolved': ['时间与负责人待确认'],
                'constraints': ['不启用模型，不发布，不回写材料'], 'acceptance_checks': ['合成金额30'],
                'resource_refs': [material['id'], text['id']]}, 201)
            app = driver.request('POST', f'/api/projects/{project}/apps/csv-preview', {
                'name': '合成金额合计 · 已保存结果', 'resource_id': material['id'], 'goal': '合成金额合计'}, 201)
            _, release, instance = driver.release(app['id'], {'column': '金额'})
            queued = driver.request('POST', f"/api/internal/instances/{instance['id']}/runs", {
                'expected_release_fingerprint': release['fingerprint'], 'expected_revision': instance['revision'],
                'input': {'column': '金额'}, 'request_key': 'browser-review-deterministic-csv'}, 202)
            result = driver.serve_run(queued['run_id'])
            require(result['status'] == 'SUCCEEDED', 'Deterministic seed Run did not succeed')
            route = f"/api/internal/instances/{instance['id']}/runs/{queued['run_id']}"
            saved = driver.request('GET', route)
            require(saved['result']['sum'] == '30' and saved['result_version'] == 1, 'Wrong saved CSV result')
            receipt = {'format': FORMAT, 'source_commit': source, 'project_id': project, 'goal_id': goal['id'],
                'app_id': app['id'], 'instance_id': instance['id'], 'run_id': queued['run_id'],
                'result_route': route, 'sum': '30', 'result_version': 1,
                'model_requests': 0, 'seed_worker_claims': driver.claims, 'runtime_workers': 0}
        put(root, 'fixture/receipt.json', (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode())
    finally:
        store.engine.dispose()
    (fixture / 'synthetic-demo.db').rename(fixture / 'review.db')
    put(root, 'start-review.cmd', b'@echo off\r\nsetlocal\r\n"%~dp0windows-runtime\\python.exe" -B "%~dp0review_server.py" serve --root "%~dp0." --port 0\r\npause\r\n')
    readme = f'''Sim2Act current-source browser review\nApplication source: {source}\nProfile: SYNTHETIC SQLITE SAVED RESULTS, READ-ONLY API.\nWindows: run start-review.cmd using the INCLUDED existing Python dependency image. No installer, .NET or WebView2 host required. No browser auto-opens. The Windows coordinator must keep candidate and browser profile inside the authorized E:\\Software directory.\nCopy the printed 127.0.0.1 URL into the existing approved browser. Public synthetic login: {PUBLIC_TOKEN}\nChoose the synthetic project, read materials and Goal, then Applications -> saved app -> current instance -> saved Run. The actual deterministic sum is30/v1. Inspect source/checks/history; use themes, density and narrow-pane navigation.\nALL API mutations return405 FRONTEND_REVIEW_READ_ONLY. Draft fields are not persisted; no worker/model runs while serving. No .env, private credential or production database discovery.\nThis is current real UI + current real API with an explicitly synthetic fixture, not a complete production/native desktop package. Windows execution and screenshots are NOT_RUN until the coordinator tests this exact archive.\nThe reused Windows runtime contains third-party dependencies from old ZIP {DEPENDENCY_ZIP_SHA}; all old sim2act application files are excluded. Current Python app sources are inserted explicitly before import. The existing _raw_snapshot module is included only after its C source exactly matches this frozen source; the two changed Cold modules are not reused. This finite read path is separately checked with that minimal dependency.\nClose this server with Ctrl+C and retain the folder/logs if stop is not confirmed. No automatic browser/install/delete/upload. Linux reviewers can use an existing locked Python3.12 environment: python -B review_server.py serve --root . --port 0.\n'''
    put(root, 'README.txt', readme.encode())
    files = {str(p.relative_to(root)).replace('\\', '/'): {'bytes': p.stat().st_size, 'sha256': digest(p)}
        for p in sorted(root.rglob('*')) if p.is_file()}
    manifest = {'format': FORMAT, 'source_commit': source,
        'source_tree': subprocess.check_output(['git', 'rev-parse', source + ':src'], cwd=repo, text=True).strip(),
        'profile': 'SYNTHETIC_SAVED_RESULTS_READ_ONLY_REAL_API', 'runtime_workers': 0, 'model_requests': 0,
        'dependency_archive_sha256': DEPENDENCY_ZIP_SHA, 'windows_dependency_files': count,
        'raw_native_dependency': {'c_source_sha256': c_hash, 'windows_sha256': native['sha256'],
            'linux_sha256': digest(linux[0]), 'other_application_native_modules': 'NOT_INCLUDED'},
        'windows_execution': 'NOT_RUN', 'browser_screenshots': 0, 'files': files}
    put(root, 'manifest.json', (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps({'status': 'PREPARED_NOT_BROWSER_ACCEPTED', 'root': str(root), 'source_commit': source,
        'files': len(files), 'windows_dependency_files': count, 'manifest_sha256': digest(root / 'manifest.json')}))


def serve(root, port, control_stdin):
    require(sys.version_info[:2] == (3, 12), 'Existing Python3.12 required; nothing will be installed')
    root = unlinked(root)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    require(manifest['format'] == FORMAT and manifest['runtime_workers'] == 0, 'Invalid review profile')
    for relative, meta in manifest['files'].items():
        path = PurePosixPath(relative)
        require(not path.is_absolute() and '..' not in path.parts, 'Invalid manifest path')
        file = unlinked(root.joinpath(*path.parts))
        require(file.is_file() and file.stat().st_size == meta['bytes'] and digest(file) == meta['sha256'], 'Frozen file differs: ' + relative)
    sys.path.insert(0, str(root / 'src'))
    import sim2act
    sim2act.__path__.append(str(root / 'native' / ('windows' if sys.platform == 'win32' else 'linux')))
    import sim2act.api
    from sim2act.config import Settings
    from sim2act.db import Store
    from starlette.responses import HTMLResponse, JSONResponse
    import uvicorn
    require(Path(sim2act.api.__file__).resolve().is_relative_to(root / 'src'), 'Wrong application source imported')
    fixture = root / 'fixture'
    database = fixture / 'review.db'
    before = digest(database)
    settings = Settings('sqlite:///' + str(database), fixture, mode='mock')
    store = Store(settings.database_url, test_only=True)
    app = sim2act.api.create_app(store, settings)

    @app.middleware('http')
    async def read_only(request, call_next):
        if request.method not in {'GET', 'HEAD'}:
            response = JSONResponse({'error': {'code': 'FRONTEND_REVIEW_READ_ONLY',
                'message': '只读合成验收快照：保存、执行、审批和发布均关闭；输入草稿未持久化。'}}, status_code=405)
            response.headers.update({'Content-Security-Policy': CSP, 'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store'})
        else:
            response = await call_next(request)
        response.headers['X-Sim2Act-Review-Source'] = manifest['source_commit']
        return response

    @app.get('/')
    def review_page():
        banner = '<section id="synthetic-workspace-banner" role="status"><strong>前端只读验收 · 合成SQLite快照</strong> 当前源码 ' + manifest['source_commit'] + '。公开测试登录：<code>' + PUBLIC_TOKEN + '</code>。只浏览已保存成果；保存、执行、审批、发布均关闭，不启用模型。</section>'
        page = (root / 'src/sim2act/web/index.html').read_text(encoding='utf-8')
        return HTMLResponse(page.replace('<body>', '<body>' + banner, 1))
    app.router.routes.insert(0, app.router.routes.pop())
    try:
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', port))
            listener.listen(128)
            address = 'http://127.0.0.1:' + str(listener.getsockname()[1])
            server = uvicorn.Server(uvicorn.Config(app, log_level='error', access_log=False, timeout_graceful_shutdown=5))
            if control_stdin:
                def stop_on_eof():
                    sys.stdin.read()
                    server.should_exit = True
                threading.Thread(target=stop_on_eof, daemon=True).start()
            print(json.dumps({'event': 'FRONTEND_REVIEW_READY', 'url': address,
                'source_commit': manifest['source_commit'], 'api_module': str(sim2act.api.__file__),
                'profile': manifest['profile'], 'public_synthetic_login': PUBLIC_TOKEN, 'runtime_workers': 0}), flush=True)
            try:
                server.run(sockets=[listener])
            except KeyboardInterrupt:
                pass
    finally:
        store.engine.dispose()
        unchanged = digest(database) == before
        print(json.dumps({'event': 'FRONTEND_REVIEW_STOPPED', 'database_unchanged': unchanged,
            'runtime_workers': 0, 'model_requests': 0}), flush=True)
        require(unchanged, 'Fixture changed; preserve candidate and logs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prep = commands.add_parser('prepare')
    prep.add_argument('--output', type=Path, required=True)
    prep.add_argument('--runtime-archive', type=Path, required=True)
    run = commands.add_parser('serve')
    run.add_argument('--root', type=Path, default=Path(__file__).parent)
    run.add_argument('--port', type=int, default=0)
    run.add_argument('--control-stdin', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.output, args.runtime_archive)
    else:
        require(0 <= args.port <= 65535, 'Invalid loopback port')
        serve(args.root, args.port, args.control_stdin)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Browser review stopped; preserve files: ' + type(error).__name__ + ': ' + str(error), file=sys.stderr)
        raise SystemExit(1)
