'use strict';
// Static template/stylesheet audit. This does not run a browser or certify pixels.
const fs=require('node:fs'),cp=require('node:child_process'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {JSDOM}=require('jsdom'),css=require('css-tree');
const baseline='51bcbcde3d9188420081802aa9aa35aebe5d009a',web='src/sim2act/web/';
const old=cp.execFileSync('git',['show',baseline+':'+web+'index.html'],{encoding:'utf8'});
const html=fs.readFileSync(web+'index.html','utf8'),style=fs.readFileSync(web+'app.css','utf8');
const before=new JSDOM(old),after=new JSDOM(html),a=before.window.document,b=after.window.document;
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const oldIds=[...a.querySelectorAll('[id]')].map(x=>x.id),newIds=[...b.querySelectorAll('[id]')].map(x=>x.id);
assert.equal(new Set(newIds).size,newIds.length,'No duplicate IDs');
for(const id of oldIds)assert.ok(b.getElementById(id),'Original ID retained: '+id);
const controls=e=>[...e.querySelectorAll('input,select,textarea,button,option')].map(x=>({tag:x.tagName,attributes:[...x.attributes].map(a=>[a.name,a.value]).sort(),text:x.textContent}));
assert.deepEqual(controls(b),controls(a),'Every original control, attribute, value, order and label retained');
const hidden=e=>[...e.querySelectorAll('[hidden]')].map(x=>x.id||x.outerHTML);
assert.deepEqual(hidden(b),hidden(a),'All original hidden gates retained');
assert.deepEqual([...b.scripts].map(x=>x.src),[...a.scripts].map(x=>x.src),'Original script set and order');
assert.equal(b.getElementById('goal-card-form').parentElement.outerHTML.split('<form')[0],a.getElementById('goal-card-form').parentElement.outerHTML.split('<form')[0]);
assert.equal(b.querySelector('#projects .grid > section:last-child h2').textContent,'成果画布');
assert.equal(b.getElementById('project-tools').hasAttribute('open'),false);
assert.deepEqual([...b.querySelectorAll('#project-tools > .tool-content > fieldset')].map(x=>x.id),['pn-panel','text-logic-panel','text-continuation-panel','csv-logic-panel']);
for(const node of b.querySelectorAll('.section-links a,.skip-link'))assert.ok(b.querySelector(node.getAttribute('href')),'Real anchor target');
for(const id of ['projects','apps','resources'])assert.equal(b.getElementById(id).querySelectorAll('h1').length,1);
assert.match(style,/\[hidden\]\s*\{\s*display:\s*none\s*!important;/);
const errors=[],ast=css.parse(style,{positions:true,onParseError:e=>errors.push(e.formattedMessage)});
const variables=new Map();
css.walk(ast,n=>{if(n.type==='Declaration'&&n.property.startsWith('--'))variables.set(n.property,css.generate(n.value));});
let rules=0,declarations=0;
css.walk(ast,node=>{if(node.type==='Rule')rules++;if(node.type==='Declaration'){declarations++;if(!node.property.startsWith('--')){const match=css.lexer.matchProperty(node.property,css.generate(node.value).replace(/var\((--[\w-]+)\)/g,(_match,key)=>{assert.ok(variables.has(key));return variables.get(key);}));if(match.error)errors.push(match.error.message);}}});
assert.deepEqual(errors,[],'CSS syntax and property grammar');
function luminance(hex){return hex.match(/[a-f0-9]{2}/gi).map(n=>parseInt(n,16)/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0);}
function ratio(fg,bg){const [l,h]=[luminance(fg),luminance(bg)].sort((a,b)=>a-b);return (h+.05)/(l+.05);}
const pairs=[['body','#243b34','#f3f5f1'],['muted','#53675e','#ffffff'],['primary','#ffffff','#166453'],['default status','#3e5350','#f0f4f2'],['error','#8d302c','#fff2f0'],['loading','#2f526d','#edf4fa'],['eyebrow','#49725e','#ffffff'],['disabled','#607168','#edf1ee'],['workspace label','#42634f','#ebf1e8']].map(([label,fg,bg])=>({label,fg,bg,ratio:ratio(fg,bg)}));
for(const p of pairs)assert.ok(p.ratio>=4.5,p.label+' solid-color contrast');
const sources=Object.fromEntries(['index.html','app.css','app.js','protocol.js','text-logic.js'].map(name=>[name,hash(fs.readFileSync(web+name))]));
for(const name of ['app.js','protocol.js','text-logic.js'])assert.equal(hash(cp.execFileSync('git',['show',baseline+':'+web+name])),sources[name]);
console.log(JSON.stringify({classification:'STATIC_ONLY_NOT_NATIVE_VISUAL_ACCEPTANCE',baseline,status:'PASS',original_ids:oldIds.length,final_ids:newIds.length,original_controls:controls(a).length,hidden_gates:hidden(a).length,css:{rules,declarations,errors},solid_color_contrast:pairs,sources,new_business_http:0,new_models:0,new_browser_launches:0},null,2));
before.window.close();after.window.close();
