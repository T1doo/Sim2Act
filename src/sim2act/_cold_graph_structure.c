#include <stddef.h>

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <string.h>
/* Independent bounded structure. Original mutable references are identity-only;
 * edges and scalar bits are owned. No content/permission verdict survives calls. */
static PyObject *unsupported, *unsupported_error;
typedef struct {PyObject *key;size_t ordinal;} Entry;
typedef struct {size_t slots,count;Entry*entries;} Map;
typedef struct {PyObject*row,*limits,*quoted,*readrow,*readlimits,*marker,*reduce,*view,*owned;} Encoder;
typedef struct {PyObject*original;unsigned char kind;uint64_t bits;size_t count,*edges;int active;} Node;
typedef struct {Node*nodes;size_t count,capacity,work,bytes;Map map;PyObject*args,*scope;Encoder types;Map immutable;PyObject*immutable_held;size_t immutable_work;} Tree;
static size_t slot(PyObject*v,size_t slots){uintptr_t x=(uintptr_t)v;x>>=3;x^=x>>23;x*=UINT64_C(0x2127599bf4325c37);x^=x>>47;return (size_t)x&(slots-1);}
static Entry*find(Map*m,PyObject*v){if(!m->slots)return NULL;size_t j=slot(v,m->slots);while(m->entries[j].key){if(m->entries[j].key==v)return m->entries+j;j=(j+1)&(m->slots-1);}return NULL;}
static int insert(Map*m,PyObject*v,size_t ordinal){
 if(!m->slots||m->count>=m->slots/2){size_t n=m->slots?m->slots*2:1024;Entry*next=PyMem_Calloc(n,sizeof(Entry));if(!next){PyErr_NoMemory();return -1;}
 for(size_t i=0;i<m->slots;i++)if(m->entries[i].key){size_t j=slot(m->entries[i].key,n);while(next[j].key)j=(j+1)&(n-1);next[j]=m->entries[i];}PyMem_Free(m->entries);m->entries=next;m->slots=n;}
 size_t j=slot(v,m->slots);while(m->entries[j].key)j=(j+1)&(m->slots-1);m->entries[j]=(Entry){v,ordinal};m->count++;return 0;
}
static int kind(Encoder*s,PyObject*v){return v==s->marker?'p':v==Py_None?'n':v==Py_True?'t':v==Py_False?'f':PyLong_CheckExact(v)?'i':PyFloat_CheckExact(v)?'d':PyUnicode_CheckExact(v)?'s':PyBytes_CheckExact(v)?'b':PyDict_CheckExact(v)?'m':PyList_CheckExact(v)?'l':PyTuple_CheckExact(v)?'q':(PyObject*)Py_TYPE(v)==s->row?'r':(PyObject*)Py_TYPE(v)==s->limits?'c':(PyObject*)Py_TYPE(v)==s->quoted?'u':s->view&&(PyObject*)Py_TYPE(v)==s->view?'o':s->owned&&(PyObject*)Py_TYPE(v)==s->owned?'w':0;}
static int memoized(int k){return k!='n'&&k!='t'&&k!='f'&&k!='i'&&k!='d';}
static int scalar_bits(PyObject*v,int k,uint64_t*bits){
 if(k=='d'){double d=PyFloat_AS_DOUBLE(v);memcpy(bits,&d,8);return 0;}
 int overflow=0;long long n=PyLong_AsLongLongAndOverflow(v,&overflow);if(PyErr_Occurred())return -1;if(overflow){PyErr_SetString(unsupported_error,"Cold graph integer range");return -1;}*bits=(uint64_t)n;return 0;
}
/* Complete immutable identity inventory, shared across ALL owned roots.
 * Held references make pointer membership stable. These are not comparison
 * nodes: no array zeroing or immutable-content walk is needed on each match. */
static int inventory(Tree*t,PyObject*v,int depth){
 if(++t->immutable_work+t->work>1000000||depth>64){PyErr_SetString(unsupported_error,"Owned identity inventory bound");return -1;}
 if(!PyTuple_CheckExact(v)&&!PyUnicode_CheckExact(v)&&!PyBytes_CheckExact(v)){
  PyErr_SetString(unsupported_error,"Owned pin is not deeply immutable");return -1;
 }
 if(find(&t->immutable,v))return 0;
 if(t->immutable.count+t->count>=100000){PyErr_SetString(unsupported_error,"Owned inventory node bound");return -1;}
 if(!t->immutable_held){t->immutable_held=PyList_New(0);if(!t->immutable_held)return -1;}
 if(PyList_Append(t->immutable_held,v)<0||insert(&t->immutable,v,t->immutable.count)<0)return -1;
 if(PyTuple_CheckExact(v)){
  for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(v);i++)if(inventory(t,PyTuple_GET_ITEM(v,i),depth+1)<0)return -1;
 }else{
  size_t size=PyBytes_CheckExact(v)?(size_t)PyBytes_GET_SIZE(v):(size_t)PyUnicode_GET_LENGTH(v)*4;
  if(size>16*1024*1024-t->bytes){PyErr_SetString(unsupported_error,"Owned inventory byte bound");return -1;}t->bytes+=size;
 }
 return 0;
}

