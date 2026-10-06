"""Independent full control-flow fixture; encoders and inherited setup are doubles."""
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path('/home/barberb/lift_coding'); P = ROOT / 'external/ipfs_datasets'
OUT = ROOT / 'artifacts/autoencoder-wording-fit-20261006/review'
sys.path.insert(0, str(P))
from ipfs_datasets_py.logic.formalization.autoencoder import normative_wording_training_sources as builder
from ipfs_datasets_py.logic.formalization.autoencoder import training_paraphrase_source_inputs as train_source
from ipfs_datasets_py.logic.formalization.autoencoder import prospective_wording_source_inputs as dev_source
from ipfs_datasets_py.logic.formalization.autoencoder import clause_source_context as clauses

driver_path = P / 'scripts/ops/autoencoder/prepare_normative_wording_sources.py'
spec = importlib.util.spec_from_file_location('_independent_wording_preparation_driver', driver_path)
driver = importlib.util.module_from_spec(spec); spec.loader.exec_module(driver)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks = []


def check(value, name):
    if not value: raise AssertionError(name)
    checks.append(name)


def read(path): return json.loads(Path(path).read_bytes())


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, sort_keys=True, indent=2).encode()
    with path.open('xb') as stream: stream.write(data)
    return dict(path=str(path), bytes=len(data), sha256=sha(path))


