/* Fresh local typed projection; no Graph, SQL, authority or cached input PASS.
 * Reuse the qualified existing bounded projector, adding configuration and
 * exact-raw eligibility AFTER its entry signal boundary, before any copy.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *cohort_witness;
typedef struct { int selected; } CohortContext;

static int namespace_once(PyObject *space,PyObject **seen,int *used);

static int exact_namespace(PyObject *space) {
    if (!PyDict_CheckExact(space)) return 0;
    Py_ssize_t pos=0; PyObject *key,*value;
    while (PyDict_Next(space,&pos,&key,&value)) if (!PyUnicode_CheckExact(key)) return 0;
    return 1;
}

static int same_items(PyObject *space, PyObject *items) {
    if (!PyDict_CheckExact(space)||!PyTuple_CheckExact(items)
            ||PyDict_GET_SIZE(space)!=PyTuple_GET_SIZE(items)) return 0;
    Py_ssize_t pos=0,i=0; PyObject *key,*value;
    while (PyDict_Next(space,&pos,&key,&value)) {
        PyObject *pair=PyTuple_GET_ITEM(items,i++);
        if (!PyTuple_CheckExact(pair)||PyTuple_GET_SIZE(pair)!=2
                ||key!=PyTuple_GET_ITEM(pair,0)||value!=PyTuple_GET_ITEM(pair,1)) return 0;
    }
    return 1;
}

static int namespace_once(PyObject *space,PyObject **seen,int *used) {
    for (int i=0;i<*used;i++) if (seen[i]==space) return 1;
    if (!exact_namespace(space)) return 0;
    if (*used<64) seen[(*used)++]=space;
    return 1;
}

static int current_witness(void) {
    if (!cohort_witness) return 0;
    PyObject *functions=PyTuple_GET_ITEM(cohort_witness,0);
    PyObject *bindings=PyTuple_GET_ITEM(cohort_witness,1);
    PyObject *classes=PyTuple_GET_ITEM(cohort_witness,2);
    PyObject *seen[64]; int used=0;
    for (Py_ssize_t i=0;i<PyTuple_GET_SIZE(functions);i++) {
        PyObject *entry=PyTuple_GET_ITEM(functions,i),*fn=PyTuple_GET_ITEM(entry,0);
        if (!PyFunction_Check(fn)||PyFunction_GET_CODE(fn)!=PyTuple_GET_ITEM(entry,1)
                ||(PyFunction_GET_DEFAULTS(fn)?PyFunction_GET_DEFAULTS(fn):Py_None)!=PyTuple_GET_ITEM(entry,2)
                ||(PyFunction_GET_KW_DEFAULTS(fn)?PyFunction_GET_KW_DEFAULTS(fn):Py_None)!=PyTuple_GET_ITEM(entry,3)
                ||PyFunction_GET_CLOSURE(fn)!=NULL) return 0;
        PyObject *kw=PyTuple_GET_ITEM(entry,3);
        if (kw!=Py_None&&!same_items(kw,PyTuple_GET_ITEM(entry,4))) return 0;
    }
    for (Py_ssize_t i=0;i<PyTuple_GET_SIZE(bindings);i++) {
        PyObject *entry=PyTuple_GET_ITEM(bindings,i),*space=PyTuple_GET_ITEM(entry,0);
        PyObject *fallback=PyTuple_GET_ITEM(entry,1),*name=PyTuple_GET_ITEM(entry,2);
        if (!PyUnicode_CheckExact(name)||!namespace_once(space,seen,&used)
                ||!namespace_once(fallback,seen,&used)) return 0;
        PyObject *value=PyDict_GetItemWithError(space,name);
        if (!value) value=PyDict_GetItemWithError(fallback,name);
        if (!value&&!PyErr_Occurred()) value=Py_None;
        if (value!=PyTuple_GET_ITEM(entry,3)) return 0;
    }
    for (Py_ssize_t i=0;i<PyTuple_GET_SIZE(classes);i++) {
        PyObject *entry=PyTuple_GET_ITEM(classes,i),*kind=PyTuple_GET_ITEM(entry,0);
        if (!PyType_Check(kind)||(PyObject *)Py_TYPE(kind)!=PyTuple_GET_ITEM(entry,1)
                ||((PyTypeObject *)kind)->tp_mro!=PyTuple_GET_ITEM(entry,2)) return 0;
        /* Static type dictionaries are interpreter-local in CPython 3.12. */
        PyObject *dictionary=PyType_GetDict((PyTypeObject *)kind);
        if (!dictionary) return 0;
        int same=same_items(dictionary,PyTuple_GET_ITEM(entry,3));
        Py_DECREF(dictionary);
        if (!same) return 0;
    }
    PyObject *gc=PyTuple_GET_ITEM(cohort_witness,3);
    PyObject *callbacks=PyTuple_GET_ITEM(gc,1);
    return namespace_once(PyTuple_GET_ITEM(gc,0),seen,&used)
        &&PyList_CheckExact(callbacks)&&PyList_GET_SIZE(callbacks)==0
        &&PyDict_GetItemString(PyTuple_GET_ITEM(gc,0),"callbacks")==callbacks&&!PyErr_Occurred();
}

