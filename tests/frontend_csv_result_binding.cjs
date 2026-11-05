'use strict';
// Exercise the delivered pure projection; no transport, database or acceptance claims.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('src/sim2act/web/use.js','utf8');
const context=vm.createContext({});
vm.runInContext(source.slice(source.indexOf('function csvRunDownloadValue('),source.indexOf('function csvRunDownloadCSV(')),context);
const project=context.csvRunDownloadValue,checks=[];
const value={resource_id:'material-a',column:'金额',sum:'30',count:2};
const run={id:'run-a',app_run_id:'app-run-a',instance_id:'instance-a',release_id:'release-a',status:'SUCCEEDED',result_version:1,result:value};
const record={instance_id:'instance-a',run_id:'app-run-a',release_id:'release-a',version:1,data:{result:value}};
function check(ok,name){assert(ok,name);checks.push(name);}
check(project('instance-a',run,[record])?.result.sum==='30','complete original binding is readable');
for(const key of ['id','app_run_id','release_id','instance_id','result_version']){
 const incomplete={...run};delete incomplete[key];
 check(project('instance-a',incomplete,[record])===null,'missing '+key+' cannot qualify');
}
const missingRun={...run};delete missingRun.app_run_id;delete missingRun.release_id;
const missingRecord={...record};delete missingRecord.run_id;delete missingRecord.release_id;
check(project('instance-a',missingRun,[missingRecord])===null,'two missing identities cannot equal a verified binding');
for(const [key,value] of [['instance_id','instance-b'],['run_id','app-run-b'],['release_id','release-b'],['version',2]]){
 check(project('instance-a',run,[{...record,[key]:value}])===null,'reject mismatched record '+key);
}
check(project('instance-b',run,[record])===null,'caller cannot project another instance');
check(project('instance-a',run,[record,{...record}])===null,'ambiguous duplicate records do not qualify');
check(project('instance-a',run,[null])===null,'null record does not throw or qualify');
check(project('instance-a',run,[{...record,data:{result:{...value,column:'人数',sum:'5'}}}])===null,'人数5 cannot contaminate 金额30');
check(project('instance-a',{...run,status:'UNKNOWN'},[record])===null,'unknown execution cannot qualify');
const projected=project('instance-a',run,[record]);
check(!('goal_acceptance' in projected)&&!('owner_acceptance' in projected),'readback projection does not manufacture acceptance');
console.log(JSON.stringify({status:'PASS',scope:'PURE_PROJECTION_SYNTHETIC_COUNTEREXAMPLES_NOT_CONTRACT_OR_AUTHORIZATION_PROOF',checks},null,2));
