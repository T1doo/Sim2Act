/* Optional CPython 3.12 experiment. No production routing imports this module.
 * Fresh DFS, source key identity, order and completed-node aliases are retained.
 * Only public CPython APIs; never release the GIL while holding graph objects.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>

typedef struct {
    PyObject *allowed, *branch, *workflow, *require;
    PyObject *active, *seen, *object_get, *type_get;
    unsigned long ticks;
} Visitor;

static int fail(Visitor *v, const char *message) {
    PyObject *result = PyObject_CallFunction(v->require, "Os", Py_False, message);
    if (result != NULL) {
        Py_DECREF(result);
        PyErr_SetString(PyExc_RuntimeError, "typed visitor require did not raise");
    }
    return -1;
}

static int member(PyObject *items, PyObject *kind) {
    for (Py_ssize_t i = 0; i < PyTuple_GET_SIZE(items); ++i)
        if (PyTuple_GET_ITEM(items, i) == kind) return 1;
    return 0;
}

/* Exact dict/set only. Real iterators preserve mutation errors. */
static int string_keys(PyObject *value) {
    PyObject *iterator = PyObject_GetIter(value), *key;
    if (iterator == NULL) return -1;
    int ok = 1;
    while ((key = PyIter_Next(iterator)) != NULL) {
        ok = PyUnicode_CheckExact(key);
        Py_DECREF(key);
        if (!ok) break;
    }
    if (PyErr_Occurred()) ok = -1;
    Py_DECREF(iterator);
    return ok;
}

static PyObject *attribute(PyObject *descriptor, PyObject *value, const char *name) {
    PyObject *key = PyUnicode_FromString(name);
    if (key == NULL) return NULL;
    PyObject *result = PyObject_CallFunctionObjArgs(descriptor, value, key, NULL);
    Py_DECREF(key);
    return result;
}

static PyObject *visit(Visitor *v, PyObject *value);

static int omission_key(PyObject *key, const char *name) {
    if (PyUnicode_CheckExact(key)) return PyUnicode_CompareWithASCIIString(key, name) == 0;
    /* A descriptor can mutate the raw map after its original key gate. Match
     * Python equality here, rather than applying an unsafe Unicode macro or a
     * new late validation rule to a newly inserted foreign key. */
    PyObject *literal = PyUnicode_InternFromString(name);
    if (literal == NULL) return -1;
    int result = PyObject_RichCompareBool(key, literal, Py_EQ);
    Py_DECREF(literal);
    return result;
}