static int raw_supported(PyObject *value, PyObject **active, int depth, int *work) {
    /* Below the reused raw copier's first 1024-node signal poll. */
    if (++*work>=1024) return 0;
    if (PyUnicode_CheckExact(value)||PyLong_CheckExact(value)||PyFloat_CheckExact(value)
            ||PyBool_Check(value)||PyBytes_CheckExact(value)||value==Py_None) return 1;
    if (depth>=48) return 0;
    for (int i=0;i<depth;i++) if (active[i]==value) return 0;
    active[depth]=value;
    if (PyDict_CheckExact(value)) {
        Py_ssize_t pos=0; PyObject *key,*child;
        while (PyDict_Next(value,&pos,&key,&child))
            if (!PyUnicode_CheckExact(key)||!raw_supported(child,active,depth+1,work)) return 0;
        return 1;
    }
    if (PyList_CheckExact(value)||PyTuple_CheckExact(value)) {
        Py_ssize_t count=PyList_CheckExact(value)?PyList_GET_SIZE(value):PyTuple_GET_SIZE(value);
        for (Py_ssize_t i=0;i<count;i++)
            if (!raw_supported(PyList_CheckExact(value)?PyList_GET_ITEM(value,i):PyTuple_GET_ITEM(value,i),
                    active,depth+1,work)) return 0;
        return 1;
    }
    return 0;
}

static int cohort_gate(PyObject *extra) {
    if (!PyTuple_CheckExact(extra)||PyTuple_GET_SIZE(extra)!=2) return 0;
    PyObject *raw=PyTuple_GET_ITEM(extra,0);
    CohortContext *context=PyCapsule_GetPointer(PyTuple_GET_ITEM(extra,1),"sim2act.cohort.local");
    if (!context) return 0;
    PyObject *active[49]; int work=0;
    /* Never change the caller's GC policy to mint a pure-segment permit. */
    if (PyGC_IsEnabled()||!current_witness()||!PyDict_CheckExact(raw)
            ||!raw_supported(raw,active,0,&work)) return 0;
    context->selected=1;
    return 1;
}

#define SIM2ACT_COHORT_SELECTION_GATE cohort_gate
#define PyInit__cold_typed_native_impl PyInit__unused_cohort_projection
#include "_cold_typed_native_impl.c"
#undef PyInit__cold_typed_native_impl

/* Reuse the unchanged complete exact-raw copier and strict comparator.
 * Their public module/method table is not exported by this component. */
#define methods cohort_raw_methods
#define module cohort_raw_definition
#define unsupported cohort_raw_unsupported
#define PyInit__raw_snapshot PyInit__unused_cohort_raw
#define SIM2ACT_RAW_SOURCE_SHA "embedded-private-raw-helper"
#include "_raw_snapshot.c"
#undef methods
#undef module
#undef unsupported
#undef PyInit__raw_snapshot

static PyObject *first_compare(PyObject *self,PyObject *args) {
    if (!PyTuple_CheckExact(args)||PyTuple_GET_SIZE(args)!=10) {
        PyErr_SetString(PyExc_TypeError,"Exact complete cohort selection ABI required"); return NULL;
    }
    CohortContext context={.selected=0};
    PyObject *capsule=PyCapsule_New(&context,"sim2act.cohort.local",NULL);
    PyObject *extra=NULL,*arguments=NULL,*reply=NULL,*saved=NULL,*result=NULL;
    if (!capsule) goto done;
    extra=PyTuple_Pack(2,PyTuple_GET_ITEM(args,9),capsule);
    if (!extra) goto done;
    arguments=PyTuple_New(10);
    if (!arguments) goto done;
    for (int i=0;i<9;i++) PyTuple_SET_ITEM(arguments,i,Py_NewRef(PyTuple_GET_ITEM(args,i)));
    PyTuple_SET_ITEM(arguments,9,Py_NewRef(extra));
    /* selection dispatches entry signals and checks GC was ALREADY disabled.
     * No Python return/eval between projection, full raw capture and compare.
     * This function never disables/enables GC. */
    reply=selection(self,arguments);
    if (!reply) goto done;
    if (PyTuple_GET_ITEM(reply,7)==Py_False||!PyLong_AsLong(PyTuple_GET_ITEM(reply,7))) {
        result=Py_NewRef(Py_None); goto done;
    }
    PyObject *active[DEPTH+1]; long work=0;
    saved=capture(PyTuple_GET_ITEM(args,9),active,0,&work);
    if (!saved) goto done;
    int equal=equal_data(PyTuple_GET_ITEM(reply,0),saved);
    if (equal<0) goto done;
    result=PyBool_FromLong(equal);
done:;
    PyObject *error=PyErr_GetRaisedException();
    Py_XDECREF(saved);Py_XDECREF(reply);Py_XDECREF(arguments);Py_XDECREF(extra);Py_XDECREF(capsule);
    if (error) { Py_XDECREF(result);PyErr_SetRaisedException(error);return NULL; }
    return result;
}

