from pathlib import Path
import hashlib,json,subprocess,sys
r=Path('/tmp/sim2act-read-stability-20261010');root=Path.cwd();freeze=json.loads((r/'source-freeze.json').read_text());d=Path('docs/evidence/readback-stability-20261010');ref=sys.argv[1];target=Path(sys.argv[2])
def sha(v):return hashlib.sha256(v).hexdigest()
def gitbytes(path):return subprocess.check_output(['git','show',f'{ref}:{path}'],stderr=subprocess.PIPE)
for p,h in freeze['files'].items():
 assert sha(Path(p).read_bytes())==h,p
 assert sha(gitbytes(p))==h,(ref,p)
manifest=json.loads((d/'author-export-manifest.json').read_text())['explicit_whitelist']
for p,v in manifest.items():
 dst=d/p;assert sha(dst.read_bytes())==v['sha256'],str(dst);assert sha(gitbytes(dst.as_posix()))==v['sha256'],(ref,str(dst))
iw=json.loads((d/'independent/COPY_WHITELIST.json').read_text())['files']
for v in iw:
 dst=d/'independent'/v['path'];assert sha(dst.read_bytes())==v['sha256'],str(dst);assert sha(gitbytes(dst.as_posix()))==v['sha256'],(ref,str(dst))
proof=dict(ref=ref,HEAD=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_sha=freeze['source_sha'],frozen_files=len(freeze['files']),products=json.loads((r/'product-byte-proof.json').read_text())['products'],all_source_worktree_and_Git_equal=True,author_files=len(manifest),independent_files=len(iw),all_explicit_evidence_worktree_and_Git_equal=True,known_lock='codex-index-refresh.lock 0 bytes, retained')
target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(proof,indent=2)+'\n');print(proof)
