"""Independent saved-data verification; deliberately imports no package owner."""
from collections import Counter
import hashlib
import json
from pathlib import Path

OUT = Path('/home/barberb/lift_coding/artifacts/autoencoder-wording-fit-20261006/development')
checks = 0


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def check(condition, message):
    global checks
    if not condition:
        raise ValueError(message)
    checks += 1


def load(path):
    return json.loads(Path(path).read_bytes())


seal = load(OUT / 'seal-manifest.json')
check(seal['seal_manifest_sha256'] == digest({k:v for k,v in seal.items() if k != 'seal_manifest_sha256'}),
      'complete authoring seal content')
keys = {'schema','role','recipe','input_files','producer_sources','creation_policy',
    'numeric_execution_authorized','model_queries_used_for_template_choice','template_author',
    'independent_human_review_authenticated','original_meanings_previously_exposed',
    'new_training_sources_sha256','complete_prior_sources_sha256'}
check(seal['sealed_recipe_sha256'] == digest({k:seal[k] for k in keys}), 'authoring recipe basis')
for refs in [seal['input_files'], seal['producer_sources'], seal['artifact_files']]:
    for _, ref in refs.items():
        data = Path(ref['path']).read_bytes()
        check(len(data) == ref['bytes'], 'saved byte count '+ref['path'])
        check(hashlib.sha256(data).hexdigest() == ref['sha256'], 'saved SHA '+ref['path'])
rows = load(seal['artifact_files']['source_rows']['path'])
refs = load(seal['artifact_files']['references']['path'])
receipt = load(seal['artifact_files']['receipt']['path'])
bank = load(seal['artifact_files']['validation_bank']['path'])
codec = load(seal['artifact_files']['codec']['path'])
prior = load(seal['artifact_files']['exclusions']['path'])
train = load(seal['artifact_files']['training_source_exclusion']['path'])
recipe = load(seal['artifact_files']['recipe']['path'])
check(recipe == seal['recipe'], 'exact recipe seal copy')
check(receipt['receipt_sha256'] == digest({k:v for k,v in receipt.items() if k != 'receipt_sha256'}),
      'corpus receipt content seal')
check(receipt['sealed_recipe_sha256'] == seal['sealed_recipe_sha256'], 'recipe/corpus binding')
for key, value in [('source_rows_sha256',rows),('references_sha256',refs),('codec_sha256',codec),
                   ('original_validation_bank_sha256',bank),('prior_sources_sha256',prior)]:
    check(receipt[key] == digest(value), 'corpus exact content '+key)
check(digest(train) == seal['new_training_sources_sha256'], 'exact TRAIN source exclusion')
check(prior['new_training_wordings'] == train, 'all new TRAIN sources excluded')
check(len(bank) == 60 and len(rows) == len(refs) == 60, 'unpruned complete banks')
vocab = codec['target_vocabulary']; check(len(vocab) == 32, 'unchanged 32V vocabulary')
originals = {}
for row in bank:
    target = json.loads(''.join(vocab[i] for i in row['target_ids'][1:-1]))
    check(len(target['rules']) == 1, 'complete original single-rule target')
    check(row['id'] not in originals, 'unique original identity')
    originals[row['id']] = dict(source_sha256=sha(row['source_text']), target=target,
        target_sha256=digest(target), target_ids_sha256=digest(row['target_ids']))
check(len({digest(r['target']['rules'][0]) for r in originals.values()}) == 30,
      'exact 30 original validation meanings')
expected_prior = dict(exposed_r6=48, exposed_r8=48, exposed_v3=48, original_train_bank=180,
    paragraph_train=48, paragraph_validation=48, raw_canary=30, raw_test=60,
    raw_train=180, raw_validation=60, r4_training_paraphrases=48, composition64=64,
    new_training_wordings=48)
check(set(prior) == set(expected_prior), 'all13 recorded exclusion inventories')
normal = lambda text:' '.join(text.casefold().split())
forbidden, forbidden_hashes = set(), set()
for name, records in prior.items():
    check(len(records) == expected_prior[name], 'complete exclusion row count '+name)
    check(len({r['id'] for r in records}) == len(records), 'unique exclusion IDs '+name)
    check(all(set(r) == {'id','source_text'} for r in records), 'source-only exclusion '+name)
    for r in records:
        for text in [r['source_text'], *r['source_text'].split('\n\n')]:
            forbidden.add(normal(text)); forbidden_hashes.add(sha(text))
