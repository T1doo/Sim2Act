"""Independent counters, never a production/native routing replacement."""
import hashlib,json,subprocess,sysconfig
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path('/workspace/scratch/graph-shape-diagnostic-20261030');out.mkdir(exist_ok=True)
p=root/'src/sim2act/_cold_graph_structure.c';s=p.read_text();original=hashlib.sha256(p.read_bytes()).hexdigest()
s=s.replace('static Entry*find(Map*m,PyObject*v){', 'typedef struct {size_t finds,probes,inserts,resizes,allocated;} Cost;\nstatic Entry*find(Map*m,PyObject*v,Cost*cost){if(cost)cost->finds++;')
s=s.replace('while(m->entries[j].key){if(m->entries[j].key==v)', 'while(m->entries[j].key){if(cost)cost->probes++;if(m->entries[j].key==v)')
s=s.replace('return NULL;}\nstatic int insert(Map*m,PyObject*v,size_t ordinal){', 'if(cost)cost->probes++;return NULL;}\nstatic int insert(Map*m,PyObject*v,size_t ordinal,Cost*cost){if(cost)cost->inserts++;')
s=s.replace('Entry*next=PyMem_Calloc(n,sizeof(Entry));', 'if(cost){cost->resizes++;cost->allocated+=n*sizeof(Entry); }Entry*next=PyMem_Calloc(n,sizeof(Entry));')
s=s.replace('find(&t->map,v)', 'find(&t->map,v,NULL)').replace('insert(&t->map,v,id)', 'insert(&t->map,v,id,NULL)')
s=s.replace('Map changed;size_t work;} Compare;', 'Map changed;size_t work;Cost orig_cost,changed_cost;size_t originals,owned,reducers;} Compare;')
s=s.replace('find(&c->t->map,v)', 'find(&c->t->map,v,&c->orig_cost)').replace('find(&c->changed,v)', 'find(&c->changed,v,&c->changed_cost)').replace('insert(&c->changed,v,id)', 'insert(&c->changed,v,id,&c->changed_cost)')
s=s.replace('if(v==n->original){\n  /*', 'if(v==n->original){c->originals++;\n  /*')
s=s.replace('c->actual[id]=Py_NewRef(v);', 'c->owned++;c->actual[id]=Py_NewRef(v);')
s=s.replace('payload=PyObject_CallFunctionObjArgs(c->t->types.reduce,', 'c->reducers++;payload=PyObject_CallFunctionObjArgs(c->t->types.reduce,')
# Only diagnostic matches changes return type. Default native is untouched.
s=s.replace('return PyBool_FromLong(result);\n}', '''return Py_BuildValue("{s:O,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n}",
 "match",result?Py_True:Py_False,"work",(Py_ssize_t)c.work,"original_pointer_nodes",(Py_ssize_t)c.originals,"owned_current_nodes",(Py_ssize_t)c.owned,"reducer_calls",(Py_ssize_t)c.reducers,
 "original_find_calls",(Py_ssize_t)c.orig_cost.finds,"original_find_probes",(Py_ssize_t)c.orig_cost.probes,
 "changed_find_calls",(Py_ssize_t)c.changed_cost.finds,"changed_find_probes",(Py_ssize_t)c.changed_cost.probes,
 "changed_inserts",(Py_ssize_t)c.changed_cost.inserts,"changed_resizes",(Py_ssize_t)c.changed_cost.resizes,
 "changed_allocated_bytes",(Py_ssize_t)c.changed_cost.allocated,"array_allocated_bytes",(Py_ssize_t)(t->count*(sizeof(PyObject*)+sizeof(size_t))));
}''')
assert 'return PyBool_FromLong(result);' not in s
extra='''
static PyObject *shape(PyObject*self,PyObject*cap){
 (void)self;Tree*t=PyCapsule_GetPointer(cap,"sim2act.cold-graph-structure.v1");if(!t)return NULL;
 size_t edges=0,counts[256]={0};for(size_t i=0;i<t->count;i++){edges+=t->nodes[i].count;counts[t->nodes[i].kind]++;}
 PyObject*kinds=PyDict_New();if(!kinds)return NULL;
 for(int k=0;k<256;k++)if(counts[k]){char key[2]={(char)k,0};PyObject*n=PyLong_FromSize_t(counts[k]);if(!n||PyDict_SetItemString(kinds,key,n)<0){Py_XDECREF(n);Py_DECREF(kinds);return NULL;}Py_DECREF(n);}
 PyObject*out=Py_BuildValue("{s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:N}","nodes",(Py_ssize_t)t->count,"edges",(Py_ssize_t)edges,"capture_work",(Py_ssize_t)t->work,"text_storage_bound_bytes",(Py_ssize_t)t->bytes,"original_map_slots",(Py_ssize_t)t->map.slots,"captured_structure_allocated_bytes",(Py_ssize_t)(t->capacity*sizeof(Node)+edges*sizeof(size_t)+t->map.slots*sizeof(Entry)),"compare_initial_arrays_bytes",(Py_ssize_t)(t->count*(sizeof(PyObject*)+sizeof(size_t))),"kinds",kinds);return out;
}
'''
s=s.replace('static PyMethodDef methods[]=',extra+'\nstatic PyMethodDef methods[]=')
s=s.replace('methods[]={{"same_classes"','methods[]={{"shape",shape,METH_O,"Read-only bounded counters, no graph data."},{"same_classes"')
src=out/'_cold_graph_structure.c';src.write_text(s);sha=hashlib.sha256(src.read_bytes()).hexdigest();binary=out/('_cold_graph_structure'+sysconfig.get_config_var('EXT_SUFFIX'))
command=['/usr/bin/cc','-shared','-fPIC','-O2','-Wall','-Wextra','-DSIM2ACT_GRAPH_SOURCE_SHA="'+sha+'"','-I'+sysconfig.get_path('include'),str(src),'-o',str(binary)]
p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(out/'build.log').write_text(p.stdout);assert p.returncode==0,p.stdout
(out/'build.json').write_text(json.dumps(dict(classification='DIAGNOSTIC_COUNTER_MODULE_NOT_PRODUCTION_ROUTING',baseline_source_sha256=original,diagnostic_source_sha256=sha,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),command=command,returncode=p.returncode),indent=2)+'\n')
print('Private diagnostic module built with unchanged Tree/Node/Map layouts')
