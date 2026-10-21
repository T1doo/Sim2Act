"""Bounded in-memory observation inside five stages and four fixed tail spans.

No product import, extra graph walk, serializer, hash, I/O or authority. CPU
exclusive means inclusive minus observed child spans, not all child work.
"""

from contextlib import contextmanager
from threading import get_ident
from time import thread_time_ns

STAGES = ("_prepare", "_graph_run_context", "_graph_pb_accounting",
          "_graph_resolve_trial_source", "_graph_pb_archive_chain")
TAIL_STAGES = ("second_prefix", "second_commit", "recheck", "scope_exit")
METRICS = ("codec", "typed_storage", "raw_copy", "typed_equal")
FIELDS = ("calls", "returns", "raises", "inclusive_cpu_ns",
          "observed_child_exclusive_cpu_ns", "codec_output_bytes",
          "known_input_roots", "input_root_elements", "input_root_bytes",
          "unknown_input_roots")


class StageObserver:
    def __init__(self, clock=thread_time_ns, thread=get_ident, max_depth=32, *, enable_tail=False):
        self.clock, self.thread = clock, thread
        self.stages = STAGES + TAIL_STAGES if enable_tail else STAGES
        self.rows = [[0] * len(FIELDS) for _ in range(len(self.stages) * len(METRICS))]
        self.frames = [[0, 0] for _ in range(max_depth)]  # start, observed children
        self.seen = [False] * len(self.stages)
        self.owner = self.active = None
        self.depth = self.maximum_depth = 0
        self.enabled = True
        self.incomplete = False
        try:
            self.owner = self.thread()  # Same foreground thread as Worker.once.
        except BaseException:
            self.safe_fault()

    def fault(self):
        self.incomplete, self.enabled, self.active = True, False, None

    def safe_fault(self):
        try:
            self.fault()
        except BaseException:
            pass  # Diagnostic bookkeeping can never replace business control.

    @contextmanager
    def region(self, name):
        previous = self.active
        entered = False
        try:
            if self.enabled:
                current = self.thread()
                if self.owner is not None and current != self.owner:
                    pass
                elif (type(name) is not str or name not in self.stages
                      or (self.active is not None and not
                          (self.stages[self.active] == "second_commit" and name == "recheck"))):
                    self.fault()
                else:
                    if self.owner is None:
                        self.owner = current
                    if current == self.owner:
                        index = self.stages.index(name)
                        self.active = index
                        self.seen[index] = entered = True
        except BaseException:
            self.safe_fault()
        try:
            yield
        finally:
            try:
                if entered:
                    if self.depth:
                        self.fault()
                    self.active = previous if self.enabled else None
            except BaseException:
                self.safe_fault()

    def stage_wrapper(self, original, eligible):
        @contextmanager
        def wrapped(instance, name):
            # Enter/exit the original context exactly once, preserving its
            # exception handling and suppression semantics.
            with original(instance, name):
                try:
                    observe = eligible(instance)
                except BaseException:
                    self.safe_fault()
                    observe = False
                if observe:
                    with self.region(name):
                        yield
                else:
                    yield

        return wrapped

    @staticmethod
    def roots(row, args, positions):
        for position in positions:
            if position >= len(args):
                row[9] += 1
                continue
            value = args[position]
            kind = type(value)
            if kind is dict or kind is list or kind is tuple:
                row[6] += 1
                row[7] += len(value)  # Exact built-ins only; no user __len__.
            elif kind is bytes:
                row[6] += 1
                row[8] += len(value)
            else:
                row[9] += 1  # No typed-model attributes or extra traversal.

    def wrapper(self, original, metric, positions):
        metric_index = METRICS.index(metric)

        def wrapped(*args, **kwargs):
            slot = None
            try:
                if (self.enabled and self.active is not None
                        and self.thread() == self.owner):
                    if self.depth == len(self.frames):
                        self.fault()
                    else:
                        row = self.rows[self.active * 4 + metric_index]
                        row[0] += 1
                        self.roots(row, args, positions)
                        candidate = self.depth
                        frame = self.frames[candidate]
                        frame[1] = 0
                        start = self.clock()
                        if type(start) is not int:
                            raise TypeError("observer clock must return integer nanoseconds")
                        frame[0] = start
                        self.depth += 1
                        self.maximum_depth = max(self.maximum_depth, self.depth)
                        slot = candidate
            except BaseException:
                self.safe_fault()
            try:
                result = original(*args, **kwargs)
            except BaseException:
                if slot is not None:
                    self.finish(slot, row, False, None, metric_index)
                raise
            else:
                if slot is not None:
                    self.finish(slot, row, True, result, metric_index)
                return result

        return wrapped

    def finish(self, slot, row, returned, result, metric_index):
        try:
            if self.enabled:
                ended = self.clock()
                if type(ended) is not int:
                    raise TypeError("observer clock must return integer nanoseconds")
                inclusive = ended - self.frames[slot][0]
                exclusive = inclusive - self.frames[slot][1]
                if exclusive < 0:
                    raise ValueError("observer clock or nesting inconsistent")
                row[1 if returned else 2] += 1
                row[3] += inclusive
                row[4] += exclusive
                if metric_index == 0 and returned and type(result) is bytes:
                    row[5] += len(result)
                if slot:
                    self.frames[slot - 1][1] += inclusive
        except BaseException:
            self.safe_fault()
        finally:
            try:
                self.depth = slot
            except BaseException:
                self.safe_fault()

    def report(self):
        """Call only after original G0/stage unwinding; no timing-path I/O."""
        try:
            complete = not self.incomplete and self.active is None and self.depth == 0
            return dict(
                status=("COMPLETE_OBSERVATION" if complete else "INCOMPLETE")
                if any(self.seen) else ("NOT_REACHED" if complete else "INCOMPLETE"),
                timings_valid=complete and any(self.seen),
                cpu_clock="thread_time_ns",
                exclusive_basis="INCLUSIVE_MINUS_OBSERVED_CHILD_SPANS_ONLY",
                overhead="NONZERO; nested observer residual is included; not a G0 speedup proof",
                input_units="root elements/root bytes only; typed-model input bytes unmeasured",
                codec_bytes_basis="successful returned bytes, not an observed SHA call",
                stage_attribution="innermost active stage; recheck excluded from second_commit metric rows",
                max_stack_frames=len(self.frames),
                maximum_depth=self.maximum_depth,
                stages=[dict(stage=stage, reached=self.seen[i],
                             metrics={name: dict(zip(FIELDS, self.rows[i * 4 + j], strict=True))
                                      for j, name in enumerate(METRICS)} if self.seen[i] else None)
                        for i, stage in enumerate(self.stages)],
            )
        except BaseException:
            self.safe_fault()
            return dict(status="INCOMPLETE", detail="observer report unavailable")

    def install(self, patch, runtime, gate, eligible):
        patch.setattr(runtime, "_cold_graph_bytes", self.wrapper(runtime._cold_graph_bytes, "codec", (0,)))
        for attribute, metric, positions in (
            ("_trial_typed_storage", "typed_storage", (1,)),
            ("_trial_pure_data", "raw_copy", (0,)),
            ("_trial_typed_equal", "typed_equal", (0, 1)),
        ):
            patch.setattr(gate, attribute, self.wrapper(getattr(gate, attribute), metric, positions))
        patch.setattr(runtime._ColdCommitDiagnostics, "stage",
                      self.stage_wrapper(runtime._ColdCommitDiagnostics.stage, eligible))
