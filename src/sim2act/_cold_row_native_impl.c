/* Explicit offline fresh RowMapping leaf. No Pickler/reducer substitution. */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#ifndef SIM2ACT_VISITOR_SOURCE_SHA
#define SIM2ACT_VISITOR_SOURCE_SHA "unverified"
#endif

typedef struct {
    PyObject *function, *code, *require, *require_code, *leaf, *leaf_code;
    PyObject *globals, *builtins, *codec;
    PyObject *dict_sizeof;
    PyObject *kinds[4], *mros[4], *descriptors[5], *names[18], *expected[9], *messages[3];
    unsigned long native_calls, python_calls;
} Reader;

static void dispose(PyObject *capsule) {
    PyObject *error = PyErr_GetRaisedException();
    Reader *s = PyCapsule_GetPointer(capsule, "sim2act.offline.row-reader");
    if (s != NULL) {
        Py_XDECREF(s->function); Py_XDECREF(s->code); Py_XDECREF(s->require);
        Py_XDECREF(s->require_code); Py_XDECREF(s->leaf); Py_XDECREF(s->leaf_code);
        Py_XDECREF(s->globals); Py_XDECREF(s->builtins); Py_XDECREF(s->codec);
        Py_XDECREF(s->dict_sizeof);
        for (int i = 0; i < 4; ++i) { Py_XDECREF(s->kinds[i]); Py_XDECREF(s->mros[i]); }
        for (int i = 0; i < 5; ++i) Py_XDECREF(s->descriptors[i]);
        for (int i = 0; i < 18; ++i) Py_XDECREF(s->names[i]);
        for (int i = 0; i < 9; ++i) Py_XDECREF(s->expected[i]);
        for (int i = 0; i < 3; ++i) Py_XDECREF(s->messages[i]);
        PyMem_Free(s);
    }
    PyErr_Clear();
    if (error != NULL) PyErr_SetRaisedException(error);
}

/* Bounded static lookup: no custom descriptor, foreign-key hashing/equality or
 * cached type-version/PASS result. PyType_GetDict returns a NEW reference. */
static int table_budget(Reader *s, PyObject *dict) {
    /* Logical len omits dummy entries left by deletion. This exact immutable
     * built-in C descriptor measures the complete table, without hashing keys
     * or calling an input object's __sizeof__. No private dict-version cache. */
    PyObject *bytes = PyObject_CallOneArg(s->dict_sizeof, dict);
    if (bytes == NULL) return -1;
    Py_ssize_t size = PyLong_AsSsize_t(bytes);
    Py_DECREF(bytes);
    if (size == -1 && PyErr_Occurred()) return -1;
    return size <= 8192;
}

static int slots(Reader *s, PyObject *kind, PyObject **names, int count, PyObject **out) {
    PyObject *mro = ((PyTypeObject *)kind)->tp_mro;
    if (mro == NULL || !PyTuple_CheckExact(mro)) return 0;
    int found = 0, work = 0;
    for (int j = 0; j < count; ++j) out[j] = NULL;
    for (Py_ssize_t i = 0; i < PyTuple_GET_SIZE(mro) && found < count; ++i) {
        PyObject *base = PyTuple_GET_ITEM(mro, i);
        if (!PyType_Check(base)) return 0;
        PyObject *space = PyType_GetDict((PyTypeObject *)base);
        if (space == NULL) return PyErr_Occurred() ? -1 : 0;
        int bounded = table_budget(s, space);
        if (bounded != 1) { Py_DECREF(space); return bounded; }
        Py_ssize_t pos = 0;
        PyObject *key, *value;
        while (PyDict_Next(space, &pos, &key, &value)) {
            if (++work > 256 || !PyUnicode_CheckExact(key)) {
                Py_DECREF(space); return 0;
            }
        }
        for (int j = 0; j < count; ++j) if (out[j] == NULL) {
            out[j] = PyDict_GetItemWithError(space, names[j]);
            if (out[j] != NULL) ++found;
            else if (PyErr_Occurred()) { Py_DECREF(space); return -1; }
        }
        Py_DECREF(space);
    }
    return found == count;
}

static PyObject *global(Reader *s, int name) {
    PyObject *value = PyDict_GetItemWithError(s->globals, s->names[name]);
    if (value == NULL && !PyErr_Occurred())
        value = PyDict_GetItemWithError(s->builtins, s->names[name]);
    return value;
}

