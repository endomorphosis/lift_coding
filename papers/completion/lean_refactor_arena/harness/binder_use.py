"""LRA adapter — Lean binder gates live in JevOps."""
from __future__ import annotations

from pathlib import Path

import _jevops_path  # noqa: F401
from jevops import binders as _mod

globals().update({k: getattr(_mod, k) for k in dir(_mod) if not k.startswith("__")})

MEMORY_DEFAULT = (
    Path(__file__).resolve().parent.parent / "evidence" / "canaries" / "refactor-memory.json"
)
SKILL_ANALYSIS_DEFAULT = MEMORY_DEFAULT.parent / "skill-analysis.json"