static int capture_node(Tree*t,PyObject*v,int depth,size_t*out){
 if((t->work++&1023)==0&&PyErr_CheckSignals()<0)return -1;
 if(t->work+t->immutable_work>1000000||depth>64){PyErr_SetString(unsupported_error,"Cold graph capture bounds");return -1;}
 int k=kind(&t->types,v);if(!k){PyErr_SetString(unsupported_error,"Cold graph node type");return -1;}
 if(memoized(k)){Entry*e=find(&t->map,v);if(e){if(t->nodes[e->ordinal].active){PyErr_SetString(unsupported_error,"Cyclic Cold graph");return -1;}*out=e->ordinal;return 0;}}
 if(t->count+t->immutable.count>=100000){PyErr_SetString(unsupported_error,"Cold graph node bound");return -1;}
 if(t->count==t->capacity){size_t n=t->capacity?t->capacity*2:1024;Node*next=PyMem_Realloc(t->nodes,n*sizeof(Node));if(!next){PyErr_NoMemory();return -1;}t->nodes=next;t->capacity=n;}
 size_t id=t->count++;*out=id;t->nodes[id]=(Node){.original=Py_NewRef(v),.kind=k,.active=memoized(k)};
 if(memoized(k)&&insert(&t->map,v,id)<0)return -1;
 if(k=='w'){
  PyObject*reduced=PyObject_CallFunctionObjArgs(t->types.reduce,Py_None,v,NULL);
  if(!reduced)return -1;
  int ok=PyTuple_CheckExact(reduced)&&PyTuple_GET_SIZE(reduced)==2
   &&PyTuple_GET_ITEM(reduced,0)==t->types.marker&&PyTuple_CheckExact(PyTuple_GET_ITEM(reduced,1));
  if(ok)ok=inventory(t,PyTuple_GET_ITEM(reduced,1),0)==0;
  Py_DECREF(reduced);if(!ok){if(!PyErr_Occurred())PyErr_SetString(unsupported_error,"Owned complete reducer required");return -1;}
  t->nodes[id].active=0;return 0;
 }
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
  PyObject*seq=(k=='c'||k=='r'||k=='u'||k=='o'||k=='p')?payload:v;
  for(size_t i=0;i<count;i++){
   if(k=='l'&&(size_t)PyList_GET_SIZE(seq)!=count){PyErr_SetString(unsupported_error,"Cold graph list changed");goto done;}
   PyObject*x=k=='l'?PyList_GET_ITEM(seq,i):PyTuple_GET_ITEM(seq,i);Py_INCREF(x);int ok=capture_node(t,x,depth+1,edges+edge++);Py_DECREF(x);if(ok<0)goto done;
  }
 }
 if(edge!=count){PyErr_SetString(PyExc_RuntimeError,"Cold graph capture mutation");goto done;}
 t->nodes[id].count=count;t->nodes[id].edges=edges;t->nodes[id].active=0;edges=NULL;result=0;
 done:PyMem_Free(edges);Py_XDECREF(keys);Py_XDECREF(data);Py_XDECREF(index);Py_XDECREF(payload);return result;
}
static void free_tree(Tree*t){if(!t)return;PyObject*error=PyErr_GetRaisedException();for(size_t i=0;i<t->count;i++){Py_XDECREF(t->nodes[i].original);PyMem_Free(t->nodes[i].edges);}PyMem_Free(t->nodes);PyMem_Free(t->map.entries);PyMem_Free(t->immutable.entries);Py_XDECREF(t->immutable_held);Py_XDECREF(t->scope);Py_XDECREF(t->args);Py_XDECREF(t->types.marker);Py_XDECREF(t->types.reduce);PyMem_Free(t);if(error)PyErr_SetRaisedException(error);}
static void close_tree(PyObject*cap){Tree*t=PyCapsule_GetPointer(cap,"sim2act.cold-graph-structure.v1");if(!t){PyErr_Clear();return;}free_tree(t);}
static PyObject*snapshot(PyObject*self,PyObject*args){
 (void)self;Tree*t=PyMem_Calloc(1,sizeof(Tree));if(!t)return PyErr_NoMemory();PyObject*v;
 if(!PyArg_ParseTuple(args,"OOOOOOO|OO",&v,&t->types.row,&t->types.limits,&t->types.quoted,&t->types.readrow,&t->types.readlimits,&t->scope,&t->types.view,&t->types.owned)){free_tree(t);return NULL;}
 if(!PyTuple_CheckExact(t->scope)||PyTuple_GET_SIZE(t->scope)!=5){t->scope=NULL;free_tree(t);return Py_NewRef(unsupported);}Py_INCREF(t->scope);
 PyFrameObject*frame=PyThreadState_GetFrame(PyThreadState_Get());int frames=0;while(frame){PyFrameObject*back=PyFrame_GetBack(frame);Py_DECREF(frame);frame=back;frames++;}
 if(Py_GetRecursionLimit()-frames<256){free_tree(t);return Py_NewRef(unsupported);}
 t->args=PyTuple_GetSlice(args,1,PyTuple_GET_SIZE(args));if(!t->args){free_tree(t);return NULL;}
 PyObject*g=PyFunction_GetGlobals(t->types.readrow);if(!g){free_tree(t);PyErr_SetString(unsupported_error,"Cold graph original function");return NULL;}
 PyObject*cls=PyDict_GetItemString(g,"_ColdGraphPickler");t->types.marker=Py_XNewRef(PyDict_GetItemString(g,"_cold_graph_pickle_marker"));
 if(cls)t->types.reduce=PyObject_GetAttrString(cls,"reducer_override");
 if(!t->types.marker||!t->types.reduce){free_tree(t);if(!PyErr_Occurred())PyErr_SetString(unsupported_error,"Cold graph original reducer");return NULL;}size_t root;
 if(capture_node(t,v,0,&root)<0){free_tree(t);if(PyErr_ExceptionMatches(unsupported_error)){PyErr_Clear();return Py_NewRef(unsupported);}return NULL;}
 PyObject*cap=PyCapsule_New(t,"sim2act.cold-graph-structure.v1",close_tree);if(!cap)free_tree(t);return cap;
}
typedef struct {Tree*t;PyObject**actual;size_t*assigned;Map changed;size_t work;} Compare;

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

