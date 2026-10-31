/* Import-time code configuration, never model data or a cached verdict. */
#define SOURCE_CODE_FAMILIES 9
static PyObject*source_code[SOURCE_CODE_FAMILIES]={NULL};
static int code_items(PyObject*dict,PyObject*items){
 if(!PyDict_CheckExact(dict)||!PyTuple_CheckExact(items)||PyDict_GET_SIZE(dict)!=PyTuple_GET_SIZE(items))return 0;
 Py_ssize_t pos=0,i=0;PyObject*k,*v;
 while(PyDict_Next(dict,&pos,&k,&v)){
  PyObject*pair=PyTuple_GET_ITEM(items,i++);
  if(!PyTuple_CheckExact(pair)||PyTuple_GET_SIZE(pair)!=2||k!=PyTuple_GET_ITEM(pair,0)||v!=PyTuple_GET_ITEM(pair,1))return 0;
 }return 1;
}
static int code_namespace(PyObject*space){
 if(!PyDict_CheckExact(space))return 0;
 Py_ssize_t pos=0;PyObject*k,*v;
 while(PyDict_Next(space,&pos,&k,&v))if(!PyUnicode_CheckExact(k))return 0;
 return 1;
}
/* One pure module-witness segment, not a remembered code verdict. Once all
 * keys are exact Unicode, its remaining identity/field checks cannot invoke
 * Python. The caller holds the GIL and disables GC. Forget this table before
 * the class-method segment, whose dictionary lookups may have foreign keys.
 * An unusually large registry simply keeps the original complete scans. */
