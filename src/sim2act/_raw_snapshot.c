#define PY_SSIZE_T_CLEAN
#include <Python.h>

/* A private bounded selector, followed by one owned capture. No GIL release,
 * reducers, completed-node memo, borrowed result, or native-error retry. */
#define DEPTH 64
#define WORK 100000
static PyObject *unsupported;
static int scalar(PyObject *v) {
    return PyUnicode_CheckExact(v) || PyLong_CheckExact(v) || PyFloat_CheckExact(v)
        || PyBool_Check(v) || PyBytes_CheckExact(v) || v == Py_None;
}
static int scan(PyObject *v, PyObject **active, int depth, long *work) {
    if (++*work > WORK) return 0;
    if (scalar(v)) return 1;
    if (depth >= DEPTH) return 0;
    for (int i=0;i<depth;i++) if (active[i] == v) return 0;
    active[depth] = v;
    if (PyDict_CheckExact(v)) {
        Py_ssize_t pos=0; PyObject *key, *child;
        while (PyDict_Next(v,&pos,&key,&child)) {
            if (!PyUnicode_CheckExact(key) || !scan(child,active,depth+1,work)) return 0;
        }
        return 1;
    }
    if (PyList_CheckExact(v) || PyTuple_CheckExact(v)) {
        Py_ssize_t n=PySequence_Size(v);
        for (Py_ssize_t i=0;i<n;i++) {
            PyObject *child=PyList_CheckExact(v)?PyList_GET_ITEM(v,i):PyTuple_GET_ITEM(v,i);
            if (!scan(child,active,depth+1,work)) return 0;
        }
        return 1;
    }
    return 0;
}
static PyObject *capture(PyObject *v, PyObject **active, int depth, long *work) {
    PyObject *result=NULL, *view=NULL, *items=NULL, *iterator=NULL, *entry=NULL;
    if (++*work > WORK || depth > DEPTH) {
        PyErr_SetString(PyExc_RuntimeError,"Raw snapshot changed beyond selected bounds"); return NULL;
    }
    if ((*work & 1023)==0 && PyErr_CheckSignals()<0) return NULL;
    if (scalar(v)) return Py_NewRef(v);
    for (int i=0;i<depth;i++) if (active[i]==v) {
        PyErr_SetString(PyExc_RuntimeError,"Raw snapshot acquired a cycle during capture"); return NULL;
    }
    if (!PyDict_CheckExact(v) && !PyList_CheckExact(v) && !PyTuple_CheckExact(v)) {
        PyErr_SetString(PyExc_RuntimeError,"Raw snapshot acquired an unsupported value"); return NULL;
    }
    if (Py_EnterRecursiveCall(" while capturing controlled raw data")) return NULL;
    active[depth]=v;
    if (PyDict_CheckExact(v)) {
        /* Retain the original key/value-items observation before key gating.
         * Its projection is identity for exact-str dictionaries. */
        view=PyObject_CallMethod(v,"items",NULL);
        if (!view) goto done;
        items=PySequence_Tuple(view); Py_CLEAR(view);
        if (!items) goto done;
        for (Py_ssize_t i=0;i<PyTuple_GET_SIZE(items);i++) {
            if (!PyUnicode_CheckExact(PyTuple_GET_ITEM(PyTuple_GET_ITEM(items,i),0))) {
                PyErr_SetString(PyExc_RuntimeError,"Raw snapshot keys changed during capture"); goto done;
            }
        }
        Py_CLEAR(items);
        result=PyDict_New(); if (!result) goto done;
        view=PyObject_CallMethod(v,"items",NULL); if (!view) goto failed;
        iterator=PyObject_GetIter(view); Py_CLEAR(view); if (!iterator) goto failed;
        while ((entry=PyIter_Next(iterator))) {
            PyObject *key=PyTuple_GET_ITEM(entry,0), *child=PyTuple_GET_ITEM(entry,1), *copied;
            if (!PyUnicode_CheckExact(key)) {
                PyErr_SetString(PyExc_RuntimeError,"Raw snapshot keys changed during capture"); goto failed;
            }
            copied=capture(child,active,depth+1,work);
            if (!copied) goto failed;
            int set=PyDict_SetItem(result,key,copied); Py_DECREF(copied);
            if (set<0) goto failed;
            Py_CLEAR(entry);
        }
    } else {
        result=PyList_New(0); if (!result) goto done;
        iterator=PyObject_GetIter(v); if (!iterator) goto failed;
        while ((entry=PyIter_Next(iterator))) {
            PyObject *copied=capture(entry,active,depth+1,work);
            if (!copied) goto failed;
            int added=PyList_Append(result,copied); Py_DECREF(copied);
            if (added<0) goto failed;
            Py_CLEAR(entry);
        }
        if (!PyErr_Occurred() && PyTuple_CheckExact(v)) {
            PyObject *tuple=PyList_AsTuple(result); Py_SETREF(result,tuple);
        }
    }
    if (PyErr_Occurred()) goto failed;
    goto done;
failed:
    Py_CLEAR(result);
done:
    Py_XDECREF(entry); Py_XDECREF(iterator); Py_XDECREF(items); Py_XDECREF(view);
    Py_LeaveRecursiveCall(); return result;
}
static PyObject *copy_snapshot(PyObject *self, PyObject *v) {
    (void)self;
    /* Deep/foreign/RowMapping inputs select the exact original Python path
     * before capture. Leave its recursion and rejection semantics intact. */
    PyObject *active[DEPTH+1]; long work=0;
    PyFrameObject *frame=PyThreadState_GetFrame(PyThreadState_Get()); int frames=0;
    while (frame) { PyFrameObject *back=PyFrame_GetBack(frame); Py_DECREF(frame); frame=back; frames++; }
    if (PyErr_Occurred()) return NULL;
    if (Py_GetRecursionLimit()-frames < 3*DEPTH+64 || !scan(v,active,0,&work)) return Py_NewRef(unsupported);
    work=0; return capture(v,active,0,&work);
}
static int equal_data(PyObject *a, PyObject *b) {
    if (Py_TYPE(a)!=Py_TYPE(b)) return 0;
    if (PyFloat_CheckExact(a)) return PyFloat_AS_DOUBLE(a)==PyFloat_AS_DOUBLE(b);
    if (scalar(a)) return PyObject_RichCompareBool(a,b,Py_EQ);
    if (PyDict_CheckExact(a)) {
        if (PyDict_Size(a)!=PyDict_Size(b)) return 0;
        Py_ssize_t pos=0; PyObject *key,*child;
        while (PyDict_Next(a,&pos,&key,&child)) {
            PyObject *other=PyDict_GetItemWithError(b,key);
            if (!other) return PyErr_Occurred()?-1:0;
            int same=equal_data(child,other); if (same<=0) return same;
        }
        return 1;
    }
    Py_ssize_t n=PySequence_Size(a);
    if (n!=PySequence_Size(b)) return 0;
    for (Py_ssize_t i=0;i<n;i++) {
        PyObject *left=PyList_CheckExact(a)?PyList_GET_ITEM(a,i):PyTuple_GET_ITEM(a,i);
        PyObject *right=PyList_CheckExact(b)?PyList_GET_ITEM(b,i):PyTuple_GET_ITEM(b,i);
        int same=equal_data(left,right); if (same<=0) return same;
    }
    return 1;
}
static PyObject *equal_values(PyObject *self, PyObject *args) {
    (void)self; PyObject *a,*b,*active[DEPTH+1]; long work=0;
    if (!PyArg_ParseTuple(args,"OO:equal_values",&a,&b)) return NULL;
    if (!scan(a,active,0,&work)) return Py_NewRef(unsupported);
    work=0; if (!scan(b,active,0,&work)) return Py_NewRef(unsupported);
    int same=equal_data(a,b); if (same<0) return NULL;
    return PyBool_FromLong(same);
}
/* Same non-fetching row projection as Python, including live iterators and
 * strong entry ownership across quoted-name conversion callbacks. */
