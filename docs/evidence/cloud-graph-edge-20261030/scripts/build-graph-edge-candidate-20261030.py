import hashlib,json,subprocess,sysconfig
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path('/workspace/scratch/graph-edge-candidate-20261030');out.mkdir(exist_ok=True)
original=(root/'src/sim2act/_cold_graph_structure.c').read_text()
helper='''
static int compare_node(Compare*c,size_t id,PyObject*v,int depth);
/* Only leaf/current-call memo work is inlined. First mutable/reducer visits
 * still enter the original full walker. Signal/work/depth order is retained. */
static inline int compare_edge(Compare*c,size_t id,PyObject*v,int depth){
 Node*n=c->t->nodes+id;int k=n->kind;
 int cached=c->actual[id]==v&&(k=='m'||k=='l'||k=='q'||k=='s'||k=='b'||k=='p');
 int scalar=v==n->original&&(k=='n'||k=='t'||k=='f'||k=='i'||k=='d');
 int text=v==n->original&&(k=='s'||k=='b');
 if(!cached&&!scalar&&!text)return compare_node(c,id,v,depth);
 if((c->work++&1023)==0&&PyErr_CheckSignals()<0)return -1;
 if(c->work>1000000||depth>64){PyErr_SetString(unsupported_error,"Cold graph compare bounds");return -1;}
 if(scalar)return 1;
 if(c->actual[id])return c->actual[id]==v;
 /* Only the immutable text identity path can first-register here. */
 size_t*assigned=c->assigned+id;if(*assigned&&*assigned!=id+1)return 0;
 *assigned=id+1;c->actual[id]=v;return 1;
}
'''
needle='static int compare_node(Compare*c,size_t id,PyObject*v,int depth){';assert original.count(needle)==1
candidate=original.replace(needle,helper+'\n'+needle)
for old,new in [('compare_node(c,n->edges[edge++],a,depth+1)','compare_edge(c,n->edges[edge++],a,depth+1)'),('compare_node(c,n->edges[edge++],b,depth+1)','compare_edge(c,n->edges[edge++],b,depth+1)'),('compare_node(c,n->edges[edge++],x,depth+1)','compare_edge(c,n->edges[edge++],x,depth+1)')]:
 assert candidate.count(old)==1;candidate=candidate.replace(old,new)
for name,source in [('baseline',original),('candidate',candidate)]:
 folder=out/name;folder.mkdir(exist_ok=True);src=folder/'_cold_graph_structure.c';src.write_text(source);sha=hashlib.sha256(src.read_bytes()).hexdigest();binary=folder/('_cold_graph_structure'+sysconfig.get_config_var('EXT_SUFFIX'))
 command=['/usr/bin/cc','-shared','-fPIC','-O3','-DNDEBUG','-Wall','-Wextra','-DSIM2ACT_GRAPH_SOURCE_SHA="'+sha+'"','-I'+sysconfig.get_path('include'),str(src),'-o',str(binary)]
 p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(folder/'build.log').write_text(p.stdout);assert p.returncode==0,p.stdout
 (folder/'build.json').write_text(json.dumps(dict(source_sha256=sha,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),command=command,returncode=p.returncode),indent=2)+'\n')
s=(Path('/workspace/scratch/check-graph-dispatch-candidate-20261030.py').read_text().replace('graph-dispatch-candidate-20261030','graph-edge-candidate-20261030'))
(out/'check.py').write_text(s)
print('Edge-inline prototype built with the original recursive walker retained')