groups = set(map(tuple, receipt['validation_actor_action_groups']))
train_groups = set(map(tuple, receipt['original_train_actor_action_groups']))
check(len(groups) == 5 and len(train_groups) == 15 and not groups.intersection(train_groups),
      'five validation actor/action groups disjoint from15 TRAIN groups')
counts, templates, rule_uses, seen = Counter(), Counter(), Counter(), set()
false_fields = ['admitted','qualified','formalized','roundtrip_ok','proof_authority','lake_executed',
    'source_semantics_verified','source_alignment_reviewed','training_executed','encoder_executed',
    'checkpoint_promoted','historical_linguistic_teacher_modified','fresh_holdout_claimed',
    'training_allowed','selection_allowed']
for row, ref in zip(rows, refs, strict=True):
    check(set(row) == {'id','source_text'} and row == {k:ref[k] for k in row}, 'closed source-only row')
    check('\n\n' not in row['source_text'] and ref['clause_count'] == 1, 'single literal clause')
    check(row['id'] == 'prospective-normative-v1:'+sha(row['source_text']), 'source digest identity')
    check(normal(row['source_text']) not in forbidden and sha(row['source_text']) not in forbidden_hashes,
          'literal and normalized prior exclusion')
    check(normal(row['source_text']) not in seen, 'distinct generated source')
    seen.add(normal(row['source_text']))
    check(ref['split'] == 'prospective_authored_development'
        and ref['label_provenance'] == 'authored_development'
        and ref['original_meanings_previously_exposed'] is True, 'honest exposed authored label')
    check(all(ref[field] is False for field in false_fields), 'no inherited qualification')
    target = ref['target']; check(set(target) == {'rules'} and len(target['rules']) == 1, 'complete target')
    rule = target['rules'][0]
    check(set(rule) == {'modality','actor','action','object','conditions','exceptions','temporal'},
          'all seven facets')
    check(all(rule[field] == [] for field in ['conditions','exceptions','temporal']), 'empty qualifier floor')
    check((rule['actor'],rule['action']) in groups, 'original validation group')
    wire = json.loads(''.join(vocab[i] for i in ref['target_ids'][1:-1]))
    check(wire == target and ref['target_ids'][0] == 1 and ref['target_ids'][-1] == 2
        and len(ref['target_ids']) <= 512, 'lossless complete token target')
    check(ref['source_sha256'] == sha(row['source_text']) and ref['target_sha256'] == digest(target)
        and ref['target_ids_sha256'] == digest(ref['target_ids']), 'complete source/target/token bindings')
    expected = recipe['template_text'][ref['template']][rule['modality']].format(**rule,
        gerund=recipe['gerunds'][rule['action']])
    check(row['source_text'] == expected, 'sealed exact template')
    check(len(ref['derivations']) == 1, 'one complete derivation')
    d = ref['derivations'][0]
    check(d['rule_sha256'] == digest(rule) and len(d['original_validation_sources']) == 2,
          'two original renderings per rule')
    for previous in d['original_validation_sources']:
        actual = originals[previous['id']]
        check(actual['target'] == target, 'target untouched from original validation')
        check(previous == {k:actual[k] if k != 'id' else previous['id']
            for k in ['id','source_sha256','target_sha256','target_ids_sha256']}, 'upstream derivation hashes')
    counts[rule['modality']] += 1; templates[ref['template']] += 1; rule_uses[digest(rule)] += 1
check(counts == {'O':20,'P':20,'F':20}, 'balanced60 modalities')
check(templates == dict.fromkeys(recipe['templates'],30), 'balanced30 pertemplate')
check(len(rule_uses) == 30 and set(rule_uses.values()) == {2}, 'every original rule used twice')
report = dict(schema='independent-prospective-wording-audit/v1', complete=True, checks=checks,
    sources=60, rules=30, prior_inventories=13, actor_action_group_overlap=0,
    reference_targets_unchanged=True, source_rows_contain_targets=False,
    module_imports_performed=False, model_executed=False, encoder_executed=False,
    training_executed=False, qualified=False, admitted=False, lake_executed=False,
    fresh_holdout_claimed=False, original_meanings_previously_exposed=True)
report['content_sha256'] = digest(report)
with (OUT / 'independent-audit.json').open('x') as stream:
    json.dump(report, stream, indent=2, sort_keys=True); stream.write('\n')
print(json.dumps(report,indent=2))
