"""Independent scalar audit using saved JSON, binary float32 and Python math."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct

W = Path('/home/barberb/lift_coding')
P = W / 'external/ipfs_datasets'
R = P / 'workspace/test-logs/decoder-paraphrase-modality-margins-r2-20261006'
OUTPUT = W / 'artifacts/autoencoder-next-gap-20261006/diagnosis'
FIELDS = ('actor','action','modality','object')
BINDINGS = {}
CHECKS = Counter()
MAX_METRIC_DIFFERENCE = 0.


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path, expected=None):
    path = Path(path).resolve()
    actual = sha(path)
    assert expected is None or actual == expected, 'Changed artifact: ' + str(path)
    BINDINGS[str(path)] = {'sha256':actual,'bytes':path.stat().st_size}
    return json.loads(path.read_bytes())


def check(value, category):
    assert value, category
    CHECKS[category] += 1


def f32(value):
    return struct.unpack('<f',struct.pack('<f',value))[0]


def metrics(logits, target, emitted):
    check(len(logits) == 32 and all(math.isfinite(x) and f32(x) == x for x in logits), 'Finite saved full32V float32 coordinates')
    maximum = max(logits)
    return dict(argmax_token_id=max(range(32),key=logits.__getitem__),
        target_minus_best_other=logits[target]-max(v for i,v in enumerate(logits) if i != target),
        target_minus_emitted=logits[target]-logits[emitted],
        full_vocabulary_cross_entropy=maximum+math.log(math.fsum(math.exp(v-maximum) for v in logits))-logits[target])


def verify_metrics(expected, actual):
    global MAX_METRIC_DIFFERENCE
    check(set(expected) == set(actual), 'Exact component metric inventory')
    check(expected['argmax_token_id'] == actual['argmax_token_id'], 'Independent full-vocabulary argmax')
    for name in ('target_minus_best_other','target_minus_emitted','full_vocabulary_cross_entropy'):
        difference = abs(expected[name]-actual[name])
        MAX_METRIC_DIFFERENCE = max(MAX_METRIC_DIFFERENCE,difference)
        check(difference <= 1e-12, 'Independent double-precision score agrees')


def group_add(groups,key,target,winners):
    item = groups.setdefault(key,dict(events=0,source_correct=0,recurrent_correct=0,combined_correct=0,
        source_correct_combined_wrong=0,source_wrong_combined_correct=0,source_wrong_combined_wrong=0))
    item['events'] += 1
    for name,winner in winners.items():
        item[name+'_correct'] += winner == target
    item['source_correct_combined_wrong'] += winners['source'] == target and winners['combined'] != target
    item['source_wrong_combined_correct'] += winners['source'] != target and winners['combined'] == target
    item['source_wrong_combined_wrong'] += winners['source'] != target and winners['combined'] != target


manifest = load(R/'diagnostic-manifest.json')
plan = load(R/'diagnostic-plan.json',manifest['plan_sha256'])
guardian = load(R/'guardian-exit.json')
child = load(R/'diagnostic-r1/child-exit.json')
resources = load(R/'diagnostic-r1/resources-final.json')
check(guardian['returncode'] == child['returncode'] == 0 and resources['status'] == 'released', 'Successful completed/released guarded diagnostic')
summary = load(R/'diagnostic-r1/results/summary.json')
barrier = load(R/'diagnostic-r1/results/traces-complete.json')
check(summary['complete'] is True and summary['all_traces_persisted_before_reference_load'] is True
    and summary['archived_generation_parity_verified'] is True and len(summary['panels']) == 4
    and barrier['complete'] is True and barrier['v3_reference_json_loaded'] is False
    and len(barrier['records']) == 4, 'Four-trace source-before-reference barrier')
check(all(summary[k] is False for k in ('admitted','qualified','proof_authority','formalized','roundtrip_ok',
    'checkpoint_promoted','convergence_proven','lake_executed','encoder_executed','training_executed',
    'downloads_performed','used_for_selection','native_validation_executed','fresh_holdout')), 'No authority or unsupported training claim')
references = load(manifest['references'],manifest['inputs'][manifest['references']])
references_by_id = {r['id']:r for r in references}
results = []
detail_by_model = {}
for panel in summary['panels']:
    key = f'{panel["dimension"]}-{panel["arm"]}-selected'
    trace = load(panel['trace_ref']['path'],panel['trace_ref']['sha256'])
    score = load(panel['score_ref']['path'],panel['score_ref']['sha256'])
    source = load(manifest['source_inputs'][str(panel['dimension'])])
    state = load(panel['state_ref']['path'],panel['state_ref']['sha256'])
    codec = state['codec']; vocabulary = codec['target_vocabulary']
    check(len(vocabulary) == 32 and trace['trace_sha256'] == digest({k:v for k,v in trace.items() if k != 'trace_sha256'})
        and score['score_sha256'] == digest({k:v for k,v in score.items() if k != 'score_sha256'})
        and score['trace_sha256'] == trace['trace_sha256'], 'Exact complete trace/score digests')
    check(trace['source_rows_sha256'] == digest(source['rows'])
        and trace['source_contexts_sha256'] == digest(source['source_contexts'])
        and trace['codec_sha256'] == digest(codec)
        and trace['input_transform_sha256'] == digest(state['input_transform'])
        and trace['model_tensor_sha256'] == score['model_tensor_sha256'] == state['tensor_sha256'], 'Source/context/codec/model identity')
    archived_ref = manifest['archived_predictions'][key]
    archived = load(archived_ref['path'],archived_ref['sha256'])
    compare_keys = ('id','token_ids','generation_status','eos_reached')
    predicted = [{k:r[k] for k in compare_keys} for r in trace['predictions']]
    original = [{k:r[k] for k in compare_keys} for r in archived['predictions']]
    check(predicted == original, 'Exact archived greedy token/status/EOS parity')
    events = {(e['id'],e['position'],e['slot'],e['field']):e for e in score['events']}
    groups = {};errors=[];visited=set();event_count=0;decomposition_coordinates=0
    confusion = {kind:Counter() for kind in ('source','recurrent','combined')}
    margin_sums = {field:{kind:[] for kind in ('source','recurrent','combined')} for field in FIELDS}
    for row,prediction in zip(trace['rows'],trace['predictions']):
        reference = references_by_id[row['id']]
        context = source['source_contexts'][row['id']]
        check(prediction['id'] == row['id'] and row['consumed_prefix'] == [1]+prediction['token_ids'][:len(row['consumed_prefix'])-1], 'Actual consumed prefix binding')
        for site in row['scalar_sites']:
            check(site['source_slot_available'] is True and site['source_guidance_active'] is True
                and site['source_clause_sha256'] == context['segments'][site['slot']]['source_sha256'], 'Available causal source-clause route')
            raw,source_logits,combined = (site[n] for n in ('raw_recurrent_logits','applied_source_logits','combined_logits'))
            check(len(raw) == len(source_logits) == len(combined) == 32
                and all(f32(a+b) == c for a,b,c in zip(raw,source_logits,combined)), 'Exact independent float32 additive decomposition')
            decomposition_coordinates += 32
            position=site['position']; field=site['field']; slot=site['slot']
            check(vocabulary[row['consumed_prefix'][position]] == ':'
                and vocabulary[row['consumed_prefix'][position-1]] == json.dumps(field)
                and prediction['token_ids'][position] == site['actual_next_token_id'], 'Actual generated scalar token site')
            target = vocabulary.index(json.dumps(reference['target']['rules'][slot][field]))
            emitted = site['actual_next_token_id']
            event = events[row['id'],position,slot,field]
            check(event['target_token_id'] == target and event['actual_next_token_id'] == emitted, 'Independent authored target alignment')
            components = dict(source=metrics(source_logits,target,emitted),recurrent=metrics(raw,target,emitted),combined=metrics(combined,target,emitted))
            for name,value in components.items():
                verify_metrics(value,event[name]);margin_sums[field][name].append(value['target_minus_best_other'])
            check(components['combined']['argmax_token_id'] == emitted, 'Actual combined decision equals full-vocabulary argmax')
            winners = {name:v['argmax_token_id'] for name,v in components.items()}
            template = reference['template_family']; component=reference['components'][slot]
            pair = 'seen' if component['training_pair_seen'] else 'unseen'
            for group in ('all','field:'+field,'field:'+field+'/target:'+vocabulary[target],
                'field:'+field+'/template:'+template,'field:'+field+'/pair:'+pair):
                group_add(groups,group,target,winners)
            if field == 'modality':
                for name,winner in winners.items():
                    confusion[name][vocabulary[target]+'>'+vocabulary[winner]] += 1
            record=dict(id=row['id'],slot=slot,field=field,source_text=context['segments'][slot]['source_text'],
                target=vocabulary[target],emitted=vocabulary[emitted],template_family=template,training_pair_stratum=pair,
                source_correct=winners['source']==target,recurrent_correct=winners['recurrent']==target,
                combined_correct=winners['combined']==target,components=components)
            detail_by_model.setdefault(key,{})[row['id'],slot,field]=record
            if emitted != target:errors.append(record)
            visited.add((row['id'],slot,field));event_count += 1
    expected_sites={(r['id'],slot,field) for r in references for slot in range(r['clause_count']) for field in FIELDS}
    missing=sorted(expected_sites-visited)
    check(event_count == score['scored_sites'] == len(score['events']) and missing == sorted(
        (v['id'],v['slot'],v['field']) for v in score['unvisited_reference_sites'])
        and len(score['unscored_sites']) == 0, 'Complete scored/unvisited/unavailable accounting')
    for field in FIELDS:
        observed=groups['field:'+field];saved=score['per_field'][field]
        check(saved['scored'] == observed['events'] and all(saved[k] == observed[k] for k in
            ('source_correct','recurrent_correct','combined_correct','source_correct_combined_wrong')), 'Independent per-field counts')
    results.append(dict(dimension=panel['dimension'],arm=panel['arm'],role='selected',groups=groups,
        modality_confusion={k:dict(sorted(v.items())) for k,v in confusion.items()},errors=errors,
        scored_sites=event_count,decomposition_coordinates=decomposition_coordinates,unvisited_sites=missing,
        margins={field:{name:dict(count=len(values),minimum=min(values),mean=math.fsum(values)/len(values),maximum=max(values))
            for name,values in kinds.items()} for field,kinds in margin_sums.items()},
        generation_seconds=panel['generation_seconds'],scoring_seconds=panel['scoring_seconds']))

findings=load(OUTPUT/'findings.json')
changed_examples=[]
for row in findings['selected_formula_transitions']['384']:
    for slot,(zero,positive) in enumerate(zip(row['zero']['rules'],row['positive']['rules'])):
        if zero != positive:
            changed_examples.append(dict(id=row['id'],slot=slot,expected=row['expected']['rules'][slot],
                zero=detail_by_model['384-paraphrase-modality-zero-selected'][row['id'],slot,'modality'],
                positive=detail_by_model['384-paraphrase-modality-ce-selected'][row['id'],slot,'modality']))
result=dict(schema='independent-paraphrase-modality-margin-numerical-audit/v1',passed=True,findings=[],
    checks=dict(CHECKS),check_count=sum(CHECKS.values()),panels=results,
    changed_384_examples=changed_examples,maximum_component_metric_absolute_difference=MAX_METRIC_DIFFERENCE,
    score_tolerance=1e-12,score_tolerance_scope='Independent double log-sum-exp versus saved double metric, not model replay tolerance',
    float32_addition='struct pack/unpack after Python-double addition of two saved float32 operands',
    artifacts=BINDINGS,model_executed=False,torch_imported=False,encoder_executed=False,training_executed=False,
    checkpoint_promoted=False,admission_granted=False,fresh_holdout=False)
path=OUTPUT/'independent-numerical-audit.json'
path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({'path':str(path),'sha256':sha(path),'checks':sum(CHECKS.values()),'passed':True,
    'panels':[{'dimension':p['dimension'],'arm':p['arm'],'modality':p['groups']['field:modality']} for p in results]}))
