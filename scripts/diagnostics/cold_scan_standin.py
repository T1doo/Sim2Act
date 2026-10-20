"""Offline primitive-data cost split, NOT a production graph/profile/optimizer."""

import hashlib
import io
import pickle
import time


def encode(values):
    output = io.BytesIO()
    output.write(b"SIM2ACT_COLD_GRAPH_PICKLE_V2\x00")
    pickle._Pickler(output, protocol=5).dump(values)
    return output.getvalue()


def measure(values, iterations):
    if type(iterations) is not int or iterations < 1:
        raise ValueError("positive iterations required")
    serialization_seconds = digest_seconds = 0.0
    digest = None
    size = None
    for _ in range(iterations):
        started = time.perf_counter()
        raw = encode(values)  # Always serialize all values anew, with alias memo.
        encoded = time.perf_counter()
        current = hashlib.sha256(raw).hexdigest()
        ended = time.perf_counter()
        if digest is not None and current != digest:
            raise ValueError("stand-in changed during measurement")
        digest, size = current, len(raw)
        serialization_seconds += encoded - started
        digest_seconds += ended - encoded
    return dict(
        scope="STORED_PRIMITIVE_STANDIN_NOT_PRODUCTION_CPU_PROFILE",
        iterations=iterations,
        serialized_bytes=size,
        sha256=digest,
        serialization_seconds=serialization_seconds,
        digest_seconds=digest_seconds,
        total_seconds=serialization_seconds + digest_seconds,
        includes_product_validation_or_database=False,
        predicts_G0_speedup=False,
    )