#define SOURCE_NAMESPACE_SLOTS 64
static int code_namespace_once(PyObject*space,PyObject**seen,Py_ssize_t*used){
 for(Py_ssize_t i=0;i<*used;i++)if(seen[i]==space)return 1;
 if(!code_namespace(space))return 0;
 if(*used<SOURCE_NAMESPACE_SLOTS)seen[(*used)++]=space;
 return 1;
}
static int code_state(PyObject*state,int depth){
 if(depth>64||!PyTuple_CheckExact(state)||PyTuple_GET_SIZE(state)!=7)return 0;
 PyObject*fn=PyTuple_GET_ITEM(state,0),*kw=PyTuple_GET_ITEM(state,3),*closure=PyTuple_GET_ITEM(state,5),*cells=PyTuple_GET_ITEM(state,6);
 if(!PyFunction_Check(fn)||PyFunction_GET_CODE(fn)!=PyTuple_GET_ITEM(state,1)
   ||(PyFunction_GET_DEFAULTS(fn)?PyFunction_GET_DEFAULTS(fn):Py_None)!=PyTuple_GET_ITEM(state,2)
   ||(PyFunction_GET_KW_DEFAULTS(fn)?PyFunction_GET_KW_DEFAULTS(fn):Py_None)!=kw
   ||(PyFunction_GET_CLOSURE(fn)?PyFunction_GET_CLOSURE(fn):Py_None)!=closure
   ||!PyTuple_CheckExact(cells))return 0;
 if(kw==Py_None){if(!PyTuple_CheckExact(PyTuple_GET_ITEM(state,4))||PyTuple_GET_SIZE(PyTuple_GET_ITEM(state,4)))return 0;}
 else if(!code_items(kw,PyTuple_GET_ITEM(state,4)))return 0;
 if(closure==Py_None)return PyTuple_GET_SIZE(cells)==0;
 if(!PyTuple_CheckExact(closure)||PyTuple_GET_SIZE(closure)!=PyTuple_GET_SIZE(cells))return 0;
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(cells);i++){
  PyObject*record=PyTuple_GET_ITEM(cells,i),*cell=PyTuple_GET_ITEM(closure,i);
  if(!PyTuple_CheckExact(record)||PyTuple_GET_SIZE(record)!=3||!PyCell_Check(cell)||cell!=PyTuple_GET_ITEM(record,0)||PyCell_GET(cell)!=PyTuple_GET_ITEM(record,1))return 0;
  PyObject*nested=PyTuple_GET_ITEM(record,2);if(nested!=Py_None&&!code_state(nested,depth+1))return 0;
 }
 return 1;
}
static int code_function(PyObject*entry,PyObject*namespace){
 if(!PyTuple_CheckExact(entry)||PyTuple_GET_SIZE(entry)!=3||!PyDict_CheckExact(namespace))return 0;
 PyObject*name=PyTuple_GET_ITEM(entry,0),*states=PyTuple_GET_ITEM(entry,2);
 if(!PyUnicode_CheckExact(name)||!PyTuple_CheckExact(states)||PyDict_GetItemWithError(namespace,name)!=PyTuple_GET_ITEM(entry,1))return 0;
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(states);i++)if(!code_state(PyTuple_GET_ITEM(states,i),0))return 0;
 return 1;
}
static PyObject*register_code(PyObject*self,PyObject*args){
 (void)self;int index;PyObject*record;
 if(!PyArg_ParseTuple(args,"iO",&index,&record))return NULL;
 if(index<0||index>=SOURCE_CODE_FAMILIES||source_code[index]||!PyTuple_CheckExact(record)||PyTuple_GET_SIZE(record)!=3){PyErr_SetString(PyExc_RuntimeError,"Source code registration is one-time and complete");return NULL;}
 source_code[index]=Py_NewRef(record);Py_RETURN_NONE;
}
static PyObject*verify_code(PyObject*self,PyObject*unused){
 (void)self;(void)unused;int prior=PyGC_Disable(),ok=1;
 for(int index=0;ok&&index<SOURCE_CODE_FAMILIES;index++){
  PyObject*seen_namespaces[SOURCE_NAMESPACE_SLOTS];Py_ssize_t used_namespaces=0;
  PyObject*record=source_code[index];if(!record){ok=0;break;}
  PyObject*witnesses=PyTuple_GET_ITEM(record,0),*classes=PyTuple_GET_ITEM(record,1);
  if(!PyTuple_CheckExact(witnesses)||!PyTuple_CheckExact(classes)){ok=0;break;}
  for(Py_ssize_t i=0;ok&&i<PyTuple_GET_SIZE(witnesses);i++){
   PyObject*w=PyTuple_GET_ITEM(witnesses,i);if(!PyTuple_CheckExact(w)||PyTuple_GET_SIZE(w)!=2){ok=0;break;}
   PyObject*namespace=PyTuple_GET_ITEM(w,0),*entries=PyTuple_GET_ITEM(w,1);if(!PyTuple_CheckExact(entries)||!code_namespace_once(namespace,seen_namespaces,&used_namespaces)){ok=0;break;}
   for(Py_ssize_t j=0;ok&&j<PyTuple_GET_SIZE(entries);j++)ok=code_function(PyTuple_GET_ITEM(entries,j),namespace);
  }
  PyObject*constants=PyTuple_GET_ITEM(record,2);
  if(!PyTuple_CheckExact(constants)){ok=0;break;}
  for(Py_ssize_t i=0;ok&&i<PyTuple_GET_SIZE(constants);i++){
   PyObject*entry=PyTuple_GET_ITEM(constants,i);if(!PyTuple_CheckExact(entry)||PyTuple_GET_SIZE(entry)!=2){ok=0;break;}
   PyObject*space=PyTuple_GET_ITEM(entry,0),*items=PyTuple_GET_ITEM(entry,1);if(!code_namespace_once(space,seen_namespaces,&used_namespaces)||!PyTuple_CheckExact(items)){ok=0;break;}
   for(Py_ssize_t j=0;ok&&j<PyTuple_GET_SIZE(items);j++){
    PyObject*pair=PyTuple_GET_ITEM(items,j);if(!PyTuple_CheckExact(pair)||PyTuple_GET_SIZE(pair)!=2||!PyUnicode_CheckExact(PyTuple_GET_ITEM(pair,0))||PyDict_GetItemWithError(space,PyTuple_GET_ITEM(pair,0))!=PyTuple_GET_ITEM(pair,1))ok=0;
   }
  }
  for(Py_ssize_t i=0;ok&&i<PyTuple_GET_SIZE(classes);i++){
   PyObject*e=PyTuple_GET_ITEM(classes,i);if(!PyTuple_CheckExact(e)||PyTuple_GET_SIZE(e)!=5){ok=0;break;}
   PyObject*cls=PyTuple_GET_ITEM(e,0),*methods=PyTuple_GET_ITEM(e,4);
   if(!PyType_Check(cls)||(PyObject*)Py_TYPE(cls)!=PyTuple_GET_ITEM(e,1)||((PyTypeObject*)cls)->tp_mro!=PyTuple_GET_ITEM(e,2)||!code_items(((PyTypeObject*)cls)->tp_dict,PyTuple_GET_ITEM(e,3))||!PyTuple_CheckExact(methods)){ok=0;break;}
   for(Py_ssize_t j=0;ok&&j<PyTuple_GET_SIZE(methods);j++)ok=code_function(PyTuple_GET_ITEM(methods,j),((PyTypeObject*)cls)->tp_dict);
  }
 }
 if(prior)PyGC_Enable();
 if(PyErr_Occurred())return NULL;
 return PyBool_FromLong(ok);
}
