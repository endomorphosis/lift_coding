"""Run one retained bounded CPU command against the staged native source."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('--name', required=True)
parser.add_argument('--probe', action='store_true')
parser.add_argument('--native-source', type=Path)
parser.add_argument('--logs', type=Path)
parser.add_argument('tests', nargs='*')
args = parser.parse_args()
base = Path(__file__).resolve().parent
source = (args.native_source or base / 'native_source').resolve()
logs = (args.logs or base / 'executions').resolve()
logs.mkdir(exist_ok=True)
prefix = logs / args.name
env = {
    'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin',
    'HOME': '/home/barberb',
    'IPFS_AUTO_INSTALL': 'false', 'IPFS_DATASETS_AUTO_INSTALL': 'false',
    'IPFS_KIT_AUTO_INSTALL_DEPS': '0', 'IPFS_DATASETS_PY_MINIMAL_IMPORTS': '1',
    'IPFS_DATASETS_PY_LAZY_INSTALL_ERGOAI': '0',
    'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
    'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2',
    'CUDA_VISIBLE_DEVICES': '', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
}
bootstrap = "import sys; sys.path[:0]=[sys.argv.pop(1), '/home/barberb/.local/lib/python3.12/site-packages']; import torch; torch.set_num_threads(2); torch.set_num_interop_threads(2); import pytest; raise SystemExit(pytest.main(sys.argv[1:]))"
if args.probe:
    argv = ['/usr/bin/python3.12', '-I', '-B', str(base / 'probe_native_cpu.py'), '--native-source', str(source)]
else:
    argv = ['/usr/bin/python3.12', '-I', '-B', '-c', bootstrap, str(source),
            '-c', '/dev/null', '--rootdir=' + str(source), '-p', 'no:cacheprovider', '-q', '-ra', *args.tests]
affinity = sorted(os.sched_getaffinity(0))[:2]

def limits():
    resource.setrlimit(resource.RLIMIT_AS, (16 * 1024**3, 16 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    os.sched_setaffinity(0, affinity)

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
record = {'schema': 'af-native-training-actual-command/v1',
    'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'argv': argv, 'cwd': str(source), 'environment': env,
    'limits': {'wall_seconds': 150, 'cpu_seconds': 120, 'address_space_bytes': 16 * 1024**3, 'cpu_affinity': affinity},
    'source_snapshot_sha256': sha(base / 'source_snapshot.json'),
    'packed_source_sha256': sha(source / 'ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_autoencoder_cuda.py'),
    'driver_sha256': sha(__file__),
    'probe_sha256': sha(base / 'probe_native_cpu.py') if args.probe else None,
    'test_sources': {p: sha(source / p) for p in args.tests if (source / p).is_file()}, 'research_run': False, 'provider_invoked': False}
clock = time.monotonic()
with prefix.with_suffix('.stdout.txt').open('xb') as out, prefix.with_suffix('.stderr.txt').open('xb') as err:
    try:
        process = subprocess.run(argv, cwd=source, env=env, stdout=out, stderr=err, timeout=150, preexec_fn=limits)
        exit_code = process.returncode
    except subprocess.TimeoutExpired:
        record["timed_out"] = True
        exit_code = None
    out.flush(); os.fsync(out.fileno()); err.flush(); os.fsync(err.fileno())
record.update(exit_code=exit_code, elapsed_seconds=time.monotonic()-clock,
    finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
record['logs'] = {str(prefix.with_suffix(s)): sha(prefix.with_suffix(s)) for s in ('.stdout.txt', '.stderr.txt')}
with prefix.with_suffix('.json').open('x') as f:
    json.dump(record, f, indent=2); f.write('\n')
print(json.dumps({'record': str(prefix.with_suffix('.json')), 'exit_code': exit_code}))

raise SystemExit(0 if exit_code == 0 else 1)
