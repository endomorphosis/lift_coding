"""Read-only stream-hash and saved-data readiness checks; no package models."""
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import time

W = Path('/home/barberb/lift_coding')
P = W / 'external/ipfs_datasets'
R = P / 'workspace/test-logs/decoder-normative-wording-r2-20261006'
OUT = W / 'artifacts/autoencoder-wording-fit-20261006/review'
checks, artifacts = [], {}
started = time.monotonic()


def check(value, label):
    if not value:
        raise ValueError(label)
    checks.append(label)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def bind(path, expected=None):
    path = Path(path).resolve(); h = hashlib.sha256(); size = 0
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576), b''):
            h.update(block); size += len(block)
    value = dict(sha256=h.hexdigest(), bytes=size)
    check(expected is None or value['sha256'] == expected, 'streamed SHA '+str(path))
    check(str(path) not in artifacts or artifacts[str(path)] == value, 'stable reviewed file '+str(path))
    artifacts[str(path)] = value
    return value


def load(path):
    return json.loads(Path(path).read_bytes())


manifest = load(R / 'training-manifest.json'); plan = load(R / 'training-plan.json')
bind(R / 'training-manifest.json', '45a48f359ce7db22f82296f64777dde6f190800e3b20176a98c93b5cddedbc00')
bind(R / 'training-plan.json', manifest['plan_sha256'])
check(plan['input_sha256'] == manifest['inputs'], 'exact plan/input map')
check(len(manifest['inputs']) == 1113 and len(manifest['extensions']) == 20
    and len(manifest['producer_pins']) == 226, 'complete sealed closure sizes')
for path, wanted in manifest['inputs'].items():
    bind(path, wanted)
for relative, wanted in manifest['extensions'].items():
    bind(R / 'experiment-source' / relative, wanted)
for path, wanted in manifest['producer_pins'].items():
    bind(path, wanted)
check(manifest['prospective_development_references_bound_in_training'] is False,
      'future label binding disabled')
future_dir = W / 'artifacts/autoencoder-wording-fit-20261006/development'
check(str(future_dir / 'development-references.json') not in manifest['inputs']
    and str(future_dir / 'development-corpus-receipt.json') not in manifest['inputs']
    and str(future_dir / 'original-validation-bank-used.json') not in manifest['inputs'],
    'prospective reference and target-bank bodies absent from TRAIN input map')
frozen = R / 'experiment-source'
trainer_path = frozen / 'scripts/ops/autoencoder/benchmark_normative_wording_training.py'
spec = importlib.util.spec_from_file_location('_readiness_private_trainer', trainer_path)
runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
runner.validate_plan(plan)
check(True, 'fixed numerical plan pure validation')
owner = runner.load_training_owner()
check(owner.FIXED['optimizer_steps_per_fit'] == 170 and owner.FIXED['row_presentations'] == 1220
    and owner.FIXED['valid_target_token_presentations'] == 112920
    and owner.FIXED['source_value_presentations'] == 12800, 'original work denominators')
check(owner.FIXED['zero_arm_exact_m2_zero_replay'] is True
    and owner.FIXED['source_training_mixture_enabled'] is False
    and owner.FIXED['selection_unchanged'] is True, 'zero/original/selection contracts preserved')
for path in (R / 'run_guardian.py', R / 'run_reserved.py', R / 'owned_lease_watchdog.py',
             R / 'adopt_shared_scheduler.py', R / 'lazy_scheduler_adoption.py'):
    bind(path)
guardian = (R / 'run_guardian.py').read_text(); reserved = (R / 'run_reserved.py').read_text()
check("ready.get('phase') != args.phase" in guardian and "ready['dimension'] != args.dimension" in guardian
    and "str(R.resolve())" in guardian, 'guardian refuses different phase/width/root')
check("'preflight': ('benchmark_normative_wording_training.py',100_000_000,1536,900)" in reserved
    and "manifest_phase = 'training' if args.phase == 'preflight' else args.phase" in reserved,
    'bounded per-width preflight points to sealed training manifest')
for name in ('preparation-r1-guardian-exit.json', 'preparation-r1/child-exit.json',
             'preparation-r1/resources-final.json', 'preparation-r1/results/summary.json'):
    bind(R / name)
check(load(R / 'preparation-r1-guardian-exit.json')['returncode'] == 0
    and load(R / 'preparation-r1/child-exit.json')['returncode'] == 0
    and load(R / 'preparation-r1/resources-final.json')['status'] == 'released',
    'actual native child/outer success and owned lease released')
