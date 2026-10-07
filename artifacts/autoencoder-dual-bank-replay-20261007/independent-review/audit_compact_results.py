"""Independent saved-byte/stdlib audit; never imports an experiment owner."""
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

W = Path('/home/barberb/lift_coding')
R = W / 'artifacts/autoencoder-dual-bank-replay-20261007'
RUN = W / 'external/ipfs_datasets/workspace/test-logs/decoder-dual-bank-replay-20261007'
OLD = W / 'artifacts/autoencoder-balanced-wording-20261007'
OLD_RUN = W / 'external/ipfs_datasets/workspace/test-logs/decoder-balanced-wording-20261007'
FIELDS = ('actor', 'action', 'modality', 'object')
FACETS = FIELDS + ('conditions', 'exceptions', 'temporal')
TRAIN = ('original_train48', 'normative_train48', 'new_balanced_train48')
COHORTS = TRAIN + ('exposed_v3_48',)
ROLES = ('selected', 'last-attempt')
BASE_TENSOR = '9e5772d99191e311b15f316138a27407d4a73346af3ce495129ad5febcf5bd4c'
PARENT_TENSOR = '0b3c7c3b1a5581cd393d9bb8db1d24b87fe2cb9dff0be268aa2b5ed1f88b6594'
NEW_TENSOR = '6e47fc6d5452bd0becbe4e36e60be7ee0a388d969dad68dc817123307412cea5'
ARTIFACTS = {}
CHECKS = []


def check(ok, name):
    CHECKS.append(dict(check=name, passed=bool(ok)))
    if not ok:
        raise ValueError(name)


def bind(path, expected=None):
    path = Path(path).resolve()
    check(path.is_file() and not path.is_symlink(), 'Regular input: ' + str(path))
    data = path.read_bytes()
    info = dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
    if expected is not None:
        check(info == {k: expected[k] for k in ('sha256', 'bytes')}, 'Exact saved bytes: ' + str(path))
    ARTIFACTS[str(path)] = info
    return data


def read(path, expected=None):
    return json.loads(bind(path, expected))


def ref(binding):
    return read(binding['path'], binding)


def close(actual, expected):
    return math.isclose(actual, expected, rel_tol=1e-7, abs_tol=1e-7)


def source_rows(inventories):
    return dict(original_train48=inventories['control']['prior_sources_by_dataset']['paragraph_train'],
        normative_train48=inventories['control']['corpus']['source_rows'],
        new_balanced_train48=inventories['balanced']['corpus']['source_rows'],
        exposed_v3_48=inventories['control']['prior_sources_by_dataset']['exposed_v3'])


def recount_formula(fidelity, rows, perfect=False):
    check(len(fidelity['rows']) == len(rows) == 48, 'Complete 48 formula/source rows')
    check([x['id'] for x in fidelity['rows']] == [x['id'] for x in rows], 'Positional formula/source identity')
    aggregates = Counter()
    totals = Counter()
    correct = Counter()
    for source, row in zip(rows, fidelity['rows']):
        n = len(source['source_text'].split('\n\n'))
        expected, generated = row['expected_ir']['rules'], row['generated_ir']['rules']
        check(n == len(expected) == len(generated), 'No missing or extra positional rule: ' + source['id'])
        check(set(row['by_facet']) == set(FACETS), 'All seven formula facets: ' + source['id'])
        for field in FACETS:
            measured = sum(a[field] == b[field] for a, b in zip(expected, generated))
            check(type(row['by_facet'][field]['total']) is int and row['by_facet'][field]['total'] == n
                and row['by_facet'][field]['correct'] == measured, 'Per-row facet arithmetic: ' + field)
            totals[field] += n
            correct[field] += measured
        check(row['counts']['ordered_exact'] == int(expected == generated), 'Actual ordered full formula equality')
        check(row['counts']['eos_count'] == int(row['generation_status'] == 'eos'), 'Actual row EOS count')
        if perfect:
            wanted = dict(rows=1, expected_rules=n, generated_rules=n, valid_generated_rules=n,
                eos_count=1, parsed_documents=1, syntax_valid=1, ordered_exact=1, all_rules_preserved=1,
                whole_rules_missing=0, whole_rules_extra=0, duplicate_rules=0, invalid_rule_count=0,
                invalid_rows=0, unscorable_generation_rows=0, prediction_missing_rows=0, order_mismatch_rows=0)
            check(all(type(row['counts'].get(k)) is int and row['counts'][k] == v for k, v in wanted.items()),
                'Complete perfect TRAIN row floor: ' + source['id'])
            check(all(correct_value['correct'] == n for correct_value in row['by_facet'].values()), 'Perfect TRAIN seven facets')
        aggregates.update(row['counts'])
    check(dict(aggregates) == fidelity['metrics'], 'Complete row/summary formula metric sum')
    check(sum(len(r['source_text'].split('\n\n')) for r in rows) == 180, 'Full 180 source clauses retained')
    check(all(totals[f] == 180 and fidelity['by_facet'][f]['total'] == 180
        and fidelity['by_facet'][f]['correct'] == correct[f] for f in FACETS), 'Full seven 180-site facet aggregates')
    return {f: dict(correct=correct[f], total=totals[f]) for f in FACETS}