def run_fixture(failure=None):
    with tempfile.TemporaryDirectory(prefix='independent-wording-prep-') as directory:
        work = Path(directory); results = work / 'results'; events = []
        r4 = P / 'workspace/test-logs/decoder-training-paraphrases-r4-20261004/preparation-r1/results'
        dev = ROOT / 'artifacts/autoencoder-wording-fit-20261006/development'
        bank = read(r4 / 'original-training-bank-used.json')
        priors = read(dev / 'prior-source-inventories.json')
        inputs = {}
        def input_file(name, value):
            path = work / name; save(path, value); inputs[str(path)] = sha(path); return str(path)
        parent_path = input_file('r4-manifest.json', dict(extensions={driver.PARENT: 'pinned-parent'},
                             parent_extension_root=str(work / 'fresh'), parent_manifest=str(work / 'fresh-manifest.json'),
                             parent_plan=str(work / 'fresh-plan.json')))
        input_file('fresh-manifest.json', dict(extensions={driver.FRESH: 'pinned-fresh'}))
        input_file('fresh-plan.json', {})
        bank_path = input_file('training-bank.json', bank)
        prior_path = input_file('prior-sources.json', priors)
        source_path = input_file('development-sources.json', read(dev / 'source-rows.json'))
        expected_path = input_file('expected-training-sources.json', read(dev / 'new-training-source-exclusion.json'))
        hidden_path = input_file('never-parse-development-references.json', dict(must_not_parse_this_reference_body=True))
        hidden_bytes = Path(hidden_path).read_bytes()
        seal = read(dev / 'seal-manifest.json')
        seal['artifact_files']['source_rows'] = dict(path=source_path, bytes=Path(source_path).stat().st_size, sha256=sha(source_path))
        seal['artifact_files']['references'] = dict(path=hidden_path, bytes=len(hidden_bytes), sha256=sha(hidden_path))
        if failure == 'development_seal': seal['encoder_executed'] = True
        seal_path = input_file('development-seal.json', seal)
        asset_path = input_file('assets.json', {'384': {'snapshot_path': '/fixture/snapshot'}, '768': dict(
            manifest_path='/fixture/manifest', expected_manifest_sha256='c' * 64,
            model_directory='/fixture/model', code_directory='/fixture/code')})
        extension_root = work / 'extensions'; extension_root.mkdir()
        manifest = dict(inputs=inputs, extensions={}, producer_pins={}, parent_manifest=parent_path,
                        parent_extension_root=str(work / 'r4'), training_bank=bank_path, prior_sources=prior_path,
                        development_sources=source_path, development_seal=seal_path,
                        independent_training_sources=expected_path, asset_config=asset_path, recipe_seal='d' * 64)
        plan = dict(driver.FIXED, input_sha256=inputs)
        plan_path = work / 'plan.json'; save(plan_path, plan); manifest['plan_sha256'] = sha(plan_path)
        manifest_path = work / 'manifest.json'; save(manifest_path, manifest)
        args = SimpleNamespace(dependency_root=work / 'dependency', extension_root=extension_root,
                               manifest=manifest_path, plan=plan_path, output=results, phase='preparation')
        def vectors(shape, width, kind):
            check((results / 'pre-native-source-seal.json').is_file(), 'source seal exists before native double ' + kind)
            if kind == 'development':
                check((results / f'production-{width}.json').is_file(), 'completed TRAIN native evidence retained before dependentDEV')
            events.append((kind, width))
            if failure == 'development_forward' and kind == 'development':
                raise ValueError('injected development forward refusal')
            offset = 0 if kind == 'train' else 1000
            rows = []
            for index, row in enumerate(shape['source_inputs']):
                theta = (offset + index + 1) / 10000
                vector = [math.cos(theta), math.sin(theta)] + [0.] * (width - 2)
                rows.append(dict(id=row['id'], source_sha256=builder.text_sha(row['source_text']),
                                 vector=vector, token_count=4, token_input_sha256='e' * 64))
            return dict(vectors=rows, production_sha256=builder.digest(rows), elapsed_seconds=1.,
                        explicit_test_double=True, qualified=False, admitted=False)
        def train_produce(plan, *, dimension, asset_config, source_artifact_directory, batch_size, max_seconds):
            check(batch_size == 4 and 0 < max_seconds <= 600, 'fixed TRAIN producer execution bounds')
            check(plan['sealed_recipe_sha256'] == manifest['recipe_seal'], 'TRAIN plan uses own recipe seal')
            return vectors(plan['shape_plan'], dimension, 'train')
        def dev_produce(plan, *, dimension, asset_config, source_artifact_directory, batch_size, max_seconds):
            check(batch_size == 4 and 0 < max_seconds <= 600, 'fixed DEV producer execution bounds')
            check(plan['sealed_recipe_sha256'] == seal['sealed_recipe_sha256']
                  == '14f8a6b363580c6ed1e5556e8a5990cc187f83dfdb1b0e59ca109e57903f1474', 'DEV keeps proper separately sealed14f8 recipe')
            return vectors(plan['shape_plan'], dimension, 'development')
        def dev_assemble(plan, report, *, dimension):
            check((results / f'development-production-{dimension}.json').is_file(), 'completed DEV report persisted before dependentassembly')
            lookup = {r['source_sha256']: r['vector'] for r in report['vectors']}
            rows = [dict(row, input=lookup[builder.text_sha(row['source_text'])]) for row in plan['shape_plan']['source_rows']]
            cache = [dict(id='clause:' + builder.text_sha(row['source_text']), source_text=row['source_text'], input=row['input']) for row in rows]
            contexts = clauses.build_source_contexts(plan['shape_plan']['source_rows'], cache)
            return dict(rows=rows, clause_cache=cache, source_contexts=contexts,
                        qualified=False, admitted=False, targets_attached=False, explicit_test_double=True)
        train_stub = SimpleNamespace(source_plan=train_source.source_plan, produce_width=train_produce,
                                     validate_report=lambda plan, report: len(report['vectors'][0]['vector']))
        dev_stub = SimpleNamespace(source_plan=dev_source.source_plan, produce_width=dev_produce,
                                   assemble=dev_assemble, digest=builder.digest)
        module_map = dict(authored_training_paraphrases=builder.original,
                          training_paraphrase_source_inputs=train_stub,
                          normative_wording_training_sources=builder,
                          prospective_wording_source_inputs=dev_stub)
        def extension(root, rel, canonical, pins): return module_map[canonical.rsplit('.', 1)[1]]
        ctx = dict(helpers=SimpleNamespace(save=save, extension=extension),
                   donor=dict(codec=dict(schema='typed-json-lexical/v1', target_vocabulary=list(builder.base.VOCABULARY))),
                   validate_rule=lambda target: dict(valid=True, canonical_ir=target),
                   owners=dict(clause_source_context=clauses))
        def load_context(previous):
            check(not results.exists(), 'context validation precedes output creation')
            return ctx
        def load_producers(previous, ctx):
            check(not results.exists(), 'producer initialization precedes output creation')
        fresh_stub = SimpleNamespace(load_context=load_context, load_producers=load_producers)
        def initialize(owner, previous, validate):
            value = owner.load_context(previous); owner.load_producers(previous, value)
            before = validate(value); results.mkdir(); return value, before
        old_stub = SimpleNamespace(initialize_preparation=initialize, source_inventory=lambda args, manifest: {},
                                   prior_vectors=lambda manifest, d: ({(1.,) + (0.,) * (d - 1)}, 1))
        def helpers(path, wanted, name): return old_stub if name == '_normative_source_r4' else fresh_stub
        original_loads = json.loads
        def load_without_labels(value, *a, **kw):
            check(value != hidden_bytes and value != hidden_bytes.decode(), 'future reference JSON is not parsed')
            return original_loads(value, *a, **kw)
        package = sys.modules[driver.PREFIX[:-1]]
        prior_attributes = {name: getattr(package, name, None) for name in module_map}
        try:
            with patch.object(driver, 'helper', helpers), patch.object(json, 'loads', load_without_labels), redirect_stdout(io.StringIO()):
                try:
                    driver.execute(args)
                except ValueError as exc:
                    check(failure is not None, 'only declared fixture failures may abort')
                    if failure == 'development_forward':
                        check('injected development' in str(exc), 'native refusal remains visible')
                        check((results / 'production-384.json').is_file() and (results / 'dimension-inputs-384.json').is_file(), 'completed TRAIN artifacts remain after failedDEV')
                        check(not (results / 'summary.json').exists(), 'partial phase receives no complete summary')
                    elif failure == 'development_seal':
                        check('source seal differs' in str(exc) and not events, 'invalid lifecycle seal refuses before any native call')
                    else: raise
                else:
                    check(failure is None, 'declared failure cannot complete')
                    check(events == [('train', 384), ('development', 384), ('train', 768), ('development', 768)], 'sequential exact native width/kind order')
                    summary = read(results / 'summary.json')
                    check(summary['complete'] and not summary['development_reference_json_parsed'], 'complete diagnostic summary preserves label barrier')
                    check(summary['qualified'] is False and summary['admitted'] is False and summary['training_executed'] is False, 'preparation gives no fit or proof admission')
                    check(read(results / 'prior-source-inventories.json')['prospective_development_sources'] == read(source_path), 'future source exclusion retained in TRAIN inventory')
                    check('new_training_wordings' not in read(results / 'prior-source-inventories.json'), 'self-generatedTRAIN exclusion removed only while exact independently sealedTRAIN replay is enforced')
                    for d in (384, 768):
                        data = read(results / f'dimension-inputs-{d}.json')
                        check(len(data['rows']) == 48 and len(data['clause_cache']) == 180 and len(data['source_contexts']) == 48, 'unchanged216 TRAIN source contract ' + str(d))
                        data = read(results / f'development-inputs-{d}.json')
                        check(len(data['rows']) == len(data['clause_cache']) == len(data['source_contexts']) == 60, 'complete60 DEV contexts ' + str(d))
        finally:
            for name, value in prior_attributes.items():
                if value is None: delattr(package, name)
                else: setattr(package, name, value)


before = sha(driver_path)
run_fixture()
run_fixture('development_forward')
run_fixture('development_seal')
check(sha(driver_path) == before, 'driver bytes unchanged during independent fixture')
result = dict(schema='normative-preparation-driver-independent-controls/v1', all_checks_passed=True,
              checks=len(checks), checks_passed=checks, driver=dict(path=str(driver_path), sha256=before),
              reviewed_at=datetime.now(timezone.utc).isoformat(), actual_encoders_executed=False,
              head_models_loaded=False, actual_training=False, qualified=False, admitted=False,
              fixture_scope='Genuine complete authoredTRAINbuilder and source/context shape APIs; inherited authenticated setup/nativeencoders/evidencevalidators are explicit doubles.')
destination = OUT / 'preparation_driver_independent_checks.json'
with destination.open('x') as stream: json.dump(result, stream, sort_keys=True, indent=2); stream.write('\n')
print(json.dumps(dict(checks=len(checks), passed=True, source_sha256=before, output=str(destination)), sort_keys=True))
