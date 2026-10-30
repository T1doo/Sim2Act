"""Preserved handoff exploit. Exit 1 if forged synthetic flags are accepted.

This candidate is uninstalled. The probe passing closes this exploit only; it is not production
acceptance or a complete Source-family handoff proof.
"""
import json
from source_image import capture
from test_config import config
from test_native import native

original = bytes(bytearray(b'synthetic non-sensitive ordinary leaf ' + b'x' * 128))
clone = bytes(bytearray(original))
assert clone == original and clone is not original
image, anchors = capture(original, ())
forged = (*image[:4], (image[0],), *image[5:])
owner = native.make_owned(forged)
accepted = native.match_live(owner, clone, anchors, config(), ())
print(json.dumps(dict(status='KNOWN_BLOCKER_UNINSTALLED' if accepted else 'CLOSED',
                      expected_accepted=False, actual_accepted=accepted)))
raise SystemExit(1 if accepted else 0)
