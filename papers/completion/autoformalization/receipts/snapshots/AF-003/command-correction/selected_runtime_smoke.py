"""Bounded CPU/source/native-tool preflight; synthetic sentinel inputs only."""
import hashlib
import importlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import resource
import subprocess
import sys

resource.setrlimit(resource.RLIMIT_AS, (16 * 1024**3, 16 * 1024**3))
model_dir = Path(sys.argv[1]).resolve()
artifact_dir = Path(sys.argv[2]).resolve()
artifact_dir.mkdir(parents=True, exist_ok=True)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(argv, source=None):
    result = subprocess.run(argv, input=source, text=True, capture_output=True, timeout=30)
    record = {'argv': argv, 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
    assert result.returncode == 0, record
    return record


result = {'schema': 'autoformalization-selected-runtime-smoke/v1', 'scope': 'Synthetic preflight only; no corpus, held-out input, training, benchmark or rollout.',
          'python': {'executable': sys.executable, 'version': sys.version}, 'cpu_threads': 2,
          'memory_limit_bytes': 16 * 1024**3, 'source_interfaces': [], 'solver_probes': []}
for module_name, symbol in (
    ('ipfs_datasets_py.logic.intent_ir.formalize.compiler', 'IntentFormalizationCompiler'),
    ('ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_autoencoder', 'AdaptiveModalAutoencoder'),
):
    module = importlib.import_module(module_name)
    entry = getattr(module, symbol)
    instance = entry()
    record = {'module': module_name, 'symbol': symbol, 'source_file': module.__file__, 'source_sha256': sha(Path(module.__file__)),
              'constructor_signature': str(inspect.signature(entry)), 'instantiated': True,
              'qualification': 'import and constructor smoke only; not source-formalization or training qualification'}
    if hasattr(module, 'INTENT_FORMALIZATION_COMPILER_VERSION'):
        record['compiler_version'] = module.INTENT_FORMALIZATION_COMPILER_VERSION
        record['view_registry'] = module.INTENT_FORMALIZATION_VIEW_REGISTRY.to_dict()
    if hasattr(module, 'MODAL_AUTOENCODER_ARCHITECTURE_VERSION'):
        record['architecture_version'] = module.MODAL_AUTOENCODER_ARCHITECTURE_VERSION
        record['initial_state_sha256'] = hashlib.sha256(json.dumps(instance.state.to_dict(), sort_keys=True).encode()).hexdigest()
        record['trained_checkpoint'] = None
    result['source_interfaces'].append(record)

import torch
from transformers import AutoModel, AutoTokenizer
torch.set_num_threads(2)
tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True, trust_remote_code=False)
model = AutoModel.from_pretrained(str(model_dir), local_files_only=True, trust_remote_code=False).to('cpu').eval()
sentences = ['A valve is closed.', 'A sensor is active.']
inputs = tokenizer(sentences, padding=True, truncation=True, max_length=256, return_tensors='pt')
with torch.inference_mode():
    hidden = model(**inputs).last_hidden_state
    mask = inputs['attention_mask'].unsqueeze(-1).expand(hidden.size()).float()
    embeddings = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
assert tuple(embeddings.shape) == (2, 384)
assert bool(torch.isfinite(embeddings).all())
assert not torch.equal(embeddings[0], embeddings[1])
result['embedding_model'] = {'model_id': 'sentence-transformers/all-MiniLM-L6-v2', 'revision': model_dir.name,
    'model_directory': str(model_dir), 'files': [{'path': str(path.relative_to(model_dir)), 'size': path.stat().st_size, 'sha256': sha(path)} for path in sorted(model_dir.rglob('*')) if path.is_file()],
    'loader': 'transformers.AutoTokenizer.from_pretrained + transformers.AutoModel.from_pretrained',
    'pooling': 'attention-mask mean pooling then L2 normalization', 'max_length': 256,
    'trust_remote_code': False, 'local_files_only': True, 'device': 'cpu', 'dtype': str(next(model.parameters()).dtype),
    'synthetic_inputs': sentences, 'output_shape': list(embeddings.shape), 'finite': True, 'distinct': True,
    'output_sha256': hashlib.sha256(embeddings.numpy().tobytes()).hexdigest(),
    'qualification': 'local loading and two synthetic embedding inferences only; no semantic-quality or retrieval measurement'}
result['runtime_packages'] = {name: importlib.metadata.version(name) for name in ('torch', 'transformers', 'tokenizers', 'safetensors', 'numpy')}

smt = '(set-logic QF_LIA)\n(declare-const x Int)\n(assert (> x 1))\n(assert (< x 0))\n(check-sat)\n'
(artifact_dir / 'sentinel.smt2').write_text(smt)
for binary, args in [('/home/barberb/.local/bin/z3', ['-in', '-smt2']), ('/home/barberb/.local/bin/cvc5', ['--lang=smt2'])]:
    path = Path(binary).resolve()
    probe = run([str(path), *args], smt)
    assert probe['stdout'].strip() == 'unsat', probe
    result['solver_probes'].append({'binary_path': binary, 'resolved_binary': str(path), 'binary_sha256': sha(path),
                                   'version': run([str(path), '--version']), 'probe': probe,
                                   'stdin_artifact': 'sentinel.smt2', 'status': 'synthetic QF_LIA smoke only; solver-local result'})
lean = Path('/home/barberb/.elan/toolchains/leanprover--lean4---v4.33.1/bin/lean')
source = artifact_dir / 'sentinel.lean'
source.write_text('example (P : Prop) (h : P) : P := h\n')
result['native_checker'] = {'binary_path': str(lean), 'binary_sha256': sha(lean), 'version': run([str(lean), '--version']),
                            'probe': run([str(lean), str(source)]), 'source_artifact': 'sentinel.lean',
                            'status': 'fresh kernel checks synthetic identity theorem; no task-generated proof or bridge qualified'}
print(json.dumps(result, indent=2, sort_keys=True))
