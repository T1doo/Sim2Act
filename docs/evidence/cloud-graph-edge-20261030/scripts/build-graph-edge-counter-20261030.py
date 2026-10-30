import hashlib,json,subprocess,sysconfig
from pathlib import Path
base=Path('/workspace/scratch/graph-shape-diagnostic-20261030/_cold_graph_structure.c').read_text();out=Path('/workspace/scratch/graph-edge-counter-20261030');out.mkdir(exist_ok=True)
base=base.replace('size_t originals,owned,reducers;} Compare;','size_t originals,owned,reducers,fast_edges,slow_edges;} Compare;')
helper='''
static int compare_node(Compare*c,size_t id,PyObject*v,int depth);
static int measured_edge(Compare*c,size_t id,PyObject*v,int depth){
 Node*n=c->t->nodes+id;int k=n->kind;
 int cached=c->actual[id]==v&&(k=='m'||k=='l'||k=='q'||k=='s'||k=='b'||k=='p');
 int scalar=v==n->original&&(k=='n'||k=='t'||k=='f'||k=='i'||k=='d');
 int text=v==n->original&&(k=='s'||k=='b');
 if(cached||scalar||text)c->fast_edges++;else c->slow_edges++;
 return compare_node(c,id,v,depth);
}
'''
needle='static int compare_node(Compare*c,size_t id,PyObject*v,int depth){';assert base.count(needle)==1;base=base.replace(needle,helper+'\n'+needle)
for item in ('a','b','x'):base=base.replace('compare_node(c,n->edges[edge++],'+item+',depth+1)','measured_edge(c,n->edges[edge++],'+item+',depth+1)')
old='"array_allocated_bytes",(Py_ssize_t)(t->count*(sizeof(PyObject*)+sizeof(size_t))));'
new='"array_allocated_bytes",(Py_ssize_t)(t->count*(sizeof(PyObject*)+sizeof(size_t))),"fast_edges",(Py_ssize_t)c.fast_edges,"slow_edges",(Py_ssize_t)c.slow_edges);'
assert base.count(old)==1;base=base.replace(old,new)
base=base.replace('"{s:O,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n}"','"{s:O,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n,s:n}"')
src=out/'_cold_graph_structure.c';src.write_text(base);sha=hashlib.sha256(src.read_bytes()).hexdigest();binary=out/('_cold_graph_structure'+sysconfig.get_config_var('EXT_SUFFIX'))
command=['/usr/bin/cc','-shared','-fPIC','-O3','-DNDEBUG','-DSIM2ACT_GRAPH_SOURCE_SHA="'+sha+'"','-I'+sysconfig.get_path('include'),str(src),'-o',str(binary)];p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(out/'build.log').write_text(p.stdout);assert p.returncode==0,p.stdout;(out/'build.json').write_text(json.dumps(dict(classification='ORIGINAL_WALK_WITH_POTENTIAL_EDGE_COUNTS_DIAGNOSTIC_ONLY',source_sha256=sha,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),command=command,returncode=p.returncode),indent=2)+'\n')
print('Counter preserves full old walker and counts eligible original edges')
