"""Pure complete prospective wording preparation; no numerical execution."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path('/home/barberb/lift_coding')
P = ROOT / 'external/ipfs_datasets'
OUT = ROOT / 'artifacts/autoencoder-wording-fit-20261006/development'
sys.path.insert(0, str(P))
from ipfs_datasets_py.logic.formalization.autoencoder import prospective_normative_development as dev
from ipfs_datasets_py.logic.formalization.autoencoder import normative_wording_training_sources as train
from ipfs_datasets_py.optimizers.logic_theorem_optimizer import legal_formula_codec

checks = 0
bindings = {}
start = time.monotonic()


def check(condition, label):
    global checks
    if not condition:
        raise ValueError(label)
    checks += 1


def bound(path, expected=None):
    path = Path(path).resolve(); data = path.read_bytes()
    ref = dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    check(expected is None or ref['sha256'] == expected, 'changed authenticated file: '+str(path))
    bindings[str(path)] = ref
    return ref


def load(path, expected=None):
    bound(path, expected)
    return json.loads(Path(path).read_bytes())


def save(name, value):
    path = OUT / name
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write('\n')
    return bound(path)


def resident_sources():
    refs = {}
    for name, module in list(sys.modules.items()):
        if name == 'ipfs_datasets_py' or name.startswith('ipfs_datasets_py.'):
            path = getattr(module, '__file__', None)
            if path:
                path = Path(path).resolve()
                check(path.is_relative_to(P), 'drifted canonical import: '+str(path))
                refs[str(path)] = bound(path)
    check('torch' not in sys.modules and 'transformers' not in sys.modules,
          'pure preparation unexpectedly imported a numerical runtime')
    return refs


def validate_rule(value):
    legal_formula_codec._rule(value)
    return dict(valid=True, canonical_ir=value)


r4 = P / 'workspace/test-logs/decoder-training-paraphrases-r4-20261004'
result = r4 / 'preparation-r1/results'
manifest = load(r4 / 'preparation-manifest.json')
summary = load(result / 'summary.json')
source_ref = summary['source_rows']
check(bound(source_ref['path']) == source_ref, 'R4 source receipt binding differs')
r4_sources = load(source_ref['path'])
corpus_ref = summary['corpus_receipt']
check(bound(corpus_ref['path']) == corpus_ref, 'R4 corpus receipt binding differs')
corpus = load(corpus_ref['path'])
check(corpus['receipt_sha256'] == dev.digest({k:v for k,v in corpus.items() if k != 'receipt_sha256'}),
      'R4 corpus seal differs')
bank = load(result / 'original-training-bank-used.json')
prior = load(result / 'prior-source-inventories.json')
check(dev.digest(bank) == corpus['original_train_bank_sha256'], 'original TRAIN bank binding differs')
check(dev.digest(prior) == corpus['prior_sources_sha256'], 'prior inventory binding differs')
check(dev.digest(r4_sources) == corpus['source_rows_sha256'], 'R4 source content binding differs')
raw_dev = P / 'workspace/test-logs/decoder-distillation-limits-20261002/prepared-r1/prepared384-validation.json'
raw = load(raw_dev, manifest['inputs'][str(raw_dev)])
validation = [{k:r[k] for k in ('id','source_text','target_ids')} for r in raw]
raw_codec = ROOT / 'artifacts/source-reconstruction-v2-20261001/run-01/legal_ir/raw_ce-1729-checkpoint.json'
codec = load(raw_codec, manifest['inputs'][str(raw_codec)])['codec']
check(dev.digest(codec) == corpus['codec_sha256'], 'unchanged complete32V codec differs')
composition_file = ROOT / 'artifacts/autoformalization-publication-20261004/expansion/cohort-01/source-inputs.json'
composition = load(composition_file)
check(composition['content_sha256'] == dev.digest({k:v for k,v in composition.items() if k != 'content_sha256'}),
      'composition source-only content seal differs')
check(composition['row_count'] == len(composition['rows']) == 64
    and composition['contains_formal_targets'] is False, 'composition64 source-only inventory differs')
prior['r4_training_paraphrases'] = r4_sources
prior['composition64'] = [dict(id=r['id'], source_text=r['input']['source_text']) for r in composition['rows']]

producer_before = resident_sources()
spec = bound(OUT.parent / 'development-spec.md')
script = bound(__file__)
recipe = dev.recipe()
basis = dict(schema='prospective-wording-authoring-seal/v1', role=dev.ROLE,
    recipe=recipe, input_files=deepcopy(bindings), producer_sources=deepcopy(producer_before),
    creation_policy='fixed wording before all new encoder/model queries and fits',
    numeric_execution_authorized=False, model_queries_used_for_template_choice=False,
    template_author='prospective_wording_dev preparation owner',
    independent_human_review_authenticated=False, original_meanings_previously_exposed=True)
provisional = dev.digest(basis)
# This independently authored TRAIN rendering is used only as an exact source
# exclusion. Its targets/receipt are discarded; no DEV targets reach it.
training_sources = train.build(training_bank=bank, prior_sources_by_dataset=prior,
    codec=codec, sealed_recipe_sha256=provisional, validate_rule=validate_rule)['source_rows']
prior['new_training_wordings'] = training_sources
basis['new_training_sources_sha256'] = dev.digest(training_sources)
basis['complete_prior_sources_sha256'] = dev.digest(prior)
seal = dev.digest(basis)
built = dev.build(validation_bank=validation, training_bank=bank,
    prior_sources_by_dataset=prior, codec=codec, sealed_recipe_sha256=seal,
    validate_rule=validate_rule)
check(len(built['source_rows']) == len(built['references']) == 60, 'complete60 retained')
check(built['receipt']['actor_action_group_overlap'] == 0, 'TRAIN group overlap')
check(Counter(r['template'] for r in built['references']) == dict.fromkeys(dev.TEMPLATES,30),
      'all30rules pertemplate')
for row, ref in zip(built['source_rows'], built['references'], strict=True):
    check(row == {k:ref[k] for k in ('id','source_text')}, 'source/reference identity mismatch')
    rule = ref['target']['rules'][0]
    check(ref['source_sha256'] == dev.base.text_sha(row['source_text']), 'source binding')
    check(ref['target_sha256'] == dev.digest(ref['target']), 'target binding')
    check(ref['target_ids_sha256'] == dev.digest(ref['target_ids']), 'tokens binding')
    check(row['source_text'] == dev.sentence(ref['template'],rule), 'fixed authored rendering')
    check(all(ref[k] is False for k in dev.FALSE), 'no derived admissions')
    validate_rule(ref['target']); check(True, 'real canonical grammar syntax validation')
producer_after = resident_sources()
check(producer_after == producer_before, 'producer import/content closure changed')
for path, ref in list(bindings.items()):
    check(bound(path) == ref, 'source/preparation input changed before seal')

outputs = dict(
    source_rows=save('source-rows.json', built['source_rows']),
    references=save('development-references.json', built['references']),
    receipt=save('development-corpus-receipt.json', built['receipt']),
    recipe=save('recipe.json', recipe),
    validation_bank=save('original-validation-bank-used.json', validation),
    exclusions=save('prior-source-inventories.json', prior),
    training_source_exclusion=save('new-training-source-exclusion.json', training_sources),
    codec=save('codec.json', codec),
)
sealed = dict(basis, sealed_recipe_sha256=seal, created_utc=datetime.now(timezone.utc).isoformat(),
    artifact_files=outputs, complete=True, pure_checks=checks,
    generation_seconds=time.monotonic()-start, source_semantics_verified=False,
    encoder_executed=False, training_executed=False, model_scored=False,
    qualified=False, admitted=False, lake_executed=False, checkpoint_promoted=False,
    fresh_holdout_claimed=False)
sealed['seal_manifest_sha256'] = dev.digest(sealed)
final = save('seal-manifest.json', sealed)
print(json.dumps(dict(complete=True, sources=60, checks=checks, seal_manifest=final,
    artifact_files=outputs, producer_source_count=len(producer_after)), indent=2))