static int schema(Reader *s) {
    if (PyFunction_GetCode(s->function) != s->code ||
            PyFunction_GetCode(s->require) != s->require_code ||
            PyFunction_GetCode(s->leaf) != s->leaf_code ||
            Py_TYPE(s->codec) != &PyModule_Type) return 0;
    /* Known implementation globals/builtins only. Original single-arg function
     * handles unknown code/callbacks after this C frame has returned None. */
    for (int i = 0; i < 9; ++i) if (global(s, i) != s->expected[i])
        return PyErr_Occurred() ? -1 : 0;
    if (global(s, 17) != s->codec ||
            PyDict_GetItemWithError(PyModule_GetDict(s->codec), s->names[0]) != s->leaf)
        return PyErr_Occurred() ? -1 : 0;
    for (int i = 0; i < 4; ++i) {
        if (((PyTypeObject *)s->kinds[i])->tp_mro != s->mros[i] ||
                global(s, i + 13) != s->kinds[i]) return PyErr_Occurred() ? -1 : 0;
    }
    if (((PyTypeObject *)s->kinds[3])->tp_str != PyUnicode_Type.tp_str) return 0;
    PyObject *actual[3];
    int ok = slots(s, s->kinds[0], s->names + 9, 3, actual);
    if (ok != 1) return ok;
    for (int i = 0; i < 3; ++i) if (actual[i] != s->descriptors[i]) return 0;
    return 1;
}

static PyObject *get(PyObject *descriptor, PyObject *value) {
    return Py_TYPE(descriptor)->tp_descr_get(descriptor, value, (PyObject *)Py_TYPE(value));
}

static void fail(Reader *s, int message) {
    PyObject *result = PyObject_CallFunctionObjArgs(s->require, Py_False, s->messages[message], NULL);
    if (result != NULL) {
        Py_DECREF(result);
        PyErr_SetString(PyExc_RuntimeError, "row require did not raise");
    }
}

static PyObject *select_row(PyObject *capsule, PyObject *value) {
    Reader *s = PyCapsule_GetPointer(capsule, "sim2act.offline.row-reader");
    if (s == NULL || PyErr_CheckSignals() < 0) return NULL;
    PyObject *parent = NULL, *data = NULL, *index = NULL, *keys = NULL;
    PyObject *lookup = NULL, *text = NULL, *result = NULL;
    int ok = schema(s);
    if (ok < 0) return NULL;
    if (!ok || (PyObject *)Py_TYPE(value) != s->kinds[0]) goto legacy;
    parent = get(s->descriptors[0], value);
    if (parent == NULL) goto done;
    int meta = (PyObject *)Py_TYPE(parent) == s->kinds[1] ? 1 :
        ((PyObject *)Py_TYPE(parent) == s->kinds[2] ? 2 : 0);
    if (meta) {
        PyObject *actual[1];
        ok = slots(s, s->kinds[meta], s->names + 12, 1, actual);
        if (ok < 0) goto done;
        if (!ok || actual[0] != s->descriptors[meta + 2]) goto legacy;
    }
    /* Same three original reads, then combined storage gate, then _keys. */
    data = get(s->descriptors[1], value);
    if (data == NULL) goto done;
    index = get(s->descriptors[2], value);
    if (index == NULL) goto done;
    if (!meta || !PyTuple_CheckExact(data) || !PyDict_CheckExact(index)) {
        ++s->native_calls; fail(s, 0); goto done;
    }
    keys = get(s->descriptors[meta + 2], parent);
    if (keys == NULL) goto done;
    if (!PyList_CheckExact(keys)) { ++s->native_calls; fail(s, 1); goto done; }
    /* Only optimization work is bounded; a larger valid row goes unchanged to
     * legacy before lookup allocation. Foreign index keys count toward work.
     * Hidden data is returned intact; it is neither scanned nor truncated. */
    if (PyList_GET_SIZE(keys) > 64 || PyDict_Size(index) > 64) goto legacy;
    ok = table_budget(s, index);
    if (ok < 0) goto done;
    if (!ok) goto legacy;
    Py_ssize_t chars = 0;
    for (Py_ssize_t i = 0; i < PyList_GET_SIZE(keys); ++i) {
        PyObject *key = PyList_GET_ITEM(keys, i);
        if (!PyUnicode_CheckExact(key) && (PyObject *)Py_TYPE(key) != s->kinds[3]) {
            ++s->native_calls; fail(s, 1); goto done;
        }
        Py_ssize_t n = PyUnicode_GET_LENGTH(key);
        if (n > 8192 - chars) goto legacy;
        chars += n;
    }
    Py_ssize_t pos = 0;
    PyObject *key, *position;
    while (PyDict_Next(index, &pos, &key, &position)) {
        if (PyUnicode_CheckExact(key) || (PyObject *)Py_TYPE(key) == s->kinds[3]) {
            Py_ssize_t n = PyUnicode_GET_LENGTH(key);
            if (n > 8192 - chars) goto legacy;
            chars += n;
        }
    }
    ++s->native_calls;
    lookup = PyDict_New();
    if (lookup == NULL) goto done;
    pos = 0;
    while (PyDict_Next(index, &pos, &key, &position)) {
        if (!PyUnicode_CheckExact(key) && (PyObject *)Py_TYPE(key) != s->kinds[3]) continue;
        if (!PyLong_CheckExact(position)) { fail(s, 2); goto done; }
        Py_ssize_t number = PyLong_AsSsize_t(position);
        if (number == -1 && PyErr_Occurred()) {
            if (!PyErr_ExceptionMatches(PyExc_OverflowError)) goto done;
            PyErr_Clear(); fail(s, 2); goto done;
        }
        if (number < 0 || number >= PyTuple_GET_SIZE(data)) { fail(s, 2); goto done; }
        text = PyObject_Str(key);
        if (text == NULL || PyDict_SetItem(lookup, text, position) < 0) goto done;
        Py_CLEAR(text);
    }
    for (Py_ssize_t i = 0; i < PyList_GET_SIZE(keys); ++i) {
        text = PyObject_Str(PyList_GET_ITEM(keys, i));
        if (text == NULL) goto done;
        ok = PyDict_Contains(lookup, text);
        Py_CLEAR(text);
        if (ok < 0) goto done;
        if (!ok) { fail(s, 1); goto done; }
    }
    result = PyTuple_Pack(3, keys, data, lookup);
    goto done;
legacy:
    ++s->python_calls;
    result = Py_NewRef(Py_None);
done:;
    PyObject *error = PyErr_GetRaisedException();
    Py_XDECREF(parent); Py_XDECREF(data); Py_XDECREF(index); Py_XDECREF(keys);
    Py_XDECREF(lookup); Py_XDECREF(text);
    if (error != NULL) { Py_XDECREF(result); PyErr_SetRaisedException(error); return NULL; }
    return result;
}

