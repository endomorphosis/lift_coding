"""Small actual native packed-CPU training probe; synthetic qualification only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import math
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--native-source', type=Path, required=True)
args = parser.parse_args()
sys.path[:0] = [str(args.native_source), '/home/barberb/.local/lib/python3.12/site-packages']
import torch
torch.set_num_threads(2)
torch.set_num_interop_threads(2)
test = args.native_source / 'tests/unit/optimizers/logic_theorem_optimizer/test_modal_autoencoder_cuda_training.py'
spec = importlib.util.spec_from_file_location('native_training_fixture', test)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
from ipfs_datasets_py.optimizers.logic_theorem_optimizer import modal_autoencoder_cuda as native
apply_cpu_reference_projection_update = native.apply_cpu_reference_projection_update

model = fixture._autoencoder('python')
samples = fixture._samples()
before = model.state.to_dict()
blocks = []
scatter = native._scatter_blocks

def witness(autoencoder, session):
    for name, block in sorted(session.blocks.items()):
        grad = block.parameter.grad
        blocks.append({
            'component': block.component, 'parameter_count': block.parameter.numel(),
            'gradient_finite': bool(torch.isfinite(grad).all()),
            'gradient_squared_norm': float(grad.square().sum()),
            'changed_parameter_count': int((block.parameter != block.initial).sum()),
            'sgd_max_absolute_error': float((block.parameter - (block.initial - 0.025 * grad)).abs().max())})
    return scatter(autoencoder, session)

tx = model.state.transaction(label='AF009-native-packed-CPU-probe').begin()
try:
    with patch.object(native, '_scatter_blocks', side_effect=witness):
        report = apply_cpu_reference_projection_update(model, samples,
            update_targets=('family_logits', 'decoded_embedding', 'legal_ir_view_logits'),
            learning_rate=0.025).to_dict()
    assert report['admitted'] and report['applied'] and report['gradient_norm'] > 0
    assert all(b['gradient_finite'] and b['sgd_max_absolute_error'] <= 1e-7 for b in blocks)
    touched = tx.touched_row_count
    tx.commit()
except BaseException:
    if tx.active:
        tx.rollback()
    raise
after = model.state.to_dict()
digest = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
changed = [name for name in before if before[name] != after[name]]
print(json.dumps({'torch_version': torch.__version__, 'torch_file': torch.__file__,
    'cuda_available': torch.cuda.is_available(), 'implementation_file': sys.modules[apply_cpu_reference_projection_update.__module__].__file__,
    'report': report, 'same_step_parameter_witness': blocks,
    'profile_counter_scope': 'native packed logical instrumentation; CPU run is not GPU transfer/kernel measurement', 'changed_components': changed, 'touched_rows': touched,
    'before_sha256': digest(before), 'after_sha256': digest(after),
    'synthetic_inputs_only': True, 'input_embedding': 'native existing mock:stable-sha256 test fixture', 'research_measurement': False}, indent=2))