static int compare_node(Compare*c,size_t id,PyObject*v,int depth){
 if((c->work++&1023)==0&&PyErr_CheckSignals()<0)return -1;
 if(c->work>1000000||depth>64){PyErr_SetString(unsupported_error,"Cold graph compare bounds");return -1;}
 Node*n=c->t->nodes+id;int k=kind(&c->t->types,v);if(k!=n->kind)return 0;
 if(v!=n->original&&memoized(k)){
  Entry*before=find(&c->t->immutable,n->original),*now=find(&c->t->immutable,v);
  if((before||now)&&(!before||!now||before->ordinal!=now->ordinal))return 0;
 }
 if(k=='w'){
  if(v!=n->original)return 0;
  if(c->actual[id])return c->actual[id]==v;
  size_t*assigned=c->assigned+id;if(*assigned&&*assigned!=id+1)return 0;
  *assigned=id+1;c->actual[id]=v;return 1;
 }

 if(k=='i'||k=='d'){if(v==n->original)return 1;uint64_t b;if(scalar_bits(v,k,&b)<0)return -1;return b==n->bits;}
 if(k=='n'||k=='t'||k=='f')return 1;
 if(c->actual[id])return c->actual[id]==v;
 if(v==n->original){
  /* The captured tree already owns this exact reference and its ordinal.
   * Preserve reverse-alias assignment, but avoid a redundant pointer lookup
   * and temporary reference. Mutable nodes STILL traverse every child below. */
  size_t*assigned=c->assigned+id;if(*assigned&&*assigned!=id+1)return 0;
  *assigned=id+1;c->actual[id]=v;
 }else{
  Entry*old=find(&c->t->map,v);
  if(old){size_t*assigned=c->assigned+old->ordinal;if(*assigned&&*assigned!=id+1)return 0;*assigned=id+1;}
  else{Entry*seen=find(&c->changed,v);if(seen&&seen->ordinal!=id)return 0;if(!seen&&insert(&c->changed,v,id)<0)return -1;}
  c->actual[id]=Py_NewRef(v);
 }
 if(k=='s'){if(v==n->original)return 1;int same=PyUnicode_Compare(v,n->original);if(same==-1&&PyErr_Occurred())return -1;return same==0;}
 if(k=='b')return v==n->original||(PyBytes_GET_SIZE(v)==PyBytes_GET_SIZE(n->original)&&!memcmp(PyBytes_AS_STRING(v),PyBytes_AS_STRING(n->original),PyBytes_GET_SIZE(v)));
 size_t edge=0;int result=1;PyObject*keys=NULL,*data=NULL,*index=NULL,*payload=NULL;
 if(k=='m'){
  if((size_t)PyDict_Size(v)*2!=n->count)return 0;Py_ssize_t pos=0;PyObject*a,*b;
  while(PyDict_Next(v,&pos,&a,&b)){if(edge+1>=n->count||(size_t)PyDict_Size(v)*2!=n->count){result=0;break;}Py_INCREF(a);Py_INCREF(b);result=compare_edge(c,n->edges[edge++],a,depth+1);if(result>0)result=compare_edge(c,n->edges[edge++],b,depth+1);Py_DECREF(a);Py_DECREF(b);if(result<=0)break;}
 }else{
  PyObject*seq=v;
  if(k=='p'){
   PyObject*module=PyObject_GetAttrString(v,"__module__"),*name=PyObject_GetAttrString(v,"__qualname__");if(module&&name)payload=PyTuple_Pack(2,module,name);Py_XDECREF(module);Py_XDECREF(name);if(!payload){result=-1;goto done;}seq=payload;
  }else if(k=='c'||k=='r'||k=='u'||k=='o'){
   payload=PyObject_CallFunctionObjArgs(c->t->types.reduce,Py_None,v,NULL);if(!payload){result=-1;goto done;}
   if(!PyTuple_CheckExact(payload)||PyTuple_GET_SIZE(payload)!=2||PyTuple_GET_ITEM(payload,0)!=c->t->types.marker||!PyTuple_CheckExact(PyTuple_GET_ITEM(payload,1))){PyErr_SetString(unsupported_error,"Cold graph reducer result");result=-1;goto done;}seq=payload;
  }
  size_t count=(size_t)(k=='l'?PyList_GET_SIZE(seq):PyTuple_GET_SIZE(seq));if(count!=n->count){result=0;goto done;}
  for(size_t i=0;i<count;i++){if(k=='l'&&(size_t)PyList_GET_SIZE(seq)!=count){result=0;break;}PyObject*x=k=='l'?PyList_GET_ITEM(seq,i):PyTuple_GET_ITEM(seq,i);Py_INCREF(x);result=compare_edge(c,n->edges[edge++],x,depth+1);Py_DECREF(x);if(result<=0)break;}
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
 int result=compare_node(&c,0,v,0);PyObject*error=PyErr_GetRaisedException();for(size_t i=0;i<t->count;i++)if(c.actual[i]!=t->nodes[i].original)Py_XDECREF(c.actual[i]);PyMem_Free(c.actual);PyMem_Free(c.assigned);PyMem_Free(c.changed.entries);if(error)PyErr_SetRaisedException(error);
 if(result<0){if(PyErr_ExceptionMatches(unsupported_error)){PyErr_Clear();return Py_NewRef(unsupported);}return NULL;}return PyBool_FromLong(result);
}
static int same_namespace(PyTypeObject *kind, PyObject *items, size_t *work) {
    /* 3.12 static builtin namespaces are interpreter-local. Public GetDict
     * returns a NEW reference; direct tp_dict is only valid for heap types. */
    PyObject *dictionary = PyType_GetDict(kind);
    if (!dictionary) return PyErr_Occurred() ? -1 : 0;
    int result = 0;
    if (!PyTuple_CheckExact(items) || !PyDict_CheckExact(dictionary)
            || PyDict_Size(dictionary) != PyTuple_GET_SIZE(items)) goto done;
    Py_ssize_t position = 0, ordinal = 0;
    PyObject *key, *value;
    while (PyDict_Next(dictionary, &position, &key, &value)) {
        if (++*work > 100000) goto done;
        if (ordinal >= PyTuple_GET_SIZE(items)
                || PyDict_Size(dictionary) != PyTuple_GET_SIZE(items)) goto done;
        PyObject *pair = PyTuple_GET_ITEM(items, ordinal++);
        if (!PyTuple_CheckExact(pair) || PyTuple_GET_SIZE(pair) != 2
                || PyTuple_GET_ITEM(pair, 0) != key || PyTuple_GET_ITEM(pair, 1) != value) goto done;
    }
    result = 1;
done:
    Py_DECREF(dictionary);
    return result;
}

static PyObject *same_classes(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *metas, *classes;
    size_t work = 0;
    if (!PyArg_ParseTuple(args, "OO", &metas, &classes)) return NULL;
    /* Dispatch pending signals before borrowing namespace entries. The bounded
     * comparison itself invokes no Python callbacks and keeps the GIL. */
    if (PyErr_CheckSignals() < 0) return NULL;
    if (!PyTuple_CheckExact(metas) || !PyTuple_CheckExact(classes)
            || PyTuple_GET_SIZE(metas) > 256 || PyTuple_GET_SIZE(classes) > 256) Py_RETURN_FALSE;
    for (int group = 0; group < 2; group++) {
        PyObject *entries = group ? classes : metas;
        for (Py_ssize_t i = 0; i < PyTuple_GET_SIZE(entries); i++) {
            PyObject *entry = PyTuple_GET_ITEM(entries, i);
            if (!PyTuple_CheckExact(entry) || PyTuple_GET_SIZE(entry) != (group ? 4 : 3)) Py_RETURN_FALSE;
            PyObject *kind = PyTuple_GET_ITEM(entry, 0);
            PyObject *meta = group ? PyTuple_GET_ITEM(entry, 1) : (PyObject *)&PyType_Type;
            PyObject *mro = PyTuple_GET_ITEM(entry, group ? 2 : 1);
            if (!PyType_Check(kind) || (PyObject *)Py_TYPE(kind) != meta
                    || ((PyTypeObject *)kind)->tp_mro != mro) Py_RETURN_FALSE;
            int same = same_namespace((PyTypeObject *)kind,
                PyTuple_GET_ITEM(entry, group ? 3 : 2), &work);
            if (same < 0) return NULL;
            if (!same) Py_RETURN_FALSE;
        }
    }
    Py_RETURN_TRUE;
}


/* A publication owns the EXACT original V2 bytes, not a hash-only verdict or
 * a tree reconstructed from later mutable inputs. Versions never change.
 * The journal owns only its current version; retained old versions are data,
 * and cannot become current again. No permission is stored here. */
typedef struct {PyObject_HEAD PyObject *raw,*key,*scope,*sequence,*journal;} PinVersion;
typedef struct {PyObject_HEAD PyObject *scope,*version,*frontier,*cleanup;size_t sequence;int closed;PyObject*weakrefs;} PinJournal;
static PyTypeObject pin_version_type,pin_journal_type;
static PyObject *pin_modules,*pin_keys;
static PyObject *pin_create_code,*pin_publish_code,*pin_constructors,*pin_publishers,*pin_issued,*pin_graph_class,*pin_frontier_class,*pin_source_verifier;
static int pin_version_traverse(PinVersion*v,visitproc visit,void*arg){Py_VISIT(v->raw);Py_VISIT(v->key);Py_VISIT(v->scope);Py_VISIT(v->sequence);Py_VISIT(v->journal);return 0;}
static int pin_version_clear(PinVersion*v){Py_CLEAR(v->raw);Py_CLEAR(v->key);Py_CLEAR(v->scope);Py_CLEAR(v->sequence);Py_CLEAR(v->journal);return 0;}
static void pin_version_free(PinVersion*v){PyObject_GC_UnTrack(v);pin_version_clear(v);Py_TYPE(v)->tp_free((PyObject*)v);}
static int pin_journal_traverse(PinJournal*j,visitproc visit,void*arg){Py_VISIT(j->scope);Py_VISIT(j->version);Py_VISIT(j->frontier);Py_VISIT(j->cleanup);return 0;}
static int pin_journal_clear(PinJournal*j){j->closed=1;Py_CLEAR(j->scope);Py_CLEAR(j->version);Py_CLEAR(j->frontier);Py_CLEAR(j->cleanup);return 0;}
/* Revocation must retain original cleanup identity until the original Python
 * teardown runs. It is not a live scope or permission. GC still clears all. */
static void pin_journal_revoke(PinJournal*j){j->closed=1;Py_CLEAR(j->scope);Py_CLEAR(j->version);}
static void pin_journal_free(PinJournal*j){PyObject_GC_UnTrack(j);if(j->weakrefs)PyObject_ClearWeakRefs((PyObject*)j);pin_journal_clear(j);Py_TYPE(j)->tp_free((PyObject*)j);}
#define PIN_GET(name) static PyObject*pin_get_##name(PinVersion*v,void*unused){(void)unused;if(!v->name){PyErr_SetString(PyExc_ValueError,"Closed version storage");return NULL;}return Py_NewRef(v->name);}
PIN_GET(raw) PIN_GET(key) PIN_GET(sequence)
static PyGetSetDef pin_getsets[]={
 {"raw",(getter)pin_get_raw,NULL,"Exact publication V2 bytes.",NULL},
 {"key",(getter)pin_get_key,NULL,"Original publication key.",NULL},
 {"sequence",(getter)pin_get_sequence,NULL,"Monotone journal version.",NULL},{NULL}};
static PyTypeObject pin_version_type={PyVarObject_HEAD_INIT(NULL,0)
 .tp_name="sim2act._cold_graph_structure.PinVersion",.tp_basicsize=sizeof(PinVersion),
 .tp_flags=Py_TPFLAGS_DEFAULT|Py_TPFLAGS_HAVE_GC|Py_TPFLAGS_IMMUTABLETYPE,
 .tp_dealloc=(destructor)pin_version_free,.tp_traverse=(traverseproc)pin_version_traverse,
 .tp_clear=(inquiry)pin_version_clear,.tp_getset=pin_getsets};
static PyTypeObject pin_journal_type={PyVarObject_HEAD_INIT(NULL,0)
 .tp_name="sim2act._cold_graph_structure.PinJournal",.tp_basicsize=sizeof(PinJournal),
 .tp_flags=Py_TPFLAGS_DEFAULT|Py_TPFLAGS_HAVE_GC|Py_TPFLAGS_IMMUTABLETYPE,
 .tp_dealloc=(destructor)pin_journal_free,.tp_traverse=(traverseproc)pin_journal_traverse,
 .tp_clear=(inquiry)pin_journal_clear,.tp_weaklistoffset=offsetof(PinJournal,weakrefs)};
static int pin_thread(PyObject*v){
 if(!PyLong_CheckExact(v))return 0;
 unsigned long long value=PyLong_AsUnsignedLongLong(v);
 if(PyErr_Occurred()){PyErr_Clear();return 0;}
 return value==(unsigned long long)PyThread_get_thread_ident();
}
static int pin_scope(PyObject*s){return PyTuple_CheckExact(s)&&PyTuple_GET_SIZE(s)==13
 &&PyLong_CheckExact(PyTuple_GET_ITEM(s,9))&&PyUnicode_CheckExact(PyTuple_GET_ITEM(s,10))
 &&pin_thread(PyTuple_GET_ITEM(s,12));}
static int pin_same_scope(PyObject*a,PyObject*b){
 if(!pin_scope(a)||!pin_scope(b))return 0;
 for(Py_ssize_t i=0;i<13;i++)if(PyTuple_GET_ITEM(a,i)!=PyTuple_GET_ITEM(b,i))return 0;
 return 1;
}
static PyObject*pin_error(void){PyErr_SetString(PyExc_ValueError,"Graph publication lifecycle changed");return NULL;}
static PyObject*pin_fields(PyObject*subject){
 PyObject*d=PyObject_GenericGetDict(subject,NULL);if(!d)return NULL;
 if(!PyDict_CheckExact(d)){Py_DECREF(d);return pin_error();}
 Py_ssize_t pos=0;PyObject*k,*v;
 while(PyDict_Next(d,&pos,&k,&v))if(!PyUnicode_CheckExact(k)){Py_DECREF(d);return pin_error();}
 return d;
}
static int pin_scope_items(PyObject*subject,PyObject**items){
 if((PyObject*)Py_TYPE(subject)!=pin_graph_class&&(PyObject*)Py_TYPE(subject)!=pin_frontier_class){pin_error();return 0;}
 PyObject*sf=pin_fields(subject);if(!sf)return 0;
 PyObject*graph=(PyObject*)Py_TYPE(subject)==pin_graph_class?subject:PyDict_GetItemString(sf,"graph");
 if(!graph||(PyObject*)Py_TYPE(graph)!=pin_graph_class){Py_DECREF(sf);pin_error();return 0;}
 PyObject*gf=pin_fields(graph);if(!gf){Py_DECREF(sf);return 0;}
 items[0]=subject;items[1]=graph;
 const char*names[]={"nonce","inputs","role_limits","binding","connection","transaction","scope","epoch","phase","driver","thread"};
 int ok=1;for(int i=0;i<11;i++){items[i+2]=PyDict_GetItemString(gf,names[i]);if(!items[i+2]){ok=0;break;}}
 if(ok)ok=PyLong_CheckExact(items[9])&&PyUnicode_CheckExact(items[10])&&pin_thread(items[12]);
 /* Caller borrows under the GIL and must hold every item before allocating. */
 Py_DECREF(sf);Py_DECREF(gf);if(!ok)pin_error();return ok;
}
static int pin_actual_scope(PyObject*scope){
 if(!pin_scope(scope))return 0;PyObject*items[13];
 if(!pin_scope_items(PyTuple_GET_ITEM(scope,0),items))return 0;
 for(int i=0;i<13;i++)if(items[i]!=PyTuple_GET_ITEM(scope,i))return 0;
 return 1;
}
static PyObject*pin_read_scope(PyObject*self,PyObject*subject){
 (void)self;PyObject*items[13];if(!pin_scope_items(subject,items))return NULL;
 for(int i=0;i<13;i++)Py_INCREF(items[i]);
 PyObject*scope=PyTuple_New(13);
 if(!scope){for(int i=0;i<13;i++)Py_DECREF(items[i]);return NULL;}
 for(int i=0;i<13;i++)PyTuple_SET_ITEM(scope,i,items[i]);
 if(!pin_actual_scope(scope)){Py_DECREF(scope);if(!PyErr_Occurred())pin_error();return NULL;}
 return scope;
}
static PyObject*pin_function(PyObject*fn){
 if(!PyFunction_Check(fn))return pin_error();
 return PyTuple_Pack(3,fn,PyFunction_GET_CODE(fn),PyFunction_GET_GLOBALS(fn));
}
static int pin_frame(PyFrameObject*f,PyObject*record){
 if(!f||!PyTuple_CheckExact(record)||PyTuple_GET_SIZE(record)!=3)return 0;
 PyCodeObject*c=PyFrame_GetCode(f);PyObject*g=PyFrame_GetGlobals(f);
 int ok=(PyObject*)c==PyTuple_GET_ITEM(record,1)&&g==PyTuple_GET_ITEM(record,2)
  &&PyFunction_GET_CODE(PyTuple_GET_ITEM(record,0))==PyTuple_GET_ITEM(record,1);
 Py_DECREF(c);Py_DECREF(g);return ok;
}
static int pin_callsite(PyObject*helper,PyObject*allowed,PyObject*subject,PyObject*raw,PyObject*predecessor){
 if(!helper||!PyTuple_CheckExact(allowed))return 0;
 PyFrameObject*f=PyThreadState_GetFrame(PyThreadState_Get());if(!f)return 0;
 int ok=pin_frame(f,helper);PyFrameObject*parent=ok?PyFrame_GetBack(f):NULL;Py_DECREF(f);if(!parent)return 0;
 ok=0;for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(allowed);i++)if(pin_frame(parent,PyTuple_GET_ITEM(allowed,i))){ok=1;break;}
 if(ok){PyObject*local=PyFrame_GetLocals(parent);if(!local)ok=0;
  else{ok=PyDict_CheckExact(local)&&PyDict_GetItemString(local,"self")==subject
    &&(!raw||(PyDict_GetItemString(local,"_pin_raw")==raw
      &&PyDict_GetItemString(local,"_pin_previous")==predecessor));Py_DECREF(local);}}
 Py_DECREF(parent);return ok;
}
static PyObject*register_pin_code(PyObject*self,PyObject*args){
 (void)self;PyObject*a,*b,*c,*d,*graph,*frontier,*verifier,*modules;if(!PyArg_ParseTuple(args,"OOOOOOOO",&a,&b,&c,&d,&graph,&frontier,&verifier,&modules))return NULL;
 if(!PyTuple_CheckExact(modules)||PyTuple_GET_SIZE(modules)!=5)return pin_error();
 for(Py_ssize_t i=0;i<5;i++){PyObject*m=PyTuple_GET_ITEM(modules,i);if(m!=Py_None&&!PyModule_CheckExact(m))return pin_error();}
 if(!PyType_Check(graph)||!PyType_Check(frontier)||(verifier!=Py_None&&!PyCFunction_Check(verifier)))return pin_error();
 if(pin_create_code||!PyFunction_Check(a)||!PyFunction_Check(b)||!PyTuple_CheckExact(c)||!PyTuple_CheckExact(d))return pin_error();
 PyObject*constructors=PyTuple_New(2),*publishers=PyTuple_New(4),*ca=NULL,*cb=NULL,*keys=NULL,*issued=NULL;
 if(!constructors||!publishers)goto bad;
 for(int group=0;group<2;group++){PyObject*t=group?d:c,*out=group?publishers:constructors;
  if(PyTuple_GET_SIZE(t)!=(group?4:2))goto bad;
  for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(t);i++){PyObject*record=pin_function(PyTuple_GET_ITEM(t,i));if(!record)goto bad;PyTuple_SET_ITEM(out,i,record);}}
 ca=pin_function(a);cb=pin_function(b);if(!ca||!cb)goto bad;
 static const char*names[]={"nonce","inputs","role_limits","binding","connection","transaction","scope","epoch","phase","driver","thread","graph","_pin_journal","key","expected","_accounted_frontier","content_version","export_version","_content_matches","check","add","invalidate","input_key","input_bytes","_check_dynamic","values","_refresh","added"};
 keys=PyTuple_New(28);if(!keys)goto bad;
 for(int i=0;i<28;i++){PyObject*k=PyUnicode_InternFromString(names[i]);if(!k)goto bad;PyTuple_SET_ITEM(keys,i,k);}
 issued=PyDict_New();if(!issued)goto bad;
 pin_graph_class=Py_NewRef(graph);pin_frontier_class=Py_NewRef(frontier);pin_source_verifier=Py_NewRef(verifier);
 pin_modules=Py_NewRef(modules);pin_keys=keys;pin_issued=issued;
 pin_create_code=ca;pin_publish_code=cb;pin_constructors=constructors;pin_publishers=publishers;
 Py_RETURN_NONE;
 bad:Py_XDECREF(keys);Py_XDECREF(issued);Py_XDECREF(constructors);Py_XDECREF(publishers);Py_XDECREF(ca);Py_XDECREF(cb);if(!PyErr_Occurred())return pin_error();return NULL;
}
static PyObject*pin_forget(PyObject*key,PyObject*weak){
 if(pin_issued){PyObject*entry=PyDict_GetItemWithError(pin_issued,key);
  if(entry&&PyTuple_CheckExact(entry)&&PyTuple_GET_ITEM(entry,0)==weak){if(PyDict_DelItem(pin_issued,key)<0)return NULL;}
  else if(PyErr_Occurred())return NULL;}
 Py_RETURN_NONE;
}
static PyMethodDef pin_forget_def={"_pin_forget",pin_forget,METH_O,NULL};
static int pin_code_current(void){
 if(!pin_source_verifier||pin_source_verifier==Py_None)return 0;
 PyObject*ok=PyObject_CallNoArgs(pin_source_verifier);if(!ok)return 0;
 int same=ok==Py_True;Py_DECREF(ok);return same;
}
static PyObject*pin_lookup_raw(PyObject*subject){
 if(!pin_issued)return pin_error();PyObject*key=PyLong_FromVoidPtr(subject);if(!key)return NULL;
 PyObject*entry=PyDict_GetItemWithError(pin_issued,key);Py_DECREF(key);
 if(!entry){if(PyErr_Occurred())return NULL;Py_RETURN_NONE;}
 if(!PyTuple_CheckExact(entry)||PyTuple_GET_SIZE(entry)!=2)return pin_error();
 PyObject*owner=PyWeakref_GetObject(PyTuple_GET_ITEM(entry,0));
 if(owner!=subject)return pin_error();
 PyObject*journal=PyWeakref_GetObject(PyTuple_GET_ITEM(entry,1));
 if(journal==Py_None||Py_TYPE(journal)!=&pin_journal_type)return pin_error();
 return Py_NewRef(journal);
}
static PyObject*pin_lookup(PyObject*subject){
 PyObject*j=pin_lookup_raw(subject);if(!j)return NULL;
 if(j!=Py_None||((PyObject*)Py_TYPE(subject)==pin_graph_class&&pin_source_verifier!=Py_None)){
  if(!pin_code_current()){Py_DECREF(j);if(!PyErr_Occurred())pin_error();return NULL;}
  PyObject*fields=pin_fields(subject);if(!fields){Py_DECREF(j);return NULL;}
  const char*names[]={"content_version","export_version","_content_matches","check","add","invalidate","input_key","input_bytes","_check_dynamic",NULL};
  int shadow=0;for(int i=0;names[i];i++)if(PyDict_GetItemString(fields,names[i])){shadow=1;break;}
  if((PyObject*)Py_TYPE(subject)==pin_frontier_class){
   const char*frontier_names[]={"key","values","_refresh","added",NULL};
   for(int i=0;frontier_names[i];i++)if(PyDict_GetItemString(fields,frontier_names[i])){shadow=1;break;}
  }
  Py_DECREF(fields);if(shadow){Py_DECREF(j);return pin_error();}
 }
 return j;
}
static PyObject*pin_registered(PyObject*self,PyObject*subject){(void)self;return pin_lookup(subject);}
static PyObject*pin_create(PyObject*self,PyObject*scope){
 (void)self;if(!pin_scope(scope)||!pin_callsite(pin_create_code,pin_constructors,PyTuple_GET_ITEM(scope,0),NULL,NULL))return pin_error();
 PinJournal*j=PyObject_GC_New(PinJournal,&pin_journal_type);if(!j)return NULL;
 j->scope=Py_NewRef(scope);j->version=NULL;j->frontier=NULL;j->cleanup=NULL;j->sequence=0;j->closed=0;j->weakrefs=NULL;PyObject_GC_Track(j);
 PyObject*subject=PyTuple_GET_ITEM(scope,0),*key=PyLong_FromVoidPtr(subject),*callback=NULL,*owner=NULL,*weak=NULL,*entry=NULL;
 if(!key)goto bad_create;
 if(PyDict_Contains(pin_issued,key)!=0){if(!PyErr_Occurred())pin_error();goto bad_create;}
 callback=PyCFunction_NewEx(&pin_forget_def,key,NULL);if(!callback)goto bad_create;
 owner=PyWeakref_NewRef(subject,callback);weak=PyWeakref_NewRef((PyObject*)j,NULL);
 if(!owner||!weak)goto bad_create;entry=PyTuple_Pack(2,owner,weak);if(!entry||PyDict_SetItem(pin_issued,key,entry)<0)goto bad_create;
 if(subject!=PyTuple_GET_ITEM(scope,1)){
  PyObject*fields=pin_fields(subject);if(!fields)goto bad_create;
  PyObject*mode=PyDict_GetItemString(fields,"mode");Py_XINCREF(mode);Py_DECREF(fields);
  if(!mode){pin_error();goto bad_create;}
  fields=pin_fields(mode);if(!fields){Py_DECREF(mode);goto bad_create;}
  PyObject*owner_scope=PyDict_GetItemString(fields,"scope"),*candidate=PyDict_GetItemString(fields,"_native");
  if(!owner_scope||!candidate||PyDict_GetItemString(fields,"graph")!=PyTuple_GET_ITEM(scope,1)){
   Py_DECREF(mode);Py_DECREF(fields);pin_error();goto bad_create;}
  Py_INCREF(owner_scope);Py_INCREF(candidate);
  j->cleanup=PyTuple_Pack(3,mode,owner_scope,candidate);
  Py_DECREF(owner_scope);Py_DECREF(candidate);Py_DECREF(mode);Py_DECREF(fields);if(!j->cleanup)goto bad_create;
  PyObject*parent=pin_lookup(PyTuple_GET_ITEM(scope,1));
  if(!parent||Py_TYPE(parent)!=&pin_journal_type){Py_XDECREF(parent);if(!PyErr_Occurred())pin_error();goto bad_create;}
  PinJournal*parent_journal=(PinJournal*)parent;
  if(parent_journal->closed||parent_journal->frontier){Py_DECREF(parent);pin_error();goto bad_create;}
  parent_journal->frontier=Py_NewRef(owner);Py_DECREF(parent);
 }
 Py_DECREF(key);Py_DECREF(callback);Py_DECREF(owner);Py_DECREF(weak);Py_DECREF(entry);return(PyObject*)j;
 bad_create:Py_XDECREF(key);Py_XDECREF(callback);Py_XDECREF(owner);Py_XDECREF(weak);Py_XDECREF(entry);Py_DECREF(j);return NULL;
}
static PyObject*pin_publish(PyObject*self,PyObject*args){
 (void)self;PyObject*object,*raw,*key,*scope,*predecessor;if(!PyArg_ParseTuple(args,"OOOOO",&object,&raw,&key,&scope,&predecessor))return NULL;
 if(Py_TYPE(object)!=&pin_journal_type||!pin_scope(scope)||!pin_callsite(pin_publish_code,pin_publishers,PyTuple_GET_ITEM(scope,0),raw,predecessor)
  ||!PyBytes_CheckExact(raw)||!PyUnicode_CheckExact(key)||PyUnicode_GET_LENGTH(key)!=64)return pin_error();
 PinJournal*j=(PinJournal*)object;
 if(j->closed||!pin_same_scope(j->scope,scope)||!pin_actual_scope(scope)||j->sequence==SIZE_MAX
  ||(j->version?j->version!=predecessor:predecessor!=Py_None))return pin_error();
 static const char prefix[]="SIM2ACT_COLD_GRAPH_PICKLE_V2\0";
 if(PyBytes_GET_SIZE(raw)<(Py_ssize_t)(sizeof(prefix)-1)||memcmp(PyBytes_AS_STRING(raw),prefix,sizeof(prefix)-1))return pin_error();
 PinVersion*v=PyObject_GC_New(PinVersion,&pin_version_type);if(!v)return NULL;
 v->raw=Py_NewRef(raw);v->key=Py_NewRef(key);v->scope=Py_NewRef(scope);v->journal=Py_NewRef(object);
 v->sequence=PyLong_FromSize_t(j->sequence+1);
 if(!v->sequence){pin_version_clear(v);PyObject_GC_Del(v);return NULL;}
 /* All allocations precede the indivisible key/current-version update. */
 PyObject*subject=PyTuple_GET_ITEM(scope,0),*registered=pin_lookup(subject);
 if(!registered||registered!=object){Py_XDECREF(registered);pin_version_clear(v);PyObject_GC_Del(v);if(!PyErr_Occurred())pin_error();return NULL;}Py_DECREF(registered);
 PyObject*fields=pin_fields(subject);
 if(!fields||!PyDict_CheckExact(fields)){Py_XDECREF(fields);pin_version_clear(v);PyObject_GC_Del(v);if(!PyErr_Occurred())pin_error();return NULL;}
 Py_ssize_t pos=0;PyObject*k,*item;int plain=1;while(PyDict_Next(fields,&pos,&k,&item))if(!PyUnicode_CheckExact(k)){plain=0;break;}
 const char*name=subject==PyTuple_GET_ITEM(scope,1)?"key":"expected";
 PyObject*old=PyDict_GetItemString(fields,name);
 int prior=j->version?old==((PinVersion*)j->version)->key:
  (old==NULL||(PyUnicode_CheckExact(old)&&PyUnicode_Compare(old,key)==0));
 if(!pin_code_current()||!plain||!prior||PyDict_GetItemString(fields,"_pin_journal")!=object||j->closed
   ||!pin_same_scope(j->scope,scope)||!pin_actual_scope(scope)
   ||(j->version?j->version!=predecessor:predecessor!=Py_None)){
  Py_DECREF(fields);pin_version_clear(v);PyObject_GC_Del(v);if(!PyErr_Occurred())pin_error();return NULL;
 }
 Py_XINCREF(old);
 if(PyDict_SetItemString(fields,name,key)<0){Py_XDECREF(old);Py_DECREF(fields);pin_version_clear(v);PyObject_GC_Del(v);if(!PyErr_Occurred())pin_error();return NULL;}
 Py_DECREF(fields);PyObject_GC_Track(v);j->sequence++;Py_XSETREF(j->version,Py_NewRef((PyObject*)v));Py_XDECREF(old);return(PyObject*)v;
}
static PyObject*pin_current(PyObject*self,PyObject*args){
 (void)self;PyObject*object,*scope,*key;if(!PyArg_ParseTuple(args,"OOO",&object,&scope,&key))return NULL;
 if(Py_TYPE(object)!=&pin_journal_type)return pin_error();PinJournal*j=(PinJournal*)object;
 if(!pin_code_current()||j->closed||!pin_same_scope(j->scope,scope)||!pin_actual_scope(scope)||!j->version||Py_TYPE(j->version)!=&pin_version_type)return pin_error();
 PinVersion*v=(PinVersion*)j->version;
 PyObject*subject=PyTuple_GET_ITEM(scope,0),*fields=pin_fields(subject);if(!fields)return NULL;
 const char*name=subject==PyTuple_GET_ITEM(scope,1)?"key":"expected";
 PyObject*actual_key=PyDict_GetItemString(fields,name);
 int actual=PyDict_GetItemString(fields,"_pin_journal")==object&&actual_key==v->key;
 Py_DECREF(fields);
 if(!actual||v->journal!=object||(key!=Py_None&&v->key!=key))return pin_error();
 if(PyTuple_GET_ITEM(scope,0)==PyTuple_GET_ITEM(scope,1)){
  PyObject*fields=PyObject_GenericGetDict(PyTuple_GET_ITEM(scope,0),NULL);if(!fields)return NULL;
  PyObject*actual=PyDict_CheckExact(fields)?PyDict_GetItemString(fields,"_accounted_frontier"):NULL;
  PyObject*expected=j->frontier?PyWeakref_GetObject(j->frontier):Py_None;
  int ok=actual==expected&&(!j->frontier||expected!=Py_None);Py_DECREF(fields);if(!ok)return pin_error();
 }
 return Py_NewRef(j->version);
}
/* One fresh complete code gate for one Version read. Scope/dict materializing
 * happens before the gate; after it all lookups use fixed exact Unicode keys.
 * The registered verifier reads C metadata with GC disabled/restored itself:
 * no allocation, Python callback or GIL release occurs in the final segment.
 * This is DATA currentness; never a Graph/permission/lease PASS. */