static PyMethodDef reader_method = {"select_row", select_row, METH_O,
    "Fresh bounded row projection or None before projection; exceptions never retry."};

static PyObject *make_reader(PyObject *module, PyObject *args) {
    (void)module;
    PyObject *function, *require, *leaf, *kinds[4];
    if (!PyArg_ParseTuple(args, "OOOOOOO", &function, &require, &leaf,
            &kinds[0], &kinds[1], &kinds[2], &kinds[3])) return NULL;
    if (!PyFunction_Check(function) || !PyFunction_Check(require) || !PyFunction_Check(leaf)) Py_RETURN_NONE;
    for (int i = 0; i < 4; ++i) if (!PyType_Check(kinds[i])) Py_RETURN_NONE;
    Reader *s = PyMem_Calloc(1, sizeof(*s));
    if (s == NULL) return PyErr_NoMemory();
    PyObject *capsule = PyCapsule_New(s, "sim2act.offline.row-reader", dispose);
    if (capsule == NULL) { PyMem_Free(s); return NULL; }
    s->function = Py_NewRef(function); s->code = Py_NewRef(PyFunction_GetCode(function));
    s->require = Py_NewRef(require); s->require_code = Py_NewRef(PyFunction_GetCode(require));
    s->leaf = Py_NewRef(leaf); s->leaf_code = Py_NewRef(PyFunction_GetCode(leaf));
    s->globals = Py_NewRef(PyFunction_GetGlobals(function));
    s->builtins = PyObject_GetAttrString(function, "__builtins__");
    if (s->builtins == NULL) goto error;
    s->dict_sizeof = PyObject_GetAttrString((PyObject *)&PyDict_Type, "__sizeof__");
    if (s->dict_sizeof == NULL) goto error;
    if (Py_TYPE(s->dict_sizeof) != &PyMethodDescr_Type) goto unsuitable;
    if (!PyDict_CheckExact(s->globals) || !PyDict_CheckExact(s->builtins)) goto unsuitable;
    const char *names[] = {"require", "type", "object", "dict", "list", "tuple", "str", "len", "all",
        "_parent", "_data", "_key_to_index", "_keys", "_ColdGraphRowMapping",
        "_ColdGraphCursorMeta", "_ColdGraphSimpleMeta", "_ColdGraphQuotedName", "codec"};
    for (int i = 0; i < 18; ++i) {
        s->names[i] = PyUnicode_InternFromString(names[i]);
        if (s->names[i] == NULL) goto error;
    }
    for (int i = 0; i < 9; ++i) {
        PyObject *item = global(s, i);
        if (item == NULL) goto unsuitable;
        s->expected[i] = Py_NewRef(item);
    }
    if (s->expected[0] != require || s->expected[1] != (PyObject *)&PyType_Type ||
            s->expected[2] != (PyObject *)&PyBaseObject_Type || s->expected[3] != (PyObject *)&PyDict_Type ||
            s->expected[4] != (PyObject *)&PyList_Type || s->expected[5] != (PyObject *)&PyTuple_Type ||
            s->expected[6] != (PyObject *)&PyUnicode_Type) goto unsuitable;
    s->codec = PyDict_GetItemString(s->globals, "codec");
    if (s->codec == NULL) goto unsuitable;
    Py_INCREF(s->codec);
    for (int i = 0; i < 4; ++i) {
        s->kinds[i] = Py_NewRef(kinds[i]);
        PyObject *mro = ((PyTypeObject *)kinds[i])->tp_mro;
        if (mro == NULL) goto unsuitable;
        s->mros[i] = Py_NewRef(mro);
    }
    PyObject *found[3];
    int ok = slots(s, kinds[0], s->names + 9, 3, found);
    if (ok != 1) goto unsuitable;
    for (int i = 0; i < 3; ++i) {
        if (Py_TYPE(found[i]) != &PyGetSetDescr_Type) goto unsuitable;
        s->descriptors[i] = Py_NewRef(found[i]);
    }
    for (int i = 1; i < 3; ++i) {
        ok = slots(s, kinds[i], s->names + 12, 1, found);
        if (ok != 1 || Py_TYPE(found[0]) != &PyMemberDescr_Type) goto unsuitable;
        s->descriptors[i + 2] = Py_NewRef(found[0]);
    }
    const char *messages[] = {"Exact Cold graph SQL row storage required",
        "Complete Cold graph SQL row keys required", "Complete Cold graph SQL row index positions required"};
    PyObject *constants = PyObject_GetAttrString(s->code, "co_consts");
    if (constants == NULL) goto error;
    for (int j = 0; j < 3; ++j)
        for (Py_ssize_t i = 0; i < PyTuple_GET_SIZE(constants); ++i) {
            PyObject *item = PyTuple_GET_ITEM(constants, i);
            if (PyUnicode_CheckExact(item) && PyUnicode_CompareWithASCIIString(item, messages[j]) == 0) {
                s->messages[j] = Py_NewRef(item); break;
            }
        }
    Py_DECREF(constants);
    for (int i = 0; i < 3; ++i) if (s->messages[i] == NULL) goto unsuitable;
    ok = schema(s);
    if (ok != 1) goto unsuitable;
    PyObject *result = PyCFunction_NewEx(&reader_method, capsule, NULL);
    Py_DECREF(capsule); return result;
unsuitable:
    if (PyErr_Occurred()) goto error;
    Py_DECREF(capsule); Py_RETURN_NONE;
error:
    Py_DECREF(capsule); return NULL;
}

