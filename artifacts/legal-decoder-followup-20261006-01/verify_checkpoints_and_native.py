"""Separate-process replay and real native scope controls after fixed selection."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import torch
from ipfs_datasets_py.logic.deontic import coordination_decoder as semantic
from ipfs_datasets_py.logic.formalization.autoencoder import legal_grouped_span_decoder_v2 as head
from ipfs_datasets_py.logic.formalization.autoencoder import native_family_lean_emitters as emitters

OUT = Path(__file__).resolve().parent
LAKE = Path('/home/barberb/.elan/toolchains/leanprover--lean4---v4.26.0/bin/lake')


def reference(path):
    return {'path': str(path), 'sha256': sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}


torch.set_num_threads(2)
torch.use_deterministic_algorithms(True)
results = json.loads((OUT / 'training-results.json').read_text())
verified = {}
for arm, result in results['arms'].items():
    checkpoint_path = Path(result['selected']['checkpoint']['path'])
    assert reference(checkpoint_path) == result['selected']['checkpoint']
    checkpoint = json.loads(checkpoint_path.read_text())
    model, optimizer, steps = head.restore_grouped_span_checkpoint(checkpoint)
    assert steps == result['selected']['optimizer_steps']
    assert all(int(state['step']) == steps for state in optimizer.state.values())
    assert head.save_grouped_span_checkpoint(model, optimizer, steps=steps) == checkpoint
    measured = json.loads((OUT / 'runs' / arm / 'fresh-final.json').read_text())
    for item in measured['outputs']:
        actual = head.predict_grouped_span_decoder(model, **item['input'])
        assert actual == item['prediction'], item['case_id']
    verified[arm] = {'predictions_exact': len(measured['outputs']), 'optimizer_steps_verified': steps,
                     'checkpoint_exact_resave': True, 'checkpoint': reference(checkpoint_path)}

selected = results['arms']['position_local_negatives']['selected']
checkpoint = json.loads(Path(selected['checkpoint']['path']).read_text())
model, optimizer, steps = head.restore_grouped_span_checkpoint(checkpoint)
selection = json.loads(Path(selected['evaluation']['path']).read_text())
groups = {}
for item in selection['outputs']:
    if item['supported'] and item['prediction']['request'] is not None:
        groups.setdefault(item['source_group_id'], {})[item['input']['modal_scope']] = item
pairs = [group for group in groups.values() if set(group) == set(head.SCOPES)
         and all(item['prediction']['raw_prediction']['count'] == 8 for item in group.values())]
assert pairs, 'No eight-member pair for actual native scope validation'
pair = pairs[0]
records, cases = [], []
for scope in head.SCOPES:
    item = pair[scope]
    actual = head.predict_grouped_span_decoder(model, **item['input'])
    assert actual == item['prediction']
    records.append(semantic.decode_coordination_request(semantic.CoordinationDecodeRequest.from_dict(actual['request'])))
    cases.append({'case_id': item['case_id'], 'input': item['input'], 'prediction': actual})
assert head.save_grouped_span_checkpoint(model, optimizer, steps=steps) == checkpoint
# Reuse only these two exact builder functions; its unpublished parser imports
# and old training policy never execute in this replay process.
builder = OUT.parent / 'legal-grouped-head-v2-20261006/audit_checkpoint_native.py'
tree = ast.parse(builder.read_text())
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {'native_source', 'build'}]
assert {node.name for node in functions} == {'native_source', 'build'}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(builder), 'exec'), globals())
source = native_source(records)
positive = build(OUT / 'native-positive', source)
negative = build(OUT / 'native-negative', source + '\nexample : Narrow.formula_0 twoWorlds 0 := by\n  simp [Narrow.formula_0, twoWorlds]\n')
assert positive['returncode'] == 0 and negative['returncode'] != 0
assert 'unsolved goals' in (OUT / 'native-negative/stdout.txt').read_text()
report = {'schema': 'grouped-boundary-checkpoint-replay-native/v1', 'status': 'passed',
    'runner': reference(Path(__file__)), 'reused_builder': reference(builder), 'producer_pins': head.producer_pins(),
    'models': verified, 'exact_fresh_prediction_replays': 256, 'native_generated_cases': cases,
    'positive_build': positive, 'false_scope_build': negative, 'actual_lake_build_legal_passed': True,
    'false_scope_claim_rejected': True, 'native_scope': 'Constructed two-world witness from actual eight-member selection outputs.',
    'legal_meaning_verified': False, 'global_proof_admission': False, 'training_calls': 0, 'selection_changes': 0}
p = OUT / 'checkpoint-replay-native.json'; assert not p.exists()
p.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
print(json.dumps({'status': 'passed', 'exact_replays': 256, 'lake_build_legal': True, 'false_claim_rejected': True}))