native_summary = load(R / 'preparation-r1/results/summary.json')
check(native_summary['complete'] is True and native_summary['encoder_executed'] is True
    and native_summary['development_reference_json_parsed'] is False
    and native_summary['unique_sources_per_width'] == 276,
    'actual complete native preparation, no future target JSON parsed')
data = R / 'preparation-r1/results'
corpus = load(data / 'training-corpus-receipt.json')
check(corpus['receipt_sha256'] == digest({k:v for k,v in corpus.items() if k != 'receipt_sha256'}),
    'TRAIN corpus content receipt')
rows = load(data / 'source-rows.json'); refs = load(data / 'training-references.json')
clauses = load(data / 'clause-training-references.json'); prior = load(data / 'prior-source-inventories.json')
check(len(rows) == len(refs) == 48 and len(clauses) == 180, 'complete paragraph/clause TRAIN census')
check(corpus['source_rows_sha256'] == digest(rows) and corpus['references_sha256'] == digest(refs)
    and corpus['prior_sources_sha256'] == digest(prior), 'exact TRAIN data bindings')
expected_names = {'original_train_bank','raw_train','raw_validation','raw_test','raw_canary',
    'paragraph_train','paragraph_validation','exposed_r6','exposed_r8','exposed_v3',
    'r4_training_paraphrases','composition64','prospective_development_sources'}
check(set(prior) == expected_names, 'all thirteen strict training source inventories')
check(len(prior['prospective_development_sources']) == 60 and all(set(r) == {'id','source_text'}
    for r in prior['prospective_development_sources']), 'future exclusions sixty closed sources without label bodies')
normal = lambda text:' '.join(text.casefold().split())
forbidden = {normal(text) for records in prior.values() for row in records
    for text in [row['source_text'], *row['source_text'].split('\n\n')]}
check(not {normal(text) for row in rows for text in [row['source_text'],*row['source_text'].split('\n\n')]}
    .intersection(forbidden), 'all TRAIN paragraph/clause wordings excluded from entire prior inventory')
check(Counter(c['modality_stratum'] for c in clauses) == {'O':60,'P':60,'F':60}, 'balanced complete TRAIN clause modalities')
draws = load(manifest['independent_inputs']['auxiliary_schedule'])
check(len(draws) == 170 and all(len(d['row_ids']) == len(set(d['row_ids'])) == 6 for d in draws),
      '170 complete independent six-row auxiliary draws')
exposure = Counter(identity for draw in draws for identity in draw['row_ids'])
check(len(exposure) == 180 and sum(exposure.values()) == 1020 and set(exposure.values()) == {5,6},
      'all180 TRAIN clauses observed five or six times')
