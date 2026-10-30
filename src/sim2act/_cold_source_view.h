/* Read-only business views over an exact immutable Owner. No Python class,
 * serializer, getattr hook or module-global read callback participates. */
static PyObject*view_read(Owned*,Py_ssize_t);
static int view_node(SourceView*v,Py_UCS4*tag,PyObject**payload){
 PyObject*data=v->owner->data;
 if(!PyTuple_CheckExact(data)||PyTuple_GET_SIZE(data)!=8)return 0;
 PyObject*nodes=PyTuple_GET_ITEM(data,1);
 if(!PyTuple_CheckExact(nodes)||v->ref<0||v->ref>=PyTuple_GET_SIZE(nodes))return 0;
 PyObject*node=PyTuple_GET_ITEM(nodes,v->ref);
 if(!PyTuple_CheckExact(node)||PyTuple_GET_SIZE(node)!=2)return 0;
 PyObject*t=PyTuple_GET_ITEM(node,0);if(!PyUnicode_CheckExact(t)||PyUnicode_GET_LENGTH(t)!=1)return 0;
 *tag=PyUnicode_READ_CHAR(t,0);*payload=PyTuple_GET_ITEM(node,1);return 1;
}
static PyObject*view_error(void){PyErr_SetString(PyExc_TypeError,"Malformed immutable Source view");return NULL;}
static void view_free(PyObject*o){Py_DECREF(((SourceView*)o)->owner);PyObject_Del(o);}
static PyObject*view_read_ref(SourceView*v,PyObject*r){
 Py_ssize_t ref;if(!PyLong_CheckExact(r)||(ref=PyLong_AsSsize_t(r))<0){if(PyErr_Occurred())return NULL;return view_error();}
 return view_read(v->owner,ref);
}
static PyObject*view_body(PyObject*o,PyObject*unused){
 (void)unused;SourceView*v=(SourceView*)o;Py_UCS4 tag;PyObject*p;
 if(!view_node(v,&tag,&p))return view_error();
 return Py_NewRef(PyTuple_GET_ITEM(PyTuple_GET_ITEM(v->owner->data,1),v->ref));
}
static PyObject*view_data(PyObject*o,PyObject*unused){(void)unused;return Py_NewRef(((SourceView*)o)->owner->data);}
static PyObject*view_ref(PyObject*o,PyObject*unused){(void)unused;return PyLong_FromSsize_t(((SourceView*)o)->ref);}
static PyObject*view_owner(PyObject*o,PyObject*unused){(void)unused;return Py_NewRef((PyObject*)((SourceView*)o)->owner);}
static PyObject*view_pin(PyObject*o,PyObject*unused){
 (void)unused;SourceView*v=(SourceView*)o;PyObject*ref=PyLong_FromSsize_t(v->ref);if(!ref)return NULL;
 PyObject*r=PyTuple_Pack(2,v->owner->pin,ref);Py_DECREF(ref);return r;
}
static PyObject*view_child(PyObject*o,PyObject*r){return view_read_ref((SourceView*)o,r);}
static PyObject*view_label(PyObject*o,PyObject*unused){
 (void)unused;SourceView*v=(SourceView*)o;Py_UCS4 tag;PyObject*p;
 if(!view_node(v,&tag,&p)||tag!='u')return view_error();
 return view_read_ref(v,p);
}
static PyObject*view_getitem(PyObject*o,PyObject*key){
 SourceView*v=(SourceView*)o;Py_UCS4 tag;PyObject*p;
 if(!view_node(v,&tag,&p))return view_error();
 if(tag=='m'){
  if(!PyTuple_CheckExact(p)||PyTuple_GET_SIZE(p)!=5)return view_error();
  PyObject*raw=view_read_ref(v,PyTuple_GET_ITEM(p,1));if(!raw)return NULL;
  if(Py_TYPE(raw)!=&SourceViewType){Py_DECREF(raw);return view_error();}
  PyObject*result=view_getitem(raw,key);Py_DECREF(raw);return result;
 }
 if(tag=='r'){
  if(!PyTuple_CheckExact(p)||PyTuple_GET_SIZE(p)!=3)return view_error();
  PyObject*index=view_read_ref(v,PyTuple_GET_ITEM(p,2));if(!index)return NULL;
  if(Py_TYPE(index)!=&SourceViewType){Py_DECREF(index);return view_error();}
  PyObject*position=view_getitem(index,key);Py_DECREF(index);if(!position)return NULL;
  PyObject*data=view_read_ref(v,PyTuple_GET_ITEM(p,1));if(!data){Py_DECREF(position);return NULL;}
  if(Py_TYPE(data)!=&SourceViewType){Py_DECREF(data);Py_DECREF(position);return view_error();}
  PyObject*result=view_getitem(data,position);Py_DECREF(data);Py_DECREF(position);return result;
 }
 if(tag=='d'){
  if(!PyUnicode_CheckExact(key)||!PyTuple_CheckExact(p))return view_error();
  for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(p);i++){
   PyObject*pair=PyTuple_GET_ITEM(p,i);if(!PyTuple_CheckExact(pair)||PyTuple_GET_SIZE(pair)!=2)return view_error();
   PyObject*k=view_read_ref(v,PyTuple_GET_ITEM(pair,0));if(!k)return NULL;
   if(Py_TYPE(k)==&SourceViewType){PyObject*label=view_label(k,NULL);Py_DECREF(k);k=label;if(!k)return NULL;}
   if(!PyUnicode_CheckExact(k)){Py_DECREF(k);return view_error();}
   int equal=PyUnicode_Compare(k,key)==0;Py_DECREF(k);
   if(equal)return view_read_ref(v,PyTuple_GET_ITEM(pair,1));
  }
  PyErr_SetObject(PyExc_KeyError,key);return NULL;
 }
 if(tag=='q'||tag=='l'||tag=='e'){
  if(!PyTuple_CheckExact(p)||!PyLong_CheckExact(key))return view_error();
  Py_ssize_t index=PyLong_AsSsize_t(key),n=PyTuple_GET_SIZE(p);if(PyErr_Occurred())return NULL;
  if(index<0)index+=n;
  if(index<0||index>=n){PyErr_SetString(PyExc_IndexError,"Source index out of range");return NULL;}
  return view_read_ref(v,PyTuple_GET_ITEM(p,index));
 }
 return view_error();
}
static Py_ssize_t view_length(PyObject*o){
 SourceView*v=(SourceView*)o;Py_UCS4 tag;PyObject*p;
 if(!view_node(v,&tag,&p)){view_error();return -1;}
 if(tag=='r'||tag=='m'){
  if(!PyTuple_CheckExact(p)||PyTuple_GET_SIZE(p)!=(tag=='r'?3:5)){view_error();return -1;}
  PyObject*child=view_read_ref(v,PyTuple_GET_ITEM(p,tag=='r'?0:1));if(!child)return -1;
  if(Py_TYPE(child)!=&SourceViewType){Py_DECREF(child);view_error();return -1;}
  Py_ssize_t n=view_length(child);Py_DECREF(child);return n;
 }
 if((tag=='d'||tag=='q'||tag=='l'||tag=='e')&&PyTuple_CheckExact(p))return PyTuple_GET_SIZE(p);
 view_error();return -1;
}
static PyObject*view_iter(PyObject*o){
 SourceView*v=(SourceView*)o;Py_UCS4 tag;PyObject*p;
 if(!view_node(v,&tag,&p))return view_error();
 if(tag=='r'||tag=='m'){
  if(!PyTuple_CheckExact(p)||PyTuple_GET_SIZE(p)!=(tag=='r'?3:5))return view_error();
  PyObject*child=view_read_ref(v,PyTuple_GET_ITEM(p,tag=='r'?0:1));if(!child)return NULL;
  if(Py_TYPE(child)!=&SourceViewType){Py_DECREF(child);return view_error();}
  PyObject*it=view_iter(child);Py_DECREF(child);return it;
 }
 if((tag!='d'&&tag!='q'&&tag!='l'&&tag!='e')||!PyTuple_CheckExact(p))return view_error();
 PyObject*items=PyTuple_New(PyTuple_GET_SIZE(p));if(!items)return NULL;
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(p);i++){
  PyObject*ref=PyTuple_GET_ITEM(p,i);
  if(tag=='d'){
   if(!PyTuple_CheckExact(ref)||PyTuple_GET_SIZE(ref)!=2){Py_DECREF(items);return view_error();}
   ref=PyTuple_GET_ITEM(ref,0);
  }
  PyObject*value=view_read_ref(v,ref);if(!value){Py_DECREF(items);return NULL;}
  if(Py_TYPE(value)==&SourceViewType){
   Py_UCS4 child_tag;PyObject*child_p;
   if(!view_node((SourceView*)value,&child_tag,&child_p)){Py_DECREF(value);Py_DECREF(items);return view_error();}
   if(child_tag=='u'){PyObject*label=view_label(value,NULL);Py_DECREF(value);value=label;if(!value){Py_DECREF(items);return NULL;}}
  }
  PyTuple_SET_ITEM(items,i,value);
 }
 PyObject*it=PyObject_GetIter(items);Py_DECREF(items);return it;
}
static PyObject*view_getattr(PyObject*o,PyObject*name){
 PyObject*standard=PyObject_GenericGetAttr(o,name);
 if(standard||!PyErr_ExceptionMatches(PyExc_AttributeError))return standard;
 PyErr_Clear();Py_UCS4 tag;PyObject*p;
 if(!PyUnicode_CheckExact(name)||!view_node((SourceView*)o,&tag,&p)||tag!='m'||PyUnicode_GET_LENGTH(name)==0||PyUnicode_READ_CHAR(name,0)=='_'){
  PyErr_SetObject(PyExc_AttributeError,name);return NULL;
 }
 PyObject*value=view_getitem(o,name);
 if(!value&&PyErr_ExceptionMatches(PyExc_KeyError)){PyErr_Clear();PyErr_SetObject(PyExc_AttributeError,name);}return value;
}
static PyObject*view_get(PyObject*o,PyObject*args){
 PyObject*k,*fallback=Py_None;if(!PyArg_ParseTuple(args,"O|O",&k,&fallback))return NULL;
 PyObject*v=view_getitem(o,k);if(!v&&PyErr_ExceptionMatches(PyExc_KeyError)){PyErr_Clear();return Py_NewRef(fallback);}return v;
}
static PyObject*view_keys(PyObject*o,PyObject*unused){
 (void)unused;PyObject*it=view_iter(o);if(!it)return NULL;
 PyObject*keys=PySequence_Tuple(it);Py_DECREF(it);return keys;
}
static int view_equal(PyObject*,PyObject*,int,size_t*);
static int view_shape(PyObject*o,PyObject**normalized){
 *normalized=Py_NewRef(o);
 if(Py_TYPE(o)==&SourceViewType){
  Py_UCS4 tag;PyObject*p;if(!view_node((SourceView*)o,&tag,&p))return -1;
  if(tag=='u'){
   Py_DECREF(*normalized);*normalized=view_label(o,NULL);return *normalized?0:-1;
  }
  if(tag=='m')return 'm';
  if(tag=='d'||tag=='r')return 'd';
  if(tag=='q'||tag=='l')return tag;
  return -1;
 }
 if(PyDict_CheckExact(o))return 'd';
 if(PyList_CheckExact(o))return 'l';
 if(PyTuple_CheckExact(o))return 'q';
 return 0;
}
static PyObject*view_value_at(PyObject*o,Py_ssize_t index){
 if(Py_TYPE(o)==&SourceViewType){PyObject*k=PyLong_FromSsize_t(index);if(!k)return NULL;PyObject*v=view_getitem(o,k);Py_DECREF(k);return v;}
 return Py_NewRef(PyList_CheckExact(o)?PyList_GET_ITEM(o,index):PyTuple_GET_ITEM(o,index));
}
static int view_equal(PyObject*a,PyObject*b,int depth,size_t*work){
 if(++*work>1000000||depth>64){PyErr_SetString(PyExc_ValueError,"Source business comparison bound exceeded");return -1;}
 if(Py_TYPE(a)==&SourceViewType&&Py_TYPE(b)==&SourceViewType
    &&((SourceView*)a)->owner==((SourceView*)b)->owner&&((SourceView*)a)->ref==((SourceView*)b)->ref)return 1;
 PyObject*x=NULL,*y=NULL;int tx=view_shape(a,&x),ty=view_shape(b,&y),equal=0;
 if(tx<0||ty<0||tx!=ty)goto done;
 if(tx=='m'){
  SourceView*vx=(SourceView*)x,*vy=(SourceView*)y;
  PyObject*cx=PyTuple_GET_ITEM(vx->owner->data,7),*cy=PyTuple_GET_ITEM(vy->owner->data,7);
  Py_ssize_t ix=-1,iy=-1;
  for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(cx);i++){PyObject*p=PyTuple_GET_ITEM(cx,i);if(PyLong_AsSsize_t(PyTuple_GET_ITEM(p,0))==vx->ref)ix=PyLong_AsSsize_t(PyTuple_GET_ITEM(p,1));}
  for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(cy);i++){PyObject*p=PyTuple_GET_ITEM(cy,i);if(PyLong_AsSsize_t(PyTuple_GET_ITEM(p,0))==vy->ref)iy=PyLong_AsSsize_t(PyTuple_GET_ITEM(p,1));}
  if(ix<0||ix!=iy)goto done;
  Py_UCS4 t;PyObject*px,*py;if(!view_node(vx,&t,&px)||!view_node(vy,&t,&py))goto done;
  PyObject*rx=view_read_ref(vx,PyTuple_GET_ITEM(px,1)),*ry=view_read_ref(vy,PyTuple_GET_ITEM(py,1));
  if(rx&&ry)equal=view_equal(rx,ry,depth+1,work);
  Py_XDECREF(rx);Py_XDECREF(ry);goto done;
 }
 if(tx=='d'){
  PyObject*spaces[2]={x,y};
  for(int which=0;which<2;which++)if(PyDict_CheckExact(spaces[which])){
   Py_ssize_t pos=0;PyObject*k,*v;
   while(PyDict_Next(spaces[which],&pos,&k,&v))if(!PyUnicode_CheckExact(k))goto done;
  }
  Py_ssize_t nx=Py_TYPE(x)==&SourceViewType?view_length(x):PyDict_GET_SIZE(x),ny=Py_TYPE(y)==&SourceViewType?view_length(y):PyDict_GET_SIZE(y);
  if(nx<0||ny<0){equal=-1;goto done;}if(nx!=ny)goto done;
  PyObject*it=Py_TYPE(x)==&SourceViewType?view_iter(x):PyObject_GetIter(x);if(!it){equal=-1;goto done;}
  PyObject*k;equal=1;
  while((k=PyIter_Next(it))){
   if(!PyUnicode_CheckExact(k)){Py_DECREF(k);equal=0;break;}
   PyObject*lx=Py_TYPE(x)==&SourceViewType?view_getitem(x,k):Py_XNewRef(PyDict_GetItemWithError(x,k));
   PyObject*ry=Py_TYPE(y)==&SourceViewType?view_getitem(y,k):Py_XNewRef(PyDict_GetItemWithError(y,k));Py_DECREF(k);
   if(!lx||!ry){if(PyErr_ExceptionMatches(PyExc_KeyError))PyErr_Clear();equal=PyErr_Occurred()?-1:0;Py_XDECREF(lx);Py_XDECREF(ry);break;}
   equal=view_equal(lx,ry,depth+1,work);Py_DECREF(lx);Py_DECREF(ry);if(equal!=1)break;
  }
  Py_DECREF(it);if(PyErr_Occurred())equal=-1;goto done;
 }
 if(tx=='q'||tx=='l'){
  Py_ssize_t nx=Py_TYPE(x)==&SourceViewType?view_length(x):PySequence_Size(x),ny=Py_TYPE(y)==&SourceViewType?view_length(y):PySequence_Size(y);
  if(nx<0||ny<0){equal=-1;goto done;}if(nx!=ny)goto done;equal=1;
  for(Py_ssize_t i=0;i<nx;i++){
   PyObject*vx=view_value_at(x,i),*vy=view_value_at(y,i);
   if(!vx||!vy){Py_XDECREF(vx);Py_XDECREF(vy);equal=-1;break;}
   equal=view_equal(vx,vy,depth+1,work);Py_DECREF(vx);Py_DECREF(vy);if(equal!=1)break;
  }goto done;
 }
 /* Only exact safe scalar types may reach rich comparison here. */
 if((PyUnicode_CheckExact(x)||PyBytes_CheckExact(x)||PyLong_CheckExact(x)||PyFloat_CheckExact(x)||x==Py_None||x==Py_True||x==Py_False)
  &&(PyUnicode_CheckExact(y)||PyBytes_CheckExact(y)||PyLong_CheckExact(y)||PyFloat_CheckExact(y)||y==Py_None||y==Py_True||y==Py_False))equal=PyObject_RichCompareBool(x,y,Py_EQ);
 done:Py_XDECREF(x);Py_XDECREF(y);if(PyErr_Occurred())return -1;return equal;
}
static PyObject*view_rich(PyObject*a,PyObject*b,int op){
 if(op!=Py_EQ&&op!=Py_NE)Py_RETURN_NOTIMPLEMENTED;
 int prior=PyGC_Disable();size_t work=0;int equal=view_equal(a,b,0,&work);if(prior)PyGC_Enable();if(equal<0)return NULL;return PyBool_FromLong(op==Py_EQ?equal:!equal);
}
static int view_contains(PyObject*o,PyObject*target){
 PyObject*it=view_iter(o);if(!it)return -1;PyObject*child;int found=0;
 while((child=PyIter_Next(it))){int prior=PyGC_Disable();size_t work=0;found=view_equal(child,target,0,&work);if(prior)PyGC_Enable();Py_DECREF(child);if(found)break;}
 Py_DECREF(it);return PyErr_Occurred()?-1:found;
}
static PyObject*view_items(PyObject*o,PyObject*unused){
 (void)unused;PyObject*it=view_iter(o);if(!it)return NULL;PyObject*list=PyList_New(0),*key;
 if(!list){Py_DECREF(it);return NULL;}
 while((key=PyIter_Next(it))){PyObject*v=view_getitem(o,key),*pair=v?PyTuple_Pack(2,key,v):NULL;Py_DECREF(key);Py_XDECREF(v);if(!pair||PyList_Append(list,pair)<0){Py_XDECREF(pair);Py_DECREF(it);Py_DECREF(list);return NULL;}Py_DECREF(pair);}
 Py_DECREF(it);if(PyErr_Occurred()){Py_DECREF(list);return NULL;}PyObject*result=PyList_AsTuple(list);Py_DECREF(list);return result;
}
static PyMethodDef view_methods[]={
 {"node",view_body,METH_NOARGS,NULL},{"read",view_child,METH_O,NULL},{"label",view_label,METH_NOARGS,NULL},
 {"owner",view_owner,METH_NOARGS,NULL},{"pin",view_pin,METH_NOARGS,NULL},
 {"keys",view_keys,METH_NOARGS,NULL},
 {"data",view_data,METH_NOARGS,NULL},{"ref",view_ref,METH_NOARGS,NULL},{"get",view_get,METH_VARARGS,NULL},{"items",view_items,METH_NOARGS,NULL},{NULL,NULL,0,NULL}};
