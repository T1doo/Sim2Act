'use strict';
// Offline CSS semantics and contrast only: no layout, pixels, HTTP or model.
const fs=require('node:fs'),assert=require('node:assert/strict'),cp=require('node:child_process'),css=require('css-tree');
const base='91fbafce024795b071c0f03015945b055669de6b',file='src/sim2act/web/app.css';
const before=cp.execFileSync('git',['show',`${base}:${file}`],{encoding:'utf8'}),after=fs.readFileSync(file,'utf8');
function rules(text){const result=[];function visit(list,media=''){for(const n of list){if(n.type==='Rule')result.push({selector:css.generate(n.prelude),media,decl:[...n.block.children].filter(d=>d.type==='Declaration').map(d=>[d.property,css.generate(d.value).trim()+(d.important?'!important':'')])});else if(n.type==='Atrule'&&n.block)visit(n.block.children,media+'@'+n.name+(n.prelude?css.generate(n.prelude):''));}}visit(css.parse(text).children);return result;}
const previous=rules(before),current=rules(after),checks=[],contrasts=[];
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const canonical=s=>css.generate(css.parse(s,{context:'selectorList'}));
function rule(selector,media=''){const found=current.filter(r=>r.selector===canonical(selector)&&r.media===media).at(-1);assert(found,selector);return Object.fromEntries(found.decl);}
const tokens=rule(':root'),resolve=v=>v.replace(/var\((--[\w-]+)\)/g,(_,name)=>{assert(tokens[name],name);return tokens[name];});
function luminance(color){let hex=resolve(color);assert.match(hex,/^#[0-9a-f]{3,6}$/i);hex=hex.slice(1);if(hex.length===3)hex=[...hex].map(c=>c+c).join('');const c=[0,2,4].map(i=>parseInt(hex.slice(i,i+2),16)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return .2126*c[0]+.7152*c[1]+.0722*c[2];}
function contrast(name,fg,bg,minimum=4.5){const a=luminance(fg),b=luminance(bg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);contrasts.push({name,foreground:resolve(fg),background:resolve(bg),ratio:Number(ratio.toFixed(4)),minimum});assert(ratio>=minimum,name+': '+ratio);}
contrast('primary white text','#fff',tokens['--accent']);
contrast('primary hover white text','#fff',tokens['--accent-hover']);
contrast('secondary action on white',tokens['--accent'],'#fff');
contrast('current narrow navigation',tokens['--accent'],tokens['--accent-soft']);
contrast('main body text',tokens['--ink'],'#fff');
contrast('secondary text on canvas',tokens['--muted'],tokens['--canvas']);
const wide='@media(min-width:1100px)';
contrast('wide navigation normal',rule('#workspace-nav [data-tab]',wide).color,tokens['--nav-surface']);
contrast('wide navigation current',rule('#workspace-nav [data-tab][aria-current="true"]',wide).color,tokens['--nav-current']);
contrast('wide navigation helper',rule('#workspace-nav::before',wide).color,tokens['--nav-surface']);
contrast('page focus outline',tokens['--focus'],'#fff',3);
contrast('navigation focus outline',tokens['--nav-focus'],tokens['--nav-current'],3);
check(contrasts.length===11,'representative text and focus colors meet stated contrast thresholds');

// Compare the whole stylesheet, removing only color/presentation differences.
// Geometry, source order, visibility, content strings and animation guards must
// remain identical, apart from the two deliberately larger eyebrow styles.
const colorProperties=new Set(['color','background','background-color','border-color','border-left-color','border-bottom-color','border-top-color','outline-color','accent-color','caret-color']);
const colorVars=new Set(Object.entries(tokens).filter(([,v])=>/^#/.test(v)).map(([k])=>k));
const cleanValue=v=>v.replace(/#[\da-f]{3,8}\b|rgba?\([^)]*\)/gi,'COLOR').replace(/var\((--[\w-]+)\)/g,(full,name)=>colorVars.has(name)?'COLOR':full);
function structural(list){return list.map(r=>({...r,decl:r.decl.filter(([p])=>!p.startsWith('--')&&!colorProperties.has(p)&&!((r.selector==='.eyebrow'||r.selector==='.panel-heading .eyebrow')&&['font-size','letter-spacing'].includes(p))).map(([p,v])=>[p,cleanValue(v)])})).filter(r=>r.decl.length);}
assert.deepEqual(structural(current),structural(previous));
check(true,'all non-color geometry, visibility, content and motion rules preserved except explicit eyebrow typography');
const states=list=>list.filter(r=>/data-state=|data-read-state=|\.reading-unknown|reading-error-title/.test(r.selector));
assert.deepEqual(states(current),states(previous));
check(true,'error, unknown, success and loading selectors and declarations stay unchanged');
const hidden=rule('[hidden]');check(hidden.display==='none!important','hidden content remains forcibly hidden');
check(rule(':root','@media(forced-colors:active)')['--focus']==='Highlight'&&rule(':root','@media(forced-colors:active)')['--nav-focus']==='Highlight','forced-color focus remains a system color on page and navigation');
const oldUrls=[],newUrls=[];css.walk(css.parse(before),n=>{if(n.type==='Url')oldUrls.push(n.value);});css.walk(css.parse(after),n=>{if(n.type==='Url')newUrls.push(n.value);});assert.deepEqual(newUrls,oldUrls);
check(true,'no new font, image or external asset URL');
console.log(JSON.stringify({status:'PASS',scope:'offline CSS AST and numerical contrast; NOT native layout or pixel acceptance',base,checks,contrasts,network_requests:0,models:0},null,2));
