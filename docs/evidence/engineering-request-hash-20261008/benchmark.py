"""Paired pure-hash stage on the exact recorded, owned baseline snapshots.

This isolates serialization/hash cost. It does not emulate SQL, authorization,
or the full request and cannot establish an end-to-end or Windows speedup.
"""

import gzip
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

from sim2act.db import fingerprint


def baseline(snapshot):
    return fingerprint(snapshot), fingerprint(snapshot)


def optimized(snapshot):
    return (value := fingerprint(snapshot)), value


def main():
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    input_data = source.read_bytes()
    if source.suffix == ".gz":
        input_data = gzip.decompress(input_data)
    observations = json.loads(input_data)
    rows = []
    iterations = 300
    rounds = 9
    for expected, snapshot in observations["inputs"].items():
        assert baseline(snapshot) == optimized(snapshot) == (expected, expected)
        for _ in range(10):
            baseline(snapshot)
            optimized(snapshot)
        timings = []
        for round_index in range(rounds):
            pair = {}
            # Alternate order to avoid assigning the warm end to one variant.
            order = [baseline, optimized] if round_index % 2 == 0 else [optimized, baseline]
            for variant in order:
                start = time.perf_counter_ns()
                for _ in range(iterations):
                    assert variant(snapshot) == (expected, expected)
                pair[variant.__name__] = time.perf_counter_ns() - start
            timings.append(pair)
        old = statistics.median(t["baseline"] for t in timings) / iterations
        new = statistics.median(t["optimized"] for t in timings) / iterations
        rows.append(
            {
                "snapshot_fingerprint": expected,
                "serialized_bytes": len(json.dumps(snapshot).encode()),
                "pairs_nanoseconds": timings,
                "median_baseline_nanoseconds": old,
                "median_optimized_nanoseconds": new,
                "median_saved_nanoseconds": old - new,
                "stage_reduction_percent": (old - new) / old * 100,
            }
        )
    output.write_text(
        json.dumps(
            {
                "input_file_sha256": hashlib.sha256(input_data).hexdigest(),
                "iterations_per_variant_per_round": iterations,
                "rounds": rounds,
                "samples": rows,
                "product_fingerprint": "sim2act.db.fingerprint, unchanged",
                "scope": "pure adjacent double-hash stage only; exact same immutable input",
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"snapshots": len(rows), "output": str(output)}))


if __name__ == "__main__":
    main()