def comparison(join, fidelity):
    by_id = {r['id']: r for r in fidelity['rows']}
    fields = {f: dict(reference_sites=0, visited=0, source_correct=0, recurrent_correct=0,
        combined_correct=0, formula_correct=0, combined_correct_formula_wrong=0,
        combined_wrong_formula_correct=0) for f in FIELDS}
    wrong = []
    check(len(join['rows']) == 180 and len({(r['id'], r['slot']) for r in join['rows']}) == 180,
        'All 180 unique rule/slot joins')
    for row in join['rows']:
        formula = by_id[row['id']]
        check(row['expected_rule'] == formula['expected_ir']['rules'][row['slot']], 'Exact expected rule join')
        generated = formula['generated_ir']['rules'][row['slot']]
        for f in FIELDS:
            value = row['fields'][f]
            counters = fields[f]
            counters['reference_sites'] += 1
            formula_correct = generated[f] == row['expected_rule'][f]
            check(type(value['formula_field_correct']) is bool and value['formula_field_correct'] == formula_correct,
                'Scalar join versus actual emitted formula: ' + f)
            counters['formula_correct'] += int(formula_correct)
            check(value['status'] == 'visited', 'Every reference site actually visited')
            counters['visited'] += 1
            contribution_correct = {c: value[c]['argmax_token_id'] == value['target_token_id']
                for c in ('source', 'recurrent', 'combined')}
            for c, matched in contribution_correct.items():
                counters[c + '_correct'] += int(matched)
            cc = contribution_correct['combined']
            counters['combined_correct_formula_wrong'] += int(cc and not formula_correct)
            counters['combined_wrong_formula_correct'] += int(not cc and formula_correct)
            if not cc or not formula_correct:
                wrong.append(dict(id=row['id'], slot=row['slot'], field=f,
                    expected_rule=row['expected_rule'], observed=value))
    check(all(x['reference_sites'] == x['visited'] == 180 for x in fields.values()), '720 complete comparison sites')
    return dict(fields=fields, wrong_sites=wrong)


def source_bank(readout, tensor):
    check(readout['complete'] is True and readout['model_tensor_sha256'] == tensor and len(readout['rows']) == 180,
        'Exact complete 180-clause source-bank tensor endpoint')
    correct = Counter()
    for row in readout['rows']:
        check(set(row['fields']) == set(FIELDS), 'Complete source-bank four fields')
        for f, value in row['fields'].items():
            logits = value['full32_logits']
            check(len(logits) == 32 and all(type(x) in (float, int) and math.isfinite(x) for x in logits),
                'Finite full32 bank distribution')
            argmax = max(range(32), key=lambda i: logits[i])
            matched = argmax == value['target_token_id']
            check(argmax == value['argmax_token_id'] and type(value['correct']) is bool
                and value['correct'] == matched, 'Unrestricted full32 bank argmax')
            target = value['target_token_id']
            high = max(logits)
            ce = high + math.log(sum(math.exp(x-high) for x in logits)) - logits[target]
            margin = logits[target] - max(x for i, x in enumerate(logits) if i != target)
            check(close(value['cross_entropy'], ce) and close(value['margin'], margin), 'Full32 bank CE and margin')
            correct[f] += int(matched)
    check(all(readout['by_field'][f]['correct'] == correct[f] and readout['by_field'][f]['total'] == 180
        for f in FIELDS), 'Bank counters independently summed')
    return {f: dict(correct=correct[f], total=180) for f in FIELDS}


