"use strict";
// Test platform adapter, not native-browser acceptance. Shares only Storage/Web Locks.
const fs=require("node:fs");
module.exports=function browser(storagePath,options={}){
 const origins=new Map(),locks=new Map(),busy=new Set(),events=[];
 function install(window){
  const origin=window.location.origin;
  if(!origins.has(origin))origins.set(origin,{values:new Map(storagePath&&fs.existsSync(storagePath)?JSON.parse(fs.readFileSync(storagePath)):[]),windows:new Set()});
  const state=origins.get(origin);state.windows.add(window);
  function change(key,value){
   const oldValue=state.values.get(key)??null;
   if(value===null)state.values.delete(key);else state.values.set(key,String(value));
   if(storagePath)fs.writeFileSync(storagePath,JSON.stringify([...state.values]));
   if(options.storageEvents!==false)for(const other of state.windows)if(other!==window&&!other.closed)other.dispatchEvent(new other.StorageEvent("storage",{key,oldValue,newValue:value,url:window.location.href}));
  }
  Object.defineProperty(window,"localStorage",{value:{get length(){return state.values.size;},key:index=>[...state.values.keys()][index]??null,getItem:key=>state.values.get(key)??null,setItem:(key,value)=>change(key,String(value)),removeItem:key=>change(key,null)}});
  Object.defineProperty(window.navigator,"locks",{configurable:true,value:{request(name,options,callback){
   if(options.mode!=="exclusive")throw Error("Only explicit exclusive Web Locks supported in fixture");
   const key=JSON.stringify([origin,name]),previous=locks.get(key)||Promise.resolve();
   if(options.ifAvailable&&busy.has(key)){events.push({event:"BUSY",origin,name});return Promise.resolve().then(()=>callback(null));}
   busy.add(key);
   events.push({event:"WAIT",origin,name});
   const work=previous.catch(()=>{}).then(async()=>{events.push({event:"ACQUIRE",origin,name});try{return await callback({name,mode:"exclusive"});}finally{busy.delete(key);events.push({event:"RELEASE",origin,name});}});
   locks.set(key,work.catch(()=>{}));return work;
  }}});
 }
 return {install,events,values:origin=>[...(origins.get(origin)?.values||[])]};
};
