#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <marshal.h>
#include <stdint.h>
#if defined(Py_GIL_DISABLED) && Py_GIL_DISABLED
#error "This uninstalled live matcher requires the CPython GIL"
#endif
/* Prototype immutable parsed data owner. No model/row/permission object may
 * enter data. Wire metadata is derived here, never supplied by a caller. */
typedef struct {PyObject_HEAD PyObject *data,*pin,*parents,*contract_models,*dump_refs,*contract_json,*contract_fp,*contract_origin,*contract_config,*dump_models;Py_ssize_t contract_ref,dump_ref;unsigned int depth;} Owned;
static PyTypeObject OwnedType;
typedef struct {PyObject_HEAD Owned*owner;Py_ssize_t ref;} SourceView;
static PyTypeObject SourceViewType;
static PyObject *unsupported;
static PyObject *contract_models;
static PyObject *contract_sha;
static PyObject *contract_schemas,*contract_classes,*contract_schema_leaves;
static PyTypeObject *contract_validator_type,*contract_serializer_type;
static PyObject *contract_binding_type,*contract_binding_code,*contract_binding_globals,*contract_binding_version,*contract_binding_keys,*contract_bindings;
static int contract_schemas_current_internal(void);
static int contract_config_current(PyObject*config);
static int immutable(PyObject*v,size_t*work,size_t*bytes,int depth){
 if(++*work>1000000||depth>64)return 0;
 if(PyTuple_CheckExact(v)){
  Py_ssize_t n=PyTuple_GET_SIZE(v);
  if((size_t)n>1000000-*work)return 0;
  for(Py_ssize_t i=0;i<n;i++){int ok=immutable(PyTuple_GET_ITEM(v,i),work,bytes,depth+1);if(ok<=0)return ok;}
  return 1;
 }
 if(PyUnicode_CheckExact(v)){
  Py_ssize_t n=PyUnicode_GET_LENGTH(v);
  if(n>16*1024*1024/4||(size_t)n*4>16*1024*1024-*bytes)return 0;
  *bytes+=(size_t)n*4;return 1;
 }
 if(PyBytes_CheckExact(v)){
  Py_ssize_t n=PyBytes_GET_SIZE(v);
  if((size_t)n>16*1024*1024-*bytes)return 0;
  *bytes+=(size_t)n;return 1;
 }
 if(v==Py_None||v==Py_True||v==Py_False)return 1;
 if(PyLong_CheckExact(v)){
  int overflow=0;PyLong_AsLongLongAndOverflow(v,&overflow);
  if(PyErr_Occurred())return -1;
  return !overflow;
 }
 return 0;
}
static void owned_free(PyObject*v){
 Owned*o=(Owned*)v;PyObject*error=PyErr_GetRaisedException();
 Py_XDECREF(o->data);Py_XDECREF(o->pin);Py_XDECREF(o->parents);Py_XDECREF(o->contract_models);Py_XDECREF(o->dump_refs);Py_XDECREF(o->contract_json);Py_XDECREF(o->contract_fp);Py_XDECREF(o->contract_origin);Py_XDECREF(o->contract_config);Py_XDECREF(o->dump_models);Py_TYPE(v)->tp_free(v);
 if(error)PyErr_SetRaisedException(error);
}
static PyObject*no_new(PyTypeObject*t,PyObject*a,PyObject*k){
 (void)t;(void)a;(void)k;PyErr_SetString(PyExc_TypeError,"Owned facts require their bounded factory");return NULL;
}
static PyTypeObject OwnedType={PyVarObject_HEAD_INIT(NULL,0)
 .tp_name="_cold_source_owned_impl.Owned",.tp_basicsize=sizeof(Owned),
 .tp_flags=Py_TPFLAGS_DEFAULT|Py_TPFLAGS_IMMUTABLETYPE,.tp_new=no_new,.tp_dealloc=owned_free};
#include "_cold_source_shape.h"
static PyObject*make_owned_domain(PyObject*data,PyObject*parents,PyObject*contract_models){
 if(!PyTuple_CheckExact(parents)||PyTuple_GET_SIZE(parents)>256)return Py_NewRef(unsupported);
 unsigned int depth=1;
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(parents);i++){
  PyObject*p=PyTuple_GET_ITEM(parents,i);
  if(Py_TYPE(p)!=&OwnedType||((Owned*)p)->depth>=64)return Py_NewRef(unsupported);
  if(((Owned*)p)->depth+1>depth)depth=((Owned*)p)->depth+1;
  for(Py_ssize_t j=0;j<i;j++)if(PyTuple_GET_ITEM(parents,j)==p)return Py_NewRef(unsupported);
 }
 if(!PyTuple_CheckExact(data)||PyTuple_GET_SIZE(data)!=8)return Py_NewRef(unsupported);
 PyObject*leaves=PyTuple_GET_ITEM(data,2);
 if(!PyTuple_CheckExact(leaves))return Py_NewRef(unsupported);
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(leaves);i++){
  PyObject*v=PyTuple_GET_ITEM(leaves,i);
  if(!PyUnicode_CheckExact(v)&&!PyBytes_CheckExact(v))return Py_NewRef(unsupported);
 }
 size_t work=0,bytes=0;int ok=immutable(data,&work,&bytes,0);
 if(ok<0)return NULL;
 if(!ok)return Py_NewRef(unsupported);
 if(!source_image_shape(data,contract_models?PyTuple_GET_SIZE(contract_models):17))return Py_NewRef(unsupported);
 PyObject*nodes=PyTuple_GET_ITEM(data,1);
 unsigned char used_parents[256]={0};
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(nodes);i++){
  PyObject*node=PyTuple_GET_ITEM(nodes,i);
  /* PB owns only its complete model/JSON family. SQL rows, quoted names
   * and parent-owner bridges belong to their original separate protocols. */
  Py_UCS4 tag=PyUnicode_READ_CHAR(PyTuple_GET_ITEM(node,0),0);
  if(contract_models&&(tag=='r'||tag=='u'||tag=='o'||tag=='a'))return Py_NewRef(unsupported);
  if(PyUnicode_READ_CHAR(PyTuple_GET_ITEM(node,0),0)=='o'){
   PyObject*p=PyTuple_GET_ITEM(node,1);Py_ssize_t ordinal,ref;
   if(!shape_ref(PyTuple_GET_ITEM(p,0),PyTuple_GET_SIZE(parents),&ordinal))return Py_NewRef(unsupported);
   used_parents[ordinal]=1;
   Owned*parent=(Owned*)PyTuple_GET_ITEM(parents,ordinal);
   if(!shape_ref(PyTuple_GET_ITEM(p,1),PyTuple_GET_SIZE(PyTuple_GET_ITEM(parent->data,1)),&ref))return Py_NewRef(unsupported);
  }
 }
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(parents);i++)if(!used_parents[i])return Py_NewRef(unsupported);
 /* All data are now exact immutable builtins. Marshal writes only metadata;
  * original leaves remain the exact original objects in the full graph pin. */
 Py_ssize_t n=PyTuple_GET_SIZE(data);PyObject*metadata=PyTuple_New(n-1);
 if(metadata){Py_ssize_t j=0;for(Py_ssize_t i=0;i<n;i++)if(i!=2)PyTuple_SET_ITEM(metadata,j++,Py_NewRef(PyTuple_GET_ITEM(data,i)));}
 if(!metadata)return NULL;
 PyObject*wire=PyMarshal_WriteObjectToString(metadata,4);Py_DECREF(metadata);
 if(!wire)return NULL;
 if(PyBytes_GET_SIZE(wire)>16*1024*1024){Py_DECREF(wire);return Py_NewRef(unsupported);}
 PyObject*parent_pins=PyTuple_New(PyTuple_GET_SIZE(parents));
 if(!parent_pins){Py_DECREF(wire);return NULL;}
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(parents);i++)PyTuple_SET_ITEM(parent_pins,i,Py_NewRef(((Owned*)PyTuple_GET_ITEM(parents,i))->pin));
 PyObject*pin=PyTuple_GET_SIZE(parents)?PyTuple_Pack(3,wire,leaves,parent_pins):PyTuple_Pack(2,wire,leaves);
 Py_DECREF(parent_pins);Py_DECREF(wire);if(!pin)return NULL;
 Owned*o=PyObject_New(Owned,&OwnedType);if(!o){Py_DECREF(pin);return NULL;}
 o->data=Py_NewRef(data);o->pin=pin;o->parents=Py_NewRef(parents);o->depth=depth;
 o->contract_models=Py_XNewRef(contract_models);o->dump_refs=o->contract_json=o->contract_fp=o->contract_origin=o->contract_config=o->dump_models=NULL;o->contract_ref=o->dump_ref=-1;return (PyObject*)o;
}
static PyObject*make_owned_core(PyObject*data,PyObject*parents){return make_owned_domain(data,parents,NULL);}
static PyObject*make_owned(PyObject*self,PyObject*data){
 (void)self;PyObject*parents=PyTuple_New(0);if(!parents)return NULL;
 PyObject*r=make_owned_core(data,parents);Py_DECREF(parents);return r;
}
static PyObject*make_composite(PyObject*self,PyObject*args){
 (void)self;PyObject*data,*parents;if(!PyArg_ParseTuple(args,"OO",&data,&parents))return NULL;
 return make_owned_core(data,parents);
}
static PyObject*owned_data(PyObject*self,PyObject*v){
 (void)self;if(Py_TYPE(v)!=&OwnedType){PyErr_SetString(PyExc_TypeError,"Exact immutable owner required");return NULL;}
 return Py_NewRef(((Owned*)v)->data);
}
static PyObject*owned_pin(PyObject*self,PyObject*v){
 (void)self;if(Py_TYPE(v)!=&OwnedType){PyErr_SetString(PyExc_TypeError,"Exact immutable owner required");return NULL;}
 return Py_NewRef(((Owned*)v)->pin);
}
typedef struct {PyObject_HEAD PyObject *owner,*nonce,*phase,*anchors,*scope,*pin;uint64_t epoch;} Binding;
static PyTypeObject BindingType;
static uint64_t binding_serial=0;
static int binding_traverse(PyObject*v,visitproc visit,void*arg){
 Binding*b=(Binding*)v;Py_VISIT(b->owner);Py_VISIT(b->nonce);Py_VISIT(b->phase);Py_VISIT(b->anchors);Py_VISIT(b->scope);Py_VISIT(b->pin);return 0;
}
static int binding_clear(PyObject*v){
 Binding*b=(Binding*)v;Py_CLEAR(b->owner);Py_CLEAR(b->nonce);Py_CLEAR(b->phase);Py_CLEAR(b->anchors);Py_CLEAR(b->scope);Py_CLEAR(b->pin);return 0;
}
static void binding_free(PyObject*v){
 PyObject*error=PyErr_GetRaisedException();PyObject_GC_UnTrack(v);binding_clear(v);PyObject_GC_Del(v);if(error)PyErr_SetRaisedException(error);
}
static PyTypeObject BindingType={PyVarObject_HEAD_INIT(NULL,0)
 .tp_name="_cold_source_owned_impl.Binding",.tp_basicsize=sizeof(Binding),
 .tp_flags=Py_TPFLAGS_DEFAULT|Py_TPFLAGS_IMMUTABLETYPE|Py_TPFLAGS_HAVE_GC,
 .tp_new=no_new,.tp_dealloc=binding_free,.tp_traverse=binding_traverse,.tp_clear=binding_clear,.tp_free=PyObject_GC_Del};
static PyObject*make_binding(PyObject*self,PyObject*args){
 (void)self;PyObject*owner,*nonce,*epoch,*phase,*anchors,*scope;
 if(!PyArg_ParseTuple(args,"OOOOOO",&owner,&nonce,&epoch,&phase,&anchors,&scope))return NULL;
 if(Py_TYPE(owner)!=&OwnedType||Py_TYPE(nonce)!=&PyBaseObject_Type||!PyLong_CheckExact(epoch)
  ||!PyUnicode_CheckExact(phase)||!PyTuple_CheckExact(anchors)||!PyTuple_CheckExact(scope)||PyTuple_GET_SIZE(scope)!=7)return Py_NewRef(unsupported);
 unsigned long long e=PyLong_AsUnsignedLongLong(epoch);if(PyErr_Occurred())return NULL;
 if(PyUnicode_CompareWithASCIIString(phase,"post")!=0&&PyUnicode_CompareWithASCIIString(phase,"pre")!=0)return Py_NewRef(unsupported);
 if(binding_serial>=INT64_MAX){PyErr_SetString(PyExc_RuntimeError,"Binding identity exhausted");return NULL;}
 PyObject*serial=PyLong_FromUnsignedLongLong(++binding_serial);if(!serial)return NULL;
 PyObject*pin=PyTuple_Pack(3,serial,owner,anchors);Py_DECREF(serial);if(!pin)return NULL;
 Binding*b=PyObject_GC_New(Binding,&BindingType);if(!b){Py_DECREF(pin);return NULL;}
 b->owner=Py_NewRef(owner);b->nonce=Py_NewRef(nonce);b->phase=Py_NewRef(phase);b->anchors=Py_NewRef(anchors);b->scope=Py_NewRef(scope);b->pin=pin;b->epoch=e;
 PyObject_GC_Track(b);return (PyObject*)b;
}
static PyObject*binding_current(PyObject*self,PyObject*args){
 (void)self;PyObject*v,*owner,*nonce,*epoch,*phase,*scope;
 if(!PyArg_ParseTuple(args,"OOOOOO",&v,&owner,&nonce,&epoch,&phase,&scope))return NULL;
 if(Py_TYPE(v)!=&BindingType||!PyLong_CheckExact(epoch)||!PyUnicode_CheckExact(phase)||!PyTuple_CheckExact(scope)||PyTuple_GET_SIZE(scope)!=7)Py_RETURN_FALSE;
 Binding*b=(Binding*)v;if(!b->owner||!b->nonce||!b->phase||!b->anchors||!b->scope||!b->pin)Py_RETURN_FALSE;
 unsigned long long e=PyLong_AsUnsignedLongLong(epoch);if(PyErr_Occurred())return NULL;
 for(int i=0;i<7;i++)if(PyTuple_GET_ITEM(b->scope,i)!=PyTuple_GET_ITEM(scope,i))Py_RETURN_FALSE;
 return PyBool_FromLong(b->owner==owner&&b->nonce==nonce&&b->epoch==e&&PyUnicode_Compare(b->phase,phase)==0);
}
static PyObject*binding_pin(PyObject*self,PyObject*v){
 (void)self;if(Py_TYPE(v)!=&BindingType||!((Binding*)v)->pin){PyErr_SetString(PyExc_TypeError,"Live exact source binding required");return NULL;}
 return Py_NewRef(((Binding*)v)->pin);
}
#include "_cold_source_live_match.h"
static PyObject*binding_owner(PyObject*self,PyObject*v){
 (void)self;if(Py_TYPE(v)!=&BindingType||!((Binding*)v)->owner){PyErr_SetString(PyExc_TypeError,"Live exact binding required");return NULL;}return Py_NewRef(((Binding*)v)->owner);
}
#include "_cold_source_code.h"
#include "_cold_source_view.h"
static PyObject*register_contract_models(PyObject*self,PyObject*args){
 (void)self;PyObject*models,*sha;if(!PyArg_ParseTuple(args,"OO",&models,&sha))return NULL;
 if(contract_models||!PyTuple_CheckExact(models)||PyTuple_GET_SIZE(models)!=27||!PyCFunction_Check(sha)){PyErr_SetString(PyExc_ValueError,"PB model domain is complete and registered once");return NULL;}
 for(Py_ssize_t i=0;i<27;i++)if(!PyType_Check(PyTuple_GET_ITEM(models,i))){PyErr_SetString(PyExc_TypeError,"Exact PB model classes required");return NULL;}
 contract_models=Py_NewRef(models);contract_sha=Py_NewRef(sha);Py_RETURN_NONE;
}
static PyObject*contract_node(Owned*o,Py_ssize_t ref){return PyTuple_GET_ITEM(PyTuple_GET_ITEM(o->data,1),ref);}
static PyObject*contract_text(Owned*o,PyObject*ref){
 PyObject*n=contract_node(o,PyLong_AsSsize_t(ref));
 if(PyUnicode_READ_CHAR(PyTuple_GET_ITEM(n,0),0)!='s')return NULL;
 return PyTuple_GET_ITEM(PyTuple_GET_ITEM(o->data,2),PyLong_AsSsize_t(PyTuple_GET_ITEM(n,1)));
}
/* Derive every nested model's canonical output FROM THE ROOT model/dump
 * pairing. A caller cannot nominate an equal-valued subtree with different
 * identities. Model raw field order remains captured independently; the
 * canonical serializer's field order is retained by its original dump tree. */
