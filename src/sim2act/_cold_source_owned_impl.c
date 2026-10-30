#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <marshal.h>
#include <stdint.h>
#if defined(Py_GIL_DISABLED) && Py_GIL_DISABLED
#error "This uninstalled live matcher requires the CPython GIL"
#endif
/* Prototype immutable parsed data owner. No model/row/permission object may
 * enter data. Wire metadata is derived here, never supplied by a caller. */
typedef struct {PyObject_HEAD PyObject *data,*pin,*parents;unsigned int depth;} Owned;
static PyTypeObject OwnedType;
typedef struct {PyObject_HEAD Owned*owner;Py_ssize_t ref;} SourceView;
static PyTypeObject SourceViewType;
static PyObject *unsupported;
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
 Py_XDECREF(o->data);Py_XDECREF(o->pin);Py_XDECREF(o->parents);Py_TYPE(v)->tp_free(v);
 if(error)PyErr_SetRaisedException(error);
}
static PyObject*no_new(PyTypeObject*t,PyObject*a,PyObject*k){
 (void)t;(void)a;(void)k;PyErr_SetString(PyExc_TypeError,"Owned facts require their bounded factory");return NULL;
}
static PyTypeObject OwnedType={PyVarObject_HEAD_INIT(NULL,0)
 .tp_name="_cold_source_owned_impl.Owned",.tp_basicsize=sizeof(Owned),
 .tp_flags=Py_TPFLAGS_DEFAULT|Py_TPFLAGS_IMMUTABLETYPE,.tp_new=no_new,.tp_dealloc=owned_free};
#include "_cold_source_shape.h"
static PyObject*make_owned_core(PyObject*data,PyObject*parents){
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
 if(!source_image_shape(data))return Py_NewRef(unsupported);
 PyObject*nodes=PyTuple_GET_ITEM(data,1);
 unsigned char used_parents[256]={0};
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(nodes);i++){
  PyObject*node=PyTuple_GET_ITEM(nodes,i);
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
 o->data=Py_NewRef(data);o->pin=pin;o->parents=Py_NewRef(parents);o->depth=depth;return (PyObject*)o;
}
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
 PyObject*pin=PyTuple_Pack(3,serial,((Owned*)owner)->pin,anchors);Py_DECREF(serial);if(!pin)return NULL;
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
static PyObject*source_view_pin(PyObject*self,PyObject*v){
 (void)self;if(Py_TYPE(v)!=&SourceViewType){PyErr_SetString(PyExc_TypeError,"Exact immutable Source view required");return NULL;}
 return view_pin(v,NULL);
}
static PyMethodDef methods[]={
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