static PyMappingMethods view_mapping={.mp_length=view_length,.mp_subscript=view_getitem};
static PySequenceMethods view_sequence={.sq_length=view_length,.sq_contains=view_contains};
static PyTypeObject SourceViewType={PyVarObject_HEAD_INIT(NULL,0)
 .tp_name="sim2act._cold_source_owned_impl.View",.tp_basicsize=sizeof(SourceView),
 .tp_flags=Py_TPFLAGS_DEFAULT|Py_TPFLAGS_IMMUTABLETYPE,.tp_new=no_new,.tp_dealloc=view_free,
 .tp_getattro=view_getattr,.tp_as_mapping=&view_mapping,.tp_as_sequence=&view_sequence,
 .tp_iter=view_iter,.tp_richcompare=view_rich,.tp_methods=view_methods,.tp_hash=PyObject_HashNotImplemented};
static PyObject*view_read(Owned*owner,Py_ssize_t ref){
 SourceView temporary={PyObject_HEAD_INIT(&SourceViewType) .owner=owner,.ref=ref};Py_UCS4 tag;PyObject*p;
 if(!view_node(&temporary,&tag,&p))return view_error();
 if(tag=='o'){
  Py_ssize_t ordinal=PyLong_AsSsize_t(PyTuple_GET_ITEM(p,0)),child=PyLong_AsSsize_t(PyTuple_GET_ITEM(p,1));
  if(PyErr_Occurred()||ordinal<0||ordinal>=PyTuple_GET_SIZE(owner->parents))return view_error();
  return view_read((Owned*)PyTuple_GET_ITEM(owner->parents,ordinal),child);
 }
 if(tag=='s'||tag=='b'){
  PyObject*leaves=PyTuple_GET_ITEM(owner->data,2);Py_ssize_t index;
  if(!PyTuple_CheckExact(leaves)||!PyLong_CheckExact(p)||(index=PyLong_AsSsize_t(p))<0||index>=PyTuple_GET_SIZE(leaves)){if(PyErr_Occurred())return NULL;return view_error();}
  return Py_NewRef(PyTuple_GET_ITEM(leaves,index));
 }
 if(tag=='n')Py_RETURN_NONE;
 if(tag=='t')Py_RETURN_TRUE;
 if(tag=='f')Py_RETURN_FALSE;
 if(tag=='i'){if(!PyLong_CheckExact(p))return view_error();return Py_NewRef(p);}
 if(tag=='v'){if(!PyBytes_CheckExact(p)||PyBytes_GET_SIZE(p)!=8)return view_error();double d=PyFloat_Unpack8(PyBytes_AS_STRING(p),0);if(PyErr_Occurred())return NULL;return PyFloat_FromDouble(d);}
 if(tag!='d'&&tag!='l'&&tag!='q'&&tag!='e'&&tag!='r'&&tag!='m'&&tag!='u')return view_error();
 SourceView*v=PyObject_New(SourceView,&SourceViewType);if(!v)return NULL;v->owner=(Owned*)Py_NewRef((PyObject*)owner);v->ref=ref;return (PyObject*)v;
}
static PyObject*read_owner(PyObject*self,PyObject*o){
 (void)self;if(Py_TYPE(o)!=&OwnedType){PyErr_SetString(PyExc_TypeError,"Exact immutable Source owner required");return NULL;}
 PyObject*data=((Owned*)o)->data;if(!PyTuple_CheckExact(data)||PyTuple_GET_SIZE(data)!=8)return view_error();
 PyObject*root=PyTuple_GET_ITEM(data,0);if(!PyLong_CheckExact(root))return view_error();Py_ssize_t ref=PyLong_AsSsize_t(root);if(PyErr_Occurred())return NULL;return view_read((Owned*)o,ref);
}

