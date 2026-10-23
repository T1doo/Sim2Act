"""Offline actual producer AST -> actual Node consumer; no page/API/browser."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

repo = Path('/workspace/Sim2Act')
source = (repo / 'scripts/protocol_completion_browser_ci.py').read_text()
tree = ast.parse(source)
assignment = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'lf_hashes' for t in n.targets))
inventory = next(n for n in ast.walk(tree) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name) and n.value.func.id == 'write' and len(n.value.args) > 1 and isinstance(n.value.args[1], ast.Constant) and n.value.args[1].value == 'inventory.json')
binding = next(n for n in ast.walk(tree) if isinstance(n, ast.If) and isinstance(n.test, ast.Name) and n.test.id == 'workspace_visual' and any(isinstance(x, ast.Assign) and any(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id == 'info' and isinstance(t.slice, ast.Constant) and t.slice.value == 'visual_source' for t in x.targets) for x in n.body))
program = compile(ast.fix_missing_locations(ast.Module(body=[assignment, inventory, binding], type_ignores=[])), '<actual-production-metadata-statements>', 'exec')
assets = ['src/sim2act/web/' + x for x in ('app.js', 'app.css', 'protocol.js', 'index.html')]
expected = {name: hashlib.sha256((repo / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() for name in assets}
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
payloads = []
with tempfile.TemporaryDirectory(prefix='sim2act-meta-', dir='/tmp') as temporary:
    fixture = Path(temporary)
    for name in assets:
        path = fixture / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((repo / name).read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
    for revision in (commit, 'a' * 40):
        writes = {}
        info = {'cases': [{'current': {'phase': 'source'}}]}
        namespace = dict(REPO=fixture, hashes={name: hashlib.sha256((fixture / name).read_bytes()).hexdigest() for name in assets}, hashlib=hashlib, commit=revision, business_at=45, root=fixture, write=lambda _root, name, value: writes.__setitem__(name, value), workspace_visual=True, info=info)
        exec(program, namespace)
        assert writes['inventory.json']['source_lf_sha256'] == expected
        assert info['visual_source'] == {'commit': revision, 'asset_lf_sha256': expected}
        assert all(writes['inventory.json']['source_sha256'][name] != expected[name] for name in assets)
        payloads.append(info)
    node = r'''
    const fs=require('node:fs'),assert=require('node:assert/strict');
    const {runWorkspaceVisual}=require(process.cwd()+'/scripts/browser-ci/workspace-visual.cjs');
    const inputs=JSON.parse(fs.readFileSync(0,'utf8'));let pages=0,untilCalls=0;
    const page=new Proxy({}, {get(){pages++;throw Error('Page access forbidden');}});
    async function valid(info){const result={};const stop=Error('STOP_AFTER_METADATA');await assert.rejects(runWorkspaceVisual({page,info,result,until:async()=>{untilCalls++;throw stop;}}), e=>e===stop);assert.equal(result.visual.product_source,info.visual_source.commit);assert.deepEqual(result.visual.product_asset_lf_sha256,info.visual_source.asset_lf_sha256);assert.equal(result.visual.capture_revision,'workspace-density-v2');return result;}
    (async()=>{
      const a=await valid(inputs[0]),b=await valid(inputs[1]);assert.notEqual(a.visual.product_source,b.visual.product_source);
      for(const kind of ['missing','malformed-hash']){const info=structuredClone(inputs[0]),result={};if(kind==='missing')delete info.visual_source;else info.visual_source.asset_lf_sha256['src/sim2act/web/app.css']='not-a-sha';await assert.rejects(runWorkspaceVisual({page,info,result,until:async()=>{throw Error('Invalid metadata must reject before until');}}));assert.equal(result.visual,undefined);}
      assert.equal(pages,0);assert.equal(untilCalls,2);
      console.log(JSON.stringify({status:'PASS',valid_commit_propagations:2,missing_and_malformed_rejected:2,page_accesses:pages,browser_api_model_calls:0}));
    })().catch(e=>{console.error(e);process.exitCode=1;});
    '''
    result = subprocess.run(['node', '-e', node], input=json.dumps(payloads), cwd=repo, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    checks = json.loads(result.stdout)
old = subprocess.check_output(['git', 'show', 'HEAD:scripts/browser-ci/workspace-visual.cjs'], cwd=repo, text=True)
new = (repo / 'scripts/browser-ci/workspace-visual.cjs').read_text()
assert old.split(' const view=async(width)=>', 1)[1] == new.split(' const view=async(width)=>', 1)[1]
for name in assets:
    assert (repo / name).read_bytes() == subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=repo)
print(json.dumps(dict(status='PASS',scope='OFFLINE metadata integration, not native visual acceptance',real_producer_statements=True,crlf_inventory_and_info_identical=True,node=checks,all_visual_actions_and_assertions_unchanged=True,business_asset_bytes_unchanged=True,base_commit=commit,asset_lf_sha256=expected), indent=2))
