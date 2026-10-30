/* Import-time code configuration, never model data or a cached verdict. */
static PyObject*source_code[6]={NULL,NULL,NULL,NULL,NULL,NULL};
static int code_items(PyObject*dict,PyObject*items){
 if(!PyDict_CheckExact(dict)||!PyTuple_CheckExact(items)||PyDict_GET_SIZE(dict)!=PyTuple_GET_SIZE(items))return 0;
 Py_ssize_t pos=0,i=0;PyObject*k,*v;
 while(PyDict_Next(dict,&pos,&k,&v)){
  PyObject*pair=PyTuple_GET_ITEM(items,i++);
  if(!PyTuple_CheckExact(pair)||PyTuple_GET_SIZE(pair)!=2||k!=PyTuple_GET_ITEM(pair,0)||v!=PyTuple_GET_ITEM(pair,1))return 0;
 }return 1;
}
static int code_function(PyObject*entry,PyObject*namespace){
 if(!PyTuple_CheckExact(entry)||PyTuple_GET_SIZE(entry)!=6)return 0;
 PyObject*name=PyTuple_GET_ITEM(entry,0),*fn=PyTuple_GET_ITEM(entry,1),*kw=PyTuple_GET_ITEM(entry,4);
 if(!PyUnicode_CheckExact(name)||!PyFunction_Check(fn)||!PyDict_CheckExact(namespace))return 0;
 return PyDict_GetItemWithError(namespace,name)==fn&&PyFunction_GET_CODE(fn)==PyTuple_GET_ITEM(entry,2)
  &&(PyFunction_GET_DEFAULTS(fn)?PyFunction_GET_DEFAULTS(fn):Py_None)==PyTuple_GET_ITEM(entry,3)
  &&(PyFunction_GET_KW_DEFAULTS(fn)?PyFunction_GET_KW_DEFAULTS(fn):Py_None)==kw
  &&(kw==Py_None?PyTuple_CheckExact(PyTuple_GET_ITEM(entry,5))&&PyTuple_GET_SIZE(PyTuple_GET_ITEM(entry,5))==0:code_items(kw,PyTuple_GET_ITEM(entry,5)));
}
static PyObject*register_code(PyObject*self,PyObject*args){
 (void)self;int index;PyObject*record;
 if(!PyArg_ParseTuple(args,"iO",&index,&record))return NULL;
 if(index<0||index>=6||source_code[index]||!PyTuple_CheckExact(record)||PyTuple_GET_SIZE(record)!=3){PyErr_SetString(PyExc_RuntimeError,"Source code registration is one-time and complete");return NULL;}
 source_code[index]=Py_NewRef(record);Py_RETURN_NONE;
}
static PyObject*verify_code(PyObject*self,PyObject*unused){
 (void)self;(void)unused;int prior=PyGC_Disable(),ok=1;
 for(int index=0;ok&&index<6;index++){
  PyObject*record=source_code[index];if(!record){ok=0;break;}
  PyObject*witnesses=PyTuple_GET_ITEM(record,0),*classes=PyTuple_GET_ITEM(record,1);
  if(!PyTuple_CheckExact(witnesses)||!PyTuple_CheckExact(classes)){ok=0;break;}
  for(Py_ssize_t i=0;ok&&i<PyTuple_GET_SIZE(witnesses);i++){
   PyObject*w=PyTuple_GET_ITEM(witnesses,i);if(!PyTuple_CheckExact(w)||PyTuple_GET_SIZE(w)!=2){ok=0;break;}
   PyObject*namespace=PyTuple_GET_ITEM(w,0),*entries=PyTuple_GET_ITEM(w,1);if(!PyTuple_CheckExact(entries)){ok=0;break;}
   for(Py_ssize_t j=0;ok&&j<PyTuple_GET_SIZE(entries);j++)ok=code_function(PyTuple_GET_ITEM(entries,j),namespace);
  }
  PyObject*constants=PyTuple_GET_ITEM(record,2);
  if(!PyTuple_CheckExact(constants)){ok=0;break;}
  for(Py_ssize_t i=0;ok&&i<PyTuple_GET_SIZE(constants);i++){
   PyObject*entry=PyTuple_GET_ITEM(constants,i);if(!PyTuple_CheckExact(entry)||PyTuple_GET_SIZE(entry)!=2){ok=0;break;}
   PyObject*space=PyTuple_GET_ITEM(entry,0),*items=PyTuple_GET_ITEM(entry,1);if(!PyDict_CheckExact(space)||!PyTuple_CheckExact(items)){ok=0;break;}
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
