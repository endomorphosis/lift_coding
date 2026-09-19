"""Put ~/lift_coding/JevOps on sys.path and default LRA CAS dir."""
from __future__ import annotations

import os
import sys
from pathlib import Path

JEVOPS_ROOT = Path.home() / "lift_coding" / "JevOps"
if JEVOPS_ROOT.is_dir() and str(JEVOPS_ROOT) not in sys.path:
    sys.path.insert(0, str(JEVOPS_ROOT))

_LRA_CAS = Path(__file__).resolve().parent.parent / "evidence" / "canaries" / "nca-cas"
os.environ.setdefault("JEVOPS_CAS_DIR", str(_LRA_CAS))

try:
    import _jevops_hooks

    _jevops_hooks.register_lra_hooks()
except Exception:
    pass