static PyObject *configure(PyObject *self, PyObject *record) {
    (void)self;
    if (cohort_witness||!PyTuple_CheckExact(record)||PyTuple_GET_SIZE(record)!=4) {
        PyErr_SetString(PyExc_RuntimeError,"Cohort configuration is one-time"); return NULL;
    }
    /* Only the fixed internal Python issuer supplies this code metadata.
     * Reject malformed records before retaining them, never run their hooks.
     */
    for (Py_ssize_t i=0;i<3;i++) if (!PyTuple_CheckExact(PyTuple_GET_ITEM(record,i))) {
        PyErr_SetString(PyExc_TypeError,"Exact configuration tuples required"); return NULL;
    }
    for (Py_ssize_t group=0;group<3;group++) {
        PyObject *items=PyTuple_GET_ITEM(record,group);
        for (Py_ssize_t i=0;i<PyTuple_GET_SIZE(items);i++) {
            PyObject *entry=PyTuple_GET_ITEM(items,i);
            if (!PyTuple_CheckExact(entry)||PyTuple_GET_SIZE(entry)!=(group==0?5:4)) {
                PyErr_SetString(PyExc_TypeError,"Exact configuration entry required"); return NULL;
            }
        }
    }
    PyObject *gc=PyTuple_GET_ITEM(record,3);
    if (!PyTuple_CheckExact(gc)||PyTuple_GET_SIZE(gc)!=2
            ||!PyDict_CheckExact(PyTuple_GET_ITEM(gc,0))) {
        PyErr_SetString(PyExc_TypeError,"Exact GC configuration required"); return NULL;
    }
    cohort_witness=Py_NewRef(record);
    if (!current_witness()) {
        Py_CLEAR(cohort_witness);
        if (!PyErr_Occurred()) PyErr_SetString(PyExc_ValueError,"Changed cohort configuration");
        return NULL;
    }
    Py_RETURN_NONE;
}

static PyObject *current(PyObject *self, PyObject *unused) {
    (void)self;(void)unused;
    if (PyErr_CheckSignals()<0) return NULL;
    int result=current_witness();
    if (PyErr_Occurred()) return NULL;
    return PyBool_FromLong(result);
}

static PyObject *cohort_stack_ready(PyObject *self,PyObject *unused) {
    if (PyGC_IsEnabled()) Py_RETURN_FALSE;
    return stack_ready(self,unused);
}

static PyMethodDef cohort_methods[]={
    {"configure",configure,METH_O,"One-time code configuration, never model data."},
    {"current",current,METH_NOARGS,"Fresh complete code configuration comparison."},
    {"first_compare",first_compare,METH_VARARGS,"One bounded actual/raw complete comparison segment."},
    {"stack_ready",cohort_stack_ready,METH_NOARGS,"Original-frame GC and remaining stack eligibility."},
    {"build_identity",build_identity,METH_NOARGS,"Exact interpreter/ABI layout witness."},
    {NULL,NULL,0,NULL}
};
static struct PyModuleDef cohort_definition={
    PyModuleDef_HEAD_INIT,"_cold_typed_cohort",NULL,-1,cohort_methods,NULL,NULL,NULL,NULL
};
PyMODINIT_FUNC PyInit__cold_typed_cohort(void) {
    PyObject *module=PyModule_Create(&cohort_definition);
    if (!module) return NULL;
    if (PyModule_AddStringConstant(module,"SOURCE_SHA256",SIM2ACT_VISITOR_SOURCE_SHA)<0) {
        Py_DECREF(module); return NULL;
    }
    return module;
}