baseline_evidence = {}
for width in (384,768):
    baseline = load(manifest['baseline_summaries'][str(width)])
    check(baseline['dimension'] == width and baseline['arm'] == 'paraphrase-modality-zero'
        and baseline['budget_completed'] is True and baseline['zero_arm_archived_replay_verified'] is True,
        'completed authenticated M2 zero baseline '+str(width))
    report = load(baseline['training_ref']['path'])
    primary = load(manifest['independent_inputs']['primary_schedules'][str(width)])
    check(report['optimizer_steps'] == len(report['committed_updates']) == len(primary) == 170,
        'all original170 baseline updates '+str(width))
    for update, item in zip(report['committed_updates'], primary, strict=True):
        check(update['decoder_row_ids'] == item['decoder_ids'] and update['count_row_ids'] == item['count_ids'],
            'unchanged primary schedule '+str(width))
        if width == 384:
            check(update['auxiliary_source_modality']['receipt'] == item['original_auxiliary_source_modality'],
                'unchanged original384 auxiliary schedule')
    baseline_evidence[str(width)] = dict(initial=report['initial_weights_sha256'],
        selected=report['selected_weights_sha256'],last_complete=report['last_complete_attempt_weights_sha256'],
        selected_epoch=report['selected_epoch'],step_count=170)
    prod = load(data / f'production-{width}.json'); cache = load(data / f'dimension-inputs-{width}.json')
    devprod = load(data / f'development-production-{width}.json')
    devcache = load(data / f'development-inputs-{width}.json')
    for payload in (prod, devprod):
        check(payload['production_sha256'] == digest({k:v for k,v in payload.items() if k != 'production_sha256'}),
            'native production content seal '+str(width))
        check(payload['complete'] is True and payload['dimension'] == width
            and payload['representation']['dtype'] == 'float32'
            and payload['representation']['experiment_token_limit'] == 512
            and payload['representation']['actual_forward_tokens_verified'] is True
            and payload['targets_attached'] is False and payload['target_access'] is False
            and payload['downloads_performed'] is False,
            'native actual profile/fixed context/no targets '+str(width))
        for vector in payload['vectors']:
            check(len(vector['vector']) == width and all(type(v) in (int,float)
                and math.isfinite(v) for v in vector['vector']), 'finite exact native width '+str(width))
            check(0 < vector['token_count'] <= 512, 'native overlength refusal receipt '+str(width))
    check(len(prod['vectors']) == 216 and len(devprod['vectors']) == 60, 'complete216 TRAIN and60 DEV native sources '+str(width))
    vectors = {v['source_sha256']:v['vector'] for v in prod['vectors']}
    devvectors = {v['source_sha256']:v['vector'] for v in devprod['vectors']}
    check(len(vectors) == 216 and len(devvectors) == 60 and not set(vectors).intersection(devvectors),
        'native source identities disjoint '+str(width))
    check(len({struct.pack('<'+'f'*width,*v) for v in [*vectors.values(),*devvectors.values()]}) == 276,
        'all276 actual float32 vectors distinct '+str(width))
    for payload, sources, mapping in [(cache,rows,vectors),
            (devcache,prior['prospective_development_sources'],devvectors)]:
        check(payload['inputs_sha256'] == digest({k:v for k,v in payload.items() if k != 'inputs_sha256'})
            and payload['complete'] is True and payload['dimension'] == width, 'source cache content binding '+str(width))
        check([{k:r[k] for k in ('id','source_text')} for r in payload['rows']] == sources,
            'actual source cache ordered exact text '+str(width))
        for row in payload['rows']:
            sha = hashlib.sha256(row['source_text'].encode()).hexdigest()
            check(set(row) == {'id','source_text','input'} and row['input'] == mapping[sha],
                'exact source-only produced vector '+str(width))
            packet = payload['source_contexts'][row['id']]
            pieces = row['source_text'].split('\n\n')
            check(packet['source_sha256'] == sha and len(packet['segments']) == len(pieces),
                'complete ordered source segments '+str(width))
            for text, segment in zip(pieces, packet['segments'], strict=True):
                text_sha = hashlib.sha256(text.encode()).hexdigest()
                check(segment['source_text'] == text and segment['source_sha256'] == text_sha
                    and segment['vector'] == mapping[text_sha] and segment['embedding_sha256'] == digest(segment['vector']),
                    'exact native source-context segment '+str(width))
                check(row['source_text'][segment['char_start']:segment['char_end']] == text
                    and row['source_text'].encode()[segment['byte_start']:segment['byte_end']] == text.encode(),
                    'unaltered normative prefixes and source byte/character offsets '+str(width))
    check(devcache['schema'] == 'prospective-wording-source-inputs/v1'
        and len(devcache['rows']) == len(devcache['clause_cache']) == 60,
        'strict sixty-source prospective cache '+str(width))

observer_path = frozen / 'scripts/ops/autoencoder/evaluate_normative_wording_development.py'
bind(observer_path, '6be7e03656087fa9b5607b7e82b4a0a1244ca920cad8a81d64510f140962cfc6')
spec = importlib.util.spec_from_file_location('_readiness_updated_observer', observer_path)
observer = importlib.util.module_from_spec(spec); spec.loader.exec_module(observer)
check(observer.FIXED['source_head_trace_same_greedy_pass'] is True
    and observer.FIXED['extra_source_head_evaluations'] == 0
    and observer.FIXED['full_vocabulary_source_recurrent_combined_logits'] is True
    and observer.FIXED['source_head_and_formula_join_after_reference_barrier'] is True
    and observer.FIXED['unvisited_source_sites_counted_correct'] is False,
    'previous prospective source-head/formula measurement gap closed without extra model passes')
SOWNER = 'ipfs_datasets_py/logic/formalization/autoencoder/generated_scalar_observation.py'
S_SHA = '1f1d35f7fd90df0396f3222676f2ffd11f17e2b1b2c79c0a79f1600488eb08d8'
scalar_paths = [p for p,s in manifest['inputs'].items() if p.endswith('/'+SOWNER) and s == S_SHA]
check(len(scalar_paths) == 1 and manifest['producer_pins'][scalar_paths[0]] == S_SHA,
    'exact authenticated same-pass scalar owner in numerical closure')
