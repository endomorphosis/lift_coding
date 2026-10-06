"""Independent pure controls for the prospective native adapter, with test doubles."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path('/home/barberb/lift_coding')
P = ROOT / 'external/ipfs_datasets'
sys.path.insert(0, str(P))
from ipfs_datasets_py.logic.formalization.autoencoder import prospective_wording_source_inputs as owner
from ipfs_datasets_py.logic.formalization.autoencoder import source_embeddings_768_complete as complete
from ipfs_datasets_py.optimizers.logic_theorem_optimizer import autoencoder_embedding_runtime as runtime

OUT = ROOT / 'artifacts/autoencoder-wording-fit-20261006/review'
checks = []


def check(condition, name):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def reject(call, name):
    try:
        call()
    except (ValueError, TimeoutError):
        checks.append(name)
        return
    raise AssertionError('unexpected acceptance: ' + name)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sign(value):
    value['production_sha256'] = owner.digest({k: v for k, v in value.items() if k != 'production_sha256'})


def payload(shape, width):
    rep = dict(dimension=width, semantic_embedding=True, device='cpu', dtype='float32',
               experiment_token_limit=512, actual_forward_tokens_verified=True)
    body = dict(explicit_test_double=True)
    if width == 384:
        rep.update(kind='native_gte_small_semantic_embedding', model_id='thenlper/gte-small', revision=runtime.PINNED_REVISION)
        body['execution'] = dict(batch_size=4)
    else:
        rep.update(kind='native_gte_multilingual_semantic_embedding', profile_id=complete.PROFILE_ID,
                   historical_profile_token_limit=8192, cached_profile_relabelled=False)
        body['execution_profile'] = dict(batch_size=4, device='cpu', dtype='float32', pooling='cls',
                                        normalization='l2', max_tokens_including_special_tokens=512,
                                        attention_implementation='eager')
    return dict(vectors=[dict(id=r['id'], source_sha256=owner.native.authored.text_sha(r['source_text']),
                             vector=[1.] + [0.] * (width - 1), token_count=2,
                             token_input_sha256='b' * 64) for r in shape['source_inputs']],
                native_production=body, producer_files=owner.native._pins(), source_artifact=None, representation=rep)


paths = [Path(module.__file__).resolve() for module in (owner, owner.native, owner.clauses,
         complete, complete.reference, complete.reference._PROFILE, runtime)]
tests_path = P / 'tests/unit/logic/formalization/autoencoder/test_prospective_wording_source_inputs.py'
paths.append(tests_path)
before = {str(path): sha(path) for path in paths}
rows = [dict(id=f'independent-native-source:{i}', source_text=f'An explicit fixturé clause number {i}.') for i in range(60)]
original = deepcopy(rows)
plan = owner.source_plan(rows, expected_source_rows_sha256=owner.digest(rows), sealed_recipe_sha256='a' * 64)
check(rows == original, 'source builder preserves input')
check(len(plan['shape_plan']['source_inputs']) == 60, 'sixty native source inputs')
check(len(plan['shape_plan']['source_aliases']) == 120, 'one paragraph and clause alias per input')
for slot, row in enumerate(rows):
    aliases = plan['shape_plan']['source_aliases'][slot * 2: slot * 2 + 2]
    check([v['role'] for v in aliases] == ['paragraph', 'clause'], 'source alias role order')
    check([v['slot'] for v in aliases] == [None, 0], 'single clause alias positions')
    check(all(v['source_sha256'] == owner.native.authored.text_sha(row['source_text']) for v in aliases), 'full unicode source byte hash')
check(all(plan[k] is False for k in owner.FALSE), 'source plan has no qualification authority')
for key, value in [('target', {}), ('prediction', []), ('admitted', True)]:
    changed = deepcopy(rows); changed[0][key] = value
    reject(lambda: owner.source_plan(changed, expected_source_rows_sha256=owner.digest(changed), sealed_recipe_sha256='a' * 64), 'closed source refuses ' + key)
for count in (59, 61):
    changed = deepcopy(rows[:count])
    if count == 61:
        changed.append(dict(id='extra', source_text='An extra source.'))
    reject(lambda: owner.source_plan(changed, expected_source_rows_sha256=owner.digest(changed), sealed_recipe_sha256='a' * 64), 'exact source count ' + str(count))
reject(lambda: owner.native.source_plan(rows, expected_source_rows_sha256=owner.digest(rows), sealed_comparison_sha256='a' * 64), 'old48 shape continues to refuse60')
for width in (384, 768):
    config = dict(snapshot_path='/fixture/snapshot') if width == 384 else dict(manifest_path='/fixture/manifest',
             expected_manifest_sha256='c' * 64, model_directory='/fixture/model', code_directory='/fixture/code')
    seen = []
    def binder(shape, report):
        seen.append((deepcopy(shape), deepcopy(report['native_production'])))
    with patch.object(owner.native, '_produce' + str(width), lambda shape, *a: payload(shape, width)), \
         patch.object(owner.native, '_validate_native_binding', binder):
        report = owner.produce_width(plan, dimension=width, asset_config=config,
                                    source_artifact_directory='/fixture/sources' if width == 384 else None)
        assembled = owner.assemble(plan, report, dimension=width)
        check(len(seen) == 2 and all(shape == plan['shape_plan'] for shape, _ in seen), 'full native binding invoked produce and assemble')
        check(len(assembled['rows']) == len(assembled['clause_cache']) == len(assembled['source_contexts']) == 60, 'complete sixty source contexts ' + str(width))
        check(all(assembled[k] is False for k in owner.FALSE), 'assembly grants no qualification ' + str(width))
        for row in assembled['rows']:
            seg = assembled['source_contexts'][row['id']]['segments'][0]
            check(set(row) == {'id', 'source_text', 'input'}, 'assembled model row source only')
            check(seg['source_text'] == row['source_text'] and seg['vector'] == row['input'], 'exact clause context joins full source')
            check(seg['char_start'] == seg['byte_start'] == 0 and seg['char_end'] == len(row['source_text'])
                  and seg['byte_end'] == len(row['source_text'].encode()), 'unicode clause offsets preserved')
        mutations = [(['vectors', 0, 'token_count'], 513), (['vectors', 0, 'token_count'], True),
                     (['vectors', 0, 'source_sha256'], '0' * 64), (['qualified'], True),
                     (['role'], 'train_augmentation'), (['representation', 'experiment_token_limit'], 8192)]
        if width == 384:
            mutations.extend([(['representation', 'model_id'], 'different/model'),
                              (['representation', 'revision'], '0' * 40), (['native_production', 'execution', 'batch_size'], 8)])
        else:
            mutations.extend([(['representation', 'historical_profile_token_limit'], 512),
                              (['representation', 'cached_profile_relabelled'], True),
                              (['representation', 'profile_id'], 'unbound'),
                              (['native_production', 'execution_profile', 'batch_size'], 8),
                              (['native_production', 'execution_profile', 'pooling'], 'mean'),
                              (['native_production', 'execution_profile', 'device'], 'cuda'),
                              (['native_production', 'execution_profile', 'dtype'], 'float64')])
        for keys, value in mutations:
            changed = deepcopy(report); node = changed
            for key in keys[:-1]: node = node[key]
            node[keys[-1]] = value; sign(changed)
            reject(lambda: owner.validate_report(plan, changed), 'rehash cannot bypass ' + '/'.join(map(str, keys)) + ':' + str(width))
        with patch.object(owner.native, '_validate_native_binding', side_effect=ValueError('independent binding refusal')):
            reject(lambda: owner.assemble(plan, report, dimension=width), 'native binding refusal preserved ' + str(width))
after = {str(path): sha(path) for path in paths}
check(before == after, 'reviewed source bytes unchanged during independent controls')
result = dict(schema='prospective-native-adapter-independent-controls/v1', checks=len(checks), checks_passed=checks,
              source_sha256=after, all_checks_passed=True, actual_native_forward=False,
              encoders_loaded=False, training_executed=False, admitted=False, qualified=False,
              execution_scope='Pure source/context controls and explicit normalized-vector/native test doubles; real native evidence validation delegated, not numerically executed.',
              created_at=datetime.now(timezone.utc).isoformat())
destination = OUT / 'native_adapter_independent_checks.json'
with destination.open('x') as stream: json.dump(result, stream, indent=2, sort_keys=True); stream.write('\n')
print(json.dumps(dict(checks=len(checks), passed=True, output=str(destination), source_sha256=after), sort_keys=True))
