/* Optional CPython 3.12 experiment. No production routing imports this module.
 * Fresh DFS, source key identity, order and completed-node aliases are retained.
 * Only public CPython APIs; never release the GIL while holding graph objects.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stddef.h>
#include <structmember.h>

#ifndef SIM2ACT_VISITOR_SOURCE_SHA
#define SIM2ACT_VISITOR_SOURCE_SHA "unverified"
#endif

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

/* This narrow route deliberately stays below the existing signal-poll interval.
 * On the exact pinned 3.12 build, GC allocations schedule an eval breaker;
 * these bounded C-only operations do not execute it. Signals/GC may execute at
 * the entry poll, BEFORE fresh scanning. No GC state/counter is changed.
 */
#define QUAL_VISITS 255
#define QUAL_WORK 4096
typedef struct {
    PyObject *value, *raw;
    Py_ssize_t position, count;
    int model, weight, memo;
} QualFrame;

typedef struct {
    PyObject *spaces[QUAL_VISITS];
    int count, ok;
    int *work;
} QualNamespaces;

static int qualified_keys(PyObject *value, int *work);

static PyObject *dict_name(PyObject *space, const char *name) {
    PyObject *key = PyUnicode_InternFromString(name);
    if (key == NULL) return NULL;
    PyObject *result = PyDict_GetItemWithError(space, key);
    Py_DECREF(key);
    return result;
}

static PyObject *static_member(PyTypeObject *kind, const char *name, QualNamespaces *namespaces) {
    int *work = namespaces->work;
    PyObject *mro = kind->tp_mro;
    if (mro == NULL || !PyTuple_CheckExact(mro) || PyTuple_GET_SIZE(mro) > 16) {
        namespaces->ok = 0;
        return NULL;
    }
    for (Py_ssize_t i = 0; i < PyTuple_GET_SIZE(mro); ++i) {
        if (++*work > QUAL_WORK) { namespaces->ok = 0; return NULL; }
        PyObject *space = PyType_GetDict((PyTypeObject *)PyTuple_GET_ITEM(mro, i));
        if (space == NULL) { namespaces->ok = 0; return NULL; }
        int known = 0;
        for (int j = 0; j < namespaces->count; ++j) if (namespaces->spaces[j] == space) { known = 1; break; }
        if (!known) {
            /* Lookup must not dispatch foreign namespace key hash/equality.
             * This witness is invocation-local inside the C-only region.
             */
            if (namespaces->count >= QUAL_VISITS || !qualified_keys(space, work)) {
                Py_DECREF(space);
                namespaces->ok = 0;
                return NULL;
            }
            namespaces->spaces[namespaces->count++] = space;
        } else Py_DECREF(space);  /* PyType_GetDict returns a new reference. */
        PyObject *found = dict_name(space, name);
        if (found != NULL) return found;  /* Borrowed, no descriptor invocation. */
        if (PyErr_Occurred()) return NULL;
    }
    return NULL;
}

static int qualified_keys(PyObject *value, int *work) {
    if (!PyDict_CheckExact(value)) return 0;
    Py_ssize_t position = 0;
    PyObject *key, *child;
    while (PyDict_Next(value, &position, &key, &child)) {
        if (++*work > QUAL_WORK || !PyUnicode_CheckExact(key)) return 0;
    }
    return 1;
}

