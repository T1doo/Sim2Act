"""Optional bounded raw-data capture accelerator; Python remains available."""

import hashlib
import os
from pathlib import Path

from setuptools import Extension, setup

source = Path(__file__).parent / "src/sim2act/_raw_snapshot.c"
setup(
    ext_modules=[]
    if os.environ.get("SIM2ACT_BUILD_PYTHON_PREVIEW") == "1"
    else [
        Extension(
            "sim2act._raw_snapshot",
            ["src/sim2act/_raw_snapshot.c"],
            optional=True,
            define_macros=[
                (
                    "SIM2ACT_RAW_SOURCE_SHA",
                    '"' + hashlib.sha256(source.read_bytes()).hexdigest() + '"',
                )
            ],
        ),
        Extension(
            "sim2act._cold_graph_structure",
            ["src/sim2act/_cold_graph_structure.c"],
            optional=True,
            define_macros=[
                (
                    "SIM2ACT_GRAPH_SOURCE_SHA",
                    '"'
                    + hashlib.sha256(
                        Path(__file__)
                        .parent.joinpath("src/sim2act/_cold_graph_structure.c")
                        .read_bytes()
                    ).hexdigest()
                    + '"',
                )
            ],
        ),
        Extension(
            "sim2act._cold_typed_cohort",
            ["src/sim2act/_cold_typed_cohort.c"],
            optional=True,
            depends=["src/sim2act/_cold_typed_native_impl.c", "src/sim2act/_raw_snapshot.c", "src/sim2act/_cold_cohort_backend.py"],
            define_macros=[("SIM2ACT_VISITOR_SOURCE_SHA", '"' + hashlib.sha256(b''.join(
                Path(__file__).parent.joinpath("src/sim2act", name).read_bytes()
                for name in ("_cold_typed_cohort.c", "_cold_typed_native_impl.c", "_raw_snapshot.c", "_cold_cohort_backend.py")
            )).hexdigest() + '"')],
        ),
        Extension(
            "sim2act._cold_source_owned_impl",
            ["src/sim2act/_cold_source_owned_impl.c"],
            optional=True,
            depends=["src/sim2act/_cold_source_live_match.h", "src/sim2act/_cold_source_code.h", "src/sim2act/_cold_source_view.h", "src/sim2act/_cold_source_shape.h"],
            define_macros=[("SOURCE_SHA", '"' + hashlib.sha256(
                Path(__file__).parent.joinpath("src/sim2act/_cold_source_owned_impl.c").read_bytes()
                + Path(__file__).parent.joinpath("src/sim2act/_cold_source_live_match.h").read_bytes()
                + Path(__file__).parent.joinpath("src/sim2act/_cold_source_code.h").read_bytes()
                + Path(__file__).parent.joinpath("src/sim2act/_cold_source_view.h").read_bytes()
                + Path(__file__).parent.joinpath("src/sim2act/_cold_source_shape.h").read_bytes()
            ).hexdigest() + '"')],
        ),
    ]
)
