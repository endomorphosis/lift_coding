"""Compare completed saved outputs and apply the unchanged TRAIN-only gate.

No model, encoder, compiler, prover, selection, resource or Hub operation runs.
The archived control is an explicit formula/site baseline; the actual parent
readouts provide the separate auxiliary-bank floors. Neither is a fresh control.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

W = Path('/home/barberb/lift_coding')
R = W / 'artifacts/autoencoder-dual-bank-replay-20261007'
RUN = W / 'external/ipfs_datasets/workspace/test-logs/decoder-dual-bank-replay-20261007'
OLD_RUN = W / 'external/ipfs_datasets/workspace/test-logs/decoder-balanced-wording-20261007'
COHORTS = ('original_train48', 'normative_train48', 'new_balanced_train48', 'exposed_v3_48')
ROLES = ('selected', 'last-attempt')
FIELDS = ('actor', 'action', 'modality', 'object')
ARTIFACTS = {}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(path, wanted=None):
    path = Path(path).resolve()
    actual = sha(path)
    require(wanted is None or actual == wanted, 'saved artifact changed: ' + str(path))
    ARTIFACTS[str(path)] = dict(sha256=actual, bytes=path.stat().st_size)
    return json.loads(path.read_bytes())


def bound(ref):
    return read(ref['path'], ref['sha256'])


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def numerical_panel(panel, source_rows):
    fidelity = bound(panel['formula_fidelity_ref'])
    scalar = bound(panel['scalar_score_ref'])
    trace = bound(panel['trace_ref'])
    require(fidelity['complete_evaluation'] is True and scalar['complete'] is True,
        'complete numerical panels required')
    require(len(trace['rows']) == len(source_rows) == 48
        and all(observed['id'] == source['id'] and observed['source_text_sha256'] ==
            hashlib.sha256(source['source_text'].encode()).hexdigest()
            for source, observed in zip(source_rows, trace['rows'])),
        'actual complete source identities and text bindings differ')
    rows_sha = hashlib.sha256(json.dumps(source_rows, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    return dict(complete=True, rows=48, expected_rules=180,
        source_binding=dict(source_contexts_sha256=scalar['source_contexts_sha256'],
            references_sha256=scalar['references_sha256'], codec_sha256=scalar['codec_sha256'],
            source_text_rows_sha256=rows_sha),
        model_tensor_sha256=panel['state_ref']['tensor_sha256'],
        formula_metrics=fidelity['metrics'], formula_rows=fidelity['rows'],
        seven_facets=panel['seven_facets'], scalar_by_field=panel['scalar_by_field'])


def field_comparison(panel):
    joined = bound(panel['scalar_formula_join_ref'])
    fields = {field: dict(reference_sites=0, visited=0, source_correct=0,
        recurrent_correct=0, combined_correct=0, formula_correct=0,
        combined_correct_formula_wrong=0, combined_wrong_formula_correct=0) for field in FIELDS}
    wrong = []
    for row in joined['rows']:
        for field in FIELDS:
            observed = row['fields'][field]
            counters = fields[field]
            counters['reference_sites'] += 1
            counters['formula_correct'] += int(observed['formula_field_correct'])
            if observed['status'] != 'visited':
                continue
            counters['visited'] += 1
            for contribution in ('source', 'recurrent', 'combined'):
                counters[contribution + '_correct'] += int(
                    observed[contribution]['argmax_token_id'] == observed['target_token_id'])
            combined_correct = observed['combined']['argmax_token_id'] == observed['target_token_id']
            formula_correct = observed['formula_field_correct']
            counters['combined_correct_formula_wrong'] += int(combined_correct and not formula_correct)
            counters['combined_wrong_formula_correct'] += int(not combined_correct and formula_correct)
            if not combined_correct or not formula_correct:
                wrong.append(dict(id=row['id'], slot=row['slot'], field=field,
                    expected_rule=row['expected_rule'], observed=observed))
    require(all(v['reference_sites'] == 180 for v in fields.values()), 'all720 reference sites retained')
    return dict(fields=fields, wrong_sites=wrong)


def main():
    require(read(RUN / 'evaluation-r1-guardian-exit.json')['returncode'] == 0
        and read(RUN / 'evaluation-r1/resources-final.json')['status'] == 'released',
        'successful completed evaluation with released resources required')
    current = read(RUN / 'evaluation-r1/results/summary.json')
    old = read(OLD_RUN / 'evaluation-r1/results/summary.json')
    require(current['complete'] is True and len(current['panels']) == 8,
        'all eight physical panels required')
    manifest = read(RUN / 'training-manifest.json')
    inventories = {role: read(path) for role, path in manifest['source_inventories'].items()}
    source_rows = dict(original_train48=inventories['control']['prior_sources_by_dataset']['paragraph_train'],
        normative_train48=inventories['control']['corpus']['source_rows'],
        new_balanced_train48=inventories['balanced']['corpus']['source_rows'])
    require(sha(R / 'runtime/experiment-source/dual_bank_retention.py') ==
        '15accfcf8bbc4e578e32ca7842ac338be2b563458c4c90a85fbe18429da000f1', 'unchanged gate required')
    spec = importlib.util.spec_from_file_location('_retention_pure', R / 'runtime/experiment-source/dual_bank_retention.py')
    retention = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(retention)
    schedule = read(W / 'artifacts/autoencoder-balanced-wording-20261007/next-retention-plan/proposed-dual-bank-schedule.json',
        '11a9c660f5101dbcf2981cfa0d451d13c6a81ebbc75b7ad2699e07d37106e2e1')
    train_summary = read(RUN / 'training-384-r1/results/summary.json')
    fit = bound(train_summary['runs'][0])
    preflight = read(RUN / 'preflight-384-r1/results/summary.json')
    baseline = {}
    bindings = {}
    for cohort, rows in source_rows.items():
        panel = next(p for p in old['panels'] if p['arm'] == 'control-wording-ce'
            and p['role'] == 'selected' and p['cohort'] == cohort)
        baseline[cohort] = numerical_panel(panel, rows)
        bindings[cohort] = dict(source_rows=rows,
            **{k: baseline[cohort]['source_binding'][k] for k in
                ['source_contexts_sha256', 'references_sha256', 'codec_sha256']})
    baseline_bank_fields = {bank: {field: dict(correct=values['correct'], total=values['total'])
        for field, values in metrics.items()}
        for bank, metrics in preflight['initial_bank_source_scalar_metrics'].items()}
    decisions = {}
    for role in ROLES:
        candidate = {}
        for cohort, rows in source_rows.items():
            panel = next(p for p in current['panels'] if p['role'] == role and p['cohort'] == cohort)
            candidate[cohort] = numerical_panel(panel, rows)
        readouts = {bank: bound(ref) for bank, ref in fit['full180_postfit_readouts'][role].items()}
        candidate_bank_fields = {bank: {field: dict(correct=values['correct'], total=values['total'])
            for field, values in readout['by_field'].items()} for bank, readout in readouts.items()}
        decisions[role] = retention.retention_gate(schedule=schedule, expected_bindings=bindings,
            baseline_panels=baseline, candidate_panels=candidate,
            baseline_bank_fields=baseline_bank_fields, candidate_bank_fields=candidate_bank_fields)
    panels = []
    for panel in current['panels']:
        comparison = field_comparison(panel)
        archived = {arm: next(p for p in old['panels'] if p['arm'] == arm
            and p['role'] == panel['role'] and p['cohort'] == panel['cohort'])['formula_metrics']['ordered_exact']
            for arm in ['control-wording-ce', 'balanced-wording-ce']}
        panels.append(dict(role=panel['role'], cohort=panel['cohort'],
            formula_metrics=panel['formula_metrics'], seven_facets=panel['seven_facets'],
            scalar_by_field=panel['scalar_by_field'], source_recurrent_combined_formula=comparison,
            generation_seconds=panel['generation_seconds'], scoring_seconds=panel['scoring_seconds'],
            archived_ordered_exact=archived, model_tensor_sha256=panel['state_ref']['tensor_sha256']))
    save(R / 'postfit-comparison.json', dict(schema='dual-bank-replay-postfit-comparison/v1',
        complete=True, decisions=decisions, panels=panels,
        baseline_formula_tensor_sha256=next(iter(baseline.values()))['model_tensor_sha256'],
        baseline_source_bank_tensor_sha256=preflight['parent_tensor_sha256'],
        baseline_scope='Archived control selected full formula/site panels; actual unchanged parent auxiliary-bank floors. No fresh matched control or new semantic holdout.',
        auxiliary_chronology_changed=True, bank_mix_effect_causally_isolated=False,
        selected_last_tensor_alias=fit['selected_last_tensor_alias'],
        fits=1, physical_panels=8, reference_paragraphs=384, reference_rules=1440, reference_scalar_sites=5760,
        training_call_seconds=fit['training_call_elapsed_seconds'],
        training_rows_per_second=fit['training_rows_per_second'],
        evaluation_driver_seconds=current['elapsed_seconds'],
        bridge_names=[], legal_ir_evaluate_provers=False, metric_disk_cache_used=False,
        cpu_slots=1, workers=1, temperature=0, context_tokens=512, output_tokens=512,
        cached_native_inputs=True, OS_cache_state_uncontrolled=True,
        timing_scope='Cached authored decoder fit/source-only generation; no encoder, current compiler, bridge-on IR, native-family or Lake throughput.',
        qualified=False, admitted=False, proof_authority=False, formalized=False, checkpoint_promoted=False,
        convergence_proven=False, Constitution_formalized=False, artifacts=ARTIFACTS))
    print(json.dumps(dict(decisions={r: dict(passed=d['numerical_retention_passed'], findings=d['findings'])
        for r, d in decisions.items()}, ordered_exact=[dict(role=p['role'], cohort=p['cohort'],
        correct=p['formula_metrics']['ordered_exact']) for p in panels]), sort_keys=True))


if __name__ == '__main__':
    main()