static int contract_pair_map(Owned*o,Py_ssize_t actual,Py_ssize_t raw,int depth,size_t*work,int model_fields){
 if(++*work>1000000||depth>64)return 0;
 PyObject*a=contract_node(o,actual),*b=contract_node(o,raw),*ap=PyTuple_GET_ITEM(a,1),*bp=PyTuple_GET_ITEM(b,1);
 Py_UCS4 at=PyUnicode_READ_CHAR(PyTuple_GET_ITEM(a,0),0),bt=PyUnicode_READ_CHAR(PyTuple_GET_ITEM(b,0),0);
 if(at=='m'){
  if(bt!='d')return 0;
  PyObject*prior=PyTuple_GET_ITEM(o->dump_models,raw);PyTuple_SET_ITEM(o->dump_models,raw,Py_NewRef(Py_True));Py_DECREF(prior);
  if(!PyTuple_GET_ITEM(o->dump_refs,actual)){
   PyObject*r=PyLong_FromSsize_t(raw);if(!r)return -1;PyTuple_SET_ITEM(o->dump_refs,actual,r);
  }
  return contract_pair_map(o,PyLong_AsSsize_t(PyTuple_GET_ITEM(ap,1)),raw,depth+1,work,1);
 }
 if(at!=bt)return 0;
 if(at=='d'){
  Py_ssize_t count=PyTuple_GET_SIZE(ap);if(PyTuple_GET_SIZE(bp)!=count)return 0;
  for(Py_ssize_t i=0;i<count;i++){
   PyObject*pair=PyTuple_GET_ITEM(ap,i),*wanted=contract_text(o,PyTuple_GET_ITEM(pair,0)),*found=NULL;
   if(!wanted)return 0;
   for(Py_ssize_t j=0;j<count;j++){
    if(!model_fields&&i!=j)continue;
    PyObject*candidate=PyTuple_GET_ITEM(bp,j),*key=contract_text(o,PyTuple_GET_ITEM(candidate,0));
    if(!key)return 0;if(PyUnicode_Compare(wanted,key)==0){found=candidate;break;}
   }
   if(!found)return 0;
   int ok=contract_pair_map(o,PyLong_AsSsize_t(PyTuple_GET_ITEM(pair,1)),PyLong_AsSsize_t(PyTuple_GET_ITEM(found,1)),depth+1,work,0);if(ok<=0)return ok;
  }
  return 1;
 }
 if(at=='l'||at=='q'){
  if(PyTuple_GET_SIZE(ap)!=PyTuple_GET_SIZE(bp))return 0;
  for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(ap);i++){
   int ok=contract_pair_map(o,PyLong_AsSsize_t(PyTuple_GET_ITEM(ap,i)),PyLong_AsSsize_t(PyTuple_GET_ITEM(bp,i)),depth+1,work,0);if(ok<=0)return ok;
  }
  return 1;
 }
 if(at=='s'||at=='b'){
  PyObject*leaves=PyTuple_GET_ITEM(o->data,2);return PyObject_RichCompareBool(PyTuple_GET_ITEM(leaves,PyLong_AsSsize_t(ap)),PyTuple_GET_ITEM(leaves,PyLong_AsSsize_t(bp)),Py_EQ);
 }
 if(at=='n'||at=='t'||at=='f')return 1;
 if(at=='i'||at=='v')return PyObject_RichCompareBool(ap,bp,Py_EQ);
 return 0;
}
/* Original fingerprint JSON, directly from deeply immutable canonical data.
 * No mutable export or Python encoder callback can be changed and restored
 * around hashing. This is a DATA digest only, never an approval or permit. */
typedef struct {char*data;size_t size,capacity,work;} ContractJSON;
static int contract_append(ContractJSON*w,const char*data,size_t count){
 if(count>16*1024*1024-w->size)return 0;
 size_t wanted=w->size+count;
 if(wanted>w->capacity){size_t capacity=w->capacity?w->capacity:1024;while(capacity<wanted)capacity*=2;
  char*next=PyMem_Realloc(w->data,capacity);if(!next){PyErr_NoMemory();return -1;}w->data=next;w->capacity=capacity;}
 memcpy(w->data+w->size,data,count);w->size=wanted;return 1;
}
static int contract_string(ContractJSON*w,PyObject*text){
 Py_ssize_t size;const char*data=PyUnicode_AsUTF8AndSize(text,&size);if(!data)return -1;
 int ok=contract_append(w,"\"",1);if(ok<=0)return ok;
 static const char*hex="0123456789abcdef";
 for(Py_ssize_t i=0;i<size;i++){
  unsigned char c=(unsigned char)data[i];const char*escape=NULL;
  switch(c){case '"':escape="\\\"";break;case '\\':escape="\\\\";break;case '\b':escape="\\b";break;case '\f':escape="\\f";break;case '\n':escape="\\n";break;case '\r':escape="\\r";break;case '\t':escape="\\t";break;}
  if(escape)ok=contract_append(w,escape,2);
  else if(c<32){char value[6]={'\\','u','0','0',hex[c>>4],hex[c&15]};ok=contract_append(w,value,6);}
  else ok=contract_append(w,data+i,1);
  if(ok<=0)return ok;
 }
 return contract_append(w,"\"",1);
}
typedef struct {PyObject*key;Py_ssize_t value;} ContractKey;
static int contract_key_order(const void*a,const void*b){return PyUnicode_Compare(((const ContractKey*)a)->key,((const ContractKey*)b)->key);}
static int contract_json_write(Owned*o,Py_ssize_t ref,ContractJSON*w,int depth){
 if(++w->work>1000000||depth>64)return 0;
 PyObject*node=contract_node(o,ref),*p=PyTuple_GET_ITEM(node,1);Py_UCS4 tag=PyUnicode_READ_CHAR(PyTuple_GET_ITEM(node,0),0);int ok;
 if(tag=='n')return contract_append(w,"null",4);if(tag=='t')return contract_append(w,"true",4);if(tag=='f')return contract_append(w,"false",5);
 if(tag=='s')return contract_string(w,PyTuple_GET_ITEM(PyTuple_GET_ITEM(o->data,2),PyLong_AsSsize_t(p)));
 if(tag=='i'){
  PyObject*text=PyObject_Str(p);if(!text)return -1;Py_ssize_t size;const char*value=PyUnicode_AsUTF8AndSize(text,&size);ok=value?contract_append(w,value,(size_t)size):-1;Py_DECREF(text);return ok;
 }
 if(tag=='v'){
  double value=PyFloat_Unpack8(PyBytes_AS_STRING(p),0);if(PyErr_Occurred())return -1;
  if(!Py_IS_FINITE(value)){PyErr_SetString(PyExc_ValueError,"Nonfinite PB JSON number");return -1;}
  char*text=PyOS_double_to_string(value,'r',0,Py_DTSF_ADD_DOT_0,NULL);if(!text)return -1;
  ok=contract_append(w,text,strlen(text));PyMem_Free(text);return ok;
 }
 if(tag=='d'){
  Py_ssize_t count=PyTuple_GET_SIZE(p);ContractKey*keys=PyMem_Malloc((count?count:1)*sizeof(ContractKey));if(!keys){PyErr_NoMemory();return -1;}
  for(Py_ssize_t i=0;i<count;i++){
   PyObject*pair=PyTuple_GET_ITEM(p,i),*key=contract_text(o,PyTuple_GET_ITEM(pair,0));if(!key){PyMem_Free(keys);return 0;}
   keys[i]=(ContractKey){key,PyLong_AsSsize_t(PyTuple_GET_ITEM(pair,1))};
  }
  qsort(keys,(size_t)count,sizeof(ContractKey),contract_key_order);
  ok=contract_append(w,"{",1);
  for(Py_ssize_t i=0;ok>0&&i<count;i++){
   if(i)ok=contract_append(w,",",1);if(ok>0)ok=contract_string(w,keys[i].key);
   if(ok>0)ok=contract_append(w,":",1);if(ok>0)ok=contract_json_write(o,keys[i].value,w,depth+1);
  }
  PyMem_Free(keys);return ok>0?contract_append(w,"}",1):ok;
 }
 if(tag=='l'||tag=='q'){
  ok=contract_append(w,"[",1);for(Py_ssize_t i=0;ok>0&&i<PyTuple_GET_SIZE(p);i++){
   if(i)ok=contract_append(w,",",1);if(ok>0)ok=contract_json_write(o,PyLong_AsSsize_t(PyTuple_GET_ITEM(p,i)),w,depth+1);
  }
  return ok>0?contract_append(w,"]",1):ok;
 }
 return 0;
}
/* First-producer handoff only. The caller has performed the original semantic
 * validation. This final atomic read proves the COMPLETE current model+dump,
 * type/order/alias/hidden fields against the immutable image before retiring
 * the mutable model. No Graph/permission/transaction result enters the Owner. */
