"""Read saved JSON only; no canonical imports, models, or review fabrication."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path('/home/barberb/lift_coding')
P = ROOT / 'external/ipfs_datasets'
OUT = ROOT / 'artifacts/autoencoder-next-gap-20261006/data'
R4 = P / 'workspace/test-logs/decoder-training-paraphrases-r4-20261004'
A = ROOT / 'artifacts/autoformalization-alignment-20261003'
E = ROOT / 'artifacts/autoformalization-publication-20261004/expansion'
checks = 0
bindings = {}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def check(condition, label):
    global checks
    assert condition, label
    checks += 1


def bound(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    ref = {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    bindings[str(path)] = ref
    return ref


def load(path):
    return json.loads(Path(path).read_text())


def pinned_load(path):
    bound(path)
    return load(path)


def seal_check(value, field):
    check(value[field] == digest({k: v for k, v in value.items() if k != field}), field)


def write(name, value):
    value['content_sha256'] = digest(value)
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    return bound(OUT / name)


results = R4 / 'preparation-r1/results'
summary = pinned_load(results / 'summary.json')
for ref in [summary['corpus_receipt'], summary['training_references'], summary['source_rows']]:
    check(bound(ref['path']) == ref, 'R4 saved summary artifact binding')
receipt = pinned_load(results / 'training-corpus-receipt.json')
refs = pinned_load(results / 'training-references.json')
rows = pinned_load(results / 'source-rows.json')
bank = pinned_load(results / 'original-training-bank-used.json')
prior = pinned_load(results / 'prior-source-inventories.json')
plan = pinned_load(results / 'source-plan.json')
check(len(rows) == len(refs) == 48 and len(bank) == 180, 'complete R4 paragraph/original bank')
seal_check(receipt, 'receipt_sha256')
seal_check(plan, 'plan_sha256')
for k, v in [('source_rows_sha256', rows), ('references_sha256', refs),
             ('original_train_bank_sha256', bank), ('prior_sources_sha256', prior)]:
    check(receipt[k] == digest(v), 'R4 corpus ' + k)
raw_checkpoint_path = ROOT / 'artifacts/source-reconstruction-v2-20261001/run-01/legal_ir/raw_ce-1729-checkpoint.json'
raw_checkpoint = pinned_load(raw_checkpoint_path)
codec = raw_checkpoint['codec']
vocab = codec['target_vocabulary']
check(len(vocab) == 32 and receipt['codec_sha256'] == digest(codec), 'R4 exact 32V codec')
original = {}
for row in bank:
    target = json.loads(''.join(vocab[i] for i in row['target_ids'][1:-1]))
    check(len(target['rules']) == 1, 'complete original TRAIN target')
    original[row['id']] = (row, target)
paragraphs, clauses, rules, by_template = {}, {}, [], Counter()
for source, ref in zip(rows, refs, strict=True):
    check(source == {k: ref[k] for k in ['id', 'source_text']}, 'R4 target/source identity')
    check(ref['split'] == 'train_augmentation' and ref['admitted'] is False
          and ref['qualified'] is False and ref['source_semantics_verified'] is False,
          'R4 authored diagnostic provenance preserved')
    check(digest(ref['target']) == ref['target_sha256'], 'R4 target content binding')
    decoded = json.loads(''.join(vocab[i] for i in ref['target_ids'][1:-1]))
    check(decoded == ref['target'] and len(ref['target_ids']) <= 512, 'R4 codec complete target')
    texts = source['source_text'].split('\n\n')
    check(len(texts) == ref['clause_count'] == len(ref['target']['rules']) == len(ref['derivations']),
          'R4 complete ordered clauses')
    paragraphs[source['id']] = source['source_text']
    for text, rule, derived in zip(texts, ref['target']['rules'], ref['derivations'], strict=True):
        check(text not in clauses and digest(rule) == derived['rule_sha256'], 'R4 unique TRAIN clause rule')
        for upstream in derived['original_train_sources']:
            old, old_target = original[upstream['id']]
            check(sha(old['source_text']) == upstream['source_sha256']
                  and digest(old_target) == upstream['target_sha256']
                  and digest(old['target_ids']) == upstream['target_ids_sha256']
                  and old_target['rules'][0] == rule, 'R4 original TRAIN-only derivation')
        clauses[text] = {'rule': rule, 'template': ref['template'], 'paragraph_id': ref['id']}
        rules.append(rule)
        by_template[ref['template']] += 1
check(len(clauses) == 180 and len({digest(r) for r in rules}) == 90, 'R4 complete clause/rule bank')
normal = lambda text: ' '.join(text.casefold().split())
current = set(normal(t) for t in [*paragraphs.values(), *clauses])
exclusions = {}
for name, inventory in prior.items():
    textset = set(normal(t) for row in inventory for t in [row['source_text'], *row['source_text'].split('\n\n')])
    exclusions[name] = {'rows': len(inventory), 'normalized_source_count': len(textset),
                        'normalized_overlap': len(current & textset)}
    check(not current & textset, 'R4 prior source exclusion ' + name)
r4_cache = {}
for d in (384, 768):
    cachepath, productionpath = results / f'dimension-inputs-{d}.json', results / f'production-{d}.json'
    cache, production = pinned_load(cachepath), pinned_load(productionpath)
    seal_check(cache, 'inputs_sha256')
    seal_check(production, 'production_sha256')
    check(cache['production_sha256'] == production['production_sha256']
          and cache['source_plan_sha256'] == plan['plan_sha256'], 'R4 cache producer/plan join')
    produced = {r['source_sha256']: r for r in production['vectors']}
    check(len(produced) == len(plan['shape_plan']['source_inputs']) == 216, 'complete native unique-source set')
    for index, (r, source) in enumerate(zip(production['vectors'], plan['shape_plan']['source_inputs'], strict=True)):
        check(r['id'] == source['id'] and r['source_sha256'] == sha(source['source_text']), 'native source identity')
        v = r['vector']
        check(len(v) == d and all(type(x) in (int, float) and math.isfinite(x) for x in v)
              and abs(sum(x*x for x in v) - 1) < 1e-5 and r['token_count'] <= 512, 'native complete bounded vector')
        native = production['native_production']
        if d == 384:
            saved = native['results'][index]
            bits = bytes.fromhex(saved['vector']['bits'])
            check(list(struct.unpack('>' + 'f'*d, bits)) == v
                  and digest(saved['tokens']['input_ids']) == r['token_input_sha256'], 'native384 numerical/token receipt')
        else:
            check(native['vectors'][index] == v
                  and digest(native['token_rows'][index]['input_ids']) == r['token_input_sha256'], 'native768 numerical/token receipt')
    for r in [*cache['rows'], *cache['clause_cache']]:
        check(r['input'] == produced[sha(r['source_text'])]['vector'], 'cache exact produced numerical vector')
    check({r['source_text'] for r in cache['clause_cache']} == set(clauses)
          and {r['id'] for r in cache['rows']} == set(paragraphs), 'cache complete paragraph/clause inventory')
    for ref in refs:
        for text, segment in zip(ref['source_text'].split('\n\n'), cache['source_contexts'][ref['id']]['segments'], strict=True):
            check(text == segment['source_text'] and segment['vector'] == produced[sha(text)]['vector'], 'cache original ordered source segments')
    pins = production['producer_files']
    producer_matches = {path: bound(path)['sha256'] == expected for path, expected in pins.items()}
    check(all(producer_matches.values()), 'frozen R4 named producer source bytes')
    r4_cache[d] = {'cache': bound(cachepath), 'production': bound(productionpath),
        'clause_vectors': 180, 'paragraph_vectors': 48, 'unique_native_vectors': 216,
        'observed_tokens_max': max(r['token_count'] for r in production['vectors']),
        'representation': production['representation'], 'named_producer_files_rechecked': len(pins),
        'complete_binary_and_model_asset_closure_rechecked': False,
        'numeric_cache_matches_saved_native_outputs': True}

packetpath = A / 'binding-review-packet-01/reviewer_items.json'
packet = pinned_load(packetpath)
organizer = pinned_load(A / 'binding-review-packet-01/organizer_manifest_private.json')
recording = pinned_load(A / 'binding-review-admission-01/recording/receipt_private.json')
intake = pinned_load(A / 'label-evidence-intake-01/intake/intake_receipt_private.json')
sources = pinned_load(E / 'cohort-01/source-inputs.json')
metadata = pinned_load(E / 'cohort-01/cohort-metadata.json')
encoding = pinned_load(E / 'expanded-encoding-report-01.json')
for value in [organizer, intake, sources, metadata, encoding]: seal_check(value, 'content_sha256')
seal_check(recording, 'receipt_sha256')
source_items = {r['item_id']: r for r in packet['items']}
organization = {r['item_id']: r for r in organizer['rows']}
check(len(source_items) == len(sources['rows']) == 64 and recording['submission_count'] == 0
      and recording['human_reviews_authenticated'] == 0 and intake['formal_targets_admitted'] == 0, '64 pending cohort admission')
for item in packet['items']:
    check(all(x is None for x in item['annotation'].values())
          and sha(item['source_text']) == item['source_sha256']
          and digest({'source_text': item['source_text'], 'context': item['context']}) == item['input_sha256'], 'candidate-blind blank source envelope')
for item in [*organizer['rows'], *recording['items'], *intake['items']]:
    check(all(x == 0 for x in item['masks'].values()), 'pending per-item semantic masks remain zero')
source_rows = {r['id']: r for r in sources['rows']}
split_groups = {'train': set(), 'development': set()}
cachemap = []
for r in sources['rows']:
    item, org = source_items[r['review_item_id']], organization[r['review_item_id']]
    check(r['input'] == {'source_text': item['source_text'], 'context': item['context']}
          and r['input_sha256'] == item['input_sha256'] and r['source_sha256'] == item['source_sha256']
          and r['split'] == {'proposed_train': 'train', 'proposed_development': 'development'}[org['proposed_split']]
          and r['group_id'] == org['group_id'], '64 source packet/cohort identity and grouped split')
    split_groups[r['split']].add(r['group_id'])
    cachemap.append({'id': r['id'], 'review_item_id': r['review_item_id'], 'source_sha256': r['source_sha256'],
                     'input_sha256': r['input_sha256'], 'group_id': r['group_id'], 'source_reconstruction_split': r['split'],
                     'formal_target': None, 'formal_target_status': 'pending_independent_review',
                     'semantic_masks': dict.fromkeys(recording['masks'], 0)})
check(not split_groups['train'] & split_groups['development'] and all(len(s) == 8 for s in split_groups.values()),
      '64 source reconstruction group split')
composition_cache = {}
for lane, d in [('native384', 384), ('native768', 768)]:
    by_split = {}
    for split, suffix in [('train', 'train'), ('development', 'query')]:
        path = E / 'encoding-01/worker' / f'{lane}_raw_{suffix}_bundle.json'
        bundle = pinned_load(path)
        for value in [bundle, bundle['profile'], bundle['producer_receipt']]: seal_check(value, 'content_sha256')
        producerfile = bundle['producer_receipt']['artifact_binding']
        check(bound(producerfile['path']) == producerfile, '64 exact native producer artifact')
        check(len(bundle['rows']) == 32 and bundle['profile']['dimension'] == d, '64 split cache complete')
        rowbindings = {r['id']: r for r in bundle['producer_receipt']['rows']}
        for r in bundle['rows']:
            source = source_rows[r['id']]
            check(source['split'] == split and source['input'] == r['input']
                  and r['encoder_text'] == source['input']['source_text']
                  and r['encoder_text_sha256'] == source['source_sha256'] and r['status'] == 'available', '64 cache exact source split')
            check(len(r['vector']) == d and digest(r['vector']) == r['vector_sha256']
                  and all(type(x) in (int, float) and math.isfinite(x) for x in r['vector'])
                  and abs(sum(x*x for x in r['vector']) - 1) < 1e-5, '64 cached complete native vector')
            check(r['producer_row_sha256'] == digest(rowbindings[r['id']]), '64 normalized producer row binding')
        by_split[split] = {'bundle': bound(path), 'rows': 32,
                           'profile': bundle['profile'], 'producer': producerfile}
    composition_cache[lane] = by_split
weak = pinned_load(A / 'canonical-codec-01/train_weak_supervision.json')
check(len(weak['rows']) == 16 and {r['weak_label_origin'] for r in weak['rows']}
      == {'source_parser_derived_with_frozen_TRAIN_supervised_atom_catalog'},
      'existing16 weak teacher provenance')

report = {'schema': 'autoencoder-next-training-data-readiness/v1',
    'created_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'saved_data_integrity_and_readiness_only',
    'workspace_review_commit': '3eb24f89e82b74cfba3fa261ef099a1c5c7e1370',
    'datasets_review_commit': '3b3b994407b2fcfef955ce5153afc2eea01e4eff',
    'r4': {'complete_paragraphs': 48, 'unique_clauses': 180, 'unique_original_rules': 90,
        'role': 'authored_train_augmentation_diagnostic', 'templates': dict(by_template),
        'facet_counts': {k: dict(Counter(r[k] for r in rules)) for k in ['actor', 'action', 'object', 'modality']},
        'qualifier_nonempty_counts': {k: sum(bool(r[k]) for r in rules) for k in ['conditions', 'exceptions', 'temporal']},
        'explicit_absent_actor_action_object_examples': 0, 'novel_formal_rules': 0,
        'source_exclusions': exclusions, 'cache_pairs': r4_cache,
        'semantic_review_authenticated': False, 'formal_targets_admitted': 0,
        'source_semantics_verified': False,
        'allowed_reuse': 'existing authored diagnostic training; new declared arms need a frozen recipe and original controls'},
    'composition64': {'source_rows': 64, 'source_reconstruction_train_rows': 32,
        'source_reconstruction_development_rows': 32, 'source_groups': 16,
        'source_group_overlap': 0, 'submitted_reviews': 0, 'formal_targets_admitted': 0,
        'semantic_masks_nonzero': 0, 'all_annotation_slots_blank': True,
        'cache_pairs': composition_cache,
        'cached_forward_no_new_encoding_required': True,
        'allowed_reuse': 'source-only reconstruction or source-only diagnostic inference with exact profile; semantic fitting remains blocked'},
    'existing_weak_teacher': {'pairs': 16, 'groups': len({r['group_id'] for r in weak['rows']}),
        'origin': 'parser_derived_weak_teacher', 'semantic_review_authenticated': False,
        'allowed_reuse': 'separately declared weak decoder diagnostic; no semantic or contrastive labels inferred'},
    'trained_restricted32V_compatibility': {'composition64_direct_targets_compatible': False,
        'missing_actor_symbols': ['clerk', 'custodian', 'officer'],
        'missing_action_symbols': ['audit', 'authorize', 'notify', 'retain'],
        'missing_object_symbols': ['applicant', 'application', 'filing'],
        'qualifier_value_symbols_present': False,
        'scope_operators_preserved_by_flat_facets': False,
        'decoder_profile_fork_required_before_richer_fitting': True},
    'audit_operations': {'json_reads_and_hashing_only': True, 'checks': checks, 'model_forwards': 0,
        'encoder_forwards': 0, 'optimizer_updates': 0, 'downloads': 0, 'lake_builds': 0,
        'canonical_imports': 0, 'authenticated_review_or_adjudication_created': False},
    'admitted': False, 'qualified': False, 'semantic_fidelity_established': False,
    'checkpoint_promoted': False, 'constitution_formalized': False,
    'bindings': list(bindings.values())}
write('cache-pair-map.json', {'schema': 'pending-composition-cache-pair-map/v1', 'items': cachemap,
      'semantic_training_authorized': False, 'semantic_review_authenticated': False})
saved = write('readiness-audit.json', report)
print(json.dumps({'report': saved, 'checks': checks, 'r4_clauses': 180,
                  'composition_sources': 64, 'composition_admitted_targets': 0}, sort_keys=True))
