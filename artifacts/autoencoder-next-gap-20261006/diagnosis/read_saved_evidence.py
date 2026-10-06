"""Saved JSON and source inspection only; imports no package/model runtime."""
from pathlib import Path
import ast
from collections import Counter
import hashlib
import json

ROOT = Path('/home/barberb/lift_coding')
PACKAGE = ROOT / 'external/ipfs_datasets'
LOGS = PACKAGE / 'workspace/test-logs'
OUTPUT = ROOT / 'artifacts/autoencoder-next-gap-20261006/diagnosis'
AUTO = 'ipfs_datasets_py/logic/formalization/autoencoder/'
BINDINGS = {}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    path = Path(path).resolve()
    BINDINGS[str(path)] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    return json.loads(path.read_bytes())


def slim_fidelity(value):
    return {'exact': value['metrics']['ordered_exact'], 'rows': value['metrics']['rows'],
            'syntax_valid': value['metrics']['syntax_valid'], 'facets': value['by_facet']}


def head_summary(value):
    margins = []
    for row in value['rows']:
        target, logits = row['target_token_id'], row['full_vocabulary_logits']
        margins.append(logits[target] - max(v for i, v in enumerate(logits) if i != target))
    return {'all': value['groups']['all'], 'groups': value['groups'],
            'full32V_target_margin_min': min(margins),
            'full32V_target_margin_mean': sum(margins) / len(margins),
            'model_tensor_sha256': value['model_tensor_sha256']}


manifest = load(LOGS / 'decoder-paraphrase-modality-styles-20261004/evaluation-manifest.json')
training_manifest = load(manifest['training_manifest'])
experiments = []
scores = {}
for dimension in (384, 768):
    for arm in ('paraphrase-modality-zero', 'paraphrase-modality-ce'):
        folder = LOGS / f'decoder-paraphrase-modality-20261004/training-{dimension}-r2/results/{arm}'
        run = load(folder / 'summary.json')
        record = {'dimension': dimension, 'arm': arm, 'states': run['states'],
                  'selected_and_last_tensors_identical': run['states']['selected']['tensor_sha256'] ==
                    run['states']['last-attempt']['tensor_sha256'],
                  'train_readouts': {'parent': head_summary(load(run['full180_parent_readout']['path']))}}
        for role, ref in run['full180_postfit_readouts'].items():
            record['train_readouts'][role] = head_summary(load(ref['path']))
        record['exposed_v3'] = {}
        for role in ('selected', 'last-attempt'):
            observer = LOGS / f'decoder-paraphrase-modality-styles-20261004/evaluation-r1/results/{dimension}-{arm}'
            score = load(observer / (role + '-score.json'))
            prediction = load(observer / (role + '-predictions.json'))
            confusion = Counter()
            for row in score['fidelity']['rows']:
                for expected, generated in zip(row['expected_ir']['rules'], row['generated_ir']['rules']):
                    confusion[(expected['modality'], generated['modality'])] += 1
            record['exposed_v3'][role] = dict(slim_fidelity(score['fidelity']),
                token_cross_entropy=score['teacher_forced']['token_cross_entropy'],
                modality_confusion={a+'>'+b: n for (a,b), n in sorted(confusion.items())},
                by_template={name: slim_fidelity(value) for name,value in score['by_template_family'].items()},
                model_tensor_sha256=prediction['model_tensor_sha256'],
                saved_raw_source_recurrent_combined_scalar_vectors=False,
                predictions_only_fields=sorted(prediction['predictions'][0]),
                generation_seconds=prediction['elapsed_seconds'])
            scores[dimension, arm, role] = score
        experiments.append(record)

transitions = {}
for dimension in (384, 768):
    old = {r['id']: r for r in scores[dimension, 'paraphrase-modality-zero', 'selected']['fidelity']['rows']}
    changes = []
    for row in scores[dimension, 'paraphrase-modality-ce', 'selected']['fidelity']['rows']:
        previous = old[row['id']]
        if row['generated_ir'] != previous['generated_ir']:
            changes.append(dict(id=row['id'], source_text=row['source_provenance']['source_text'],
                expected=row['expected_ir'], zero=previous['generated_ir'], positive=row['generated_ir'],
                was_exact=bool(previous['counts']['ordered_exact']), now_exact=bool(row['counts']['ordered_exact'])))
    transitions[str(dimension)] = changes

inputs = {}
for dimension, path in manifest['source_inputs'].items():
    value = load(path)
    contexts = value['source_contexts']
    inputs[dimension] = dict(path=path, sha256=sha(Path(path)), schema=value['schema'],
        source_rows=len(value['rows']), unique_clause_cache_rows=len(value['clause_cache']),
        context_segments=sum(len(v['segments']) for v in contexts.values()),
        source_row_fields=sorted(value['rows'][0]),
        representation=value['representation'], source_rows_sha256=value['source_rows_sha256'],
        source_plan_sha256=value['source_plan_sha256'], production_sha256=value['production_sha256'],
        inputs_sha256=value['inputs_sha256'],
        sealed_comparison_sha256=value['sealed_comparison_sha256'],
        target_access=value['target_access'], targets_attached=value['targets_attached'])

source_files = [AUTO + name + '.py' for name in (
    'source_value_decoder_experiment', 'clause_source_decoder_experiment',
    'action_factorized_clause_decoder_experiment', 'ordered_clause_recurrent_decoder_experiment',
    'generated_scalar_observation', 'generated_field_training', 'contextual_generated_boundary_training',
    'generated_source_margin_training', 'paraphrase_modality_auxiliary_training',
    'long_span_source_value_training', 'clause_source_context', 'clause_source_controls',
    'authored_training_paraphrases', 'authored_modality_holdout_v3')]
source_files += ['scripts/ops/autoencoder/' + name + '.py' for name in (
    'diagnose_contextual_scalar_margins', 'benchmark_paraphrase_modality_training',
    'evaluate_training_mixture_styles', 'evaluate_paraphrase_modality_styles')]
sources = {}
for relative in source_files:
    path = PACKAGE / relative
    functions = []
    tree = ast.parse(path.read_text())
    def walk(node, prefix=''):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + child.name
                functions.append({'name': name, 'line': child.lineno})
                walk(child, name + '.')
            else:
                walk(child, prefix)
    walk(tree)
    sources[relative] = dict(path=str(path), sha256=sha(path), functions=functions,
        published_numerical_producer_aliases={p:h for p,h in training_manifest['producer_pins'].items()
            if p.endswith('/'+relative.split('/')[-1])})

result = dict(schema='saved-legal-decoder-next-gap-diagnosis/v1', date='2026-10-06', complete=True,
    scope='Saved code and JSON only; no imported package, Torch, checkpoint restoration, model/encoder forward or training',
    experiments=experiments, selected_formula_transitions=transitions, cached_v3_inputs=inputs,
    sources=sources, bound_evidence=BINDINGS, qualified=False, admitted=False,
    checkpoint_promoted=False, lake_executed=False, encoder_executed=False,
    model_executed=False, training_executed=False, roundtrip_ok=False)
output = OUTPUT / 'findings.json'
output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps({'path': str(output), 'sha256': sha(output), 'bytes': output.stat().st_size,
    'evidence_bindings': len(BINDINGS), 'owned_source_inspections': len(sources),
    'changed_formulas': {d: len(v) for d,v in transitions.items()}}))