static PyObject *visit_body(Visitor *v, PyObject *value) {
    PyObject *kind = (PyObject *)Py_TYPE(value);
    if (kind == (PyObject *)&PyUnicode_Type || kind == (PyObject *)&PyLong_Type ||
        kind == (PyObject *)&PyFloat_Type || kind == (PyObject *)&PyBool_Type ||
        kind == (PyObject *)&PyBytes_Type || value == Py_None) return Py_NewRef(value);
    int mapping = PyDict_CheckExact(value), list = PyList_CheckExact(value);
    int tuple = PyTuple_CheckExact(value);
    if (!mapping && !list && !tuple && !member(v->allowed, kind)) {
        fail(v, "Unsupported nested typed trial fact");
        return NULL;
    }
    PyObject *identity = PyLong_FromVoidPtr(value), *result = NULL;
    PyObject *raw = NULL, *fields = NULL, *selected = NULL, *left = NULL, *right = NULL;
    PyObject *extra = NULL, *private_value = NULL, *items = NULL, *iterator = NULL;
    PyObject *child = NULL, *key = NULL, *pair = NULL, *copied = NULL;
    if (identity == NULL) goto done;
    int status = PySet_Contains(v->active, identity);
    if (status < 0) goto done;
    if (status) { fail(v, "Cyclic typed trial fact"); goto done; }
    result = PyDict_GetItemWithError(v->seen, identity);
    if (result != NULL) { Py_INCREF(result); goto done; }
    if (PyErr_Occurred() || PySet_Add(v->active, identity) < 0) goto done;
    if (mapping) {
        status = string_keys(value);
        if (status < 0) goto done;
        if (!status) { fail(v, "Exact typed trial JSON keys required"); goto done; }
        raw = Py_NewRef(value);
    } else if (!list && !tuple) {
        /* Preserve all three unconditional reads, then original and order. */
        raw = attribute(v->object_get, value, "__dict__");
        if (raw == NULL) goto done;
        fields = attribute(v->type_get, kind, "__pydantic_fields__");
        if (fields == NULL) goto done;
        selected = attribute(v->object_get, value, "__pydantic_fields_set__");
        if (selected == NULL) goto done;
        if (!PyDict_CheckExact(raw)) goto invalid_storage;
        status = string_keys(raw);
        if (status < 0) goto done;
        if (!status || !PyDict_CheckExact(fields)) goto invalid_storage;
        status = string_keys(fields);
        if (status < 0) goto done;
        if (!status) goto invalid_storage;
        left = PyObject_CallMethod(raw, "keys", NULL);
        if (left == NULL) goto done;
        right = PyObject_CallMethod(fields, "keys", NULL);
        if (right == NULL) goto done;
        status = PyObject_RichCompareBool(left, right, Py_EQ);
        if (status < 0) goto done;
        if (!status || !PySet_CheckExact(selected)) goto invalid_storage;
        status = string_keys(selected);
        if (status < 0) goto done;
        if (!status) goto invalid_storage;
        /* Original obtains a fresh fields.keys() for the subset expression. */
        Py_CLEAR(right);
        right = PyObject_CallMethod(fields, "keys", NULL);
        if (right == NULL) goto done;
        status = PyObject_RichCompareBool(selected, right, Py_LE);
        if (status < 0) goto done;
        if (!status) goto invalid_storage;
        extra = attribute(v->object_get, value, "__pydantic_extra__");
        if (extra == NULL) goto done;
        if (extra != Py_None) goto invalid_storage;
        private_value = attribute(v->object_get, value, "__pydantic_private__");
        if (private_value == NULL) goto done;
        if (private_value != Py_None) goto invalid_storage;
    }
    if (raw != NULL) {
        items = PyObject_CallMethod(raw, "items", NULL);
        if (items == NULL) goto done;
        iterator = PyObject_GetIter(items);
        result = PyDict_New();
    } else {
        iterator = PyObject_GetIter(value);
        result = PyList_New(0);
    }
    if (iterator == NULL || result == NULL) goto done;
    while ((pair = PyIter_Next(iterator)) != NULL) {
        /* Prior loop variables stay alive through the next iterator read. */
        Py_CLEAR(key);
        Py_CLEAR(child);
        if (raw != NULL) {
            key = Py_NewRef(PyTuple_GET_ITEM(pair, 0));
            child = Py_NewRef(PyTuple_GET_ITEM(pair, 1));
            Py_CLEAR(pair);
            int omit = 0;
            if (!mapping && child == Py_None) {
                if (kind == v->branch) omit = omission_key(key, "value");
                else if (kind == v->workflow) omit = omission_key(key, "when");
            }
            if (omit < 0) goto done;
            if (omit) continue;
        } else {
            child = pair;
            pair = NULL;
        }
        copied = visit(v, child);
        if (copied == NULL) goto done;
        status = raw != NULL ? PyDict_SetItem(result, key, copied) : PyList_Append(result, copied);
        Py_CLEAR(copied);
        if (status < 0) goto done;
    }
    if (PyErr_Occurred()) goto done;
    if (tuple) {
        copied = PyList_AsTuple(result);
        Py_SETREF(result, copied);
        copied = NULL;
        if (result == NULL) goto done;
    }
    if (PySet_Discard(v->active, identity) < 0 || PyDict_SetItem(v->seen, identity, result) < 0)
        goto done;
    goto done;
invalid_storage:
    fail(v, "Complete fixed typed trial storage required");
done:;
    /* Destructors must not replace the original failure. */
    PyObject *error = PyErr_GetRaisedException();
    Py_XDECREF(identity); Py_XDECREF(raw); Py_XDECREF(fields); Py_XDECREF(selected);
    Py_XDECREF(left); Py_XDECREF(right); Py_XDECREF(extra); Py_XDECREF(private_value);
    Py_XDECREF(items); Py_XDECREF(iterator); Py_XDECREF(child); Py_XDECREF(key);
    Py_XDECREF(pair); Py_XDECREF(copied);
    if (error != NULL) {
        Py_XDECREF(result);
        result = NULL;
        PyErr_SetRaisedException(error);
    }
    return result;
}

