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
static PyMethodDef methods[]={{"copy_snapshot",copy_snapshot,METH_O,"Bounded exact built-in raw capture."},{"equal_values",equal_values,METH_VARARGS,"Strict complete selected raw equality."},{NULL,NULL,0,NULL}};
static struct PyModuleDef module={PyModuleDef_HEAD_INIT,"_raw_snapshot",NULL,-1,methods,NULL,NULL,NULL,NULL};
PyMODINIT_FUNC PyInit__raw_snapshot(void) {
    PyObject *m=PyModule_Create(&module); if (!m) return NULL;
    unsupported=PyCapsule_New((void *)&module,"sim2act.raw-snapshot.unsupported",NULL);
    if (!unsupported || PyModule_AddObjectRef(m,"UNSUPPORTED",unsupported)<0) { Py_XDECREF(unsupported); Py_DECREF(m); return NULL; }
    if (PyModule_AddStringConstant(m,"SOURCE_SHA256",SIM2ACT_RAW_SOURCE_SHA)<0) { Py_DECREF(m); return NULL; }
    return m;
}
