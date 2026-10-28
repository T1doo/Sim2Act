"""Optional bounded raw-data capture accelerator; Python remains available."""

import hashlib
from pathlib import Path

from setuptools import Extension, setup

source = Path(__file__).parent / "src/sim2act/_raw_snapshot.c"
setup(
    ext_modules=[
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
        )
    ]
)
