/* Private direct image/live verifier: exact builtin containers, original leaves,
 * bounded bidirectional aliases. No serializer, guard or arbitrary attribute
 * access is called while matching. Configuration descriptors are checked C
 * getset/member descriptors and invoke only their fixed native getter. */
#include <descrobject.h>
#include <string.h>
typedef struct {
 PyObject *nodes,*leaves,*anchors,*virtuals,*config,*reverse,*held;
 PyObject **forward; unsigned char*status; Py_ssize_t *boundary,*model_kinds; Py_ssize_t n; size_t work;
} LiveMatch;
static Py_ssize_t source_fail_ref=-1;static int source_fail_line=0;
static int source_in_match=0;
static PyObject*source_matching(PyObject*a,PyObject*b){(void)a;(void)b;return PyBool_FromLong(source_in_match);}
static PyObject*source_diagnostic(PyObject*a,PyObject*b){(void)a;(void)b;return Py_BuildValue("ni",source_fail_ref,source_fail_line);}
static int source_match(LiveMatch*,Py_ssize_t,PyObject*,int);
static int source_tick(LiveMatch*s,int depth){return ++s->work<=1000000&&depth<=64;}
static int source_index(PyObject*v,Py_ssize_t n,Py_ssize_t*out){
 if(!PyLong_CheckExact(v))return 0;
 *out=PyLong_AsSsize_t(v);if(PyErr_Occurred()){PyErr_Clear();return 0;}return *out>=0&&*out<n;
}
static int source_hold(LiveMatch*s,PyObject*v){return PyList_Append(s->held,v)==0;}
static PyObject*source_get(PyObject*descriptor,PyObject*value){
 if(Py_TYPE(descriptor)!=&PyGetSetDescr_Type&&Py_TYPE(descriptor)!=&PyMemberDescr_Type)return NULL;
 if(!PyType_IsSubtype(Py_TYPE(value),PyDescr_TYPE(descriptor)))return NULL;
 return Py_TYPE(descriptor)->tp_descr_get(descriptor,value,(PyObject*)Py_TYPE(value));
}
static PyObject*source_row(LiveMatch*s,PyObject*v){
 /* config: model tuples(type,schema,4 descriptors), row type, 3 descriptors,
  * parent tuples(type,_keys descriptor), exact quoted-name type. */
 PyObject*row=PyTuple_GET_ITEM(s->config,1),*ds=PyTuple_GET_ITEM(s->config,2);
 if((PyObject*)Py_TYPE(v)!=row)return NULL;
 PyObject*parent=source_get(PyTuple_GET_ITEM(ds,0),v);
 PyObject*data=source_get(PyTuple_GET_ITEM(ds,1),v);
 PyObject*index=source_get(PyTuple_GET_ITEM(ds,2),v),*keys=NULL,*lookup=NULL,*result=NULL;
 if(!parent||!data||!index||!PyTuple_CheckExact(data)||!PyDict_CheckExact(index))goto done;
 PyObject*parents=PyTuple_GET_ITEM(s->config,3);
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(parents);i++){
  PyObject*entry=PyTuple_GET_ITEM(parents,i);
  if((PyObject*)Py_TYPE(parent)==PyTuple_GET_ITEM(entry,0)){keys=source_get(PyTuple_GET_ITEM(entry,1),parent);break;}
 }
 if(!keys||!PyList_CheckExact(keys))goto done;
 PyObject*quoted=PyTuple_GET_ITEM(s->config,4);
 lookup=PyDict_New();if(!lookup)goto done;
 Py_ssize_t pos=0;PyObject*k,*p;
 while(PyDict_Next(index,&pos,&k,&p)){
  if(!source_tick(s,0))goto done;
  if(PyUnicode_CheckExact(k)||(PyObject*)Py_TYPE(k)==quoted){
   Py_ssize_t offset;if(!source_index(p,PyTuple_GET_SIZE(data),&offset))goto done;
   PyObject*text=PyUnicode_FromObject(k);if(!text)goto done;
   int ok=PyDict_SetItem(lookup,text,p);Py_DECREF(text);if(ok<0)goto done;
  }
 }
 for(Py_ssize_t i=0;i<PyList_GET_SIZE(keys);i++){
  if(!source_tick(s,0))goto done;
  k=PyList_GET_ITEM(keys,i);
  if(!PyUnicode_CheckExact(k)&&(PyObject*)Py_TYPE(k)!=quoted)goto done;
  PyObject*text=PyUnicode_FromObject(k);if(!text)goto done;
  int ok=PyDict_Contains(lookup,text);Py_DECREF(text);if(ok!=1)goto done;
 }
 result=PyTuple_Pack(3,keys,data,lookup);
 done:Py_XDECREF(parent);Py_XDECREF(data);Py_XDECREF(index);Py_XDECREF(keys);Py_XDECREF(lookup);return result;
}
static int source_ref_match(LiveMatch*s,PyObject*ref,PyObject*v,int depth){
 Py_ssize_t i;if(!source_index(ref,s->n,&i))return 0;int ok=source_match(s,i,v,depth);if(!ok&&!source_fail_line){source_fail_ref=i;source_fail_line=__LINE__;}return ok;
}
static int source_sequence(LiveMatch*s,PyObject*refs,PyObject*seq,int depth){
 if(!PyTuple_CheckExact(refs))return 0;
 Py_ssize_t n=PyTuple_GET_SIZE(refs);
 if((PyTuple_CheckExact(seq)?PyTuple_GET_SIZE(seq):PyList_GET_SIZE(seq))!=n)return 0;
 for(Py_ssize_t i=0;i<n;i++)if(!source_ref_match(s,PyTuple_GET_ITEM(refs,i),PyTuple_CheckExact(seq)?PyTuple_GET_ITEM(seq,i):PyList_GET_ITEM(seq,i),depth+1))return 0;
 return 1;
}
static int source_match_body(LiveMatch*s,Py_ssize_t ref,PyObject*v,int depth){
 if(!source_tick(s,depth)){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
 PyObject*node=PyTuple_GET_ITEM(s->nodes,ref);
 if(!PyTuple_CheckExact(node)||PyTuple_GET_SIZE(node)!=2){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
 PyObject*tag=PyTuple_GET_ITEM(node,0),*value=PyTuple_GET_ITEM(node,1);
 if(!PyUnicode_CheckExact(tag)||PyUnicode_GET_LENGTH(tag)!=1){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
 Py_UCS4 t=PyUnicode_READ_CHAR(tag,0);PyObject*model=NULL;
 if(t=='m'&&s->model_kinds[ref]>=0){
  PyObject*models=PyTuple_GET_ITEM(s->config,0);
  PyObject*entry=PyTuple_GET_ITEM(models,s->model_kinds[ref]);
  if((PyObject*)Py_TYPE(v)==PyTuple_GET_ITEM(entry,0))model=entry;
 }
 int allowed=(t=='n'&&v==Py_None)||(t=='t'&&v==Py_True)||(t=='f'&&v==Py_False)
  ||(t=='i'&&PyLong_CheckExact(v))||(t=='v'&&PyFloat_CheckExact(v))
  ||(t=='s'&&PyUnicode_CheckExact(v))||(t=='b'&&PyBytes_CheckExact(v))
  ||(t=='d'&&PyDict_CheckExact(v))||(t=='l'&&PyList_CheckExact(v))||(t=='q'&&PyTuple_CheckExact(v))
  ||(t=='e'&&PySet_CheckExact(v))||(t=='r'&&(PyObject*)Py_TYPE(v)==PyTuple_GET_ITEM(s->config,1))
  ||(t=='u'&&(PyObject*)Py_TYPE(v)==PyTuple_GET_ITEM(s->config,4))||(t=='m'&&model);
 if(!allowed){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
 if(s->boundary[ref]>=0&&PyTuple_GET_ITEM(s->anchors,s->boundary[ref])!=v){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
 if(t!='n'&&t!='t'&&t!='f'&&t!='i'&&t!='v'){
  if(s->forward[ref])return s->forward[ref]==v;
  PyObject*id=PyLong_FromVoidPtr(v);if(!id){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
  int present=PyDict_Contains(s->reverse,id);
  PyObject*r=PyLong_FromSsize_t(ref);int ok=present==0&&r&&PyDict_SetItem(s->reverse,id,r)==0&&source_hold(s,v);
  Py_DECREF(id);Py_XDECREF(r);if(!ok){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}s->forward[ref]=v;
 }
 if(t=='n'||t=='t'||t=='f')return value==Py_None;
 if(t=='i')return PyLong_CheckExact(value)&&PyObject_RichCompareBool(v,value,Py_EQ)==1;
 if(t=='v'){
  if(!PyBytes_CheckExact(value)||PyBytes_GET_SIZE(value)!=8){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
  unsigned char bits[8];if(PyFloat_Pack8(PyFloat_AS_DOUBLE(v),(char*)bits,0)<0){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
  return memcmp(bits,PyBytes_AS_STRING(value),8)==0;
 }
 if(t=='s'||t=='b'){
  Py_ssize_t i;if(!source_index(value,PyTuple_GET_SIZE(s->leaves),&i)){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
  PyObject*leaf=PyTuple_GET_ITEM(s->leaves,i);
  PyObject*r=PyLong_FromSsize_t(ref);if(!r){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}int virtual=PySet_Contains(s->virtuals,r);Py_DECREF(r);
  return virtual==1?Py_TYPE(leaf)==Py_TYPE(v)&&PyObject_RichCompareBool(v,leaf,Py_EQ)==1:v==leaf;
 }
 if(t=='d'){
  if(!PyTuple_CheckExact(value)||PyTuple_GET_SIZE(value)!=PyDict_GET_SIZE(v)){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
  Py_ssize_t pos=0,i=0;PyObject*k,*child;
  while(PyDict_Next(v,&pos,&k,&child)){
   if(i>=PyTuple_GET_SIZE(value))return 0;
   PyObject*pair=PyTuple_GET_ITEM(value,i++);
   if(!PyTuple_CheckExact(pair)||PyTuple_GET_SIZE(pair)!=2||!source_ref_match(s,PyTuple_GET_ITEM(pair,0),k,depth+1)||!source_ref_match(s,PyTuple_GET_ITEM(pair,1),child,depth+1)){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
  }return i==PyTuple_GET_SIZE(value);
 }
 if(t=='l'||t=='q')return source_sequence(s,value,v,depth);
 if(t=='e'){
  PyObject*list=PySequence_List(v);if(!list){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
  int ok=1;for(Py_ssize_t i=0;i<PyList_GET_SIZE(list);i++)if(!PyUnicode_CheckExact(PyList_GET_ITEM(list,i))){ok=0;break;}
  if(ok&&PyList_Sort(list)<0)ok=0;
  if(ok)ok=source_sequence(s,value,list,depth);
  Py_DECREF(list);return ok;
 }
 if(t=='u'){
  PyObject*text=PyUnicode_FromObject(v);if(!text){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
  int ok=source_hold(s,text)&&source_ref_match(s,value,text,depth+1);Py_DECREF(text);return ok;
 }
 PyObject*storage=NULL;
 if(t=='r')storage=source_row(s,v);
 else if(t=='m'){
  if(!PyTuple_CheckExact(value)||PyTuple_GET_SIZE(value)!=5){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
  storage=PyTuple_New(5);if(!storage){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
  PyObject*name=PyTuple_GET_ITEM(model,1);
  PyObject*schema=PyUnicode_FromKindAndData(PyUnicode_KIND(name),PyUnicode_DATA(name),PyUnicode_GET_LENGTH(name));
  if(!schema){Py_DECREF(storage);{if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}}PyTuple_SET_ITEM(storage,0,schema);
  for(Py_ssize_t i=0;i<4;i++){
   PyObject*field=source_get(PyTuple_GET_ITEM(model,i+2),v);
   if(!field){Py_DECREF(storage);{if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}}PyTuple_SET_ITEM(storage,i+1,field);
  }
 }
 if(!storage){if(!source_fail_line){source_fail_ref=ref;source_fail_line=__LINE__;}return 0;}
 int ok=source_hold(s,storage)&&source_sequence(s,value,storage,depth);
 Py_DECREF(storage);return ok;
}
static int source_match(LiveMatch*s,Py_ssize_t ref,PyObject*v,int depth){
 if(s->status[ref]==1)return 0; /* Active is never completed-node reuse. */
 s->status[ref]=1;
 int ok=source_match_body(s,ref,v,depth);
 s->status[ref]=ok?2:0;
 return ok;
}
static int source_config(PyObject*c){
 if(!PyTuple_CheckExact(c)||PyTuple_GET_SIZE(c)!=6)return 0;
 PyObject*models=PyTuple_GET_ITEM(c,0),*ds=PyTuple_GET_ITEM(c,2),*parents=PyTuple_GET_ITEM(c,3);
 if(!PyTuple_CheckExact(models)||!PyTuple_CheckExact(ds)||PyTuple_GET_SIZE(ds)!=3||!PyTuple_CheckExact(parents)
  ||!PyType_Check(PyTuple_GET_ITEM(c,1))||!PyType_Check(PyTuple_GET_ITEM(c,4)))return 0;
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(models);i++){
  PyObject*e=PyTuple_GET_ITEM(models,i);
  if(!PyTuple_CheckExact(e)||PyTuple_GET_SIZE(e)!=6||!PyType_Check(PyTuple_GET_ITEM(e,0))||!PyUnicode_CheckExact(PyTuple_GET_ITEM(e,1)))return 0;
  for(Py_ssize_t j=2;j<6;j++){PyTypeObject*t=Py_TYPE(PyTuple_GET_ITEM(e,j));if(t!=&PyMemberDescr_Type&&t!=&PyGetSetDescr_Type)return 0;}
 }
 for(Py_ssize_t i=0;i<3;i++)if(Py_TYPE(PyTuple_GET_ITEM(ds,i))!=&PyGetSetDescr_Type)return 0;
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(parents);i++){
  PyObject*e=PyTuple_GET_ITEM(parents,i);if(!PyTuple_CheckExact(e)||PyTuple_GET_SIZE(e)!=2||!PyType_Check(PyTuple_GET_ITEM(e,0))||Py_TYPE(PyTuple_GET_ITEM(e,1))!=&PyMemberDescr_Type)return 0;
 }
 return 1;
}

static int source_add_ref(PyObject*set,Py_ssize_t ref){
 PyObject*r=PyLong_FromSsize_t(ref);if(!r)return 0;int ok=PySet_Add(set,r)==0;Py_DECREF(r);return ok;
}
static int source_mark(LiveMatch*s,Py_ssize_t ref,PyObject*seen,PyObject*shared,PyObject*shared_leaves,PyObject*virtual_containers,int depth){
 if(!source_tick(s,depth))return 0;
 PyObject*r=PyLong_FromSsize_t(ref);if(!r)return 0;int prior=PySet_Contains(seen,r);
 if(prior<0){Py_DECREF(r);return 0;}if(prior){Py_DECREF(r);return 1;}
 if(PySet_Add(seen,r)<0){Py_DECREF(r);return 0;}
 PyObject*node=PyTuple_GET_ITEM(s->nodes,ref),*value=PyTuple_GET_ITEM(node,1);Py_UCS4 tag=PyUnicode_READ_CHAR(PyTuple_GET_ITEM(node,0),0);
 if(tag=='m'||tag=='e'){Py_DECREF(r);return 0;}
 int virtual=PySet_Contains(s->virtuals,r),container=PySet_Contains(virtual_containers,r);
 if(virtual<0||container<0){Py_DECREF(r);return 0;}
 if((tag=='d'||tag=='l'||tag=='q'||tag=='r'||tag=='u')&&!container&&PySet_Add(shared,r)<0){Py_DECREF(r);return 0;}
 if((tag=='s'||tag=='b')&&!virtual&&PySet_Add(shared_leaves,r)<0){Py_DECREF(r);return 0;}
 Py_DECREF(r);
 if(tag=='d'){
  for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(value);i++){
   PyObject*pair=PyTuple_GET_ITEM(value,i);for(int j=0;j<2;j++){
    Py_ssize_t next;if(!source_index(PyTuple_GET_ITEM(pair,j),s->n,&next)||!source_mark(s,next,seen,shared,shared_leaves,virtual_containers,depth+1))return 0;
   }
  }
 }else if(tag=='l'||tag=='q'||tag=='r'){
  for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(value);i++){
   Py_ssize_t next;if(!source_index(PyTuple_GET_ITEM(value,i),s->n,&next)||!source_mark(s,next,seen,shared,shared_leaves,virtual_containers,depth+1))return 0;
  }
 }else if(tag=='u'||tag=='c'){
  Py_ssize_t next;if(!source_index(value,s->n,&next)||!source_mark(s,next,seen,shared,shared_leaves,virtual_containers,depth+1))return 0;
 }
 return 1;
}
static int source_outside(LiveMatch*s,PyObject*v,PyObject*seen,PyObject*active,PyObject*marked,PyObject*shared,PyObject*shared_leaves,PyObject*virtual_containers,int depth){
 if(!source_tick(s,depth))return 0;
 PyObject*id=PyLong_FromVoidPtr(v);if(!id)return 0;
 int ok=0;PyObject*ref=PyDict_GetItemWithError(s->reverse,id);
 if(ref){Py_ssize_t r;if(source_index(ref,s->n,&r))ok=source_mark(s,r,marked,shared,shared_leaves,virtual_containers,depth);goto done;}
 if(PyErr_Occurred())goto done;
 if(PyUnicode_CheckExact(v)||PyBytes_CheckExact(v)||PyLong_CheckExact(v)||PyFloat_CheckExact(v)||v==Py_None||v==Py_True||v==Py_False){ok=1;goto done;}
 int busy=PySet_Contains(active,id),prior=PySet_Contains(seen,id);
 if(busy!=0||prior<0)goto done;
 if(prior){ok=1;goto done;}
 if(PySet_Add(active,id)<0||!source_hold(s,v))goto done;
 if(PyDict_CheckExact(v)){
  Py_ssize_t pos=0;PyObject*k,*child;ok=1;
  while(PyDict_Next(v,&pos,&k,&child)){
   if(!PyUnicode_CheckExact(k)&&(PyObject*)Py_TYPE(k)!=PyTuple_GET_ITEM(s->config,4)){ok=0;break;}
   if(!source_outside(s,k,seen,active,marked,shared,shared_leaves,virtual_containers,depth+1)||!source_outside(s,child,seen,active,marked,shared,shared_leaves,virtual_containers,depth+1)){ok=0;break;}
  }
 }else if(PyList_CheckExact(v)||PyTuple_CheckExact(v)){
  Py_ssize_t n=PyTuple_CheckExact(v)?PyTuple_GET_SIZE(v):PyList_GET_SIZE(v);ok=1;
  for(Py_ssize_t i=0;i<n;i++)if(!source_outside(s,PyTuple_CheckExact(v)?PyTuple_GET_ITEM(v,i):PyList_GET_ITEM(v,i),seen,active,marked,shared,shared_leaves,virtual_containers,depth+1)){ok=0;break;}
 }else if((PyObject*)Py_TYPE(v)==PyTuple_GET_ITEM(s->config,1)){
  PyObject*storage=source_row(s,v);if(!storage)goto finish;
  ok=source_hold(s,storage);
  for(int i=0;ok&&i<3;i++)ok=source_outside(s,PyTuple_GET_ITEM(storage,i),seen,active,marked,shared,shared_leaves,virtual_containers,depth+1);
  Py_DECREF(storage);
 }else if((PyObject*)Py_TYPE(v)==PyTuple_GET_ITEM(s->config,4)){
  PyObject*text=PyUnicode_FromObject(v);if(!text)goto finish;
  ok=source_hold(s,text)&&source_outside(s,text,seen,active,marked,shared,shared_leaves,virtual_containers,depth+1);Py_DECREF(text);
 }else{
  PyObject*entry=PyTuple_GET_ITEM(s->config,5);
  if(PyTuple_CheckExact(entry)&&PyTuple_GET_SIZE(entry)==3&&(PyObject*)Py_TYPE(v)==PyTuple_GET_ITEM(entry,0)){
   PyObject*raw=source_get(PyTuple_GET_ITEM(entry,1),v),*names=PyTuple_GET_ITEM(entry,2);
   if(raw&&PyDict_CheckExact(raw)&&PyTuple_CheckExact(names)&&PyDict_GET_SIZE(raw)==PyTuple_GET_SIZE(names)){
    ok=1;
    for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(names);i++){
     PyObject*name=PyTuple_GET_ITEM(names,i);
     if(!PyUnicode_CheckExact(name)){ok=0;break;}
     PyObject*value=PyDict_GetItemWithError(raw,name);
     if(!value||!PyLong_CheckExact(value)||!source_outside(s,name,seen,active,marked,shared,shared_leaves,virtual_containers,depth+1)||!source_outside(s,value,seen,active,marked,shared,shared_leaves,virtual_containers,depth+1)){ok=0;break;}
    }
   }Py_XDECREF(raw);
  }
 }
 finish:
 if(PySet_Discard(active,id)<0)ok=0;
 if(ok&&PySet_Add(seen,id)<0)ok=0;
 done:Py_DECREF(id);return ok;
}
static int source_boundary(LiveMatch*s,PyObject*data,PyObject*outside){
 PyObject*seen=PySet_New(NULL),*active=PySet_New(NULL),*marked=PySet_New(NULL),*shared=PySet_New(NULL),*leaves=PySet_New(NULL);
 PyObject*containers=NULL,*expected=NULL,*expected_leaves=NULL;int ok=0;
 if(!seen||!active||!marked||!shared||!leaves)goto done;
 PyObject*virtuals=PyTuple_GET_ITEM(data,5),*leafrefs=PyTuple_GET_ITEM(data,6);
 if(!PyTuple_CheckExact(virtuals)||!PyTuple_CheckExact(leafrefs))goto done;
 containers=PySet_New(virtuals);expected_leaves=PySet_New(leafrefs);expected=PySet_New(NULL);
 if(!containers||!expected_leaves||!expected)goto done;
 for(Py_ssize_t i=0;i<s->n;i++)if(s->boundary[i]>=0&&!source_add_ref(expected,i))goto done;
 ok=source_outside(s,outside,seen,active,marked,shared,leaves,containers,0)
  &&PyObject_RichCompareBool(shared,expected,Py_EQ)==1&&PyObject_RichCompareBool(leaves,expected_leaves,Py_EQ)==1;
 done:Py_XDECREF(seen);Py_XDECREF(active);Py_XDECREF(marked);Py_XDECREF(shared);Py_XDECREF(leaves);Py_XDECREF(containers);Py_XDECREF(expected);Py_XDECREF(expected_leaves);return ok;
}
static PyObject*match_live(PyObject*self,PyObject*args){
 (void)self;source_fail_ref=-1;source_fail_line=0;PyObject*owner,*incoming,*anchors,*config,*outside=NULL;
 if(!PyArg_ParseTuple(args,"OOOO|O",&owner,&incoming,&anchors,&config,&outside))return NULL;
 if(Py_TYPE(owner)!=&OwnedType||!PyTuple_CheckExact(anchors)||!source_config(config))Py_RETURN_FALSE;
 PyObject*data=((Owned*)owner)->data;
 if(PyTuple_GET_SIZE(data)!=8)Py_RETURN_FALSE;
 LiveMatch s={0};s.nodes=PyTuple_GET_ITEM(data,1);s.leaves=PyTuple_GET_ITEM(data,2);s.anchors=anchors;s.config=config;
 if(!PyTuple_CheckExact(s.nodes)||!PyTuple_CheckExact(s.leaves))Py_RETURN_FALSE;
 s.n=PyTuple_GET_SIZE(s.nodes);if(s.n<=0||s.n>100000)Py_RETURN_FALSE;
 /* Tracked temporary allocations must not run gc.callbacks/finalizers while
  * reading live data. Restore the caller's exact automatic-GC state at done.
  * No Python callbacks, signal checks or GIL release occur in this interval. */
 int gc_was_enabled=PyGC_Disable();source_in_match=1;
 s.status=PyMem_Calloc(s.n,sizeof(unsigned char));
 s.forward=PyMem_Calloc(s.n,sizeof(PyObject*));s.boundary=PyMem_Malloc(s.n*sizeof(Py_ssize_t));s.model_kinds=PyMem_Malloc(s.n*sizeof(Py_ssize_t));
 s.reverse=PyDict_New();s.held=PyList_New(0);s.virtuals=NULL;int ok=0;
 if(!s.status||!s.forward||!s.boundary||!s.model_kinds||!s.reverse||!s.held)goto done;
 for(Py_ssize_t i=0;i<s.n;i++){s.boundary[i]=-1;s.model_kinds[i]=-1;}
 PyObject*model_kinds=PyTuple_GET_ITEM(data,7);if(!PyTuple_CheckExact(model_kinds))goto done;
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(model_kinds);i++){
  PyObject*entry=PyTuple_GET_ITEM(model_kinds,i);Py_ssize_t ref,ordinal;
  if(!PyTuple_CheckExact(entry)||PyTuple_GET_SIZE(entry)!=2||!source_index(PyTuple_GET_ITEM(entry,0),s.n,&ref)||!source_index(PyTuple_GET_ITEM(entry,1),PyTuple_GET_SIZE(PyTuple_GET_ITEM(config,0)),&ordinal)||s.model_kinds[ref]>=0)goto done;
  s.model_kinds[ref]=ordinal;
 }
 PyObject*virtuals=PyTuple_GET_ITEM(data,4),*boundary=PyTuple_GET_ITEM(data,3);
 if(!PyTuple_CheckExact(virtuals)||!PyTuple_CheckExact(boundary)||PyTuple_GET_SIZE(boundary)!=PyTuple_GET_SIZE(anchors))goto done;
 s.virtuals=PySet_New(virtuals);if(!s.virtuals)goto done;
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(boundary);i++){
  PyObject*pair=PyTuple_GET_ITEM(boundary,i);Py_ssize_t ref,ordinal;
  if(!PyTuple_CheckExact(pair)||PyTuple_GET_SIZE(pair)!=2||!source_index(PyTuple_GET_ITEM(pair,0),s.n,&ref)||!source_index(PyTuple_GET_ITEM(pair,1),PyTuple_GET_SIZE(anchors),&ordinal)||ordinal!=i||s.boundary[ref]>=0)goto done;
  s.boundary[ref]=ordinal;
 }
 Py_ssize_t root;if(!source_index(PyTuple_GET_ITEM(data,0),s.n,&root))goto done;
 ok=source_match(&s,root,incoming,0);
 if(ok)for(Py_ssize_t i=0;i<s.n;i++)if(s.status[i]!=2){ok=0;break;}
 if(ok&&outside)ok=source_boundary(&s,data,outside);
 done:PyMem_Free(s.status);PyMem_Free(s.forward);PyMem_Free(s.boundary);PyMem_Free(s.model_kinds);Py_XDECREF(s.reverse);Py_XDECREF(s.held);Py_XDECREF(s.virtuals);
 source_in_match=0;if(gc_was_enabled)PyGC_Enable();
 if(PyErr_Occurred())return NULL;
 return PyBool_FromLong(ok);
}
