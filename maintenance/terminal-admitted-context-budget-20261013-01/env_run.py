"""Run a named W script against pinned local dependencies only."""
import os,sys,subprocess
from pathlib import Path
W=Path(__file__).resolve().parent
C=Path('/home/barberb/lift_coding/maintenance/terminal-admitted-context-budget-20261013-01/checkout')
E=Path('/home/barberb/lift_coding/maintenance/terminal-compact-retrieval-20261011-01/pinned-dependencies-v10')
paths=['/home/barberb/lift_coding/maintenance/terminal-proof-cache-revision-20261012-01/pinned-host-duckdb','/home/barberb/lift_coding/maintenance/terminal-token-pairing-20261012-01/pinned-host-tokenizer',str(C),str(E/'datasets'),str(E/'kit'),'/home/barberb/lift_coding/.venvs/terminal-bench-harbor/lib/python3.12/site-packages']
env=dict(os.environ,PYTHONPATH=':'.join(paths),PYTHONDONTWRITEBYTECODE='1',TIKTOKEN_CACHE_DIR='/tmp/data-gym-cache')
env.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE',None)
args=['/home/barberb/lift_coding/.venv/bin/python','-B',str(W/sys.argv[1]),*sys.argv[2:]]
raise SystemExit(subprocess.call(args,cwd=C,env=env))