static PyObject *counts(PyObject *module, PyObject *value) {
    (void)module;
    if (!PyCFunction_Check(value) || PyCFunction_GET_FUNCTION(value) != select_row) {
        PyErr_SetString(PyExc_TypeError, "Expected this explicit row reader"); return NULL;
    }
    Reader *s = PyCapsule_GetPointer(PyCFunction_GET_SELF(value), "sim2act.offline.row-reader");
    if (s == NULL) return NULL;
    return Py_BuildValue("kk", s->native_calls, s->python_calls);
}
static PyObject *identity(PyObject *module, PyObject *unused) {
    (void)module; (void)unused;
    return Py_BuildValue("ss", SIM2ACT_VISITOR_SOURCE_SHA, Py_GetVersion());
}
static PyMethodDef methods[] = {
    {"make_reader", make_reader, METH_VARARGS, "Explicit known-schema row reader."},
    {"counts", counts, METH_O, "Native attempts / pre-projection Python selections."},
    {"build_identity", identity, METH_NOARGS, "Exact source/build witness."},
    {NULL, NULL, 0, NULL}
};
static struct PyModuleDef definition = {PyModuleDef_HEAD_INIT, "_cold_row_native_impl", NULL, -1,
    methods, NULL, NULL, NULL, NULL};
PyMODINIT_FUNC PyInit__cold_row_native_impl(void) {
#if PY_MAJOR_VERSION != 3 || PY_MINOR_VERSION != 12
#error "Exact qualified CPython 3.12 required"
#endif
    return PyModule_Create(&definition);
}