static PyObject *visit(Visitor *v, PyObject *value) {
    if (Py_EnterRecursiveCall(" in fresh typed storage visitor")) return NULL;
    PyObject *result = NULL;
    if ((++v->ticks & 255UL) != 0 || PyErr_CheckSignals() == 0) result = visit_body(v, value);
    Py_LeaveRecursiveCall();
    return result;
}

static int class_tuple(PyObject *value) {
    if (!PyTuple_CheckExact(value)) return 0;
    for (Py_ssize_t i = 0; i < PyTuple_GET_SIZE(value); ++i)
        if (!PyType_Check(PyTuple_GET_ITEM(value, i))) return 0;
    return 1;
}

static PyObject *project(PyObject *module, PyObject *args) {
    (void)module;
    PyObject *expected, *model, *roots;
    Visitor v = {0};
    if (!PyArg_ParseTuple(args, "OOOOOOO:project", &expected, &model, &roots,
            &v.allowed, &v.branch, &v.workflow, &v.require)) return NULL;
    if (!PyType_Check(expected) || !class_tuple(roots) || !class_tuple(v.allowed) ||
        !PyType_Check(v.branch) || !PyType_Check(v.workflow) || !PyCallable_Check(v.require)) {
        PyErr_SetString(PyExc_TypeError, "Invalid fresh typed visitor ABI");
        return NULL;
    }
    if (!member(roots, expected) || (PyObject *)Py_TYPE(model) != expected) {
        fail(&v, "Exact typed trial fact required");
        return NULL;
    }
    /* Builtin type tp_dict may be NULL with CPython 3.12 per-interpreter state.
     * Obtain the same two immutable builtin descriptors through the public API.
     */
    v.object_get = PyObject_GetAttrString((PyObject *)&PyBaseObject_Type, "__getattribute__");
    if (v.object_get == NULL) return NULL;
    v.type_get = PyObject_GetAttrString((PyObject *)&PyType_Type, "__getattribute__");
    if (v.type_get == NULL) { Py_DECREF(v.object_get); return NULL; }
    v.active = PySet_New(NULL);
    v.seen = PyDict_New();
    PyObject *result = NULL;
    if (v.active != NULL && v.seen != NULL) result = visit(&v, model);
    PyObject *error = PyErr_GetRaisedException();
    Py_XDECREF(v.active); Py_XDECREF(v.seen);
    Py_DECREF(v.object_get); Py_DECREF(v.type_get);
    if (error != NULL) {
        Py_XDECREF(result);
        result = NULL;
        PyErr_SetRaisedException(error);
    }
    return result;
}

static PyMethodDef methods[] = {
    {"project", project, METH_VARARGS, "Fresh experimental typed storage projection."},
    {NULL, NULL, 0, NULL}
};
static struct PyModuleDef definition = {
    PyModuleDef_HEAD_INIT, "_cold_typed_native_impl", NULL, -1, methods,
    NULL, NULL, NULL, NULL
};
PyMODINIT_FUNC PyInit__cold_typed_native_impl(void) {
#if PY_MAJOR_VERSION != 3 || PY_MINOR_VERSION != 12
#error "This experimental component requires CPython 3.12 qualification"
#endif
    return PyModule_Create(&definition);
}
