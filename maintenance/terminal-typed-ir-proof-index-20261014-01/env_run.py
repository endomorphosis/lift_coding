"""Run an explicit successor script against preserved local dependencies."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PRIOR = ROOT.parent / "terminal-codebase-ir-training-20261014-01"
BASELINE = ROOT.parent / "terminal-dispatch-evidence-20261014-01" / "checkout"
PINNED = ROOT.parent / "terminal-compact-retrieval-20261011-01" / "pinned-dependencies-v10"
paths = [str(ROOT), str(PRIOR),
    str(ROOT.parent / "terminal-proof-cache-revision-20261012-01" / "pinned-host-duckdb"),
    str(BASELINE), str(PINNED / "datasets"), str(PINNED / "kit")]
env = dict(os.environ, PYTHONPATH=":".join(paths), PYTHONDONTWRITEBYTECODE="1",
    OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
env.pop("IPFS_ACCELERATE_META_INDEX_DUCKLAKE", None)
if len(sys.argv) < 2 or Path(sys.argv[1]).name != sys.argv[1]:
    raise SystemExit("explicit successor script name required")
raise SystemExit(subprocess.call([sys.executable, "-B", str(ROOT / "launch.py"), sys.argv[1], *sys.argv[2:]],
    cwd=ROOT, env=env))
