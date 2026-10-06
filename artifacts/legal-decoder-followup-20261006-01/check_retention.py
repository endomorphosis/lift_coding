"""Post-selection exposed regression and official-source behavior; no fitting."""
from pathlib import Path
import hashlib
import importlib.util
import json

import torch
from ipfs_datasets_py.logic.formalization.autoencoder import legal_grouped_span_decoder_v2 as head

OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('boundary_run', OUT / 'run_boundary_experiment.py')
# Import only the original measurement helper, never the training runner.
spec = importlib.util.spec_from_file_location('retained_measurement',
    OUT.parent / 'legal-grouped-head-v2-20261006/run_v2_training_corrected.py')
measurement = importlib.util.module_from_spec(spec); spec.loader.exec_module(measurement)
torch.set_num_threads(2)
torch.use_deterministic_algorithms(True)
results = json.loads((OUT / 'training-results.json').read_text())
assert results['status'] == 'completed'
old = json.loads((OUT.parent / 'legal-grouped-head-v2-20261006/authored-span-v2-corpus.json').read_text())
rows = [row for row in old['rows'] if row['split'] in {'selection', 'final_holdout'}]
assert len(rows) == 256
real = json.loads((OUT.parent / 'legal-grouped-head-v2-20261006/real-uscode-head-probe.json').read_text())
report = {'schema': 'grouped-boundary-post-selection-retention/v1', 'old_panel_is_exposed': True,
          'official_paragraphs_are_previously_exposed_and_have_no_gold': True,
          'training_calls': 0, 'selection_changes': 0, 'legal_accuracy_claimed': False, 'models': {}}
refs = {'parent': json.loads((OUT / 'experiment-plan.json').read_text())['parent_checkpoint']}
refs.update({name: arm['selected']['checkpoint'] for name, arm in results['arms'].items()})
for name, ref in refs.items():
    path = Path(ref['path']); digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == ref['sha256']
    checkpoint = json.loads(path.read_text())
    model, optimizer, steps = head.restore_grouped_span_checkpoint(checkpoint)
    measured = measurement.evaluate(model, rows, split='exposed_original_v2_regression')
    out = OUT / ('retention-' + name + '.json'); assert not out.exists()
    out.write_text(json.dumps(measured, indent=2, allow_nan=False) + '\n')
    probes = []
    for paragraph in real['paragraphs']:
        for scope in head.SCOPES:
            predicted = head.predict_grouped_span_decoder(model, paragraph['exact_text'], scope)
            probes.append({'source_id': paragraph['source_id'], 'source_sha256': paragraph['text_sha256'],
                           'modal_scope': scope, 'prediction': predicted})
    assert len(probes) == 14
    report['models'][name] = {'checkpoint_sha256': digest, 'steps': steps,
        'exposed_regression': measured['mixed_summary'], 'real_source_probes': probes,
        'real_source_requests_emitted': sum(p['prediction']['request'] is not None for p in probes),
        'real_source_learned_refusals': sum(p['prediction']['blockers'] == ['learned_source_unsupported'] for p in probes),
        'source_semantics_verified': False}
    assert head.save_grouped_span_checkpoint(model, optimizer, steps=steps) == checkpoint
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    print(json.dumps({'model': name, 'exposed_regression': measured['mixed_summary'],
                      'real_source_requests': report['models'][name]['real_source_requests_emitted']}), flush=True)
out = OUT / 'post-selection-retention.json'; assert not out.exists()
out.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
