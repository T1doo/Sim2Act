'use strict';const fs=require('node:fs'),assert=require('node:assert/strict'),path=require('node:path');
const root=process.argv[2],factory=require('/workspace/Sim2Act-native-session-diagnostic/scripts/browser-ci/conditional-fixture-session.cjs');
(async()=>{const checks=[];for(const mode of ['spawn','bad-json','stderr']){
 const secret='INDEPENDENT_TOKEN_SECRET_347';let python=path.join(root,'PRIVATE_PATH_'+secret);
 if(mode!=='spawn') {python=path.join(root,'fake-'+mode);fs.writeFileSync(python,'#!/usr/bin/env python3\nimport sys\nsys.stdin.readline()\n'+(mode==='bad-json'?'print("'+secret+' malformed PRIVATE_PATH")\n':'print("sim2act.types.DomainError: '+secret+' PRIVATE_PATH", file=sys.stderr)\nraise SystemExit(7)\n'));fs.chmodSync(python,0o700);}
 const fixture=factory({python,root,cwd:'/workspace/Sim2Act-native-session-diagnostic'});let message='';try{await fixture.action('snapshot');assert.fail('fault unexpectedly accepted');}catch(e){message+=e.message;}try{await fixture.close();}catch(e){message+=e.message;}
 const serialized=message+JSON.stringify(fixture.diagnostics);assert(!serialized.includes(secret));assert(!serialized.includes('PRIVATE_PATH'));assert.equal(fixture.diagnostics.lastRequestedAction,'snapshot');
 if(mode==='bad-json')assert(message.includes('Wrong conditional fixture reply'));
 if(mode==='stderr'){assert.equal(fixture.diagnostics.exceptionClass,'DomainError');assert.equal(fixture.diagnostics.exitCode,7);}
 if(mode==='spawn')assert(message.includes('code=ENOENT'));
 checks.push({mode,status:'PASS',diagnostics:fixture.diagnostics});
 }fs.writeFileSync(path.join(root,'safe-errors.json'),JSON.stringify({status:'PASS',checks},null,2));console.log('SAFE_ERRORS_3_PASS');})().catch(e=>{console.error(e);process.exitCode=1;});
