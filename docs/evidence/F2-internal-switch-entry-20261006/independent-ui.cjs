const fs=require('fs'),vm=require('vm');
const elements=new Map();function el(id){if(!elements.has(id))elements.set(id,{value:id==='project-select'?'proj':'',dataset:{},children:[],options:[],replaceChildren(...x){this.children=x},append(){},textContent:'',checked:false,hidden:false});return elements.get(id)}
let resolveCreate,posted;const release={id:'release',fingerprint:'a'.repeat(64)};
const instance=id=>({id,source_app_id:'app',project_id:'proj',release_id:'release',revision:1,data_version:0,release_fingerprint:release.fingerprint,data:[],runs:[]});
const context={console,token:'synthetic',activeApp:'app',appSelectionGeneration:1,$:el,crypto:{randomUUID:()=> 'synthetic-key'},setInterval:()=>0,document:{createElement:()=>({})},Option:function(text,value){this.textContent=text;this.value=value},row:(text,callback)=>({text,callback}),api:async(path,method='GET')=>{
 if(method==='POST'&&path.endsWith('/instances')){posted=true;return new Promise(r=>resolveCreate=r)}
 if(path.endsWith('/releases'))return {items:[release]};
 if(path.endsWith('/instances'))return {items:[instance('B')]};
 if(path.startsWith('/api/internal/instances/'))return instance(path.split('/').at(-1));
 throw Error('unexpected '+path)
}};
vm.createContext(context);vm.runInContext(fs.readFileSync('/workspace/Sim2Act-pb/src/sim2act/web/internal.js','utf8'),context);
(async()=>{
 const setup=()=>{vm.runInContext(`engineering={app:'app',project:'proj',token,appGeneration:1,draft:{id:'app'},busy:false,approval:null,instance:{id:'A',revision:1,release_id:'old'},run:null,instanceGeneration:1,runGeneration:0,releases:[{id:'target',fingerprint:'a'.repeat(64)}],switchGeneration:0,switchApproval:null}`,context);el('internal-switch-target').value='target'};
 setup();let postCount=0,getCount=0,resolvePrepare;context.api=async(path,method='GET')=>{if(method==='POST'){postCount++;return new Promise(r=>resolvePrepare=r)}getCount++;throw Error('late reply must not GET')};
 const first=el('internal-switch-prepare').onclick();const duplicate=el('internal-switch-prepare').onclick();el('internal-switch-cancel').onclick();resolvePrepare({id:'approval',fingerprint:'b'.repeat(64)});await first;await duplicate;
 if(postCount!==1||getCount||!el('internal-switch-approval').hidden||vm.runInContext('engineering.switchApproval',context)!==null)throw Error('late cancelled prepare restored state');console.log('late prepare cancellation and duplicate one-request PASS');
 setup();postCount=0;getCount=0;let resolveCommit;vm.runInContext(`engineering.switchApproval={id:'approval',fingerprint:'b'.repeat(64),expires_at:Date.now()/1000+300}`,context);el('internal-switch-ack').checked=true;
 context.api=async(path,method='GET')=>{if(method==='POST'){postCount++;return new Promise(r=>resolveCommit=r)}getCount++;throw Error('late commit must not reread selection')};
 const commit=el('internal-switch-commit').onclick();const duplicateCommit=el('internal-switch-commit').onclick();el('internal-switch-cancel').onclick();resolveCommit({release_id:'target',revision:2});await commit;await duplicateCommit;
 if(postCount!==1||getCount||vm.runInContext('engineering.switchApproval',context)!==null||el('internal-switch-target').value!=='')throw Error('late commit repaint/retry');console.log('one-shot commit and cancelled late receipt no repaint/retry PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