static PyObject *selection(PyObject *module, PyObject *args) {
    PyObject *expected, *model, *roots, *allowed, *branch, *workflow, *require_fn;
    PyObject *base, *meta, *extra = Py_None;
    if (!PyArg_ParseTuple(args, "OOOOOOOOO|O:select_project", &expected, &model, &roots,
            &allowed, &branch, &workflow, &require_fn, &base, &meta, &extra)) return NULL;
#ifndef SIM2ACT_COHORT_SELECTION_GATE
    if (extra != Py_None) {
        PyErr_SetString(PyExc_TypeError, "No extended selection ABI in this component");
        return NULL;
    }
#endif
    if (!class_tuple(roots) || !class_tuple(allowed) || !PyType_Check(expected) ||
        !PyType_Check(branch) || !PyType_Check(workflow) || !PyType_Check(base) ||
        !PyType_Check(meta) || !PyCallable_Check(require_fn)) {
        PyErr_SetString(PyExc_TypeError, "Invalid fresh typed qualification ABI");
        return NULL;
    }
    /* A handler can mutate input/metadata here. Re-read everything afterwards.
     * If it raises, propagate once: neither projection has started.
     */
    if (PyErr_CheckSignals() < 0) return NULL;
    PyThreadState *thread = PyThreadState_Get();
    int py_left = thread->py_recursion_remaining, c_left = thread->c_recursion_remaining;
    int work = 0, visits = 0, depth = 0, memo_count = 0, weight = 0, max_need = 64;
    const char *reason = "eligible";
    QualNamespaces namespaces = {.count = 0, .ok = 1, .work = &work};
    QualFrame *frames = PyMem_Calloc(QUAL_VISITS, sizeof(QualFrame));
    PyObject **memo = PyMem_Calloc(QUAL_VISITS, sizeof(PyObject *));
    unsigned char *active = PyMem_Calloc(QUAL_VISITS, 1);
    if (frames == NULL || memo == NULL || active == NULL) {
        PyMem_Free(frames); PyMem_Free(memo); PyMem_Free(active);
        return PyErr_NoMemory();
    }
    if (thread->c_profilefunc != NULL || thread->c_tracefunc != NULL) {
        reason = "trace-or-profile"; goto finish;
    }
#ifdef SIM2ACT_COHORT_SELECTION_GATE
    if (!SIM2ACT_COHORT_SELECTION_GATE(extra)) {
        reason = "cohort-configuration-or-raw"; goto finish;
    }
#endif
    if (!member(roots, expected) || (PyObject *)Py_TYPE(model) != expected) {
        reason = "root"; goto finish;
    }
    const char *names[] = {"__dict__", "__pydantic_fields_set__", "__pydantic_extra__", "__pydantic_private__"};
    PyObject *descriptors[4];
    for (int i = 0; i < 4; ++i) {
        descriptors[i] = static_member((PyTypeObject *)base, names[i], &namespaces);
        if (descriptors[i] == NULL || (i == 0 ? !Py_IS_TYPE(descriptors[i], &PyGetSetDescr_Type)
                : !Py_IS_TYPE(descriptors[i], &PyMemberDescr_Type))) {
            reason = "base-layout"; goto finish;
        }
    }
    PyObject *next = model;
    for (;;) {
        if (next != NULL) {
            if (++visits > QUAL_VISITS || ++work > QUAL_WORK) {
                reason = "scan-budget"; goto finish;
            }
            PyTypeObject *kind = Py_TYPE(next);
            int own_weight = kind == &PyTuple_Type ? 2 : 1;
            /* Includes visit frames, tuple generator frames, metadata/all/any,
             * require, import/helper overhead, and return to the Python adapter.
             * Overestimation only selects the unchanged Python implementation.
             */
            int need = 64 + 4 * (weight + own_weight);
            if (need > max_need) max_need = need;
            if (py_left < need || c_left < need) { reason = "remaining-stack"; goto finish; }
            if (kind == &PyUnicode_Type || kind == &PyLong_Type || kind == &PyFloat_Type ||
                kind == &PyBool_Type || kind == &PyBytes_Type || next == Py_None) goto advance;
            int found = -1;
            for (int i = 0; i < memo_count; ++i) if (memo[i] == next) { found = i; break; }
            if (found >= 0) {
                if (active[found]) { reason = "cycle"; goto finish; }
                goto advance;
            }
            PyObject *raw = NULL;
            int is_model = kind != &PyDict_Type && kind != &PyList_Type && kind != &PyTuple_Type;
            if (is_model) {
                if (!member(allowed, (PyObject *)kind) || Py_TYPE(kind) != (PyTypeObject *)meta ||
                    kind->tp_basicsize != ((PyTypeObject *)base)->tp_basicsize ||
                    kind->tp_dictoffset != ((PyTypeObject *)base)->tp_dictoffset ||
                    kind->tp_itemsize != 0) { reason = "model-layout"; goto finish; }
                for (int i = 0; i < 4; ++i) {
                    if (static_member(kind, names[i], &namespaces) != descriptors[i]) {
                        reason = "descriptor"; goto finish;
                    }
                }
                if (static_member(Py_TYPE(kind), "__pydantic_fields__", &namespaces) != NULL || !namespaces.ok) {
                    reason = "metaclass-fields"; goto finish;
                }
                PyObject *space = PyType_GetDict(kind);
                if (space == NULL) goto finish;
                PyObject *fields = dict_name(space, "__pydantic_fields__");
                Py_DECREF(space);  /* Class still owns its dictionary/fields. */
                if (fields == NULL || !qualified_keys(fields, &work)) {
                    reason = "fields"; goto finish;
                }
                /* Known builtin descriptors only, never a user descriptor. */
                PyObject *slots[3];
                for (int i = 1; i < 4; ++i) {
                    PyMemberDef *definition = ((PyMemberDescrObject *)descriptors[i])->d_member;
                    if (definition->type != T_OBJECT_EX || definition->offset < 0 ||
                        definition->offset + (Py_ssize_t)sizeof(PyObject *) > kind->tp_basicsize) {
                        reason = "slot-layout"; goto finish;
                    }
                    slots[i - 1] = *(PyObject **)((char *)next + definition->offset);
                }
                PyObject *selected = slots[0], *extra = slots[1], *private_value = slots[2];
                if (selected == NULL || !PySet_CheckExact(selected) || extra != Py_None || private_value != Py_None) {
                    reason = "slots"; goto finish;
                }
                raw = Py_TYPE(descriptors[0])->tp_descr_get(descriptors[0], next, (PyObject *)kind);
                if (raw == NULL) goto finish;
                int ok = qualified_keys(raw, &work) &&
                    qualified_keys(raw, &work) && PySet_CheckExact(selected) &&
                    PyDict_Size(raw) == PyDict_Size(fields);
                if (ok) {
                    Py_ssize_t position = 0;
                    PyObject *key, *child;
                    while (PyDict_Next(raw, &position, &key, &child)) {
                        if (++work > QUAL_WORK || PyDict_Contains(fields, key) != 1) { ok = 0; break; }
                    }
                }
                if (ok) {
                    PyObject *iterator = PyObject_GetIter(selected), *key;
                    if (iterator == NULL) ok = 0;
                    else {
                        while ((key = PyIter_Next(iterator)) != NULL) {
                            ok = ++work <= QUAL_WORK && PyUnicode_CheckExact(key) && PyDict_Contains(fields, key) == 1;
                            Py_DECREF(key);
                            if (!ok) break;
                        }
                        Py_DECREF(iterator);
                    }
                }
                if (!ok || PyErr_Occurred()) {
                    Py_XDECREF(raw);
                    if (PyErr_Occurred()) goto finish;
                    reason = "storage"; goto finish;
                }
            } else if (kind == &PyDict_Type) {
                if (!qualified_keys(next, &work)) { reason = "keys-or-budget"; goto finish; }
                raw = Py_NewRef(next);
            }
            found = memo_count++;
            memo[found] = next; active[found] = 1;
            frames[depth++] = (QualFrame){next, raw, 0,
                kind == &PyList_Type ? PyList_GET_SIZE(next) : kind == &PyTuple_Type ? PyTuple_GET_SIZE(next) : 0,
                is_model, own_weight, found};
            weight += own_weight;
        }
advance:
        next = NULL;
        while (depth > 0 && next == NULL) {
            QualFrame *frame = &frames[depth - 1];
            if (++work > QUAL_WORK) { reason = "scan-budget"; goto finish; }
            if (frame->raw != NULL) {
                PyObject *key, *child;
                while (PyDict_Next(frame->raw, &frame->position, &key, &child)) {
                    if (++work > QUAL_WORK) { reason = "scan-budget"; goto finish; }
                    if (frame->model && child == Py_None &&
                        (((PyObject *)Py_TYPE(frame->value) == branch && omission_key(key, "value") == 1) ||
                         ((PyObject *)Py_TYPE(frame->value) == workflow && omission_key(key, "when") == 1))) continue;
                    next = child;
                    break;
                }
            } else if (frame->position < frame->count) {
                next = PyList_CheckExact(frame->value) ? PyList_GET_ITEM(frame->value, frame->position)
                    : PyTuple_GET_ITEM(frame->value, frame->position);
                frame->position++;
            }
            if (next == NULL) {
                active[frame->memo] = 0;
                weight -= frame->weight;
                Py_CLEAR(frame->raw);
                depth--;
            }
        }
        if (depth == 0 && next == NULL) break;
    }
finish:;
    PyObject *error = PyErr_GetRaisedException();
    while (depth > 0) Py_XDECREF(frames[--depth].raw);
    for (int i = 0; i < namespaces.count; ++i) Py_DECREF(namespaces.spaces[i]);
    PyMem_Free(frames); PyMem_Free(memo); PyMem_Free(active);
    if (error != NULL) { PyErr_SetRaisedException(error); return NULL; }
    PyObject *result = Py_None;
    int chosen = strcmp(reason, "eligible") == 0;
    if (chosen) {
        PyObject *arguments = PyTuple_GetSlice(args, 0, 7);
        if (arguments == NULL) return NULL;
        result = project(module, arguments);  /* No Python return/eval between scan and copy. */
        Py_DECREF(arguments);
        if (result == NULL) return NULL;
    } else Py_INCREF(result);
    PyObject *reply = Py_BuildValue("Nsiiiiii", result, reason, visits, work, max_need, py_left, c_left, chosen);
    return reply;
}

