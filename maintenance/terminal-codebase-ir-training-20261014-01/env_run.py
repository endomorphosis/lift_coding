"""Run an explicit training-stage script using preserved source dependencies."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT.parent / "terminal-dispatch-evidence-20261014-01" / "checkout"
PINNED = ROOT.parent / "terminal-compact-retrieval-20261011-01" / "pinned-dependencies-v10"
PATHS = [str(ROOT),
    str(ROOT.parent / "terminal-proof-cache-revision-20261012-01" / "pinned-host-duckdb"),
    str(BASELINE), str(PINNED / "datasets"), str(PINNED / "kit")]
env = dict(os.environ, PYTHONPATH=":".join(PATHS), PYTHONDONTWRITEBYTECODE="1",
    OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
env.pop("IPFS_ACCELERATE_META_INDEX_DUCKLAKE", None)
if len(sys.argv) < 2 or Path(sys.argv[1]).name != sys.argv[1]:
    raise SystemExit("one explicit local script name required")
raise SystemExit(subprocess.call([sys.executable, "-B", str(ROOT / sys.argv[1]), *sys.argv[2:]],
    cwd=ROOT, env=env))
