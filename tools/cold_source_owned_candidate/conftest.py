"""Explicit candidate-only tests reuse synthetic SQL fixtures, never Worker IO."""
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / 'tests'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