static PyObject*make_contract_owned(PyObject*self,PyObject*args){
 (void)self;PyObject*data,*current,*config;
 if(!PyArg_ParseTuple(args,"OOO",&data,&current,&config))return NULL;
 if(!contract_models||!source_config(config)||!PyTuple_CheckExact(current)||PyTuple_GET_SIZE(current)!=2)return Py_NewRef(unsupported);
 PyObject*models=PyTuple_GET_ITEM(config,0);if(PyTuple_GET_SIZE(models)!=27)return Py_NewRef(unsupported);
 for(Py_ssize_t i=0;i<27;i++)if(PyTuple_GET_ITEM(PyTuple_GET_ITEM(models,i),0)!=PyTuple_GET_ITEM(contract_models,i))return Py_NewRef(unsupported);
 if((PyObject*)Py_TYPE(PyTuple_GET_ITEM(current,0))!=PyTuple_GET_ITEM(contract_models,17)||!PyDict_CheckExact(PyTuple_GET_ITEM(current,1)))return Py_NewRef(unsupported);
 PyObject*empty=PyTuple_New(0);if(!empty)return NULL;
 PyObject*owner=make_owned_domain(data,empty,contract_models);if(!owner||owner==unsupported){Py_DECREF(empty);return owner;}
 Owned*o=(Owned*)owner;PyObject*nodes=PyTuple_GET_ITEM(o->data,1);Py_ssize_t root=PyLong_AsSsize_t(PyTuple_GET_ITEM(data,0));
 o->contract_origin=PyWeakref_NewRef(PyTuple_GET_ITEM(current,0),NULL);if(!o->contract_origin)goto error;
 o->contract_config=Py_NewRef(config);
 PyObject*node=PyTuple_GET_ITEM(nodes,root),*refs=PyTuple_GET_ITEM(node,1);
 if(PyUnicode_READ_CHAR(PyTuple_GET_ITEM(node,0),0)!='q'||!PyTuple_CheckExact(refs)||PyTuple_GET_SIZE(refs)!=2)goto refuse;
 o->contract_ref=PyLong_AsSsize_t(PyTuple_GET_ITEM(refs,0));o->dump_ref=PyLong_AsSsize_t(PyTuple_GET_ITEM(refs,1));
 if(PyErr_Occurred())goto error;
 if(shape_tag(nodes,PyTuple_GET_ITEM(refs,0))!='m'||shape_tag(nodes,PyTuple_GET_ITEM(refs,1))!='d')goto refuse;
 o->dump_refs=PyTuple_New(PyTuple_GET_SIZE(nodes));if(!o->dump_refs)goto error;
 o->dump_models=PyTuple_New(PyTuple_GET_SIZE(nodes));if(!o->dump_models)goto error;
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(nodes);i++)PyTuple_SET_ITEM(o->dump_models,i,Py_NewRef(Py_False));
 size_t work=0;int mapped=contract_pair_map(o,o->contract_ref,o->dump_ref,0,&work,0);
 if(mapped<0)goto error;if(!mapped)goto refuse;
 PyObject*catalog=PyTuple_GET_ITEM(o->data,7);
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(catalog);i++)if(!PyTuple_GET_ITEM(o->dump_refs,PyLong_AsSsize_t(PyTuple_GET_ITEM(PyTuple_GET_ITEM(catalog,i),0))))goto refuse;
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(nodes);i++)if(!PyTuple_GET_ITEM(o->dump_refs,i))PyTuple_SET_ITEM(o->dump_refs,i,Py_NewRef(Py_None));
 ContractJSON wire={0};int encoded=contract_json_write(o,o->dump_ref,&wire,0);
 if(encoded>0)o->contract_json=PyBytes_FromStringAndSize(wire.data,(Py_ssize_t)wire.size);PyMem_Free(wire.data);
 if(encoded<0||encoded>0&&!o->contract_json)goto error;if(!encoded)goto refuse;
 PyObject*hash=PyObject_CallOneArg(contract_sha,o->contract_json);if(!hash)goto error;
 o->contract_fp=PyObject_CallMethod(hash,"hexdigest",NULL);Py_DECREF(hash);if(!o->contract_fp)goto error;
 if(!PyUnicode_CheckExact(o->contract_fp)||PyUnicode_GET_LENGTH(o->contract_fp)!=64)goto refuse;
 /* Hashing can release the GIL. Nothing from the early Python eligibility
  * check is treated as a late qualification. Both complete code families and
  * the entire original schema configuration are freshly reread here. */
 PyObject*code=verify_code_range(0,10);if(!code)goto error;
 int qualified=code==Py_True;Py_DECREF(code);
 if(!qualified||!contract_schemas_current_internal()||!contract_config_current(config)){if(PyErr_Occurred())goto error;goto refuse;}
 PyObject*match=source_match_current(owner,current,empty,config,empty,NULL);if(!match)goto error;
 int ok=match==Py_True;Py_DECREF(match);if(!ok)goto refuse;
 Py_DECREF(empty);PyObject*view=view_read(o,o->contract_ref);Py_DECREF(owner);return view;
 refuse:Py_DECREF(empty);Py_DECREF(owner);return Py_NewRef(unsupported);
 error:Py_DECREF(empty);Py_DECREF(owner);return NULL;
}
static PyObject*contract_model(PyObject*self,PyObject*value){
 (void)self;if(Py_TYPE(value)!=&SourceViewType)Py_RETURN_NONE;
 SourceView*v=(SourceView*)value;if(!v->owner->contract_models)Py_RETURN_NONE;
 Py_UCS4 tag;PyObject*p;if(!view_node(v,&tag,&p)||tag!='m')Py_RETURN_NONE;
 PyObject*catalog=PyTuple_GET_ITEM(v->owner->data,7);
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(catalog);i++){
  PyObject*row=PyTuple_GET_ITEM(catalog,i);
  if(PyLong_AsSsize_t(PyTuple_GET_ITEM(row,0))==v->ref){Py_ssize_t index=PyLong_AsSsize_t(PyTuple_GET_ITEM(row,1));if(PyErr_Occurred())return NULL;return Py_NewRef(PyTuple_GET_ITEM(v->owner->contract_models,index));}
 }
 Py_RETURN_NONE;
}
static PyObject*contract_fingerprint(PyObject*self,PyObject*value){
 (void)self;if(Py_TYPE(value)!=&SourceViewType)return view_error();SourceView*v=(SourceView*)value;
 if(!v->owner->contract_models||v->ref!=v->owner->contract_ref||!v->owner->contract_fp)return view_error();return Py_NewRef(v->owner->contract_fp);
}
static PyObject*contract_json(PyObject*self,PyObject*value){
 (void)self;if(Py_TYPE(value)!=&SourceViewType)return view_error();SourceView*v=(SourceView*)value;
 if(!v->owner->contract_models||v->ref!=v->owner->contract_ref||!v->owner->contract_json)return view_error();return Py_NewRef(v->owner->contract_json);
}
static PyObject*contract_dump(PyObject*self,PyObject*value){
 (void)self;if(Py_TYPE(value)!=&SourceViewType)return view_error();SourceView*v=(SourceView*)value;
 if(!v->owner->contract_models||!v->owner->dump_refs)return view_error();
 PyObject*ref=PyTuple_GET_ITEM(v->owner->dump_refs,v->ref);
 if(!PyLong_CheckExact(ref))return view_error();
 return view_read(v->owner,PyLong_AsSsize_t(ref));
}
/* The original _schema_shape grammar, checked with no Python callbacks,
 * tracked allocations, getters, user equality, or previous PASS. */
static int contract_schema_match(PyObject*v,PyObject*shape,PyObject**active,int depth,size_t*work){
 if(++*work>1000000||depth>64||!PyTuple_CheckExact(shape)||PyTuple_GET_SIZE(shape)!=2)return 0;
 PyObject*label=PyTuple_GET_ITEM(shape,0),*expected=PyTuple_GET_ITEM(shape,1);if(!PyUnicode_CheckExact(label))return 0;
 if(PyUnicode_CompareWithASCIIString(label,"code-object")==0){
  if(!PyLong_CheckExact(expected))return 0;void*pointer=PyLong_AsVoidPtr(expected);return !PyErr_Occurred()&&pointer==(void*)v;
 }
 const char*name=v==Py_None?"NoneType":PyBool_Check(v)?"bool":PyLong_CheckExact(v)?"int":PyFloat_CheckExact(v)?"float":PyUnicode_CheckExact(v)?"str":PyDict_CheckExact(v)?"dict":PyList_CheckExact(v)?"list":PyTuple_CheckExact(v)?"tuple":NULL;
 if(!name||PyUnicode_CompareWithASCIIString(label,name)!=0)return 0;
 if(v==Py_None||PyBool_Check(v))return v==expected;
 if(PyLong_CheckExact(v))return PyLong_CheckExact(expected)&&PyObject_RichCompareBool(v,expected,Py_EQ)==1;
 if(PyFloat_CheckExact(v))return PyFloat_CheckExact(expected)&&(v==expected||PyFloat_AS_DOUBLE(v)==PyFloat_AS_DOUBLE(expected));
 if(PyUnicode_CheckExact(v))return PyUnicode_CheckExact(expected)&&PyUnicode_Compare(v,expected)==0;
 if(!PyTuple_CheckExact(expected))return 0;
 for(int i=0;i<depth;i++)if(active[i]==v)return 0;active[depth]=v;
 Py_ssize_t count=PyTuple_GET_SIZE(expected);
 if(PyDict_CheckExact(v)){
  if(PyDict_GET_SIZE(v)!=count)return 0;Py_ssize_t pos=0,i=0;PyObject*k,*child;
  while(PyDict_Next(v,&pos,&k,&child)){
   PyObject*pair=PyTuple_GET_ITEM(expected,i++);
   if(!PyUnicode_CheckExact(k)||!PyTuple_CheckExact(pair)||PyTuple_GET_SIZE(pair)!=2||!PyUnicode_CheckExact(PyTuple_GET_ITEM(pair,0))||PyUnicode_Compare(k,PyTuple_GET_ITEM(pair,0))!=0||!contract_schema_match(child,PyTuple_GET_ITEM(pair,1),active,depth+1,work))return 0;
  }
  return 1;
 }
 if((PyList_CheckExact(v)?PyList_GET_SIZE(v):PyTuple_GET_SIZE(v))!=count)return 0;
 for(Py_ssize_t i=0;i<count;i++)if(!contract_schema_match(PyList_CheckExact(v)?PyList_GET_ITEM(v,i):PyTuple_GET_ITEM(v,i),PyTuple_GET_ITEM(expected,i),active,depth+1,work))return 0;
 return 1;
}
static int contract_schemas_current_internal(void){
 if(!contract_schemas||!contract_classes||!code_classes(contract_classes))return 0;
 size_t work=0;PyObject*active[65];
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(contract_schemas);i++){
  PyObject*entry=PyTuple_GET_ITEM(contract_schemas,i),*cls=PyTuple_GET_ITEM(entry,0),*space=((PyTypeObject*)cls)->tp_dict;
  if(!space||Py_TYPE(PyTuple_GET_ITEM(entry,3))!=contract_validator_type||Py_TYPE(PyTuple_GET_ITEM(entry,4))!=contract_serializer_type||PyDict_GetItemString(space,"__pydantic_core_schema__")!=PyTuple_GET_ITEM(entry,1)||PyDict_GetItemString(space,"__pydantic_validator__")!=PyTuple_GET_ITEM(entry,3)||PyDict_GetItemString(space,"__pydantic_serializer__")!=PyTuple_GET_ITEM(entry,4)||!contract_schema_match(PyTuple_GET_ITEM(entry,1),PyTuple_GET_ITEM(entry,2),active,0,&work))return 0;
 }
 return !PyErr_Occurred();
}
static PyObject*contract_descriptor(PyTypeObject*cls,const char*name){
 PyObject*mro=cls->tp_mro;if(!PyTuple_CheckExact(mro))return NULL;
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(mro);i++){
  PyObject*space=((PyTypeObject*)PyTuple_GET_ITEM(mro,i))->tp_dict;
  if(!space||!code_namespace(space))return NULL;
  PyObject*v=PyDict_GetItemString(space,name);if(v)return v;
 }
 return NULL;
}
static int contract_config_current(PyObject*config){
 if(!source_config(config))return 0;PyObject*models=PyTuple_GET_ITEM(config,0);
 if(PyTuple_GET_SIZE(models)!=27)return 0;
 static const char*names[]={"__dict__","__pydantic_fields_set__","__pydantic_extra__","__pydantic_private__"};
 for(Py_ssize_t i=0;i<27;i++){
  PyObject*entry=PyTuple_GET_ITEM(models,i),*cls=PyTuple_GET_ITEM(contract_models,i);
  if(PyTuple_GET_ITEM(entry,0)!=cls||!(((PyTypeObject*)cls)->tp_flags&Py_TPFLAGS_HEAPTYPE))return 0;
  PyObject*module=PyDict_GetItemString(((PyTypeObject*)cls)->tp_dict,"__module__"),*name=((PyHeapTypeObject*)cls)->ht_qualname;
  if(!module||!PyUnicode_CheckExact(module)||!name||!PyUnicode_CheckExact(name))return 0;
  PyObject*label=PyUnicode_FromFormat("%U.%U",module,name);if(!label)return 0;
  int same=PyUnicode_Compare(label,PyTuple_GET_ITEM(entry,1))==0;Py_DECREF(label);if(!same)return 0;
  for(int j=0;j<4;j++)if(contract_descriptor((PyTypeObject*)cls,names[j])!=PyTuple_GET_ITEM(entry,j+2))return 0;
 }
 return !PyErr_Occurred();
}
static PyObject*register_contract_schemas(PyObject*self,PyObject*args){
 (void)self;PyObject*schemas,*classes,*leaves,*types;
 if(!PyArg_ParseTuple(args,"OOOO",&schemas,&classes,&leaves,&types))return NULL;
 if(contract_schemas||!contract_models||!PyTuple_CheckExact(schemas)||PyTuple_GET_SIZE(schemas)!=27||!PyTuple_CheckExact(classes)||!PyTuple_CheckExact(leaves)||!PyTuple_CheckExact(types)||PyTuple_GET_SIZE(types)!=2||!PyType_Check(PyTuple_GET_ITEM(types,0))||!PyType_Check(PyTuple_GET_ITEM(types,1)))return view_error();
 for(Py_ssize_t i=0;i<27;i++){
  PyObject*r=PyTuple_GET_ITEM(schemas,i);
  if(!PyTuple_CheckExact(r)||PyTuple_GET_SIZE(r)!=5||PyTuple_GET_ITEM(r,0)!=PyTuple_GET_ITEM(contract_models,i)||!PyTuple_CheckExact(PyTuple_GET_ITEM(r,2)))return view_error();
 }
 contract_validator_type=(PyTypeObject*)PyTuple_GET_ITEM(types,0);
 contract_serializer_type=(PyTypeObject*)PyTuple_GET_ITEM(types,1);
 Py_INCREF(contract_validator_type);Py_INCREF(contract_serializer_type);
 contract_schemas=Py_NewRef(schemas);contract_classes=Py_NewRef(classes);contract_schema_leaves=Py_NewRef(leaves);
 if(!contract_schemas_current_internal()){Py_CLEAR(contract_schemas);Py_CLEAR(contract_classes);Py_CLEAR(contract_schema_leaves);Py_DECREF(contract_validator_type);Py_DECREF(contract_serializer_type);contract_validator_type=contract_serializer_type=NULL;if(!PyErr_Occurred())PyErr_SetString(PyExc_ValueError,"Changed complete PB schema configuration");return NULL;}
 Py_RETURN_NONE;
}
static PyObject*contract_schema_current(PyObject*self,PyObject*unused){(void)self;(void)unused;int ok=contract_schemas_current_internal();if(PyErr_Occurred())return NULL;return PyBool_FromLong(ok);}
static PyObject*contract_entry(PyObject*self,PyObject*unused){
 (void)self;(void)unused;PyObject*ok=verify_code_range(0,10);if(!ok)return NULL;
 int same=ok==Py_True;Py_DECREF(ok);if(!same){PyErr_SetString(PyExc_ValueError,"PB data entry code or role changed");return NULL;}Py_RETURN_NONE;
}
/* Independent optional lease-code family. Legacy Source/PB verification keeps
 * exactly its original ranges and does not require this optional protocol. */
static PyObject*lease_entry(PyObject*self,PyObject*unused){
 (void)self;(void)unused;PyObject*ok=verify_code_range(10,11);if(!ok)return NULL;
 int same=ok==Py_True;Py_DECREF(ok);if(!same){PyErr_SetString(PyExc_ValueError,"Lease control entry code or role changed");return NULL;}Py_RETURN_NONE;
}
static PyObject*lease_actor_entry(PyObject*self,PyObject*unused){
 (void)self;(void)unused;PyObject*ok=verify_code_range(10,12);if(!ok)return NULL;
 int same=ok==Py_True;Py_DECREF(ok);if(!same){PyErr_SetString(PyExc_ValueError,"Lease control actor code or role changed");return NULL;}Py_RETURN_NONE;
}
/* Runtime provenance only. These records contain no lease/permission/PASS and
 * are inaccessible to mutable Python module dictionaries. */
