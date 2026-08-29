"""Make sibling imports work both as scripts and as the `scripts` test package."""

import sys
from pathlib import Path


_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
