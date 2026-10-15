"""Explicit local experiment using immutable dependencies and native policy."""
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parent
RICH=ROOT.parent/'terminal-typed-ir-training-20261014-01'
TYPED=ROOT.parent/'terminal-typed-ir-proof-index-20261014-01'
PRIOR=ROOT.parent/'terminal-codebase-ir-training-20261014-01'
PINNED=ROOT.parent/'terminal-compact-retrieval-20261011-01'/'pinned-dependencies-v10'
paths=[ROOT,ROOT.parent/'terminal-token-pairing-20261012-01'/'pinned-host-tokenizer',RICH,TYPED,PRIOR,ROOT.parent/'terminal-proof-cache-revision-20261012-01'/'pinned-host-duckdb',
 ROOT.parent/'terminal-dispatch-evidence-20261014-01'/'checkout',PINNED/'datasets',PINNED/'kit']
env=dict(os.environ,PYTHONPATH=':'.join(map(str,paths)),PYTHONDONTWRITEBYTECODE='1',
 OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='',
 HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
env.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE',None)
for name in list(env):
 if name.startswith('GIT_'):env.pop(name)
env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_TEMPLATE_DIR='')
raise SystemExit(subprocess.call([sys.executable,'-B',str(ROOT/'launch.py'),*sys.argv[1:]],cwd=ROOT,env=env))
