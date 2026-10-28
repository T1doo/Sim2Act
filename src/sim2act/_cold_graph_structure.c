
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <string.h>
/* Independent bounded structure. Original mutable references are identity-only;
 * edges and scalar bits are owned. No content/permission verdict survives calls. */
static PyObject *unsupported, *unsupported_error;
typedef struct {PyObject *key;size_t ordinal;} Entry;
typedef struct {size_t slots,count;Entry*entries;} Map;
typedef struct {PyObject*row,*limits,*quoted,*readrow,*readlimits,*marker,*reduce;} Encoder;
typedef struct {PyObject*original;unsigned char kind;uint64_t bits;size_t count,*edges;int active;} Node;
typedef struct {Node*nodes;size_t count,capacity,work,bytes;Map map;PyObject*args,*scope;Encoder types;} Tree;
static size_t slot(PyObject*v,size_t slots){uintptr_t x=(uintptr_t)v;x>>=3;x^=x>>23;x*=UINT64_C(0x2127599bf4325c37);x^=x>>47;return (size_t)x&(slots-1);}
static Entry*find(Map*m,PyObject*v){if(!m->slots)return NULL;size_t j=slot(v,m->slots);while(m->entries[j].key){if(m->entries[j].key==v)return m->entries+j;j=(j+1)&(m->slots-1);}return NULL;}
static int insert(Map*m,PyObject*v,size_t ordinal){
 if(!m->slots||m->count>=m->slots/2){size_t n=m->slots?m->slots*2:1024;Entry*next=PyMem_Calloc(n,sizeof(Entry));if(!next){PyErr_NoMemory();return -1;}
 for(size_t i=0;i<m->slots;i++)if(m->entries[i].key){size_t j=slot(m->entries[i].key,n);while(next[j].key)j=(j+1)&(n-1);next[j]=m->entries[i];}PyMem_Free(m->entries);m->entries=next;m->slots=n;}
 size_t j=slot(v,m->slots);while(m->entries[j].key)j=(j+1)&(m->slots-1);m->entries[j]=(Entry){v,ordinal};m->count++;return 0;
}
static int kind(Encoder*s,PyObject*v){return v==s->marker?'p':v==Py_None?'n':v==Py_True?'t':v==Py_False?'f':PyLong_CheckExact(v)?'i':PyFloat_CheckExact(v)?'d':PyUnicode_CheckExact(v)?'s':PyBytes_CheckExact(v)?'b':PyDict_CheckExact(v)?'m':PyList_CheckExact(v)?'l':PyTuple_CheckExact(v)?'q':(PyObject*)Py_TYPE(v)==s->row?'r':(PyObject*)Py_TYPE(v)==s->limits?'c':(PyObject*)Py_TYPE(v)==s->quoted?'u':0;}
static int memoized(int k){return k!='n'&&k!='t'&&k!='f'&&k!='i'&&k!='d';}
static int scalar_bits(PyObject*v,int k,uint64_t*bits){
 if(k=='d'){double d=PyFloat_AS_DOUBLE(v);memcpy(bits,&d,8);return 0;}
 int overflow=0;long long n=PyLong_AsLongLongAndOverflow(v,&overflow);if(PyErr_Occurred())return -1;if(overflow){PyErr_SetString(unsupported_error,"Cold graph integer range");return -1;}*bits=(uint64_t)n;return 0;
}
static int capture_node(Tree*t,PyObject*v,int depth,size_t*out){
 if((t->work++&1023)==0&&PyErr_CheckSignals()<0)return -1;
 if(t->work>1000000||depth>64){PyErr_SetString(unsupported_error,"Cold graph capture bounds");return -1;}
 int k=kind(&t->types,v);if(!k){PyErr_SetString(unsupported_error,"Cold graph node type");return -1;}
 if(memoized(k)){Entry*e=find(&t->map,v);if(e){if(t->nodes[e->ordinal].active){PyErr_SetString(unsupported_error,"Cyclic Cold graph");return -1;}*out=e->ordinal;return 0;}}
 if(t->count>=100000){PyErr_SetString(unsupported_error,"Cold graph node bound");return -1;}
 if(t->count==t->capacity){size_t n=t->capacity?t->capacity*2:1024;Node*next=PyMem_Realloc(t->nodes,n*sizeof(Node));if(!next){PyErr_NoMemory();return -1;}t->nodes=next;t->capacity=n;}
 size_t id=t->count++;*out=id;t->nodes[id]=(Node){.original=Py_NewRef(v),.kind=k,.active=memoized(k)};
 if(memoized(k)&&insert(&t->map,v,id)<0)return -1;
 if(k=='i'||k=='d')return scalar_bits(v,k,&t->nodes[id].bits);
 if(k=='n'||k=='t'||k=='f')return 0;
 if(k=='s'||k=='b'){t->nodes[id].active=0;t->bytes+=k=='b'?PyBytes_GET_SIZE(v):PyUnicode_GET_LENGTH(v)*4;if(t->bytes>16*1024*1024){PyErr_SetString(unsupported_error,"Cold graph text bound");return -1;}return 0;}
 PyObject*keys=NULL,*data=NULL,*index=NULL,*payload=NULL;size_t count=0,*edges=NULL,edge=0;int result=-1;
 if(k=='m')count=2*(size_t)PyDict_Size(v);
 else if(k=='l'||k=='q')count=(size_t)(k=='l'?PyList_GET_SIZE(v):PyTuple_GET_SIZE(v));
 else if(k=='p'){
  PyObject*module=PyObject_GetAttrString(v,"__module__"),*name=PyObject_GetAttrString(v,"__qualname__");
  if(module&&name)payload=PyTuple_Pack(2,module,name);Py_XDECREF(module);Py_XDECREF(name);if(!payload)goto done;count=2;
 }else{
  payload=PyObject_CallFunctionObjArgs(t->types.reduce,Py_None,v,NULL);if(!payload)goto done;
  if(!PyTuple_CheckExact(payload)||PyTuple_GET_SIZE(payload)!=2||PyTuple_GET_ITEM(payload,0)!=t->types.marker||!PyTuple_CheckExact(PyTuple_GET_ITEM(payload,1))){PyErr_SetString(unsupported_error,"Cold graph reducer result");goto done;}count=2;
 }
 if(count>1000000-t->work){PyErr_SetString(unsupported_error,"Cold graph edge bound");goto done;}
 edges=PyMem_Calloc(count?count:1,sizeof(size_t));if(!edges){PyErr_NoMemory();goto done;}
 if(k=='m'){
  Py_ssize_t pos=0;PyObject*a,*b;while(PyDict_Next(v,&pos,&a,&b)){
   if(edge+1>=count||(size_t)PyDict_Size(v)*2!=count){PyErr_SetString(unsupported_error,"Cold graph dictionary changed");goto done;}
   Py_INCREF(a);Py_INCREF(b);int ok=capture_node(t,a,depth+1,edges+edge++);if(ok==0)ok=capture_node(t,b,depth+1,edges+edge++);Py_DECREF(a);Py_DECREF(b);if(ok<0)goto done;
  }
 }else{
  PyObject*seq=(k=='c'||k=='r'||k=='u'||k=='p')?payload:v;
  for(size_t i=0;i<count;i++){
   if(k=='l'&&(size_t)PyList_GET_SIZE(seq)!=count){PyErr_SetString(unsupported_error,"Cold graph list changed");goto done;}
   PyObject*x=k=='l'?PyList_GET_ITEM(seq,i):PyTuple_GET_ITEM(seq,i);Py_INCREF(x);int ok=capture_node(t,x,depth+1,edges+edge++);Py_DECREF(x);if(ok<0)goto done;
  }
 }
 if(edge!=count){PyErr_SetString(PyExc_RuntimeError,"Cold graph capture mutation");goto done;}
 t->nodes[id].count=count;t->nodes[id].edges=edges;t->nodes[id].active=0;edges=NULL;result=0;
 done:PyMem_Free(edges);Py_XDECREF(keys);Py_XDECREF(data);Py_XDECREF(index);Py_XDECREF(payload);return result;
}
static void free_tree(Tree*t){if(!t)return;PyObject*error=PyErr_GetRaisedException();for(size_t i=0;i<t->count;i++){Py_XDECREF(t->nodes[i].original);PyMem_Free(t->nodes[i].edges);}PyMem_Free(t->nodes);PyMem_Free(t->map.entries);Py_XDECREF(t->scope);Py_XDECREF(t->args);Py_XDECREF(t->types.marker);Py_XDECREF(t->types.reduce);PyMem_Free(t);if(error)PyErr_SetRaisedException(error);}
static void close_tree(PyObject*cap){Tree*t=PyCapsule_GetPointer(cap,"sim2act.cold-graph-structure.v1");if(!t){PyErr_Clear();return;}free_tree(t);}
static PyObject*snapshot(PyObject*self,PyObject*args){
 (void)self;Tree*t=PyMem_Calloc(1,sizeof(Tree));if(!t)return PyErr_NoMemory();PyObject*v;
 if(!PyArg_ParseTuple(args,"OOOOOOO",&v,&t->types.row,&t->types.limits,&t->types.quoted,&t->types.readrow,&t->types.readlimits,&t->scope)){free_tree(t);return NULL;}
 if(!PyTuple_CheckExact(t->scope)||PyTuple_GET_SIZE(t->scope)!=5){t->scope=NULL;free_tree(t);return Py_NewRef(unsupported);}Py_INCREF(t->scope);
 PyFrameObject*frame=PyThreadState_GetFrame(PyThreadState_Get());int frames=0;while(frame){PyFrameObject*back=PyFrame_GetBack(frame);Py_DECREF(frame);frame=back;frames++;}
 if(Py_GetRecursionLimit()-frames<256){free_tree(t);return Py_NewRef(unsupported);}
 t->args=PyTuple_GetSlice(args,1,6);if(!t->args){free_tree(t);return NULL;}
 PyObject*g=PyFunction_GetGlobals(t->types.readrow);if(!g){free_tree(t);PyErr_SetString(unsupported_error,"Cold graph original function");return NULL;}
 PyObject*cls=PyDict_GetItemString(g,"_ColdGraphPickler");t->types.marker=Py_XNewRef(PyDict_GetItemString(g,"_cold_graph_pickle_marker"));
 if(cls)t->types.reduce=PyObject_GetAttrString(cls,"reducer_override");
 if(!t->types.marker||!t->types.reduce){free_tree(t);if(!PyErr_Occurred())PyErr_SetString(unsupported_error,"Cold graph original reducer");return NULL;}size_t root;
 if(capture_node(t,v,0,&root)<0){free_tree(t);if(PyErr_ExceptionMatches(unsupported_error)){PyErr_Clear();return Py_NewRef(unsupported);}return NULL;}
 PyObject*cap=PyCapsule_New(t,"sim2act.cold-graph-structure.v1",close_tree);if(!cap)free_tree(t);return cap;
}
typedef struct {Tree*t;PyObject**actual;size_t*assigned;Map changed;size_t work;} Compare;
static int compare_node(Compare*c,size_t id,PyObject*v,int depth){
 if((c->work++&1023)==0&&PyErr_CheckSignals()<0)return -1;
 if(c->work>1000000||depth>64){PyErr_SetString(unsupported_error,"Cold graph compare bounds");return -1;}
 Node*n=c->t->nodes+id;int k=kind(&c->t->types,v);if(k!=n->kind)return 0;
 if(k=='i'||k=='d'){uint64_t b;if(scalar_bits(v,k,&b)<0)return -1;return b==n->bits;}
 if(k=='n'||k=='t'||k=='f')return 1;
 if(c->actual[id])return c->actual[id]==v;
 Entry*old=find(&c->t->map,v);
 if(old){size_t*assigned=c->assigned+old->ordinal;if(*assigned&&*assigned!=id+1)return 0;*assigned=id+1;}
 else{Entry*seen=find(&c->changed,v);if(seen&&seen->ordinal!=id)return 0;if(!seen&&insert(&c->changed,v,id)<0)return -1;}
 c->actual[id]=Py_NewRef(v);
 if(k=='s'){if(v==n->original)return 1;int same=PyUnicode_Compare(v,n->original);if(same==-1&&PyErr_Occurred())return -1;return same==0;}
 if(k=='b')return v==n->original||(PyBytes_GET_SIZE(v)==PyBytes_GET_SIZE(n->original)&&!memcmp(PyBytes_AS_STRING(v),PyBytes_AS_STRING(n->original),PyBytes_GET_SIZE(v)));
 size_t edge=0;int result=1;PyObject*keys=NULL,*data=NULL,*index=NULL,*payload=NULL;
 if(k=='m'){
  if((size_t)PyDict_Size(v)*2!=n->count)return 0;Py_ssize_t pos=0;PyObject*a,*b;
  while(PyDict_Next(v,&pos,&a,&b)){if(edge+1>=n->count||(size_t)PyDict_Size(v)*2!=n->count){result=0;break;}Py_INCREF(a);Py_INCREF(b);result=compare_node(c,n->edges[edge++],a,depth+1);if(result>0)result=compare_node(c,n->edges[edge++],b,depth+1);Py_DECREF(a);Py_DECREF(b);if(result<=0)break;}
 }else{
  PyObject*seq=v;
  if(k=='p'){
   PyObject*module=PyObject_GetAttrString(v,"__module__"),*name=PyObject_GetAttrString(v,"__qualname__");if(module&&name)payload=PyTuple_Pack(2,module,name);Py_XDECREF(module);Py_XDECREF(name);if(!payload){result=-1;goto done;}seq=payload;
  }else if(k=='c'||k=='r'||k=='u'){
   payload=PyObject_CallFunctionObjArgs(c->t->types.reduce,Py_None,v,NULL);if(!payload){result=-1;goto done;}
   if(!PyTuple_CheckExact(payload)||PyTuple_GET_SIZE(payload)!=2||PyTuple_GET_ITEM(payload,0)!=c->t->types.marker||!PyTuple_CheckExact(PyTuple_GET_ITEM(payload,1))){PyErr_SetString(unsupported_error,"Cold graph reducer result");result=-1;goto done;}seq=payload;
  }
  size_t count=(size_t)(k=='l'?PyList_GET_SIZE(seq):PyTuple_GET_SIZE(seq));if(count!=n->count){result=0;goto done;}
  for(size_t i=0;i<count;i++){if(k=='l'&&(size_t)PyList_GET_SIZE(seq)!=count){result=0;break;}PyObject*x=k=='l'?PyList_GET_ITEM(seq,i):PyTuple_GET_ITEM(seq,i);Py_INCREF(x);result=compare_node(c,n->edges[edge++],x,depth+1);Py_DECREF(x);if(result<=0)break;}
 }
 done:Py_XDECREF(keys);Py_XDECREF(data);Py_XDECREF(index);Py_XDECREF(payload);return result>0?edge==n->count:result;
}
static PyObject*matches_fast(PyObject*self,PyObject*args){
 (void)self;PyObject*cap,*v,*scope;if(!PyArg_ParseTuple(args,"OOO",&cap,&v,&scope))return NULL;Tree*t=PyCapsule_GetPointer(cap,"sim2act.cold-graph-structure.v1");if(!t)return NULL;
 if(!PyTuple_CheckExact(scope)||PyTuple_GET_SIZE(scope)!=5)return Py_NewRef(unsupported);
 for(int i=0;i<5;i++)if(PyTuple_GET_ITEM(scope,i)!=PyTuple_GET_ITEM(t->scope,i))return Py_NewRef(unsupported);
 PyFrameObject*frame=PyThreadState_GetFrame(PyThreadState_Get());int frames=0;while(frame){PyFrameObject*back=PyFrame_GetBack(frame);Py_DECREF(frame);frame=back;frames++;}
 if(Py_GetRecursionLimit()-frames<256)return Py_NewRef(unsupported);
 Compare c={.t=t};c.actual=PyMem_Calloc(t->count?t->count:1,sizeof(PyObject*));c.assigned=PyMem_Calloc(t->count?t->count:1,sizeof(size_t));if(!c.actual||!c.assigned){PyMem_Free(c.actual);PyMem_Free(c.assigned);return PyErr_NoMemory();}
 int result=compare_node(&c,0,v,0);PyObject*error=PyErr_GetRaisedException();for(size_t i=0;i<t->count;i++)Py_XDECREF(c.actual[i]);PyMem_Free(c.actual);PyMem_Free(c.assigned);PyMem_Free(c.changed.entries);if(error)PyErr_SetRaisedException(error);
 if(result<0){if(PyErr_ExceptionMatches(unsupported_error)){PyErr_Clear();return Py_NewRef(unsupported);}return NULL;}return PyBool_FromLong(result);
}
static PyMethodDef methods[]={{"snapshot",snapshot,METH_VARARGS,"Bounded independent complete structure for one qualified scope."},{"matches_fast",matches_fast,METH_VARARGS,"Fresh complete structure and alias comparison in the same scope."},{NULL,NULL,0,NULL}};
static struct PyModuleDef module={PyModuleDef_HEAD_INIT,"_cold_graph_structure",NULL,-1,methods};
PyMODINIT_FUNC PyInit__cold_graph_structure(void){
 PyObject*m=PyModule_Create(&module);if(!m)return NULL;
 unsupported=PyCapsule_New((void*)&module,"sim2act.cold-graph-structure.unsupported",NULL);
 unsupported_error=PyErr_NewException("sim2act._cold_graph_structure._Unsupported",NULL,NULL);
 if(!unsupported||!unsupported_error||PyModule_AddObjectRef(m,"UNSUPPORTED",unsupported)<0||PyModule_AddStringConstant(m,"SOURCE_SHA256",SIM2ACT_GRAPH_SOURCE_SHA)<0){Py_XDECREF(unsupported);Py_XDECREF(unsupported_error);Py_DECREF(m);return NULL;}return m;
}