static int pin_modules_current(void){
 if(!pin_modules||!PyTuple_CheckExact(pin_modules))return 0;
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(pin_modules);i++){
  PyObject*m=PyTuple_GET_ITEM(pin_modules,i);if(m!=Py_None&&!PyModule_CheckExact(m))return 0;
 }
 return 1;
}
static PyObject*pin_value(PyObject*fields,int index){return PyDict_GetItemWithError(fields,PyTuple_GET_ITEM(pin_keys,index));}
static int pin_plain(PyObject*d){
 if(!PyDict_CheckExact(d))return 0;Py_ssize_t pos=0;PyObject*k,*v;
 while(PyDict_Next(d,&pos,&k,&v))if(!PyUnicode_CheckExact(k))return 0;
 return 1;
}
static PyObject*pin_resolve(PyObject*self,PyObject*subject){
 (void)self;PyObject*j=NULL,*sf=NULL,*gf=NULL,*again=NULL,*graph=NULL,*result=NULL;
 int is_graph=(PyObject*)Py_TYPE(subject)==pin_graph_class;
 if(!pin_modules_current()||!pin_keys||(!is_graph&&(PyObject*)Py_TYPE(subject)!=pin_frontier_class))return pin_error();
 j=pin_lookup_raw(subject);if(!j)return NULL;
 sf=pin_fields(subject);if(!sf)goto done;
 PyObject*borrowed_graph=is_graph?subject:pin_value(sf,11);
 if(!borrowed_graph||(PyObject*)Py_TYPE(borrowed_graph)!=pin_graph_class)goto invalid;
 graph=Py_NewRef(borrowed_graph);gf=pin_fields(graph);if(!gf)goto done;
 /* A materialization/reentrant GC may have replaced either dictionary. If a
  * final lookup needs to materialize anew its identity differs: fail closed.
  * Passing these exact identities means both final lookups allocated nothing. */
 again=PyObject_GenericGetDict(subject,NULL);if(!again)goto done;
 if(again!=sf)goto invalid;Py_CLEAR(again);
 again=PyObject_GenericGetDict(graph,NULL);if(!again)goto done;
 if(again!=gf)goto invalid;Py_CLEAR(again);
 if((j!=Py_None||is_graph)&&pin_source_verifier!=Py_None&&!pin_code_current())goto invalid;
 /* Everything below the fresh code gate is no-allocation on success. */
 if(!pin_modules_current()||!pin_plain(sf)||!pin_plain(gf))goto invalid;
 for(int i=16;i<=24;i++)if(pin_value(sf,i))goto invalid;
 if(!is_graph)for(int i=25;i<=27;i++)if(pin_value(sf,i))goto invalid;
 if(!is_graph&&pin_value(sf,13))goto invalid;
 if(!is_graph&&pin_value(sf,11)!=graph)goto invalid;
 PyObject*items[13];items[0]=subject;items[1]=graph;
 for(int i=0;i<11;i++){items[i+2]=pin_value(gf,i);if(!items[i+2])goto invalid;}
 if(!PyLong_CheckExact(items[9])||!PyUnicode_CheckExact(items[10])||!pin_thread(items[12]))goto invalid;
 PyObject*stored=pin_value(sf,12);
 if(j==Py_None){if(stored&&stored!=Py_None)goto invalid;result=Py_NewRef(Py_None);goto done;}
 PinJournal*journal=(PinJournal*)j;
 if(journal->closed||stored!=j||!pin_scope(journal->scope)||!journal->version||Py_TYPE(journal->version)!=&pin_version_type)goto invalid;
 for(int i=0;i<13;i++)if(items[i]!=PyTuple_GET_ITEM(journal->scope,i))goto invalid;
 PinVersion*v=(PinVersion*)journal->version;
 if(v->journal!=j||pin_value(sf,is_graph?13:14)!=v->key)goto invalid;
 if(is_graph){
  PyObject*expected=journal->frontier?PyWeakref_GetObject(journal->frontier):Py_None;
  if((journal->frontier&&expected==Py_None)||pin_value(sf,15)!=expected)goto invalid;
 }
 result=Py_NewRef(journal->version);goto done;
 invalid:if(!PyErr_Occurred())pin_error();
 done:Py_XDECREF(again);Py_XDECREF(gf);Py_XDECREF(sf);Py_XDECREF(graph);Py_XDECREF(j);return result;
}
static PyObject*pin_matches(PyObject*self,PyObject*args){
 (void)self;PyObject*object,*raw;if(!PyArg_ParseTuple(args,"OO",&object,&raw))return NULL;
 if(Py_TYPE(object)!=&pin_version_type||!PyBytes_CheckExact(raw))return pin_error();
 PinVersion*v=(PinVersion*)object;
 if(!v->raw)return pin_error();
 Py_ssize_t n=PyBytes_GET_SIZE(raw);
 return PyBool_FromLong(n==PyBytes_GET_SIZE(v->raw)&&!memcmp(PyBytes_AS_STRING(raw),PyBytes_AS_STRING(v->raw),(size_t)n));
}
static PyObject*pin_close(PyObject*self,PyObject*object){
 (void)self;if(Py_TYPE(object)!=&pin_journal_type)return pin_error();
 pin_journal_clear((PinJournal*)object);Py_RETURN_NONE;
}
static void pin_inactive_plain(PyObject*subject){
 if((PyObject*)Py_TYPE(subject)!=pin_graph_class)return;
 PyObject*fields=PyObject_GenericGetDict(subject,NULL);if(!fields){PyErr_Clear();return;}
 int plain=PyDict_Check(fields);Py_ssize_t pos=0;PyObject*k,*v;
 if(plain)while(PyDict_Next(fields,&pos,&k,&v))if(!PyUnicode_CheckExact(k)){plain=0;break;}
 PyObject*active=plain?PyDict_GetItemString(fields,"active"):NULL;
 if(plain&&(!active||PyBool_Check(active)))if(PyDict_SetItemString(fields,"active",Py_False)<0)PyErr_Clear();
 Py_DECREF(fields);
}
static PyObject*pin_owned_frontier(PyObject*self,PyObject*subject){
 (void)self;PyObject*j=pin_lookup_raw(subject);
 if(!j){PyErr_Clear();return PyTuple_Pack(2,Py_None,Py_None);}
 PyObject*child=Py_NewRef(Py_None),*links=Py_NewRef(Py_None);
 if(j!=Py_None&&(PyObject*)Py_TYPE(subject)==pin_graph_class){
  PinJournal*parent=(PinJournal*)j;
  if(parent->frontier){
   PyObject*actual=PyWeakref_GetObject(parent->frontier);
   if(actual!=Py_None){
    Py_SETREF(child,Py_NewRef(actual));PyObject*cj=pin_lookup_raw(child);
    if(cj&&cj!=Py_None&&((PinJournal*)cj)->cleanup)
     Py_SETREF(links,Py_NewRef(((PinJournal*)cj)->cleanup));
    Py_XDECREF(cj);PyErr_Clear();
   }
  }
 }
 Py_DECREF(j);PyObject*result=PyTuple_Pack(2,child,links);Py_DECREF(child);Py_DECREF(links);return result;
}
static PyObject*pin_revoke(PyObject*self,PyObject*subject){
 (void)self;PyObject*j=pin_lookup_raw(subject);
 if(!j){PyErr_Clear();pin_inactive_plain(subject);Py_RETURN_FALSE;}
 if(j==Py_None){Py_DECREF(j);Py_RETURN_TRUE;} /* Original unissued route. */
 PinJournal*journal=(PinJournal*)j;
 if(journal->frontier){
  PyObject*child=PyWeakref_GetObject(journal->frontier);Py_INCREF(child);
  if(child!=Py_None){PyObject*cj=pin_lookup_raw(child);
   if(cj&&cj!=Py_None)pin_journal_revoke((PinJournal*)cj);Py_XDECREF(cj);PyErr_Clear();}
  Py_DECREF(child);
 }
 pin_journal_revoke(journal);Py_DECREF(j);
 int safe=pin_code_current();if(PyErr_Occurred()){PyErr_Clear();safe=0;}
 PyObject*fields=PyObject_GenericGetDict(subject,NULL);
 if(!fields){PyErr_Clear();Py_RETURN_FALSE;}
 int plain=PyDict_Check(fields);Py_ssize_t pos=0;PyObject*k,*value;
 if(plain)while(PyDict_Next(fields,&pos,&k,&value))if(!PyUnicode_CheckExact(k)){plain=0;break;}
 PyObject*active=plain?PyDict_GetItemString(fields,"active"):NULL;
 int ordinary_active=!active||PyBool_Check(active);
 safe=safe&&PyDict_CheckExact(fields)&&plain&&ordinary_active;
 if(!safe&&plain&&ordinary_active&&(PyObject*)Py_TYPE(subject)==pin_graph_class){
  if(PyDict_SetItemString(fields,"active",Py_False)<0)PyErr_Clear();
 }
 Py_DECREF(fields);return PyBool_FromLong(safe);
}
static PyMethodDef methods[]={
 {"register_pin_code",register_pin_code,METH_VARARGS,"One-time fixed publication caller metadata."},
 {"pin_read_scope",pin_read_scope,METH_O,"Exact instance roots without foreign attribute callbacks."},
 {"pin_registered",pin_registered,METH_O,"Find the original issuer independently of Python fields."},
 {"pin_create",pin_create,METH_O,"Create one scoped publication journal."},
 {"pin_publish",pin_publish,METH_VARARGS,"Publish complete immutable original bytes."},
 {"pin_resolve",pin_resolve,METH_O,"Resolve one current Version with a fresh complete code and scope check."},
 {"pin_current",pin_current,METH_VARARGS,"Require the same current scoped version."},
 {"pin_matches",pin_matches,METH_VARARGS,"Full byte comparison, never a hash verdict."},
 {"pin_revoke",pin_revoke,METH_O,"Idempotently revoke the original issuer with no Python callback."},
 {"pin_owned_frontier",pin_owned_frontier,METH_O,"Original cleanup child and links, never mutable backlinks or authority."},
 {"pin_close",pin_close,METH_O,"Revoke the journal, retaining immutable old data only."},{"same_classes",same_classes,METH_VARARGS,"Fresh complete class namespace and MRO identity comparison without callbacks."},{"snapshot",snapshot,METH_VARARGS,"Bounded independent complete structure for one qualified scope."},{"matches_fast",matches_fast,METH_VARARGS,"Fresh complete structure and alias comparison in the same scope."},{NULL,NULL,0,NULL}};
static struct PyModuleDef module={PyModuleDef_HEAD_INIT,"_cold_graph_structure",NULL,-1,methods};
PyMODINIT_FUNC PyInit__cold_graph_structure(void){
 if(PyType_Ready(&pin_version_type)<0||PyType_Ready(&pin_journal_type)<0)return NULL;
 PyObject*m=PyModule_Create(&module);if(!m)return NULL;
 if(PyModule_AddObjectRef(m,"PinVersion",(PyObject*)&pin_version_type)<0||PyModule_AddObjectRef(m,"PinJournal",(PyObject*)&pin_journal_type)<0){Py_DECREF(m);return NULL;}
 unsupported=PyCapsule_New((void*)&module,"sim2act.cold-graph-structure.unsupported",NULL);
 unsupported_error=PyErr_NewException("sim2act._cold_graph_structure._Unsupported",NULL,NULL);
 if(!unsupported||!unsupported_error||PyModule_AddObjectRef(m,"UNSUPPORTED",unsupported)<0||PyModule_AddStringConstant(m,"SOURCE_SHA256",SIM2ACT_GRAPH_SOURCE_SHA)<0){Py_XDECREF(unsupported);Py_XDECREF(unsupported_error);Py_DECREF(m);return NULL;}return m;
}