static PyObject *lease_runtime_type,*lease_runtime_issue_code,*lease_runtime_issue_globals,*lease_runtime_records;
typedef struct {
 PyObject *weak,*items,*store,*store_items;
} LeaseRuntimeRecord;
#define LEASE_RUNTIME_RECORD "sim2act.lease-runtime-record.v1"
static void lease_runtime_record_free(PyObject*capsule){
 LeaseRuntimeRecord*r=PyCapsule_GetPointer(capsule,LEASE_RUNTIME_RECORD);
 if(!r){PyErr_Clear();return;}
 Py_XDECREF(r->weak);Py_XDECREF(r->items);Py_XDECREF(r->store);Py_XDECREF(r->store_items);PyMem_Free(r);
}
static LeaseRuntimeRecord*lease_runtime_record(PyObject*value){
 return value&&PyCapsule_IsValid(value,LEASE_RUNTIME_RECORD)?PyCapsule_GetPointer(value,LEASE_RUNTIME_RECORD):NULL;
}
static PyObject*lease_runtime_error(void){PyErr_SetString(PyExc_ValueError,"Lease runtime issuance or fields changed");return NULL;}
static PyObject*lease_runtime_forget(PyObject*key,PyObject*weak){
 if(lease_runtime_records){PyObject*e=PyDict_GetItemWithError(lease_runtime_records,key);
  LeaseRuntimeRecord*r=lease_runtime_record(e);
  if(r&&r->weak==weak&&PyWeakref_GetObject(weak)==Py_None){if(PyDict_DelItem(lease_runtime_records,key)<0)return NULL;}
  else if(PyErr_Occurred())return NULL;}
 Py_RETURN_NONE;
}
static PyMethodDef lease_runtime_forget_def={"_lease_runtime_forget",lease_runtime_forget,METH_O,NULL};
static int lease_actor_current(void){
 PyObject*ok=verify_code_range(10,12);if(!ok)return 0;int same=ok==Py_True;Py_DECREF(ok);return same;
}
static PyObject*register_lease_runtime(PyObject*self,PyObject*args){
 (void)self;PyObject*cls,*fn;
 if(!PyArg_ParseTuple(args,"OO",&cls,&fn))return NULL;
 PyObject*ok=verify_code_range(10,11);if(!ok)return NULL;int same=ok==Py_True;Py_DECREF(ok);
 if(!same||lease_runtime_type||!PyType_Check(cls)||!PyFunction_Check(fn)
   ||!(((PyTypeObject*)cls)->tp_flags&Py_TPFLAGS_HEAPTYPE))return lease_runtime_error();
 PyObject*space=PyFunction_GetGlobals(fn);
 if(!code_namespace(space)||PyDict_GetItemString(space,"Runtime")!=cls
   ||PyDict_GetItemString(space,"enable")!=fn)return lease_runtime_error();
 PyObject*records=PyDict_New();if(!records)return NULL;
 lease_runtime_type=Py_NewRef(cls);lease_runtime_issue_code=Py_NewRef(PyFunction_GetCode(fn));
 lease_runtime_issue_globals=Py_NewRef(space);lease_runtime_records=records;
 Py_RETURN_NONE;
}
static PyObject*lease_dict_items(PyObject*dict){
 if(!code_namespace(dict))return NULL;
 PyObject*items=PyTuple_New(PyDict_GET_SIZE(dict));if(!items)return NULL;
 Py_ssize_t pos=0,index=0;PyObject*k,*v;
 while(PyDict_Next(dict,&pos,&k,&v)){PyObject*pair=PyTuple_Pack(2,k,v);if(!pair){Py_DECREF(items);return NULL;}PyTuple_SET_ITEM(items,index++,pair);}
 return items;
}
static int lease_store_fields_current(PyObject*store,PyObject*fields){
 PyObject*actor=source_code[11],*classes=actor?PyTuple_GET_ITEM(actor,1):NULL;
 if(!classes||!PyTuple_CheckExact(classes)||PyTuple_GET_SIZE(classes)<1||!code_namespace(fields))return 0;
 PyObject*cls=PyTuple_GET_ITEM(PyTuple_GET_ITEM(classes,0),0);
 if(Py_TYPE(store)!=(PyTypeObject*)cls)return 0;
 /* Never accept an instance shadow of a fixed actor method/descriptor. */
 PyObject*declared=((PyTypeObject*)cls)->tp_dict,*key,*value;Py_ssize_t pos=0;
 if(!code_namespace(declared))return 0;
 while(PyDict_Next(declared,&pos,&key,&value)){
  int contains=PyDict_Contains(fields,key);if(contains!=0)return 0;
 }
 return 1;
}
static PyObject*install_lease_runtime(PyObject*self,PyObject*runtime){
 (void)self;if(!lease_actor_current()){if(PyErr_Occurred())return NULL;return lease_runtime_error();}
 if(!lease_runtime_type||!lease_runtime_records||Py_TYPE(runtime)!=(PyTypeObject*)lease_runtime_type)return lease_runtime_error();
 int gc=PyGC_Disable();PyObject*fields=NULL,*locals=NULL,*key=NULL,*callback=NULL,*weak=NULL,*items=NULL,*store_fields=NULL,*store_items=NULL,*entry=NULL;
 PyFrameObject*frame=PyThreadState_GetFrame(PyThreadState_Get());int valid=0;
 if(frame){PyCodeObject*code=PyFrame_GetCode(frame);PyObject*space=PyFrame_GetGlobals(frame);
  if((PyObject*)code==lease_runtime_issue_code&&space==lease_runtime_issue_globals)locals=PyFrame_GetLocals(frame);
  Py_DECREF(code);Py_DECREF(space);Py_DECREF(frame);}
 if(!locals||!code_namespace(locals)||PyDict_GetItemString(locals,"selected")!=runtime)goto done;
 fields=PyObject_GenericGetDict(runtime,NULL);
 if(!fields||!code_namespace(fields)||PyDict_GET_SIZE(fields)!=8)goto done;
 static const char*names[]={"store","authority","path","identity","seconds","run_seconds","uri","engine"};
 for(int i=0;i<8;i++){PyObject*v=PyDict_GetItemString(fields,names[i]);if(!v||v!=PyDict_GetItemString(locals,names[i]))goto done;}
 PyObject*store=PyDict_GetItemString(fields,"store"),*uri=PyDict_GetItemString(fields,"uri");
 if(!PyUnicode_CheckExact(uri))goto done;
 PyObject*actor=source_code[11],*classes=actor?PyTuple_GET_ITEM(actor,1):NULL;
 if(!classes||!PyTuple_CheckExact(classes)||PyTuple_GET_SIZE(classes)<1)goto done;
 PyObject*store_class=PyTuple_GET_ITEM(PyTuple_GET_ITEM(classes,0),0);
 if(Py_TYPE(store)!=(PyTypeObject*)store_class)goto done;
 store_fields=PyObject_GenericGetDict(store,NULL);if(!store_fields||!code_namespace(store_fields))goto done;
 if(!lease_store_fields_current(store,store_fields))goto done;
 static const char*store_names[]={"engine","sqlite","test_only","_sqlite_commit_boundary","_workspace_writer_gate","_local_model_snapshots"};
 store_items=PyTuple_New(6);if(!store_items)goto done;
 for(int i=0;i<6;i++){PyObject*k=PyUnicode_FromString(store_names[i]),*v=PyDict_GetItemString(store_fields,store_names[i]);
  if(!k||!v){Py_XDECREF(k);goto done;}PyObject*pair=PyTuple_Pack(2,k,v);Py_DECREF(k);if(!pair)goto done;PyTuple_SET_ITEM(store_items,i,pair);}
 if(PyDict_GetItemString(store_fields,"engine")!=PyDict_GetItemString(fields,"engine")
   ||PyDict_GetItemString(store_fields,"sqlite")!=Py_True||PyDict_GetItemString(store_fields,"test_only")!=Py_True)goto done;
 key=PyLong_FromVoidPtr(runtime);if(!key)goto done;
 if(PyDict_GetItemWithError(lease_runtime_records,key)||PyErr_Occurred())goto done;
 callback=PyCFunction_NewEx(&lease_runtime_forget_def,key,NULL);if(!callback)goto done;
 weak=PyWeakref_NewRef(runtime,callback);if(!weak)goto done;
 items=lease_dict_items(fields);if(!items)goto done;
 LeaseRuntimeRecord*record=PyMem_Calloc(1,sizeof(*record));if(!record){PyErr_NoMemory();goto done;}
 record->weak=Py_NewRef(weak);record->items=Py_NewRef(items);
 record->store=Py_NewRef(store);record->store_items=Py_NewRef(store_items);
 entry=PyCapsule_New(record,LEASE_RUNTIME_RECORD,lease_runtime_record_free);
 if(!entry){Py_DECREF(record->weak);Py_DECREF(record->items);Py_DECREF(record->store);Py_DECREF(record->store_items);PyMem_Free(record);goto done;}
 if(PyDict_SetItem(lease_runtime_records,key,entry)<0)goto done;valid=1;
done:
 Py_XDECREF(fields);Py_XDECREF(locals);Py_XDECREF(key);Py_XDECREF(callback);Py_XDECREF(weak);Py_XDECREF(items);Py_XDECREF(store_fields);Py_XDECREF(store_items);Py_XDECREF(entry);
 if(gc)PyGC_Enable();if(!valid){if(PyErr_Occurred())return NULL;return lease_runtime_error();}Py_RETURN_NONE;
}
static PyObject*lease_runtime_current(PyObject*self,PyObject*runtime){
 (void)self;if(!lease_actor_current()){if(PyErr_Occurred())return NULL;return lease_runtime_error();}
 if(!lease_runtime_type||!lease_runtime_records||Py_TYPE(runtime)!=(PyTypeObject*)lease_runtime_type)return lease_runtime_error();
 int gc=PyGC_Disable();PyObject*key=PyLong_FromVoidPtr(runtime),*fields=NULL,*store_fields=NULL,*result=NULL;
 if(!key)goto done;PyObject*entry=PyDict_GetItemWithError(lease_runtime_records,key);
 LeaseRuntimeRecord*record=lease_runtime_record(entry);
 if(!record||PyWeakref_GetObject(record->weak)!=runtime)goto done;
 fields=PyObject_GenericGetDict(runtime,NULL);if(!fields||!code_items(fields,record->items))goto done;
 PyObject*store=record->store;
 store_fields=PyObject_GenericGetDict(store,NULL);if(!store_fields||!code_namespace(store_fields))goto done;
 if(!lease_store_fields_current(store,store_fields))goto done;
 PyObject*expected=record->store_items;
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(expected);i++){PyObject*pair=PyTuple_GET_ITEM(expected,i);
  if(PyDict_GetItemWithError(store_fields,PyTuple_GET_ITEM(pair,0))!=PyTuple_GET_ITEM(pair,1))goto done;}
 result=Py_NewRef(record->items);
done:
 Py_XDECREF(key);Py_XDECREF(fields);Py_XDECREF(store_fields);if(gc)PyGC_Enable();
 if(!result){if(PyErr_Occurred())return NULL;return lease_runtime_error();}return result;
}
/* Commit facts never live in a Python closure/container reachable by GC.
 * Only the fixed guarded frame can invoke its captured original delegate. */