static int row_require(PyObject *require, int ok, const char *message) {
    PyObject *r=PyObject_CallFunction(require,"Os",ok?Py_True:Py_False,message);
    if (!r) return -1;
    Py_DECREF(r); return 0;
}
static PyObject *row_lookup(PyObject *self, PyObject *args) {
    PyObject *keys,*data,*index,*quoted,*require,*it=NULL,*key=NULL;
    PyObject *entry=NULL,*items=NULL,*text=NULL,*lookup=NULL;
    PyObject *last_index_key=NULL,*last_index_position=NULL,*next=NULL;
    if (!PyArg_ParseTuple(args,"OOOOO:row_lookup",&keys,&data,&index,&quoted,&require)) return NULL;
    /* Unknown quoted conversion/destruction selects Python before projection.
     * Do not approximate arbitrary callback/destructor timing in C. */
    if (!PyType_Check(quoted) || ((PyTypeObject *)quoted)->tp_str != PyUnicode_Type.tp_str
            || PyObject_HasAttrString(quoted,"__del__")) return Py_NewRef(unsupported);
    /* The caller's original storage gate remains before this function. */
    if (!PyList_CheckExact(keys) || !PyTuple_CheckExact(data) || !PyDict_CheckExact(index)) {
        PyErr_SetString(PyExc_TypeError,"Exact row projection storage required"); return NULL;
    }
    int ok=1;
    it=PyObject_GetIter(keys); if (!it) goto done;
    while ((key=PyIter_Next(it))) {
        ok=PyUnicode_CheckExact(key) || (PyObject *)Py_TYPE(key)==quoted;
        Py_CLEAR(key); if (!ok) break;
    }
    if (PyErr_Occurred()) goto done;
    Py_CLEAR(it);
    if (row_require(require,ok,"Complete Cold graph SQL row keys required")<0) goto done;
    lookup=PyDict_New(); if (!lookup) goto done;
    items=PyObject_CallMethod(index,"items",NULL); if (!items) goto done;
    it=PyObject_GetIter(items); if (!it) goto done;
    while ((entry=PyIter_Next(it))) {
        PyObject *k=PyTuple_GET_ITEM(entry,0), *position=PyTuple_GET_ITEM(entry,1);
        /* Python UNPACK_SEQUENCE / STORE_FAST key then position lifetime. */
        Py_XSETREF(last_index_key,Py_NewRef(k));
        Py_XSETREF(last_index_position,Py_NewRef(position));
        if (PyUnicode_CheckExact(k) || (PyObject *)Py_TYPE(k)==quoted) {
            ok=PyLong_CheckExact(position);
            if (ok) {
                Py_ssize_t n=PyLong_AsSsize_t(position);
                if (n==-1 && PyErr_Occurred()) {
                    if (!PyErr_ExceptionMatches(PyExc_OverflowError)) goto done;
                    PyErr_Clear(); ok=0;
                } else ok=n>=0 && n<PyTuple_GET_SIZE(data);
            }
            if (!ok && row_require(require,0,"Complete Cold graph SQL row index positions required")<0) goto done;
            text=PyObject_Str(k);
            if (!text || PyDict_SetItem(lookup,text,position)<0) goto done;
            Py_CLEAR(text);
        }
        Py_CLEAR(entry);
    }
    if (PyErr_Occurred()) goto done;
    Py_CLEAR(it); Py_CLEAR(items);
    it=PyObject_GetIter(keys); if (!it) goto done;
    ok=1;
    while ((next=PyIter_Next(it))) {
        Py_XSETREF(key,next);
        text=PyObject_Str(key); if (!text) goto done;
        ok=PyDict_Contains(lookup,text); Py_CLEAR(text);
        if (ok<0) goto done;
        if (!ok) break;
    }
    if (PyErr_Occurred()) goto done;
    Py_CLEAR(key); /* The original all() generator ends before require(). */
    if (row_require(require,ok,"Complete Cold graph SQL row keys required")<0) goto done;
    Py_CLEAR(it); Py_CLEAR(last_index_key); Py_CLEAR(last_index_position); return lookup;
 done:;
    PyObject *error=PyErr_GetRaisedException();
    Py_XDECREF(it); Py_XDECREF(key); Py_XDECREF(entry); Py_XDECREF(items); Py_XDECREF(text); Py_XDECREF(lookup);
    Py_XDECREF(last_index_key); Py_XDECREF(last_index_position);
    if (error) PyErr_SetRaisedException(error);
    return NULL;
}

static PyMethodDef methods[]={{"row_lookup",row_lookup,METH_VARARGS,"Fresh complete row lookup with owned live iterators."},{"copy_snapshot",copy_snapshot,METH_O,"Bounded exact built-in raw capture."},{"equal_values",equal_values,METH_VARARGS,"Strict complete selected raw equality."},{NULL,NULL,0,NULL}};
static struct PyModuleDef module={PyModuleDef_HEAD_INIT,"_raw_snapshot",NULL,-1,methods,NULL,NULL,NULL,NULL};
PyMODINIT_FUNC PyInit__raw_snapshot(void) {
    PyObject *m=PyModule_Create(&module); if (!m) return NULL;
    unsupported=PyCapsule_New((void *)&module,"sim2act.raw-snapshot.unsupported",NULL);
    if (!unsupported || PyModule_AddObjectRef(m,"UNSUPPORTED",unsupported)<0) { Py_XDECREF(unsupported); Py_DECREF(m); return NULL; }
    if (PyModule_AddStringConstant(m,"SOURCE_SHA256",SIM2ACT_RAW_SOURCE_SHA)<0) { Py_DECREF(m); return NULL; }
    return m;
}
