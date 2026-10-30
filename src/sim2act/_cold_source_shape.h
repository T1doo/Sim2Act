/* Constructor-only grammar/range/cycle validation of immutable representation.
 * No live value, graph, permission or successful content verdict is cached. */
static int shape_ref(PyObject*v,Py_ssize_t n,Py_ssize_t*out){
 if(!PyLong_CheckExact(v))return 0;
 *out=PyLong_AsSsize_t(v);if(PyErr_Occurred()){PyErr_Clear();return 0;}return *out>=0&&*out<n;
}
static int shape_visit(PyObject*nodes,Py_ssize_t ref,unsigned char*states,size_t*work,int depth){
 if(++*work>1000000||depth>64||states[ref]==1)return 0;
 if(states[ref]==2)return 1;
 states[ref]=1;
 PyObject*node=PyTuple_GET_ITEM(nodes,ref),*p=PyTuple_GET_ITEM(node,1);Py_UCS4 t=PyUnicode_READ_CHAR(PyTuple_GET_ITEM(node,0),0);Py_ssize_t n=PyTuple_GET_SIZE(nodes);
 if(t=='d'){
  for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(p);i++)for(int j=0;j<2;j++){
   Py_ssize_t next;if(!shape_ref(PyTuple_GET_ITEM(PyTuple_GET_ITEM(p,i),j),n,&next)||!shape_visit(nodes,next,states,work,depth+1))return 0;
  }
 }else if(t=='l'||t=='q'||t=='e'||t=='r'||t=='m'){
  for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(p);i++){Py_ssize_t next;if(!shape_ref(PyTuple_GET_ITEM(p,i),n,&next)||!shape_visit(nodes,next,states,work,depth+1))return 0;}
 }else if(t=='u'){
  Py_ssize_t next;if(!shape_ref(p,n,&next)||!shape_visit(nodes,next,states,work,depth+1))return 0;
 }
 states[ref]=2;return 1;
}
static Py_UCS4 shape_tag(PyObject*nodes,PyObject*ref){
 Py_ssize_t i;if(!shape_ref(ref,PyTuple_GET_SIZE(nodes),&i))return 0;
 return PyUnicode_READ_CHAR(PyTuple_GET_ITEM(PyTuple_GET_ITEM(nodes,i),0),0);
}
static int source_image_shape(PyObject*data){
 if(!PyTuple_CheckExact(data)||PyTuple_GET_SIZE(data)!=8)return 0;
 PyObject*nodes=PyTuple_GET_ITEM(data,1),*leaves=PyTuple_GET_ITEM(data,2),*catalog=PyTuple_GET_ITEM(data,7);
 if(!PyTuple_CheckExact(nodes)||!PyTuple_CheckExact(leaves)||!PyTuple_CheckExact(catalog))return 0;
 Py_ssize_t n=PyTuple_GET_SIZE(nodes),root;if(n<=0||n>100000||!shape_ref(PyTuple_GET_ITEM(data,0),n,&root))return 0;
 for(Py_ssize_t i=3;i<8;i++)if(!PyTuple_CheckExact(PyTuple_GET_ITEM(data,i)))return 0;
 unsigned char*states=PyMem_Calloc(n,1),*models=PyMem_Calloc(n,1);int ok=0;if(!states||!models)goto done;
 for(Py_ssize_t i=0;i<PyTuple_GET_SIZE(catalog);i++){
  PyObject*e=PyTuple_GET_ITEM(catalog,i);Py_ssize_t ref,kind;
  if(!PyTuple_CheckExact(e)||PyTuple_GET_SIZE(e)!=2||!shape_ref(PyTuple_GET_ITEM(e,0),n,&ref)||!shape_ref(PyTuple_GET_ITEM(e,1),5,&kind)||models[ref])goto done;
  models[ref]=1;
 }
 for(Py_ssize_t i=0;i<n;i++){
  PyObject*e=PyTuple_GET_ITEM(nodes,i);if(!PyTuple_CheckExact(e)||PyTuple_GET_SIZE(e)!=2)goto done;
  PyObject*tag=PyTuple_GET_ITEM(e,0),*p=PyTuple_GET_ITEM(e,1);if(!PyUnicode_CheckExact(tag)||PyUnicode_GET_LENGTH(tag)!=1)goto done;
  Py_UCS4 t=PyUnicode_READ_CHAR(tag,0);if((t=='m')!=(models[i]!=0))goto done;
  if(t=='n'||t=='t'||t=='f'){if(p!=Py_None)goto done;}
  else if(t=='i'){if(!PyLong_CheckExact(p))goto done;}
  else if(t=='v'){if(!PyBytes_CheckExact(p)||PyBytes_GET_SIZE(p)!=8)goto done;}
  else if(t=='s'||t=='b'){Py_ssize_t index;if(!shape_ref(p,PyTuple_GET_SIZE(leaves),&index))goto done;PyObject*leaf=PyTuple_GET_ITEM(leaves,index);if(t=='s'?!PyUnicode_CheckExact(leaf):!PyBytes_CheckExact(leaf))goto done;}
  else if(t=='u'){Py_ssize_t ref;if(!shape_ref(p,n,&ref))goto done;}
  else if(t=='o'){
   Py_ssize_t unused;
   if(!PyTuple_CheckExact(p)||PyTuple_GET_SIZE(p)!=2
       ||!shape_ref(PyTuple_GET_ITEM(p,0),256,&unused)
       ||!shape_ref(PyTuple_GET_ITEM(p,1),100000,&unused))goto done;
  }
  else if(t=='d'||t=='l'||t=='q'||t=='e'||t=='r'||t=='m'){
   if(!PyTuple_CheckExact(p)||(t=='r'&&PyTuple_GET_SIZE(p)!=3)||(t=='m'&&PyTuple_GET_SIZE(p)!=5))goto done;
   for(Py_ssize_t j=0;j<PyTuple_GET_SIZE(p);j++){
    PyObject*r=PyTuple_GET_ITEM(p,j);Py_ssize_t ref;
    if(t=='d'){
     if(!PyTuple_CheckExact(r)||PyTuple_GET_SIZE(r)!=2)goto done;
     for(int k=0;k<2;k++)if(!shape_ref(PyTuple_GET_ITEM(r,k),n,&ref))goto done;
    }else if(!shape_ref(r,n,&ref))goto done;
   }
  }else goto done;
 }
 /* Node arities alone are insufficient: readers recurse only into views of
  * the declared semantic kind. Validate every child after all node headers. */
 for(Py_ssize_t i=0;i<n;i++){
  PyObject*e=PyTuple_GET_ITEM(nodes,i),*p=PyTuple_GET_ITEM(e,1);Py_UCS4 t=PyUnicode_READ_CHAR(PyTuple_GET_ITEM(e,0),0);
  if(t=='m'){
   const char*expected="sdenn";
   for(int j=0;j<5;j++)if(shape_tag(nodes,PyTuple_GET_ITEM(p,j))!=(Py_UCS4)expected[j])goto done;
  }else if(t=='r'){
   const char*expected="lqd";
   for(int j=0;j<3;j++)if(shape_tag(nodes,PyTuple_GET_ITEM(p,j))!=(Py_UCS4)expected[j])goto done;
  }else if(t=='u'){if(shape_tag(nodes,p)!='s')goto done;}
  else if(t=='d'){
   for(Py_ssize_t j=0;j<PyTuple_GET_SIZE(p);j++){
    Py_UCS4 key=shape_tag(nodes,PyTuple_GET_ITEM(PyTuple_GET_ITEM(p,j),0));if(key!='s'&&key!='u')goto done;
   }
  }else if(t=='e')for(Py_ssize_t j=0;j<PyTuple_GET_SIZE(p);j++)if(shape_tag(nodes,PyTuple_GET_ITEM(p,j))!='s')goto done;
 }
 {size_t work=0;if(!shape_visit(nodes,root,states,&work,0))goto done;}
 for(Py_ssize_t i=0;i<n;i++)if(states[i]!=2)goto done;
 ok=1;
 done:PyMem_Free(states);PyMem_Free(models);return ok;
}