static PyObject *build_identity(PyObject *module, PyObject *unused) {
    (void)module; (void)unused;
    return Py_BuildValue("ssnnn", SIM2ACT_VISITOR_SOURCE_SHA, Py_GetVersion(),
        (Py_ssize_t)sizeof(PyThreadState), (Py_ssize_t)offsetof(PyThreadState, py_recursion_remaining),
        (Py_ssize_t)offsetof(PyThreadState, c_recursion_remaining));
}

static PyObject *stack_ready(PyObject *module, PyObject *unused) {
    (void)module; (void)unused;
    PyThreadState *thread = PyThreadState_Get();
    /* Called directly at the original input_bytes frame, before Python
     * selectors/catalog helpers add frames. Read only, no counter changes. */
    return PyBool_FromLong(thread->py_recursion_remaining >= 128 && thread->c_recursion_remaining >= 128);
}

static PyMethodDef methods[] = {
    {"project", project, METH_VARARGS, "Fresh experimental typed storage projection."},
    {"select_project", selection, METH_VARARGS, "Bounded qualification then one projection, or Python selection."},
    {"build_identity", build_identity, METH_NOARGS, "Exact build/source and thread-state layout witness."},
    {"stack_ready", stack_ready, METH_NOARGS, "Read current remaining stacks before Python selection wrappers."},
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