typedef struct {
 PyObject *weak,*connection,*raw,*transaction,*guarded,*original,*factory,*control,*control_connection,*control_times,*control_file;
 int invoked,committed,in_delegate;
 double control_wall_limit,control_absolute_limit;
} CommitOutcomeRecord;
#define COMMIT_OUTCOME_RECORD "sim2act.commit-outcome.v1"
static PyObject *commit_outcome_records,*commit_outcome_factories,*commit_outcome_globals,*commit_outcome_install_code,*commit_outcome_body_code,*commit_outcome_ctor_code,*commit_outcome_exit_code,*commit_outcome_guarded_code,*commit_outcome_delegate,*commit_outcome_dialect;
static PyObject *commit_owner_type,*commit_owner_descriptor;
static PyObject*commit_outcome_error(void){PyErr_SetString(PyExc_ValueError,"Commit outcome provenance changed");return NULL;}
static CommitOutcomeRecord*commit_outcome_record(PyObject*value){
 return value&&PyCapsule_IsValid(value,COMMIT_OUTCOME_RECORD)?PyCapsule_GetPointer(value,COMMIT_OUTCOME_RECORD):NULL;
}
static void commit_outcome_free(PyObject*capsule){
 CommitOutcomeRecord*r=commit_outcome_record(capsule);if(!r)return;
 Py_XDECREF(r->weak);Py_XDECREF(r->connection);Py_XDECREF(r->raw);Py_XDECREF(r->transaction);
 Py_XDECREF(r->guarded);Py_XDECREF(r->original);Py_XDECREF(r->factory);
 Py_XDECREF(r->control);Py_XDECREF(r->control_connection);Py_XDECREF(r->control_times);Py_XDECREF(r->control_file);PyMem_Free(r);
}
static PyObject*commit_outcome_forget(PyObject*key,PyObject*weak){
 if(commit_outcome_records){CommitOutcomeRecord*r=commit_outcome_record(PyDict_GetItemWithError(commit_outcome_records,key));
  if(r&&r->weak==weak&&PyWeakref_GetObject(weak)==Py_None){if(PyDict_DelItem(commit_outcome_records,key)<0)return NULL;}
  else if(PyErr_Occurred())return NULL;}
 Py_RETURN_NONE;
}
static PyMethodDef commit_outcome_forget_def={"_commit_outcome_forget",commit_outcome_forget,METH_O,NULL};
static PyObject*commit_child_code(PyObject*code,const char*name){
 if(!PyCode_Check(code))return NULL;PyObject*values=((PyCodeObject*)code)->co_consts;
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(values);i++){PyObject*v=PyTuple_GET_ITEM(values,i);
  if(PyCode_Check(v)&&PyUnicode_CompareWithASCIIString(((PyCodeObject*)v)->co_name,name)==0)return v;}
 return NULL;
}
static PyObject*commit_frame_locals(PyObject*code){
 PyFrameObject*frame=PyThreadState_GetFrame(PyThreadState_Get());if(!frame)return NULL;
 PyCodeObject*actual=PyFrame_GetCode(frame);PyObject*space=PyFrame_GetGlobals(frame),*locals=NULL;
 if((PyObject*)actual==code&&space==commit_outcome_globals)locals=PyFrame_GetLocals(frame);
 Py_DECREF(actual);Py_DECREF(space);Py_DECREF(frame);
 if(locals&&!code_namespace(locals)){Py_DECREF(locals);locals=NULL;}
 return locals;
}
static int commit_outcome_code_current(void){
 PyObject*ok=verify_code_range(12,13);if(!ok)return 0;int same=ok==Py_True;Py_DECREF(ok);return same;
}
static PyObject*register_commit_outcomes(PyObject*self,PyObject*args){
 (void)self;PyObject*install,*delegate,*dialect;
 if(!PyArg_ParseTuple(args,"OOO",&install,&delegate,&dialect))return NULL;
 if(!commit_outcome_code_current()){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 if(commit_outcome_records||!PyFunction_Check(install)||!PyFunction_Check(delegate)||!PyType_Check(dialect))return commit_outcome_error();
 PyObject*space=PyFunction_GetGlobals(install),*body=commit_child_code(PyFunction_GetCode(install),"Boundary");
 PyObject*ctor=body?commit_child_code(body,"__init__"):NULL,*guarded=commit_child_code(PyFunction_GetCode(install),"guarded");
 if(!ctor||!guarded||!commit_child_code(body,"__exit__")||!code_namespace(space)||PyDict_GetItemString(space,"install")!=install
   ||PyDict_GetItemString(space,"_sqlite_do_commit")!=delegate||PyDict_GetItemString(space,"_sqlite_dialect")!=dialect)return commit_outcome_error();
 PyObject*owner_type=PyDict_GetItemString(space,"_sa_connection"),*owner_descriptor=PyDict_GetItemString(space,"_object_class");
 if(!owner_type||!PyType_Check(owner_type)||!owner_descriptor||Py_TYPE(owner_descriptor)!=&PyGetSetDescr_Type
   ||PyDescr_TYPE(owner_descriptor)!=&PyBaseObject_Type)return commit_outcome_error();
 PyObject*records=PyDict_New(),*factories=PyDict_New();if(!records||!factories){Py_XDECREF(records);Py_XDECREF(factories);return NULL;}
 commit_outcome_globals=Py_NewRef(space);commit_outcome_ctor_code=Py_NewRef(ctor);commit_outcome_guarded_code=Py_NewRef(guarded);
 commit_outcome_install_code=Py_NewRef(PyFunction_GetCode(install));commit_outcome_body_code=Py_NewRef(body);
 commit_outcome_exit_code=Py_NewRef(commit_child_code(body,"__exit__"));
 commit_outcome_delegate=Py_NewRef(delegate);commit_outcome_dialect=Py_NewRef(dialect);
 commit_owner_type=Py_NewRef(owner_type);commit_owner_descriptor=Py_NewRef(owner_descriptor);
 commit_outcome_records=records;commit_outcome_factories=factories;Py_RETURN_NONE;
}
/* Per-engine final class/function/closure witness, captured before install
 * returns. The engine's explicit dispose event retires the registration. */
static void commit_factory_free(PyObject*capsule){
 PyObject*record=PyCapsule_GetPointer(capsule,"sim2act.commit-factory.v1");
 if(record)Py_DECREF(record);else PyErr_Clear();
}
static PyObject*commit_factory_record(PyObject*capsule){
 return capsule&&PyCapsule_IsValid(capsule,"sim2act.commit-factory.v1")?PyCapsule_GetPointer(capsule,"sim2act.commit-factory.v1"):NULL;
}
static int commit_factory_current(PyObject*capsule){
 PyObject*r=commit_factory_record(capsule);
 return r&&PyTuple_CheckExact(r)&&PyTuple_GET_SIZE(r)==5&&code_classes(PyTuple_GET_ITEM(r,0))&&code_state(PyTuple_GET_ITEM(r,1),0);
}
static PyObject*register_commit_factory(PyObject*self,PyObject*args){
 (void)self;PyObject*cls,*class_state,*guarded,*guarded_state,*engine,*entries,*locals=NULL,*key=NULL,*record=NULL,*capsule=NULL;
 if(!PyArg_ParseTuple(args,"OOOOOO",&cls,&class_state,&guarded,&guarded_state,&engine,&entries))return NULL;
 if(!commit_outcome_code_current()){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 int gc=PyGC_Disable();locals=commit_frame_locals(commit_outcome_install_code);int valid=0;
 if(!locals||!PyType_Check(cls)||Py_TYPE(cls)!=&PyType_Type||((PyTypeObject*)cls)->tp_base!=&PyBaseObject_Type
   ||PyDict_GetItemString(locals,"Boundary")!=cls||PyDict_GetItemString(locals,"guarded")!=guarded
   ||PyDict_GetItemString(locals,"engine")!=engine||PyDict_GetItemString(locals,"entries")!=entries
   ||!PyTuple_CheckExact(class_state)||PyTuple_GET_SIZE(class_state)!=5||PyTuple_GET_ITEM(class_state,0)!=cls
   ||!PyTuple_CheckExact(guarded_state)||PyTuple_GET_SIZE(guarded_state)!=7||PyTuple_GET_ITEM(guarded_state,0)!=guarded)goto done;
 PyObject*ns=((PyTypeObject*)cls)->tp_dict,*k,*v;Py_ssize_t pos=0;
 if(!code_namespace(ns))goto done;
 while(PyDict_Next(ns,&pos,&k,&v)){
  const char*name=PyUnicode_AsUTF8(k);if(!name)goto done;
  if(PyFunction_Check(v)){
   if(PyFunction_GetCode(v)!=commit_child_code(commit_outcome_body_code,name)||PyFunction_GetGlobals(v)!=commit_outcome_globals)goto done;
  }else if(strcmp(name,"committed")==0||strcmp(name,"commit_invoked")==0){
   if(Py_TYPE(v)!=&PyProperty_Type)goto done;
   PyObject*getter=PyObject_GetAttrString(v,"fget");int same=getter&&PyFunction_Check(getter)
     &&PyFunction_GetCode(getter)==commit_child_code(commit_outcome_body_code,name)&&PyFunction_GetGlobals(getter)==commit_outcome_globals;
   Py_XDECREF(getter);if(!same)goto done;
  }else if(strcmp(name,"__module__")&&strcmp(name,"__doc__")&&strcmp(name,"__dict__")&&strcmp(name,"__weakref__"))goto done;
 }
 const char*helpers[]={"guarded","fail","rollback","held_roles","restore_owner"};
 for(int i=0;i<5;i++){PyObject*fn=PyDict_GetItemString(locals,helpers[i]);
  if(!fn||!PyFunction_Check(fn)||PyFunction_GetCode(fn)!=commit_child_code(commit_outcome_install_code,helpers[i]))goto done;}
 PyObject*classes=PyTuple_Pack(1,class_state);if(!classes)goto done;
 record=PyTuple_Pack(5,classes,guarded_state,engine,entries,cls);Py_DECREF(classes);if(!record)goto done;
 capsule=PyCapsule_New(record,"sim2act.commit-factory.v1",commit_factory_free);if(!capsule)goto done;record=NULL;
 if(!commit_factory_current(capsule))goto done;
 key=PyLong_FromVoidPtr(cls);if(!key)goto done;
 if(PyDict_GetItemWithError(commit_outcome_factories,key)||PyErr_Occurred())goto done;
 if(PyDict_SetItem(commit_outcome_factories,key,capsule)<0)goto done;valid=1;
done:
 Py_XDECREF(locals);Py_XDECREF(key);Py_XDECREF(record);Py_XDECREF(capsule);
 if(gc)PyGC_Enable();
 if(!valid){if(PyErr_Occurred())return NULL;return commit_outcome_error();}Py_RETURN_NONE;
}
static PyObject*retire_commit_factory(PyObject*self,PyObject*cls){
 (void)self;PyObject*key=PyLong_FromVoidPtr(cls);if(!key)return NULL;
 /* Revocation only: cannot issue a replacement class or a successful fact. */
 if(commit_outcome_factories&&PyDict_GetItemWithError(commit_outcome_factories,key)){
  if(PyDict_DelItem(commit_outcome_factories,key)<0){Py_DECREF(key);return NULL;}}
 Py_DECREF(key);if(PyErr_Occurred())return NULL;Py_RETURN_NONE;
}
static PyObject*preinit_commit_outcome(PyObject*self,PyObject*boundary){
 (void)self;if(!commit_outcome_code_current()){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 int gc=PyGC_Disable();PyObject*locals=commit_frame_locals(commit_outcome_ctor_code),*key=PyLong_FromVoidPtr(Py_TYPE(boundary));
 PyObject*factory=key&&commit_outcome_factories?PyDict_GetItemWithError(commit_outcome_factories,key):NULL;
 PyObject*c=locals?PyDict_GetItemString(locals,"c"):NULL;
 int valid=locals&&PyDict_GetItemString(locals,"self")==boundary&&c
  &&(PyObject*)Py_TYPE(c)==PyDict_GetItemString(commit_outcome_globals,"_sa_connection")&&commit_factory_current(factory);
 Py_XDECREF(locals);Py_XDECREF(key);if(gc)PyGC_Enable();
 if(!valid){if(PyErr_Occurred())return NULL;return commit_outcome_error();}Py_RETURN_NONE;
}
static PyObject*init_commit_outcome(PyObject*self,PyObject*args){
 (void)self;PyObject*boundary,*guarded,*original;
 if(!PyArg_ParseTuple(args,"OOO",&boundary,&guarded,&original))return NULL;
 if(!commit_outcome_code_current()){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 if(!commit_outcome_records||!PyFunction_Check(guarded)||PyFunction_GetCode(guarded)!=commit_outcome_guarded_code
   ||PyFunction_GetGlobals(guarded)!=commit_outcome_globals||!PyMethod_Check(original)
   ||PyMethod_GET_FUNCTION(original)!=commit_outcome_delegate||Py_TYPE(PyMethod_GET_SELF(original))!=(PyTypeObject*)commit_outcome_dialect)return commit_outcome_error();
 int gc=PyGC_Disable(),valid=0;PyObject*locals=commit_frame_locals(commit_outcome_ctor_code),*fields=NULL,*key=NULL,*callback=NULL,*capsule=NULL,*factory_key=PyLong_FromVoidPtr(Py_TYPE(boundary));
 PyObject*factory=factory_key?PyDict_GetItemWithError(commit_outcome_factories,factory_key):NULL;
 CommitOutcomeRecord*r=NULL;
 if(!commit_factory_current(factory))goto done;
 if(!locals||PyDict_GetItemString(locals,"self")!=boundary||PyDict_GetItemString(locals,"guarded")!=guarded
   ||PyDict_GetItemString(locals,"original")!=original)goto done;
 fields=PyObject_GenericGetDict(boundary,NULL);if(!fields||!code_namespace(fields))goto done;
 PyObject*c=PyDict_GetItemString(fields,"c"),*raw=PyDict_GetItemString(fields,"raw"),*tx=PyDict_GetItemString(fields,"transaction");
 if(!c||!raw||!tx||c!=PyDict_GetItemString(locals,"c"))goto done;
 PyObject*factory_state=commit_factory_record(factory);
 if(Py_TYPE(boundary)!=(PyTypeObject*)PyTuple_GET_ITEM(factory_state,4)
   ||PyTuple_GET_ITEM(PyTuple_GET_ITEM(factory_state,1),0)!=guarded)goto done;
 Py_ssize_t occupied_pos=0;PyObject*occupied_key,*occupied_value;
 while(PyDict_Next(commit_outcome_records,&occupied_pos,&occupied_key,&occupied_value)){
  CommitOutcomeRecord*other=commit_outcome_record(occupied_value);
  if(other&&other->raw==raw&&other->transaction==tx&&PyWeakref_GetObject(other->weak)!=Py_None)goto done;
 }
 key=PyLong_FromVoidPtr(boundary);if(!key)goto done;
 if(PyDict_GetItemWithError(commit_outcome_records,key)||PyErr_Occurred())goto done;
 r=PyMem_Calloc(1,sizeof(*r));if(!r){PyErr_NoMemory();goto done;}
 callback=PyCFunction_NewEx(&commit_outcome_forget_def,key,NULL);if(!callback)goto done;
 r->weak=PyWeakref_NewRef(boundary,callback);if(!r->weak)goto done;
 r->connection=Py_NewRef(c);r->raw=Py_NewRef(raw);r->transaction=Py_NewRef(tx);
 r->guarded=Py_NewRef(guarded);r->original=Py_NewRef(original);
 r->factory=Py_NewRef(factory);
 capsule=PyCapsule_New(r,COMMIT_OUTCOME_RECORD,commit_outcome_free);if(!capsule)goto done;r=NULL;
 if(PyDict_SetItem(commit_outcome_records,key,capsule)<0)goto done;valid=1;
done:
 if(r){Py_XDECREF(r->weak);Py_XDECREF(r->connection);Py_XDECREF(r->raw);Py_XDECREF(r->transaction);Py_XDECREF(r->guarded);Py_XDECREF(r->original);Py_XDECREF(r->factory);PyMem_Free(r);}
 Py_XDECREF(locals);Py_XDECREF(fields);Py_XDECREF(key);Py_XDECREF(callback);Py_XDECREF(capsule);Py_XDECREF(factory_key);if(gc)PyGC_Enable();
 if(!valid){if(PyErr_Occurred())return NULL;return commit_outcome_error();}Py_RETURN_NONE;
}
static CommitOutcomeRecord*find_commit_outcome(PyObject*boundary){
 if(!commit_outcome_records)return NULL;PyObject*key=PyLong_FromVoidPtr(boundary);if(!key)return NULL;
 CommitOutcomeRecord*r=commit_outcome_record(PyDict_GetItemWithError(commit_outcome_records,key));Py_DECREF(key);
 return r&&PyWeakref_GetObject(r->weak)==boundary?r:NULL;
}
static PyObject*read_commit_outcome(PyObject*self,PyObject*boundary){
 (void)self;CommitOutcomeRecord*r=find_commit_outcome(boundary);
 if(!r){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 return PyTuple_Pack(2,r->committed?Py_True:Py_False,r->invoked?Py_True:Py_False);
}
static PyObject*find_commit_boundary(PyObject*self,PyObject*connection){
 (void)self;if(!commit_outcome_code_current()){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 Py_ssize_t pos=0;PyObject*key,*value;
 while(commit_outcome_records&&PyDict_Next(commit_outcome_records,&pos,&key,&value)){
  CommitOutcomeRecord*r=commit_outcome_record(value);
  if(r&&r->connection==connection&&r->factory){PyObject*scope=PyWeakref_GetObject(r->weak);
   if(scope!=Py_None){PyObject*f=commit_factory_record(r->factory);
    if(PyDict_GetItemWithError(PyTuple_GET_ITEM(f,3),r->raw)==scope)return Py_NewRef(scope);}}
 }Py_RETURN_NONE;
}
static PyObject*read_commit_control(PyObject*self,PyObject*boundary){
 (void)self;CommitOutcomeRecord*r=find_commit_outcome(boundary);
 if(!r){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 return Py_NewRef(r->control?r->control:Py_None);
}
static PyObject*bind_commit_control(PyObject*self,PyObject*args){
 (void)self;PyObject*scope,*binding,*connection;
 if(!PyArg_ParseTuple(args,"OOO",&scope,&binding,&connection))return NULL;
 if(!lease_actor_current()||!commit_outcome_code_current()){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 CommitOutcomeRecord*r=find_commit_outcome(scope);
 if(!r||r->connection!=connection||!PyTuple_CheckExact(binding)||PyTuple_GET_SIZE(binding)!=11||r->invoked||r->control_connection)return commit_outcome_error();
 PyObject*runtime=PyTuple_GET_ITEM(binding,0),*current=lease_runtime_current(NULL,runtime);if(!current)return NULL;Py_DECREF(current);
 PyFrameObject*frame=PyThreadState_GetFrame(PyThreadState_Get());PyObject*locals=NULL;int valid=0;
 if(frame){PyCodeObject*code=PyFrame_GetCode(frame);PyObject*space=PyFrame_GetGlobals(frame);
  const char*names[]={"_bind_boundary","_seed_boundary"};
  for(int i=0;i<2;i++){PyObject*fn=PyDict_GetItemString(((PyTypeObject*)lease_runtime_type)->tp_dict,names[i]);
   if(fn&&PyFunction_Check(fn)&&PyFunction_GetCode(fn)==(PyObject*)code&&PyFunction_GetGlobals(fn)==space)valid=1;}
  if(valid)locals=PyFrame_GetLocals(frame);Py_DECREF(code);Py_DECREF(space);Py_DECREF(frame);}
 valid=locals&&code_namespace(locals)&&PyDict_GetItemString(locals,"self")==runtime
   &&PyDict_GetItemString(locals,"boundary")==scope&&PyDict_GetItemString(locals,"c")==connection
   &&PyDict_GetItemString(locals,"binding")==binding;
 Py_XDECREF(locals);if(!valid)return commit_outcome_error();
 if(r->control){for(int i=0;i<7;i++)if(PyTuple_GET_ITEM(r->control,i)!=PyTuple_GET_ITEM(binding,i))return commit_outcome_error();
  if(PyTuple_GET_ITEM(r->control,7)!=Py_None)return commit_outcome_error();}
 Py_XSETREF(r->control,Py_NewRef(binding));Py_RETURN_NONE;
}
static PyObject*control_generator_code(PyObject*function,int depth){
 if(depth>8||!PyFunction_Check(function))return NULL;PyCodeObject*code=(PyCodeObject*)PyFunction_GetCode(function);
 if((code->co_flags&CO_GENERATOR)&&PyUnicode_CompareWithASCIIString(code->co_name,"boundary")==0)return function;
 PyObject*cells=PyFunction_GetClosure(function);
 for(Py_ssize_t i=0;cells&&i<PyTuple_GET_SIZE(cells);i++){PyObject*v=PyCell_GET(PyTuple_GET_ITEM(cells,i));
  PyObject*found=v?control_generator_code(v,depth+1):NULL;if(found)return found;}
 return NULL;
}
static int control_frame_current(CommitOutcomeRecord*r,PyObject*scope,PyObject*connection){
 if(!r||!r->control)return 0;PyObject*session=PyTuple_GET_ITEM(r->control,1);
 PyObject*fn=PyDict_GetItemString(Py_TYPE(session)->tp_dict,"boundary"),*generator=fn?control_generator_code(fn,0):NULL;
 PyFrameObject*frame=PyThreadState_GetFrame(PyThreadState_Get());PyObject*locals=NULL;
 if(frame){PyCodeObject*actual=PyFrame_GetCode(frame);PyObject*space=PyFrame_GetGlobals(frame);
  if(generator&&(PyObject*)actual==PyFunction_GetCode(generator)&&space==PyFunction_GetGlobals(generator))locals=PyFrame_GetLocals(frame);
  Py_DECREF(space);Py_DECREF(actual);Py_DECREF(frame);}
 int valid=locals&&code_namespace(locals)&&PyDict_GetItemString(locals,"self")==session
  &&PyDict_GetItemString(locals,"scope")==scope&&(!connection||PyDict_GetItemString(locals,"c")==connection);
 Py_XDECREF(locals);return valid;
}
static PyObject*enter_commit_control(PyObject*self,PyObject*args){
 (void)self;PyObject*scope,*connection;if(!PyArg_ParseTuple(args,"OO",&scope,&connection))return NULL;
 if(!lease_actor_current()||!commit_outcome_code_current()){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 CommitOutcomeRecord*r=find_commit_outcome(scope);
 if(!control_frame_current(r,scope,connection)||r->control_connection||!PyTuple_CheckExact(r->control)
   ||PyTuple_GET_ITEM(r->control,7)==Py_None)return commit_outcome_error();
 PyObject*session=PyTuple_GET_ITEM(r->control,1),*fields=PyObject_GenericGetDict(session,NULL),*times=NULL;
 if(fields&&code_namespace(fields)){
  PyObject*wall=PyDict_GetItemString(fields,"wall"),*mono=PyDict_GetItemString(fields,"mono"),*absolute=PyDict_GetItemString(fields,"absolute_mono");
  if(wall&&mono&&absolute)times=PyTuple_Pack(3,wall,mono,absolute);}
 Py_XDECREF(fields);if(!times){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 PyObject*authority=PyObject_GetAttrString(session,"authority"),*data=authority?PyObject_GenericGetDict(authority,NULL):NULL;
 PyObject*path=data?PyDict_GetItemString(data,"path"):NULL,*identity=data?PyDict_GetItemString(data,"file_identity"):NULL;
 PyObject*filename=path?PyOS_FSPath(path):NULL,*file=NULL;
 if(filename&&PyUnicode_CheckExact(filename)&&identity&&PyTuple_CheckExact(identity)&&PyTuple_GET_SIZE(identity)==2)
  file=PyTuple_Pack(3,filename,PyTuple_GET_ITEM(identity,0),PyTuple_GET_ITEM(identity,1));
 Py_XDECREF(authority);Py_XDECREF(data);Py_XDECREF(filename);
 if(!file){Py_DECREF(times);if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 r->control_connection=Py_NewRef(connection);r->control_times=times;r->control_file=file;Py_RETURN_NONE;
}
static PyObject*leave_commit_control(PyObject*self,PyObject*scope){
 (void)self;CommitOutcomeRecord*r=find_commit_outcome(scope);
 if(!control_frame_current(r,scope,NULL))return commit_outcome_error();
 Py_CLEAR(r->control_connection);Py_CLEAR(r->control_times);Py_CLEAR(r->control_file);Py_RETURN_NONE;
}
static PyObject*read_commit_roles(PyObject*self,PyObject*boundary){
 (void)self;CommitOutcomeRecord*r=find_commit_outcome(boundary);
 if(!r||!r->connection||!r->raw||!r->transaction){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 PyObject*c=Py_NewRef(r->connection),*raw=Py_NewRef(r->raw),*tx=Py_NewRef(r->transaction);
 PyObject*result=PyTuple_Pack(3,c,raw,tx);Py_DECREF(c);Py_DECREF(raw);Py_DECREF(tx);return result;
}
static PyObject*restore_commit_owner(PyObject*self,PyObject*boundary){
 (void)self;CommitOutcomeRecord*r=find_commit_outcome(boundary);
 if(!r||!r->connection){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 PyObject*owner=Py_NewRef(r->connection);int valid=1;
 if(!code_classes(PyTuple_GET_ITEM(source_code[12],1))){Py_DECREF(owner);return commit_outcome_error();}
 if((PyObject*)Py_TYPE(owner)!=commit_owner_type){
  if(!Py_TYPE(commit_owner_descriptor)->tp_descr_set
    ||Py_TYPE(commit_owner_descriptor)->tp_descr_set(commit_owner_descriptor,owner,commit_owner_type)<0)valid=0;
 }
 Py_DECREF(owner);if(!valid){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 Py_RETURN_NONE;
}
static int commit_physical_current(CommitOutcomeRecord*r,PyObject*proxy,int require_active);
static PyObject*retire_commit_roles(PyObject*self,PyObject*boundary){
 (void)self;PyObject*locals=commit_frame_locals(commit_outcome_exit_code);
 if(!locals||PyDict_GetItemString(locals,"self")!=boundary){Py_XDECREF(locals);return commit_outcome_error();}
 CommitOutcomeRecord*r=find_commit_outcome(boundary);Py_DECREF(locals);
 if(!r||r->in_delegate){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 /* Facts stay readable until this Boundary dies; heavy roles must not keep
  * a failed listener/Connection cycle alive through the native weak table. */
 Py_CLEAR(r->connection);Py_CLEAR(r->raw);Py_CLEAR(r->transaction);Py_CLEAR(r->guarded);Py_CLEAR(r->original);Py_CLEAR(r->factory);
 Py_CLEAR(r->control);Py_CLEAR(r->control_connection);Py_CLEAR(r->control_times);Py_CLEAR(r->control_file);Py_RETURN_NONE;
}
static PyObject*check_commit_outcome(PyObject*self,PyObject*boundary){
 (void)self;if(!commit_outcome_code_current()){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 int gc=PyGC_Disable();CommitOutcomeRecord*r=find_commit_outcome(boundary);PyObject*fields=NULL;int valid=0;
 if(!r||!commit_factory_current(r->factory))goto done;
 if(!commit_physical_current(r,r->raw,0))goto done;
 PyObject*f=commit_factory_record(r->factory);
 if(Py_TYPE(boundary)!=(PyTypeObject*)PyTuple_GET_ITEM(f,4))goto done;
 fields=PyObject_GenericGetDict(boundary,NULL);
 if(!fields||!code_namespace(fields)||PyDict_GetItemString(fields,"c")!=r->connection
   ||PyDict_GetItemString(fields,"raw")!=r->raw||PyDict_GetItemString(fields,"transaction")!=r->transaction)goto done;
 valid=1;
done:Py_XDECREF(fields);if(gc)PyGC_Enable();
 if(!valid){if(PyErr_Occurred())return NULL;return commit_outcome_error();}Py_RETURN_NONE;
}
static int commit_closure_current(PyObject*function,PyObject*locals){
 PyObject*names=PyCode_GetFreevars((PyCodeObject*)PyFunction_GetCode(function));if(!names)return 0;
 PyObject*cells=PyFunction_GetClosure(function);int valid=1;
 if(!cells||!PyTuple_CheckExact(cells)||PyTuple_GET_SIZE(cells)!=PyTuple_GET_SIZE(names))valid=0;
 for(Py_ssize_t i=0;valid&&i<PyTuple_GET_SIZE(names);i++){
  PyObject*cell=PyTuple_GET_ITEM(cells,i);
  if(!PyCell_Check(cell)||PyDict_GetItemWithError(locals,PyTuple_GET_ITEM(names,i))!=PyCell_GET(cell))valid=0;
 }
 Py_DECREF(names);return valid;
}
static PyObject*commit_slot(PyObject*object,const char*name){
 PyObject*descriptor=PyDict_GetItemString(commit_outcome_globals,name);
 if(!descriptor||Py_TYPE(descriptor)!=&PyMemberDescr_Type)return NULL;
 return Py_TYPE(descriptor)->tp_descr_get(descriptor,object,(PyObject*)Py_TYPE(object));
}
static int commit_physical_current(CommitOutcomeRecord*r,PyObject*proxy,int require_active){
 PyObject*kind=PyDict_GetItemString(commit_outcome_globals,"_sa_connection"),*tx_kind=PyDict_GetItemString(commit_outcome_globals,"_sqlite_transaction");
 if((PyObject*)Py_TYPE(r->connection)!=kind||(PyObject*)Py_TYPE(r->transaction)!=tx_kind){PyErr_SetString(PyExc_ValueError,"Commit outcome provenance changed (physical types)");return 0;}
 PyObject*fields=PyObject_GenericGetDict(r->connection,NULL),*actual=NULL,*owner=NULL,*active=NULL;int valid=0;
 const char*stage="connection fields";
 if(!fields||!code_namespace(fields)||(require_active&&PyDict_GetItemString(fields,"_transaction")!=r->transaction)
   ||PyDict_GetItemString(fields,"dialect")!=PyMethod_GET_SELF(r->original))goto done;
 PyObject*held=PyDict_GetItemString(fields,"_dbapi_connection"),*proxy_kind=PyDict_GetItemString(commit_outcome_globals,"_sqlite_proxy");
 stage="current proxy";
 if(!held||(PyObject*)Py_TYPE(held)!=proxy_kind||(proxy!=held&&proxy!=r->raw))goto done;
 actual=commit_slot(held,"_fairy_dbapi");owner=commit_slot(r->transaction,"_tx_connection");active=commit_slot(r->transaction,"_tx_active");
 stage="driver/transaction slots";
 if(actual!=r->raw||owner!=r->connection||(require_active&&active!=Py_True))goto done;
 PyObject*f=commit_factory_record(r->factory);
 stage="engine owner";
 if(!f||PyDict_GetItemString(fields,"engine")!=PyTuple_GET_ITEM(f,2))goto done;
 valid=1;
done:Py_XDECREF(fields);Py_XDECREF(actual);Py_XDECREF(owner);Py_XDECREF(active);
 if(!valid&&!PyErr_Occurred())PyErr_Format(PyExc_ValueError,"Commit outcome provenance changed (%s)",stage);return valid;
}
static int commit_control_clocks(CommitOutcomeRecord*r){
 PyObject*b=r->control,*times=r->control_times;
 PyObject*stop_fields=PyObject_GenericGetDict(PyTuple_GET_ITEM(b,4),NULL);
 if(!stop_fields||!code_namespace(stop_fields)||PyDict_GetItemString(stop_fields,"_flag")!=Py_False){Py_XDECREF(stop_fields);return 0;}Py_DECREF(stop_fields);
 PyObject*wall=PyObject_CallNoArgs(PyDict_GetItemString(commit_outcome_globals,"_commit_wall"));
 PyObject*mono=PyObject_CallNoArgs(PyDict_GetItemString(commit_outcome_globals,"_commit_mono"));
 if(!wall||!mono){Py_XDECREF(wall);Py_XDECREF(mono);return 0;}
 double w=PyFloat_AsDouble(wall),m=PyFloat_AsDouble(mono);Py_DECREF(wall);Py_DECREF(mono);
 return !PyErr_Occurred()&&w<r->control_wall_limit&&w<r->control_absolute_limit
  &&w<PyFloat_AsDouble(PyTuple_GET_ITEM(b,6))&&w<PyFloat_AsDouble(PyTuple_GET_ITEM(times,0))
  &&m<PyFloat_AsDouble(PyTuple_GET_ITEM(b,5))&&m<PyFloat_AsDouble(PyTuple_GET_ITEM(times,1))&&m<PyFloat_AsDouble(PyTuple_GET_ITEM(times,2));
}
static int commit_control_current(CommitOutcomeRecord*r){
 if(!r->control)return 1;
 if(!r->control_file)return 0;
 PyObject*stat=PyObject_CallOneArg(PyDict_GetItemString(commit_outcome_globals,"_control_stat"),PyTuple_GET_ITEM(r->control_file,0));
 if(!stat)return 0;
 PyObject*device=PyObject_GetAttrString(stat,"st_dev"),*inode=PyObject_GetAttrString(stat,"st_ino"),*mode=PyObject_GetAttrString(stat,"st_mode");
 int same=device&&inode&&mode&&PyLong_CheckExact(device)&&PyLong_CheckExact(inode)&&PyLong_CheckExact(mode)
  &&(PyLong_AsUnsignedLong(mode)&0170000)==0100000
  &&PyObject_RichCompareBool(device,PyTuple_GET_ITEM(r->control_file,1),Py_EQ)==1
  &&PyObject_RichCompareBool(inode,PyTuple_GET_ITEM(r->control_file,2),Py_EQ)==1;
 Py_XDECREF(device);Py_XDECREF(inode);Py_XDECREF(mode);Py_DECREF(stat);if(!same)return 0;
 PyObject*b=r->control,*ctrl=r->control_connection,*times=r->control_times;
 PyObject*kind=PyDict_GetItemString(commit_outcome_globals,"_sqlite_dbapi");
 if(!ctrl||!times||(PyObject*)Py_TYPE(ctrl)!=kind||(PyObject*)Py_TYPE(r->raw)!=kind)return 0;
 PyObject*factory=PyObject_GetAttrString(ctrl,"row_factory"),*active=PyObject_GetAttrString(ctrl,"in_transaction");
 int valid=factory==Py_None&&active==Py_True;Py_XDECREF(factory);Py_XDECREF(active);if(!valid)return 0;
 PyObject*execute=PyDict_GetItemString(commit_outcome_globals,"_sqlite_execute"),*fetch=PyDict_GetItemString(commit_outcome_globals,"_sqlite_fetchone");
 PyObject*sql=PyUnicode_FromString("SELECT header,nonce,state,lease_wall,absolute_deadline,intent,pending_commit,acked_commit FROM leases WHERE run_id=?");
 PyObject*params=PyTuple_Pack(1,PyTuple_GET_ITEM(b,9)),*cursor=NULL,*row=NULL;
 if(sql&&params)cursor=PyObject_CallFunctionObjArgs(execute,ctrl,sql,params,NULL);
 if(cursor)row=PyObject_CallOneArg(fetch,cursor);
 Py_XDECREF(sql);Py_XDECREF(params);Py_XDECREF(cursor);
 if(!row||!PyTuple_CheckExact(row)||PyTuple_GET_SIZE(row)!=8)goto done;
 PyObject*effect=PyTuple_GET_ITEM(b,10);
 if(!PyTuple_CheckExact(effect)||PyTuple_GET_SIZE(effect)!=2)goto done;
 PyObject*commit=PyTuple_GET_ITEM(effect,0);
 if(!commit||!PyUnicode_CheckExact(commit)||!PyUnicode_CheckExact(PyTuple_GET_ITEM(row,0))
  ||!PyUnicode_CheckExact(PyTuple_GET_ITEM(row,1))||!PyUnicode_CheckExact(PyTuple_GET_ITEM(row,2))
  ||!PyUnicode_CheckExact(PyTuple_GET_ITEM(row,6)))goto done;
 if(PyUnicode_Compare(PyTuple_GET_ITEM(row,0),PyTuple_GET_ITEM(b,2))
   ||PyUnicode_Compare(PyTuple_GET_ITEM(row,1),PyTuple_GET_ITEM(b,3))
   ||PyUnicode_CompareWithASCIIString(PyTuple_GET_ITEM(row,2),"ACTIVE")
   ||PyTuple_GET_ITEM(row,5)!=Py_None||PyUnicode_Compare(PyTuple_GET_ITEM(row,6),commit)
   ||(PyUnicode_CheckExact(PyTuple_GET_ITEM(row,7))&&!PyUnicode_Compare(PyTuple_GET_ITEM(row,7),commit)))goto done;
 /* Everything after SQL/JSON callbacks is a pure current stop/time check.
  * The control write lock still excludes cancellation/takeover commits. */
 r->control_wall_limit=PyFloat_AsDouble(PyTuple_GET_ITEM(row,3));r->control_absolute_limit=PyFloat_AsDouble(PyTuple_GET_ITEM(row,4));
 valid=!PyErr_Occurred();Py_DECREF(row);return valid;
done:Py_XDECREF(row);return 0;
}
static PyObject*invoke_commit_outcome(PyObject*self,PyObject*args){
 (void)self;PyObject*boundary,*proxy;if(!PyArg_ParseTuple(args,"OO",&boundary,&proxy))return NULL;
 if(!commit_outcome_code_current()){if(PyErr_Occurred())return NULL;return commit_outcome_error();}
 int gc=PyGC_Disable();PyObject*locals=commit_frame_locals(commit_outcome_guarded_code),*fields=NULL,*result=NULL;
 PyObject*key=PyLong_FromVoidPtr(boundary),*held=NULL;
 if(key&&commit_outcome_records){held=Py_XNewRef(PyDict_GetItemWithError(commit_outcome_records,key));}
 CommitOutcomeRecord*r=find_commit_outcome(boundary);
 const char*stage="issued frame/class/closure";
 if(!r||!commit_factory_current(r->factory)||r->invoked||!locals||PyDict_GetItemString(locals,"entry")!=boundary
   ||PyDict_GetItemString(locals,"proxy")!=proxy||PyDict_GetItemString(locals,"raw")!=r->raw
   ||PyDict_GetItemString(locals,"owner")!=r->connection||PyDict_GetItemString(locals,"transaction")!=r->transaction
   ||PyDict_GetItemString(locals,"original")!=r->original||PyFunction_GetCode(r->guarded)!=commit_outcome_guarded_code
   ||!commit_closure_current(r->guarded,locals))goto done;
 if(!commit_physical_current(r,proxy,1))goto done;
 stage="held boundary fields";
 fields=PyObject_GenericGetDict(boundary,NULL);
 if(!fields||!code_namespace(fields)||PyDict_GetItemString(fields,"c")!=r->connection
   ||PyDict_GetItemString(fields,"raw")!=r->raw||PyDict_GetItemString(fields,"transaction")!=r->transaction)goto done;
 PyObject*entries=PyDict_GetItemString(locals,"entries");
 PyObject*factory_state=commit_factory_record(r->factory);
 stage="private entries/engine";
 if(!entries||entries!=PyTuple_GET_ITEM(factory_state,3)
   ||!PyDict_CheckExact(entries)||PyDict_GetItemWithError(entries,r->raw)!=boundary)goto done;
 if(r->control){
  if(gc){PyGC_Enable();gc=0;}
  stage="current control lease/deadline/stop";
  if(!commit_control_current(r))goto done;
  gc=PyGC_Disable();
  if(!lease_actor_current()||!commit_outcome_code_current()||!commit_physical_current(r,proxy,1)
    ||!commit_factory_current(r->factory)||!commit_control_clocks(r))goto done;
  PyObject*count=PyObject_GetAttrString(r->raw,"total_changes"),*expected=PyDict_GetItemString(locals,"changes");
  int same=count&&expected&&PyLong_CheckExact(count)&&PyLong_CheckExact(expected)&&PyObject_RichCompareBool(count,expected,Py_EQ)==1;
  Py_XDECREF(count);if(!same)goto done;
 }
 r->invoked=1;
 Py_CLEAR(locals);Py_CLEAR(fields);
 if(gc){PyGC_Enable();gc=0;}
 /* DefaultDialect's documented argument is the actual DBAPI connection.
  * Fix this physical target even if a Python monitoring/GC callback changes
  * the pool proxy after the last metadata check. The hook still runs once. */
 r->in_delegate=1;
 result=(r->control?PyObject_CallOneArg(PyDict_GetItemString(commit_outcome_globals,"_sqlite_commit"),r->raw)
                    :PyObject_CallOneArg(r->original,r->raw));
 r->in_delegate=0;
 if(result){
  r->committed=1;
  if(!commit_physical_current(r,proxy,1)){Py_CLEAR(result);}
 }
done:
 Py_XDECREF(locals);Py_XDECREF(fields);Py_XDECREF(key);Py_XDECREF(held);if(gc)PyGC_Enable();
 if(!result){if(PyErr_Occurred())return NULL;PyErr_Format(PyExc_ValueError,"Commit outcome provenance changed (%s)",stage);return NULL;}return result;
}
static PyObject*contract_type(PyObject*self,PyObject*value){
 PyObject*model=contract_model(self,value);if(!model)return NULL;if(model!=Py_None)return model;Py_DECREF(model);return Py_NewRef((PyObject*)Py_TYPE(value));
}
static PyObject*register_contract_binding(PyObject*self,PyObject*args){
 (void)self;PyObject*cls,*version;if(!PyArg_ParseTuple(args,"OO",&cls,&version))return NULL;
 if(contract_binding_type||!PyType_Check(cls)||!PyUnicode_CheckExact(version))return view_error();
 PyObject*fn=PyDict_GetItemString(((PyTypeObject*)cls)->tp_dict,"__post_init__");if(!fn||!PyFunction_Check(fn))return view_error();
 PyObject*keys=Py_BuildValue("(sssss)","contract","approval_key","account_id","contract_fingerprint","version"),*registry=PyDict_New();
 if(!keys||!registry){Py_XDECREF(keys);Py_XDECREF(registry);return NULL;}
 contract_binding_type=Py_NewRef(cls);contract_binding_code=Py_NewRef(PyFunction_GetCode(fn));contract_binding_globals=Py_NewRef(PyFunction_GetGlobals(fn));
 contract_binding_version=Py_NewRef(version);contract_binding_keys=keys;contract_bindings=registry;Py_RETURN_NONE;
}
static PyObject*contract_binding_error(void){PyErr_SetString(PyExc_ValueError,"PB binding ownership or lifecycle changed");return NULL;}
static PyObject*contract_binding_forget(PyObject*key,PyObject*weak){
 if(contract_bindings){PyObject*entry=PyDict_GetItemWithError(contract_bindings,key);
  if(entry&&PyTuple_CheckExact(entry)&&PyTuple_GET_ITEM(entry,0)==weak){if(PyDict_DelItem(contract_bindings,key)<0)return NULL;}
  else if(PyErr_Occurred())return NULL;}
 Py_RETURN_NONE;
}
static PyMethodDef contract_binding_forget_def={"_pb_binding_forget",contract_binding_forget,METH_O,NULL};
static int contract_binding_fields(PyObject*fields,PyObject*view,PyObject*header){
 if(!code_namespace(fields)||!PyTuple_CheckExact(header)||PyTuple_GET_SIZE(header)!=4)return 0;
 PyObject*actual=PyDict_GetItemWithError(fields,PyTuple_GET_ITEM(contract_binding_keys,0));
 if(!actual||Py_TYPE(actual)!=&SourceViewType||Py_TYPE(view)!=&SourceViewType)return 0;
 SourceView*a=(SourceView*)actual,*b=(SourceView*)view;
 if(a->owner!=b->owner||a->ref!=b->ref||a->ref!=a->owner->contract_ref)return 0;
 for(int i=0;i<3;i++)if(PyDict_GetItemWithError(fields,PyTuple_GET_ITEM(contract_binding_keys,i+1))!=PyTuple_GET_ITEM(header,i))return 0;
 PyObject*version=PyDict_GetItemWithError(fields,PyTuple_GET_ITEM(contract_binding_keys,4));
 if(!version)version=PyDict_GetItemWithError(((PyTypeObject*)contract_binding_type)->tp_dict,PyTuple_GET_ITEM(contract_binding_keys,4));
 return version==PyTuple_GET_ITEM(header,3)&&version==contract_binding_version;
}
static int contract_constructor_frame(PyObject*binding,PyObject*checked){
 PyFrameObject*frame=PyThreadState_GetFrame(PyThreadState_Get());int found=0;
 for(int i=0;frame&&i<3;i++){
  PyCodeObject*code=PyFrame_GetCode(frame);PyObject*globals=PyFrame_GetGlobals(frame);
  if((PyObject*)code==contract_binding_code&&globals==contract_binding_globals){
   PyObject*locals=PyFrame_GetLocals(frame);if(locals){found=code_namespace(locals)&&PyDict_GetItemString(locals,"self")==binding&&PyDict_GetItemString(locals,"checked")==checked;Py_DECREF(locals);}
  }
  Py_DECREF(code);Py_DECREF(globals);PyFrameObject*back=PyFrame_GetBack(frame);Py_DECREF(frame);frame=back;
  if(found)break;
 }
 Py_XDECREF(frame);return found;
}
static int contract_late_current(void){
 PyObject*ok=verify_code_range(0,10);if(!ok)return 0;int same=ok==Py_True;Py_DECREF(ok);
 return same&&contract_schemas_current_internal();
}
/* The registered DATA reader executes no Python verifier, Graph, SQL or
 * authority code. Its complete dependencies are family nine, the original
 * Binding/model/schema witnesses and its private C registry/header below.
 * Installation and issuance retain their separate full 0..9 gates. */
static int contract_read_current(void){
 PyObject*ok=verify_code_range(9,10);if(!ok)return 0;int same=ok==Py_True;Py_DECREF(ok);
 return same&&contract_schemas_current_internal();
}
static int contract_origin_current(SourceView*view,PyObject*checked){
 Owned*o=view->owner;
 if(!o->contract_origin||PyWeakref_GetObject(o->contract_origin)!=checked||!o->contract_config||!contract_config_current(o->contract_config))return 0;
 PyObject*empty=PyTuple_New(0),*ref=PyLong_FromSsize_t(view->ref);if(!empty||!ref){Py_XDECREF(empty);Py_XDECREF(ref);return 0;}
 PyObject*same=source_match_current((PyObject*)o,checked,empty,o->contract_config,Py_None,ref);Py_DECREF(empty);Py_DECREF(ref);
 if(!same)return 0;int ok=same==Py_True;Py_DECREF(same);return ok;
}
/* Publish DATA and its original immutable header, never an authority result.
 * Registry entries hold weak Binding identity. Every consumer rechecks actual
 * fields/code/schema; neither a raw __dict__ swap nor equal cross-owner data
 * can borrow a previous lifecycle. Provisional entries cannot be consumed. */
static PyObject*install_contract_binding(PyObject*self,PyObject*args){
 (void)self;PyObject*binding,*view,*checked,*key,*account;
 if(!PyArg_ParseTuple(args,"OOOOO",&binding,&view,&checked,&key,&account))return NULL;
 if(!contract_bindings||(PyObject*)Py_TYPE(binding)!=contract_binding_type||Py_TYPE(view)!=&SourceViewType||!PyUnicode_CheckExact(key)||!PyUnicode_CheckExact(account))return contract_binding_error();
 SourceView*v=(SourceView*)view;if(!v->owner->contract_models||v->ref!=v->owner->contract_ref||!v->owner->contract_fp)return contract_binding_error();
 PyObject*identity=PyLong_FromVoidPtr(binding),*fields=NULL,*again=NULL,*weak=NULL,*callback=NULL,*header=NULL,*pending=NULL,*complete=NULL,*old=NULL,*old_fp=NULL,*error=NULL;
 int inserted=0;if(!identity)return NULL;
 if(PyDict_Contains(contract_bindings,identity)!=0)goto invalid;
 if(!contract_constructor_frame(binding,checked))goto invalid;
 fields=PyObject_GenericGetDict(binding,NULL);if(!fields)goto done;
 if(!code_namespace(fields)||PyDict_GetItemWithError(fields,PyTuple_GET_ITEM(contract_binding_keys,1))!=key||PyDict_GetItemWithError(fields,PyTuple_GET_ITEM(contract_binding_keys,2))!=account)goto invalid;
 callback=PyCFunction_New(&contract_binding_forget_def,identity);if(!callback)goto done;
 weak=PyWeakref_NewRef(binding,callback);if(!weak)goto done;
 header=PyTuple_Pack(4,key,account,v->owner->contract_fp,contract_binding_version);if(!header)goto done;
 pending=PyTuple_Pack(4,weak,view,header,Py_False);complete=PyTuple_Pack(4,weak,view,header,Py_True);if(!pending||!complete)goto done;
 old=Py_XNewRef(PyDict_GetItemWithError(fields,PyTuple_GET_ITEM(contract_binding_keys,0)));
 old_fp=Py_XNewRef(PyDict_GetItemWithError(fields,PyTuple_GET_ITEM(contract_binding_keys,3)));
 again=PyObject_GenericGetDict(binding,NULL);if(!again)goto done;if(again!=fields)goto invalid;Py_CLEAR(again);
 if((PyObject*)Py_TYPE(binding)!=contract_binding_type||!contract_late_current()||!contract_origin_current(v,checked))goto invalid;
 if(PyDict_GetItemWithError(fields,PyTuple_GET_ITEM(contract_binding_keys,1))!=key||PyDict_GetItemWithError(fields,PyTuple_GET_ITEM(contract_binding_keys,2))!=account)goto invalid;
 /* Allocation/finalization above can reenter the constructor. Never replace
  * a lifecycle that finished during that interval, even for the same self. */
 if(PyDict_Contains(contract_bindings,identity)!=0)goto invalid;
 if(PyDict_SetItem(contract_bindings,identity,pending)<0)goto done;inserted=1;
 if(PyDict_SetItem(fields,PyTuple_GET_ITEM(contract_binding_keys,0),view)<0||PyDict_SetItem(fields,PyTuple_GET_ITEM(contract_binding_keys,3),v->owner->contract_fp)<0)goto done;
 /* Retire replaced objects BEFORE the final proof. Their finalizers can run;
  * consumers still see a provisional, unusable registry entry during this. */
 Py_CLEAR(old);Py_CLEAR(old_fp);
 again=PyObject_GenericGetDict(binding,NULL);if(!again)goto done;
 if(again!=fields||(PyObject*)Py_TYPE(binding)!=contract_binding_type||!contract_late_current()||!contract_origin_current(v,checked)||!contract_binding_fields(fields,view,header))goto invalid;
 if(PyDict_SetItem(contract_bindings,identity,complete)<0)goto done;
 inserted=0;
 goto done;
 invalid:if(!PyErr_Occurred())contract_binding_error();
 done:error=PyErr_GetRaisedException();
 if(inserted&&PyDict_DelItem(contract_bindings,identity)<0)PyErr_Clear();
 Py_XDECREF(old);Py_XDECREF(old_fp);Py_XDECREF(again);Py_XDECREF(fields);Py_XDECREF(pending);Py_XDECREF(complete);Py_XDECREF(header);Py_XDECREF(weak);Py_XDECREF(callback);Py_DECREF(identity);
 if(error){PyErr_SetRaisedException(error);return NULL;}Py_RETURN_NONE;
}
static PyObject*contract_binding_current(PyObject*self,PyObject*binding){
 (void)self;if(!contract_bindings||(PyObject*)Py_TYPE(binding)!=contract_binding_type)return contract_binding_error();
 PyObject*key=PyLong_FromVoidPtr(binding);if(!key)return NULL;PyObject*entry=Py_XNewRef(PyDict_GetItemWithError(contract_bindings,key));Py_DECREF(key);
 if(!entry){
  if(PyErr_Occurred())return NULL;
  /* An owned root is never eligible for the mutable legacy fallback. */
  PyObject*fields=PyObject_GenericGetDict(binding,NULL);if(!fields)return NULL;
  if(!code_namespace(fields)||(PyObject*)Py_TYPE(binding)!=contract_binding_type){Py_DECREF(fields);return contract_binding_error();}
  PyObject*actual=PyObject_GenericGetDict(binding,NULL);if(!actual){Py_DECREF(fields);return NULL;}
  int same=actual==fields;Py_DECREF(actual);if(!same){Py_DECREF(fields);return contract_binding_error();}
  PyObject*value=PyDict_GetItemWithError(fields,PyTuple_GET_ITEM(contract_binding_keys,0));
  int owned=value&&Py_TYPE(value)==&SourceViewType&&((SourceView*)value)->owner->contract_models;
  Py_DECREF(fields);if(PyErr_Occurred())return NULL;if(owned)return contract_binding_error();Py_RETURN_NONE;
 }
 PyObject*fields=PyObject_GenericGetDict(binding,NULL),*again=NULL,*result=NULL;
 if(!fields)goto done;
 again=PyObject_GenericGetDict(binding,NULL);if(!again)goto done;
 if(again!=fields||(PyObject*)Py_TYPE(binding)!=contract_binding_type||!PyTuple_CheckExact(entry)||PyTuple_GET_SIZE(entry)!=4||PyTuple_GET_ITEM(entry,3)!=Py_True||PyWeakref_GetObject(PyTuple_GET_ITEM(entry,0))!=binding||!contract_read_current()||!contract_binding_fields(fields,PyTuple_GET_ITEM(entry,1),PyTuple_GET_ITEM(entry,2)))goto invalid;
 result=Py_NewRef(PyTuple_GET_ITEM(entry,1));goto done;
 invalid:if(!PyErr_Occurred())contract_binding_error();
 done:Py_XDECREF(again);Py_XDECREF(fields);Py_DECREF(entry);return result;
}
static PyObject*source_view_pin(PyObject*self,PyObject*v){
 (void)self;if(Py_TYPE(v)!=&SourceViewType){PyErr_SetString(PyExc_TypeError,"Exact immutable Source view required");return NULL;}
 return view_pin(v,NULL);
}
static PyMethodDef methods[]={
 {"register_contract_models",register_contract_models,METH_VARARGS,"Register the separate complete PB model domain once; never authority."},
 {"make_contract_owned",make_contract_owned,METH_VARARGS,"Complete graph-neutral model/dump data handoff; never a scoped PASS."},
 {"contract_model",contract_model,METH_O,"Exact original model class of an immutable PB view, or None."},
 {"contract_fingerprint",contract_fingerprint,METH_O,"Original canonical JSON SHA256 of immutable PB DATA, never an approval."},
 {"contract_json",contract_json,METH_O,"Original canonical UTF8 JSON of immutable PB DATA."},
 {"contract_dump",contract_dump,METH_O,"Exact immutable canonical model-dump view, sharing the full model owner."},
 {"register_contract_schemas",register_contract_schemas,METH_VARARGS,"Original complete schema/code expectations, never model data or a PASS."},
 {"contract_schema_current",contract_schema_current,METH_NOARGS,"Fresh complete live PB schema configuration, with no Python callback."},
 {"contract_entry",contract_entry,METH_NOARGS,"Fresh fixed Python data-entry roles before any foreign dispatch."},
 {"lease_entry",lease_entry,METH_NOARGS,"Fresh independent lease-control code roles; never a lease or authority result."},
 {"lease_actor_entry",lease_actor_entry,METH_NOARGS,"Fresh lease-control and original Store actor code roles."},
 {"register_lease_runtime",register_lease_runtime,METH_VARARGS,"One-time runtime issuer code, never authority."},
 {"install_lease_runtime",install_lease_runtime,METH_O,"Record actual runtime provenance from its fixed provisioning frame."},
 {"lease_runtime_current",lease_runtime_current,METH_O,"Fresh native runtime/Store identity, no lease or permission cache."},
 {"register_commit_outcomes",register_commit_outcomes,METH_VARARGS,"Fixed commit issuer and original delegate roles."},
 {"register_commit_factory",register_commit_factory,METH_VARARGS,"Pin a final per-engine Boundary class and guarded closure."},
 {"retire_commit_factory",retire_commit_factory,METH_O,"Retire issuance only; existing facts remain known."},
 {"init_commit_outcome",init_commit_outcome,METH_VARARGS,"Issue an opaque result record from the original Boundary constructor."},
 {"preinit_commit_outcome",preinit_commit_outcome,METH_O,"Reject borrowed constructors before any instance dispatch."},
 {"check_commit_outcome",check_commit_outcome,METH_O,"Check fixed actual Boundary class and private roles before dispatch."},
 {"read_commit_outcome",read_commit_outcome,METH_O,"Read actual original-delegate invocation/return facts."},
 {"find_commit_boundary",find_commit_boundary,METH_O,"Find only the actual entered scope for an owned main transaction."},
 {"read_commit_control",read_commit_control,METH_O,"Read immutable control binding, never a validation PASS."},
 {"bind_commit_control",bind_commit_control,METH_VARARGS,"Bind only from fixed Runtime main-transaction methods."},
 {"enter_commit_control",enter_commit_control,METH_VARARGS,"Enter only the issued Session generator's real control writer."},
 {"leave_commit_control",leave_commit_control,METH_O,"Leave only that same control writer scope."},
 {"read_commit_roles",read_commit_roles,METH_O,"Read original cleanup roles, never rejected mutable fields."},
 {"restore_commit_owner",restore_commit_owner,METH_O,"Restore the known owned Connection class before cleanup, never dispatch a rejected class."},
 {"retire_commit_roles",retire_commit_roles,METH_O,"Release heavy roles at actual scope exit, retaining facts."},
 {"invoke_commit_outcome",invoke_commit_outcome,METH_VARARGS,"Invoke the fixed original delegate only in its actual guarded frame."},
 {"contract_type",contract_type,METH_O,"Explicit PB schema class or original exact type; no Python getattr or impersonation."},
 {"register_contract_binding",register_contract_binding,METH_VARARGS,"Register the original production Binding lifecycle once, never a grant."},
 {"install_contract_binding",install_contract_binding,METH_VARARGS,"Constructor-only complete PB owner/header publication."},
 {"contract_binding_current",contract_binding_current,METH_O,"Fresh exact Binding/owner/header/schema/code join; never authority."},
 {"view_pin",source_view_pin,METH_O,"Complete immutable owner pin and exact node reference, not a semantic fingerprint."},
 {"match_ledger",match_ledger,METH_VARARGS,"Select and fully compare current source slots inside the same bounded interval."},
 {"read_owner",read_owner,METH_O,"Read a static immutable view of complete owned data."},
 {"register_code",register_code,METH_VARARGS,"One-time import code configuration; no data."},
 {"verify_code",verify_code,METH_NOARGS,"Fresh complete registered code and class metadata."},
 {"binding_owner",binding_owner,METH_O,"Exact immutable data owner of this binding."},
 {"matching",source_matching,METH_NOARGS,"Private numeric GC-callback test state, not authority."},
 {"diagnostic",source_diagnostic,METH_NOARGS,"Private numeric failure location only."},
 {"match_nodes",match_nodes,METH_VARARGS,"Fresh joint full storage/alias comparison for current Ledger slots."},
 {"match_node",match_node,METH_VARARGS,"Fresh full immutable image/current model storage join, not authority."},
 {"match_live",match_live,METH_VARARGS,"Private direct current-fact verifier; NOT authority or outside-boundary closure."},
 {"make_binding",make_binding,METH_VARARGS,"Scope data/anchor identity, never an authorization."},
 {"binding_current",binding_current,METH_VARARGS,"Exact nonce/epoch/phase and immutable owner identity."},
 {"binding_pin",binding_pin,METH_O,"Unique binding id plus complete data and current unconverted anchors."},
 {"make_owned",make_owned,METH_O,"Bounded immutable parsed facts with internally derived metadata."},
 {"make_composite",make_composite,METH_VARARGS,"Immutable facts with exact immutable parent owners; never a mutable parent or authority."},
 {"owned_data",owned_data,METH_O,"Read the exact immutable parsed data, never a re-decoded copy."},
 {"owned_pin",owned_pin,METH_O,"Complete metadata and every original immutable leaf."},
 {NULL,NULL,0,NULL}};
static struct PyModuleDef module={PyModuleDef_HEAD_INIT,"_cold_source_owned_impl",NULL,-1,methods,NULL,NULL,NULL,NULL};
PyMODINIT_FUNC PyInit__cold_source_owned_impl(void){
 if(PyType_Ready(&OwnedType)<0||PyType_Ready(&BindingType)<0||PyType_Ready(&SourceViewType)<0)return NULL;
 PyObject*m=PyModule_Create(&module);if(!m)return NULL;
 unsupported=PyCapsule_New((void*)&module,"source-owned-prototype.unsupported",NULL);
 if(!unsupported||PyModule_AddObjectRef(m,"UNSUPPORTED",unsupported)<0||PyModule_AddObjectRef(m,"Owned",(PyObject*)&OwnedType)<0
  ||PyModule_AddObjectRef(m,"Binding",(PyObject*)&BindingType)<0||PyModule_AddObjectRef(m,"View",(PyObject*)&SourceViewType)<0||PyModule_AddStringConstant(m,"SOURCE_SHA256",SOURCE_SHA)<0){Py_XDECREF(unsupported);Py_DECREF(m);return NULL;}
 return m;
}
