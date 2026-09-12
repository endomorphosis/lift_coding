"""Read public toolchain versions and cached-model file metadata; no provider calls."""
import datetime, hashlib, json, os, platform, subprocess, sys
from pathlib import Path
sys.path.insert(0, '/home/barberb/.local/lib/python3.12/site-packages')
import torch, numpy
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks = {}
for name, executable in {
    'lean': '/home/barberb/.elan/toolchains/leanprover--lean4---v4.33.1/bin/lean',
    'z3': '/home/barberb/.local/bin/z3',
    'cvc5': '/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/bin/cvc5',
}.items():
    p = Path(executable)
    if p.is_file():
        r = subprocess.run([executable, '--version'], capture_output=True, text=True, timeout=10,
                           env={'PATH':'/usr/bin:/bin', 'HOME':'/home/barberb'})
        checks[name] = {'path': str(p), 'sha256': sha(p), 'argv': r.args, 'exit_code': r.returncode,
                        'stdout': r.stdout, 'stderr': r.stderr, 'semantic_route_qualified_by_version': False}
    else: checks[name] = {'path': str(p), 'available': False}
cache = Path('/home/barberb/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41')
model_files = {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in cache.glob('*') if p.is_file()}
print(json.dumps({'schema':'af-host-runtime-prerequisite-inspection/v1',
    'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'machine': platform.machine(),
    'interpreter': sys.executable, 'interpreter_sha256': sha(sys.executable),
    'torch': {'version':torch.__version__, 'path':torch.__file__, 'module_sha256':sha(torch.__file__), 'cuda_available':torch.cuda.is_available()},
    'numpy': {'version':numpy.__version__, 'path':numpy.__file__, 'module_sha256':sha(numpy.__file__)},
    'native_checker_versions': checks, 'cached_embedding_model': {'repository':'sentence-transformers/all-MiniLM-L6-v2', 'revision': cache.name, 'path':str(cache), 'files':model_files},
    'scope':'host read-only inventory and version commands only; no provider-container availability, formal verification, model-inference or benchmark claim'}, indent=2))
