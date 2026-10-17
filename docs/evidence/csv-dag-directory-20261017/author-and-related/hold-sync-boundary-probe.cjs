'use strict';
// Synthetic-clock probe of the actual unmodified driver helper, not product HTTP.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const path='/workspace/Sim2Act/tests/csv_dag_directory.cjs',source=fs.readFileSync(path,'utf8');
const helper=source.slice(source.indexOf('const waitHeld='),source.indexOf('function visible('));
const cases=[
 {name:'exact gate with reply at 1s',at:1000,replies:[1000],gate:true,ok:true},
 {name:'late gate cannot renew a 13s reply gap',at:13000,replies:[13000],gate:true,error:'12s HTTP reply gap'},
 {name:'12s exact gap rejects gate',at:12000,replies:[12000],gate:true,error:'12s HTTP reply gap'},
 {name:'13s without reply rejects',at:13000,replies:[],gate:false,error:'12s without HTTP progress'},
 {name:'60s total rejects despite sub12s replies',at:60000,replies:[10000,20000,30000,40000,50000,60000],gate:true,error:'60s total'},
];
(async()=>{
 const results=[];
 for(const c of cases){
  let clock=0;const replies=[],records=[];
  const context=vm.createContext({Date:{now:()=>clock},httpReplies:replies,heldWaits:records,releaseRead:null,
   setTimeout:fn=>{clock=c.at;replies.push(...c.replies);context.releaseRead=c.gate?()=>{}:null;fn();}});
  vm.runInContext(helper+'\nglobalThis.probeWait=waitHeld;',context);
  let error;
  try{await context.probeWait(c.name);}catch(e){error=e.message;}
  if(c.ok)assert.equal(error,undefined);else assert(error?.includes(c.error),c.name+': '+error);
  results.push({name:c.name,status:'PASS',error,records});
 }
 const out={scope:'Synthetic-clock validation of exact actual driver helper; no product/HTTP/Worker/browser/model execution',driver_sha256:crypto.createHash('sha256').update(source).digest('hex'),results};
 process.stdout.write(JSON.stringify(out,null,2)+'\n');
})();