def transition(old, new):
    return 'both_correct' if old and new else 'repaired' if new else 'newly_wrong' if old else 'both_wrong'


def main():
    compact = read(R / 'postfit-comparison.json')
    census = read(R / 'development-error-census.json')
    samples = read(R / 'sampled-model-formulas.json')
    for document in (compact, census, samples):
        for path, expected in document['artifacts'].items():
            bind(path, expected)
    eval_audit = read(R / 'independent-review/actual-evaluation-r1-independent-review.json',
        dict(bytes=6027292, sha256='898539453d4ea0e4317d10984ecc4de007557587f0688d03895a410570a335e1'))
    check(eval_audit['passed'] is True and eval_audit['findings'] == [], 'Immutable complete numerical audit is clean')
    for name, expected in [
        ('actual-training-384-r1-independent-review.json', dict(bytes=1140771, sha256='09f3ba6bf9fe02c388e411cdb8f7985f841ef38ae7d1e12789d24947ea89765e')),
        ('actual-preflight-384-r1-independent-review.json', dict(bytes=1381833, sha256='4b559a178d5c9265be9b5dcbb7c935b82a61f992c2bdb2ebb41f7ee14a0e9019'))]:
        check(read(R / 'independent-review' / name, expected)['passed'] is True, 'Immutable phase audit clean: ' + name)
    current = read(RUN / 'evaluation-r1/results/summary.json')
    old = read(OLD_RUN / 'evaluation-r1/results/summary.json')
    preflight = read(RUN / 'preflight-384-r1/results/summary.json')
    train = read(RUN / 'training-384-r1/results/summary.json')
    fit = ref(train['runs'][0])
    manifest = read(RUN / 'training-manifest.json')
    inventories = {r: read(p) for r, p in manifest['source_inventories'].items()}
    sources = source_rows(inventories)
    check(compact['baseline_formula_tensor_sha256'] == BASE_TENSOR
        and compact['baseline_source_bank_tensor_sha256'] == PARENT_TENSOR,
        'Archived-control formula/site baseline differs explicitly from parent-bank floor tensor')
    original_baseline = {}
    baseline_scalars = {}
    for cohort in TRAIN:
        panel = next(p for p in old['panels'] if p['arm'] == 'control-wording-ce'
            and p['role'] == 'selected' and p['cohort'] == cohort)
        check(panel['state_ref']['tensor_sha256'] == BASE_TENSOR, 'Single authentic archived control tensor')
        fidelity, scalar, trace = (ref(panel[k]) for k in ('formula_fidelity_ref','scalar_score_ref','trace_ref'))
        facets = recount_formula(fidelity, sources[cohort], perfect=True)
        check(facets == panel['seven_facets'], 'Baseline seven facets match complete rows')
        check([x['id'] for x in trace['rows']] == [x['id'] for x in sources[cohort]], 'Full baseline source identity')
        original_baseline[cohort] = scalar
        baseline_scalars[cohort] = panel['scalar_by_field']
    parent_banks = {b: source_bank(ref(p), PARENT_TENSOR) for b,p in preflight['source_bank_readouts'].items()}
    check(parent_banks == {b:{f:dict(correct=x['correct'], total=x['total']) for f,x in v.items()}
        for b,v in preflight['initial_bank_source_scalar_metrics'].items()}, 'Actual parent source-bank floors')
    check(len(current['panels']) == len(compact['panels']) == 8 and compact['physical_panels'] == 8
        and compact['fits'] == 1 and compact['selected_last_tensor_alias'] is True,
        'One actual fit, eight physical panels, alias roles')
    bound_panels = {}
    joined = {}
    for panel, saved in zip(current['panels'], compact['panels']):
        role, cohort = panel['role'], panel['cohort']
        check(saved['role'] == role and saved['cohort'] == cohort and panel['state_ref']['tensor_sha256'] == NEW_TENSOR,
            'Exact compact panel/endpoint identity')
        fidelity, scalar, trace, join = (ref(panel[k]) for k in
            ('formula_fidelity_ref','scalar_score_ref','trace_ref','scalar_formula_join_ref'))
        facets = recount_formula(fidelity, sources[cohort], perfect=cohort in TRAIN)
        measured = comparison(join, fidelity)
        check(saved['source_recurrent_combined_formula'] == measured, 'Complete compact source/recurrent/combined/formula arithmetic')
        for key in ('formula_metrics','seven_facets','scalar_by_field','generation_seconds','scoring_seconds'):
            check(saved[key] == panel[key], 'Exact original compact metric: ' + key)
        check(facets == panel['seven_facets'], 'Actual seven-facet compact sums')
        check(len(trace['rows']) == 48 and all(observed['id'] == source['id']
            and observed['source_text_sha256'] == hashlib.sha256(source['source_text'].encode()).hexdigest()
            for observed,source in zip(trace['rows'], sources[cohort])), 'Full cached-source byte identity')
        for field in FIELDS:
            v, m = saved['scalar_by_field'][field], measured['fields'][field]
            check(v['reference_sites'] == v['visited'] == 180 and v['unvisited'] == v['unavailable'] == 0
                and v['source_correct'] == m['source_correct'] and v['source_incorrect'] == 180-m['source_correct'],
                'No scalar denominator or source-accuracy loss')
            if cohort in TRAIN:
                check(v['source_correct'] >= baseline_scalars[cohort][field]['source_correct'], 'TRAIN source-site floor: ' + field)
        if cohort in TRAIN:
            check(all(scalar[k] == original_baseline[cohort][k] for k in
                ('source_contexts_sha256','references_sha256','codec_sha256')), 'Fixed TRAIN cache/reference/codec bindings')
        for arm, value in saved['archived_ordered_exact'].items():
            archival = next(p for p in old['panels'] if p['arm']==arm and p['role']==role and p['cohort']==cohort)
            check(value == archival['formula_metrics']['ordered_exact'], 'Authentic archived cohort comparison')
        bound_panels[(role,cohort)] = fidelity
        joined[(role,cohort)] = join
    check(compact['reference_paragraphs']==384 and compact['reference_rules']==1440
        and compact['reference_scalar_sites']==5760, 'All physical denominators explicit')
    floor_results = {}
    for role in ROLES:
        current_banks = {b: source_bank(ref(p), NEW_TENSOR) for b,p in fit['full180_postfit_readouts'][role].items()}
        check(set(current_banks) == set(parent_banks) == {'control','balanced'}, 'Both complete bank floors required')
        check(all(current_banks[b]['modality']['correct']==180
            and all(current_banks[b][f]['correct'] >= parent_banks[b][f]['correct'] for f in FIELDS)
            for b in parent_banks), 'Independent actual-parent auxiliary-bank retention floor')
        decision=compact['decisions'][role]
        check(decision['numerical_retention_passed'] is True and decision['findings']==[]
            and decision['training_cohorts']==list(TRAIN) and decision['exposed_v3_used_for_selection'] is False
            and decision['bank_and_formula_gates_both_required'] is True and decision['execution_readiness_granted'] is False,
            'TRAIN-only numerical gate conveys no execution or promotion authority')
        floor_results[role]=dict(baseline_bank_fields=parent_banks,candidate_bank_fields=current_banks,
            archived_control_formula_and_source_sites_floor_passed=True, actual_parent_auxiliary_floor_passed=True)
    gate_source=bind(R/'runtime/experiment-source/dual_bank_retention.py')
    check(hashlib.sha256(gate_source).hexdigest()=='15accfcf8bbc4e578e32ca7842ac338be2b563458c4c90a85fbe18429da000f1', 'Unchanged reviewed pure retention gate')
    analyzer=bind(R/'analyze_actual_results.py').decode()
    check(analyzer.index("require(sha(R / 'runtime/experiment-source/dual_bank_retention.py')")
        < analyzer.index('spec.loader.exec_module(retention)'), 'Pure gate byte authentication precedes import execution')
    parent_compare=read(OLD/'evaluation-review/actual-evaluation-r1-parent-comparison.json')
    check(parent_compare['passed'] is True and parent_compare['findings']==[]
        and parent_compare['parent_tensor_sha256']==PARENT_TENSOR
        and parent_compare['parent_formula_metrics']['ordered_exact']==31,
        'Parent exposed-v3 figure is authenticated historical evidence, not a new baseline trace')
    for path,expected in parent_compare['artifacts'].items():
        bind(path,expected)
    old_v3=next(p for p in old['panels'] if p['role']=='selected' and p['cohort']=='exposed_v3_48' and p['arm']=='control-wording-ce')
    old_fidelity=ref(old_v3['formula_fidelity_ref']); old_join=ref(old_v3['scalar_formula_join_ref'])
    new_fidelity=bound_panels[('selected','exposed_v3_48')]; new_join=joined[('selected','exposed_v3_48')]
    transitions=Counter(); changed=[]
    for source,a,b in zip(sources['exposed_v3_48'],old_fidelity['rows'],new_fidelity['rows']):
        check(source['id']==a['id']==b['id'] and a['expected_ir']==b['expected_ir'], 'Same development source/meaning identity')
        t=transition(a['generated_ir']==a['expected_ir'],b['generated_ir']==b['expected_ir'])
        transitions[t]+=1
        if t in ('newly_wrong','repaired'):
            changed.append(dict(id=source['id'],source_text=source['source_text'],transition=t,
                expected_ir=b['expected_ir'],archived_control_generated_ir=a['generated_ir'],replay_generated_ir=b['generated_ir']))
    check(dict(transitions)==census['paragraph_transitions'] and changed==census['changed_paragraphs'], 'All 48 paragraph transitions and all changes retained')
    check(transitions==Counter(both_correct=30,both_wrong=15,newly_wrong=3) and transitions['repaired']==0,
        'Development regression: three newly wrong paragraphs, zero repairs')
    scalar_transitions={f:{c:Counter() for c in ('source','combined','formula')} for f in FIELDS}
    wrong_modalities=Counter()
    for a,b in zip(old_join['rows'],new_join['rows']):
        check(a['id']==b['id'] and a['slot']==b['slot'] and a['expected_rule']==b['expected_rule'], '180 complete unchanged development rule identities')
        for f in FIELDS:
            x,y=a['fields'][f],b['fields'][f]
            for c in ('source','combined','formula'):
                correct=lambda v: v['formula_field_correct'] if c=='formula' else v[c]['argmax_token_id']==v['target_token_id']
                scalar_transitions[f][c][transition(correct(x),correct(y))]+=1
            if y['combined']['argmax_token_id']!=y['target_token_id']:
                wrong_modalities[(f,b['expected_rule']['modality'])]+=1
    check({f:{c:dict(v) for c,v in cs.items()} for f,cs in scalar_transitions.items()}==census['scalar_transitions'],
        'All source/combined/formula per-field development transitions')
    wrong_expected=[dict(field=f,expected_modality=m,count=n) for (f,m),n in sorted(wrong_modalities.items())]
    check(wrong_expected==census['wrong_combined_by_field_and_expected_modality'] and wrong_modalities[('modality','O')]==22,
        'All 22 combined modality errors have expected O; separate F-action miss')
    expected_samples=[]
    for cohort in COHORTS:
        fidelity=bound_panels[('selected',cohort)]
        for n in (1,8):
            row=next(r for r in fidelity['rows'] if r['clause_count']==n)
            expected_samples.append((cohort,row['id']))
    expected_samples.append(('exposed_v3_48',next(r['id'] for r in new_fidelity['rows'] if not r['counts']['ordered_exact'])))
    check([(s['cohort'],s['id']) for s in samples['samples']]==expected_samples, 'Exact declared nine-sample policy, no easy-case substitution')
    for sample in samples['samples']:
        cohort=sample['cohort'];fid=bound_panels[('selected',cohort)]
        row=next(r for r in fid['rows'] if r['id']==sample['id'])
        source=next(r for r in sources[cohort] if r['id']==sample['id'])
        panel=next(p for p in current['panels'] if p['cohort']==cohort and p['role']=='selected')
        prediction=next(p for p in ref(panel['predictions_ref'])['predictions'] if p['id']==sample['id'])
        check(sample['source_text']==source['source_text'] and sample['clause_count']==row['clause_count']
            and sample['actual_model_formula_ir']==row['generated_ir']
            and sample['expected_authored_fixture_ir']==row['expected_ir']
            and sample['counts']==row['counts'] and sample['seven_facets']==row['by_facet']
            and sample['actual_greedy_token_ids']==row['generated_token_ids']==prediction['token_ids'],
            'Unmodified complete actual sampled formula/prediction/source join')
    for document in (compact,census,samples):
        check(all(document[k] is False for k in ('qualified','admitted','proof_authority')), 'Compact reports grant no authority')
    check(compact['auxiliary_chronology_changed'] is True and compact['bank_mix_effect_causally_isolated'] is False,
        'One fit versus archived control cannot isolate bank composition')
    check(compact['training_call_seconds']==fit['training_call_elapsed_seconds']
        and compact['training_rows_per_second']==fit['training_rows_per_second']
        and compact['evaluation_driver_seconds']==current['elapsed_seconds'], 'Honest exact fit/evaluation timing scope')
    report=dict(schema='dual-bank-replay-postfit-compact-independent-review/v1',passed=True,findings=[],
        checks=CHECKS,artifacts=ARTIFACTS,train_only_retention_floors=floor_results,
        development_paragraph_transitions={k:transitions[k] for k in ('both_correct','both_wrong','newly_wrong','repaired')},
        all_180_development_rules_and_720_sites_retained=True,actual_formula_samples=9,
        baseline_formula_tensor_sha256=BASE_TENSOR,baseline_auxiliary_bank_tensor_sha256=PARENT_TENSOR,
        actual_selected_and_last_alias_tensor_sha256=NEW_TENSOR,
        physical_panels=8,reference_paragraphs=384,reference_rules=1440,reference_scalar_sites=5760,
        limits=['The full32/prefix/durability/resources audit is sealed separately and unchanged.',
            'Archived-control formula/source-site floors and actual-parent bank floors have distinct tensor identities.',
            'The historical parent31 comparison is bound, with no fabricated parent same-pass TRAIN trace.',
            'TRAIN-only numerical retention passes; exposed development30 is below archived control33 and parent31.',
            'One fit and auxiliary chronology differences do not causally isolate bank composition.',
            'An authored empty-qualifier fixture is neither a fresh semantic holdout nor a proof/compiler admission.'],
        models_or_encoders_or_numerical_owners_imported_or_executed=False,selection_performed=False,
        resource_or_remote_or_git_operations=False,qualified=False,admitted=False,proof_authority=False,
        training_executed=False,checkpoint_promoted=False,Constitution_formalized=False)
    destination=R/'independent-review/postfit-comparison-independent-review.json'
    with destination.open('x') as stream:
        json.dump(report,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(passed=True,checks=len(CHECKS),bindings=len(ARTIFACTS),
        report=str(destination),bytes=destination.stat().st_size,sha256=hashlib.sha256(destination.read_bytes()).hexdigest())))


if __name__=='__main__':
    main()
