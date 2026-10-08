'use strict';
// Passive HTTP/body timings; leaves URLs, options, responses and assertions intact.
const fs=require('node:fs'),path=require('node:path');
const root=process.env.SIM2ACT_DIAG_ROOT;
if(root){
 const file=path.join(root,`node-${process.pid}.jsonl`),origin=performance.now();
 const write=value=>fs.appendFileSync(file,JSON.stringify({utc:new Date().toISOString(),elapsed_ms:performance.now()-origin,...value})+'\n');
 write({event:'process_start',argv:process.argv});
 const original=globalThis.fetch;let index=0;
 globalThis.fetch=async function(...args){
  const id=++index,start=performance.now(),url=new URL(String(args[0]));
  write({event:'http_start',id,path:url.pathname,method:args[1]?.method||'GET'});
  try{
   const response=await original.apply(this,args);
   write({event:'http_headers',id,path:url.pathname,status:response.status,seconds:(performance.now()-start)/1000});
   for(const name of ['json','text','arrayBuffer']){
    const body=response[name].bind(response);
    response[name]=async(...values)=>{const before=performance.now();try{return await body(...values);}finally{write({event:'body',id,method:name,seconds:(performance.now()-before)/1000});}};
   }
   return response;
  }catch(error){write({event:'http_error',id,path:url.pathname,type:error.name,seconds:(performance.now()-start)/1000});throw error;}
 };
 process.on('exit',code=>write({event:'process_exit',code}));
}