/* Select from the actual current Ledger and compare in ONE bounded native
 * interval. No stale list element or pre-callback Slot is passed as a proof. */
static int ledger_string_keys(PyObject*d,size_t*work){
 if(!PyDict_CheckExact(d))return 0;
 Py_ssize_t pos=0;PyObject*k,*v;while(PyDict_Next(d,&pos,&k,&v))if(++*work>1000000||!PyUnicode_CheckExact(k))return 0;return 1;
}
static PyObject*match_ledger(PyObject*self,PyObject*args){
 (void)self;PyObject*owner,*refs,*ledger,*config;
 if(!PyArg_ParseTuple(args,"OOOO",&owner,&refs,&ledger,&config))return NULL;
 if(Py_TYPE(owner)!=&OwnedType||!PyTuple_CheckExact(refs)||PyTuple_GET_SIZE(refs)!=2||!source_config(config))Py_RETURN_FALSE;
 PyObject*ledger_cfg=PyTuple_GET_ITEM(config,6);
 if((PyObject*)Py_TYPE(ledger)!=PyTuple_GET_ITEM(ledger_cfg,0))Py_RETURN_FALSE;
 int prior=PyGC_Disable(),ok=0;size_t work=0;PyObject*raw=NULL,*slots=NULL,*pairs=NULL,*expected=NULL,*empty=NULL,*result=NULL;
 raw=source_get(PyTuple_GET_ITEM(ledger_cfg,1),ledger);
 if(!raw||!ledger_string_keys(raw,&work))goto done;
 slots=Py_XNewRef(PyDict_GetItemString(raw,"slots"));
 if(!slots||(!PyTuple_CheckExact(slots)&&!PyList_CheckExact(slots)))goto done;
 Py_ssize_t n=PyTuple_CheckExact(slots)?PyTuple_GET_SIZE(slots):PyList_GET_SIZE(slots);
 if(n>100000)goto done;
 expected=PyTuple_New(2);pairs=PyTuple_New(2);if(!expected||!pairs)goto done;
 for(int i=0;i<2;i++){
  PyObject*ref=PyTuple_GET_ITEM(refs,i);Py_ssize_t index;
  if(!source_index(ref,PyTuple_GET_SIZE(PyTuple_GET_ITEM(((Owned*)owner)->data,1)),&index))goto done;
  PyObject*slot_view=view_read((Owned*)owner,index);if(!slot_view)goto done;
  if(Py_TYPE(slot_view)!=&SourceViewType){Py_DECREF(slot_view);goto done;}
  PyObject*key=PyUnicode_FromString("identity"),*identity=key?view_getitem(slot_view,key):NULL;Py_XDECREF(key);Py_DECREF(slot_view);
  if(!identity)goto done;
  if(Py_TYPE(identity)!=&SourceViewType){Py_DECREF(identity);goto done;}
  key=PyUnicode_FromString("attempt_id");PyObject*aid=key?view_getitem(identity,key):NULL;Py_XDECREF(key);Py_DECREF(identity);
  if(!aid||!PyUnicode_CheckExact(aid)){Py_XDECREF(aid);goto done;}PyTuple_SET_ITEM(expected,i,aid);
 }
 PyObject*models=PyTuple_GET_ITEM(config,0);Py_ssize_t count=0;
 for(Py_ssize_t i=0;i<n;i++){
  if(++work>1000000)goto done;
  PyObject*slot=PyTuple_CheckExact(slots)?PyTuple_GET_ITEM(slots,i):PyList_GET_ITEM(slots,i);
  if((PyObject*)Py_TYPE(slot)!=PyTuple_GET_ITEM(PyTuple_GET_ITEM(models,0),0))goto done;
  PyObject*storage=source_get(PyTuple_GET_ITEM(PyTuple_GET_ITEM(models,0),2),slot);
  if(!storage||!ledger_string_keys(storage,&work)){Py_XDECREF(storage);goto done;}
  PyObject*identity=Py_XNewRef(PyDict_GetItemString(storage,"identity"));Py_DECREF(storage);
  if(!identity)goto done;
  if((PyObject*)Py_TYPE(identity)!=PyTuple_GET_ITEM(PyTuple_GET_ITEM(models,1),0)){Py_DECREF(identity);goto done;}
  storage=source_get(PyTuple_GET_ITEM(PyTuple_GET_ITEM(models,1),2),identity);Py_DECREF(identity);
  if(!storage||!ledger_string_keys(storage,&work)){Py_XDECREF(storage);goto done;}
  PyObject*stage=PyDict_GetItemString(storage,"stage"),*aid=PyDict_GetItemString(storage,"attempt_id");
  if(!stage||!aid||!PyUnicode_CheckExact(stage)||!PyUnicode_CheckExact(aid)){Py_DECREF(storage);goto done;}
  int source=PyUnicode_CompareWithASCIIString(stage,"source")==0;
  if(source){
   count++;int found=0;
   for(int j=0;j<2;j++)if(PyUnicode_Compare(aid,PyTuple_GET_ITEM(expected,j))==0){
    if(PyTuple_GET_ITEM(pairs,j)){Py_DECREF(storage);goto done;}
    PyObject*pair=PyTuple_Pack(2,PyTuple_GET_ITEM(refs,j),slot);if(!pair){Py_DECREF(storage);goto done;}
    PyTuple_SET_ITEM(pairs,j,pair);found++;
   }
   if(found!=1){Py_DECREF(storage);goto done;}
  }
  Py_DECREF(storage);
 }
 if(count!=2||!PyTuple_GET_ITEM(pairs,0)||!PyTuple_GET_ITEM(pairs,1))goto done;
 empty=PyTuple_New(0);if(!empty)goto done;
 result=source_match_current(owner,Py_None,empty,config,Py_None,pairs);if(!result)goto done;
 ok=result==Py_True;
 done:Py_XDECREF(raw);Py_XDECREF(slots);Py_XDECREF(pairs);Py_XDECREF(expected);Py_XDECREF(empty);Py_XDECREF(result);
 if(prior)PyGC_Enable();
 if(PyErr_Occurred())return NULL;
 return PyBool_FromLong(ok);
}