scalar = Path(scalar_paths[0]).read_text(); scalar_tree = ast.parse(scalar)
check('applied_source_logits=source.tolist()' in scalar and 'raw_recurrent_logits=raw[index, 0].tolist()' in scalar
    and 'torch.equal(raw[index, 0]+source, combined)' in scalar
    and 'source_head_extra_evaluations=0' in scalar and 'extra_model_passes=0' in scalar,
    'actual owner collects full source/recurrent/combined cached logits with exact additive parity')
estimate = 60*(128*32*3*40+512*64+32768)
check(estimate == 33423360 and estimate < observer.FIXED['max_trace_memory_bytes'],
    'same-pass sixty-row trace estimate fits134217728 retention bound')
tree = ast.parse(observer_path.read_text()); execute = next(n for n in tree.body
    if isinstance(n,ast.FunctionDef) and n.name == 'execute')
calls = [(n.lineno,n.func.id if isinstance(n.func,ast.Name) else n.func.attr
    if isinstance(n.func,ast.Attribute) else '') for n in ast.walk(execute) if isinstance(n,ast.Call)]
trace_line = next(n for n,c in calls if c == 'collect_source_scalar_trace')
reference_line = next(n for n,c in calls if c == 'load_references')
score_line = next(n for n,c in calls if c == 'score_scalar_trace')
join_line = next(n for n,c in calls if c == 'join_source_heads_and_formula')
check(trace_line < reference_line < score_line < join_line, 'causal trace before complete barrier; labels and joins afterward')
check(not any(c == 'generate_panel' for _,c in calls), 'no second formula generation beside scalar trace')
check(observer.FIXED['panel_count'] == 8 and observer.FIXED['samples_per_panel'] == 60
    and observer.FIXED['all_predictions_before_reference_load'] is True
    and observer.FIXED['predictions_fsynced_before_reference_load'] is True,
    'all eight60-source trace/prediction pairs durable before future labels')
check("source_correct=None" in observer_path.read_text()
    and 'unvisited_counted_correct=False' in observer_path.read_text(), 'unvisited head sites remain null and not correct')
tests = OUT / 'training_adapter_updated_observer_tests.xml'; bind(tests)
import xml.etree.ElementTree as ET
suite = ET.parse(tests).getroot().find('testsuite')
check(int(suite.attrib['tests']) == 95 and int(suite.attrib['failures']) == 0
    and int(suite.attrib['errors']) == 0, '95 pure contracts including54 updated observer cases passed')

review = dict(schema='normative-wording-independent-phase-readiness/v1', passed=True,
    findings=[], phase='preflight', run_root=str(R.resolve()),
    created_utc=datetime.now(timezone.utc).isoformat(), reviewed_artifacts=len(artifacts),
    artifacts=artifacts, checks=len(checks), check_labels=checks,
    previous_source_head_measurement_gap_closed=True, contracts_passed=95,
    prospective_labels_not_bound_in_training=True, source_only_future_exclusions=60,
    actual_native_preparation_completed=True, native_child_and_guardian_exit=0,
    owned_native_lease_released=True, baseline_zero_evidence=baseline_evidence,
    independent_model_execution=False, independent_encoder_execution=False,
    read_only_review=True, source_edits=False, git_mutations=False,
    resource_admission_performed=False, model_preflight_executed=False,
    convergence_claimed=False, checkpoint_promoted=False, admitted=False, lake_executed=False,
    caveats=['Fresh live resource/CPU/memory admission remains the owned guardian responsibility.',
        'This report authorizes only the explicitly named bounded preflight; no fit success or convergence inferred.',
        'Native vectors are now warm cached source vectors; no bridge-on legal IR timing or semantic/Lake admission.',
        'Prospective wording retains exposed authored target meanings; no fresh semantic holdout claimed.'],
    elapsed_seconds=time.monotonic()-started)
(R / 'review').mkdir(exist_ok=True)
for width in (384,768):
    value = dict(review, dimension=width)
    value['content_sha256'] = digest(value)
    destination = R / f'review/preflight-{width}-readiness.json'
    with destination.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2); stream.write('\n')
    print(json.dumps(dict(passed=True, phase='preflight', dimension=width,
        run_root=str(R), checks=len(checks), artifacts=len(artifacts), output=str(destination))))
