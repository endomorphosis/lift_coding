"""Recheck the frozen preparation and wrapper controls without acquiring resources."""
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path('/home/barberb/lift_coding'); P = ROOT / 'external/ipfs_datasets'
R = P / 'workspace/test-logs/decoder-normative-wording-r2-20261006'
OUT = ROOT / 'artifacts/autoencoder-wording-fit-20261006/review'
checks = []
artifacts = {}


def check(value, name):
    if not value: raise AssertionError(name)
    checks.append(name)


def binding(path):
    path = Path(path).resolve(); digest = hashlib.sha256(); size = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block); size += len(block)
    return dict(sha256=digest.hexdigest(), bytes=size)


def retain(path, wanted=None):
    path = Path(path).resolve(); record = binding(path)
    if wanted is not None: check(record['sha256'] == wanted, 'frozen file ' + str(path))
    artifacts[str(path)] = record
    return record


manifest_path = R / 'preparation-manifest.json'; plan_path = R / 'preparation-plan.json'
manifest = json.loads(manifest_path.read_bytes()); plan = json.loads(plan_path.read_bytes())
retain(manifest_path); retain(plan_path, manifest['plan_sha256'])
check(plan['input_sha256'] == manifest['inputs'], 'plan retains exact full input map')
for path, wanted in manifest['inputs'].items(): retain(path, wanted)
for path, wanted in manifest['producer_pins'].items(): retain(path, wanted)
for relative, wanted in manifest['extensions'].items(): retain(R / 'experiment-source' / relative, wanted)
for filename in ('run_guardian.py', 'run_reserved.py', 'adopt_shared_scheduler.py', 'lazy_scheduler_adoption.py', 'owned_lease_watchdog.py', 'seal_preparation.py'):
    retain(R / filename)
spec = importlib.util.spec_from_file_location('_readiness_preparation', R / 'experiment-source/scripts/ops/autoencoder/prepare_normative_wording_sources.py')
preparation = importlib.util.module_from_spec(spec); spec.loader.exec_module(preparation)
preparation.validate_plan(plan)
check(preparation.FIXED['max_seconds_total'] == 1400 and preparation.FIXED['max_seconds_per_encoder'] == 600,
      'bounded cooperative preparation deadlines')
check(preparation.FIXED['context_tokens'] == 512 and preparation.FIXED['batch_size'] == 4 and preparation.FIXED['workers'] == 1,
      'fixed source context batch and worker count')
check(preparation.FIXED['bridge_names'] == [] and not preparation.FIXED['legal_ir_evaluate_provers']
      and not preparation.FIXED['metric_disk_cache_used'], 'bridge/prover/metric-cache flags remain disabled')
dev_seal = json.loads(Path(manifest['development_seal']).read_bytes())
check(dev_seal['sealed_recipe_sha256'] == '14f8a6b363580c6ed1e5556e8a5990cc187f83dfdb1b0e59ca109e57903f1474',
      'separately authored development recipe14f8 retained')
check(dev_seal['encoder_executed'] is False and dev_seal['training_executed'] is False
      and dev_seal['qualified'] is False and dev_seal['admitted'] is False, 'development lifecycle seal precedes numeric fits')
references_path = str(Path(dev_seal['artifact_files']['references']['path']).resolve())
check(references_path not in manifest['inputs'], 'new development reference bodies are not preparation inputs')
check(binding(dev_seal['artifact_files']['source_rows']['path'])['sha256'] == dev_seal['artifact_files']['source_rows']['sha256'],
      'development source handoff exact file binding')
old = P / 'workspace/test-logs/decoder-training-paraphrases-r4-20261004'
for filename in ('adopt_shared_scheduler.py', 'lazy_scheduler_adoption.py', 'owned_lease_watchdog.py'):
    check((R / filename).read_bytes() == (old / filename).read_bytes(), 'reused unchanged guardian owner ' + filename)
def functions(path):
    return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(Path(path).read_text()).body if isinstance(n, ast.FunctionDef)}
current_functions = functions(R / 'run_reserved.py'); prior_functions = functions(old / 'run_reserved.py')
for name in ('resource_owner', 'capture_owned_child', 'cleanup_owned_group'):
    check(current_functions[name] == prior_functions[name], 'unchanged owned resource/process function ' + name)
guard_text = (R / 'run_reserved.py').read_text()
check("'preparation': ('prepare_normative_wording_sources.py',100_000_000,4096,1500)" in guard_text,
      'preparation outer bound100MB/4096MiB/1500seconds')
for piece in ("cpu_slots=1", "child_process_slots=1", "watchdog.start()", "watchdog.assert_healthy()",
              "HF_HUB_OFFLINE='1'", "TRANSFORMERS_OFFLINE='1'", "CUDA_VISIBLE_DEVICES=''", "OMP_NUM_THREADS='1'"):
    check(piece in guard_text, 'guardian retains ' + piece)
source = P / 'workspace/test-logs/ui-modal-coverage-20261002/validation-source-r2'
owner_path = P / 'workspace/test-logs/native4096-four-width-20261004/resource-cap/autoencoder_daemon_resources.py'
scheduler_path = source / 'ipfs_datasets_py/optimizers/logic_theorem_optimizer/resource_scheduler.py'
retain(owner_path, 'b00d2752ba852fe73760bba4fbd51b0e845742c3527642606a2a77ed9f8f5e2c')
retain(scheduler_path, 'a418e84f70ed8509ba0518feea69e7a8c27865139f83b6c81349eefdfd5893a4')
check('MAX_STORAGE_BYTES = 145_000_000_000' in owner_path.read_text(), 'retained145GB cap unchanged')
spec = importlib.util.spec_from_file_location('_readiness_outer_wrapper', R / 'run_guardian.py')
wrapper = importlib.util.module_from_spec(spec); spec.loader.exec_module(wrapper)
with tempfile.TemporaryDirectory(prefix='independent-readiness-wrapper-') as directory:
    temporary = Path(directory); wrapper.R = temporary
    reviewed_file = temporary / 'reviewed-artifact'; reviewed_file.write_bytes(b'bounded reviewed bytes')
    good = dict(passed=True, findings=[], phase='preparation', run_root=str(temporary.resolve()), dimension=None,
                artifacts={str(reviewed_file): binding(reviewed_file)})
    cases = [('phase', 'training'), ('run_root', str(temporary / 'other')), ('dimension', 384),
             ('passed', False), ('findings', ['unresolved'])]
    for index, (key, value) in enumerate(cases):
        bad = deepcopy(good); bad[key] = value
        review = temporary / f'bad-{index}.json'; review.write_text(json.dumps(bad))
        argv = ['run_guardian.py', '--phase', 'preparation', '--attempt', 'attempt-' + str(index), '--review', str(review)]
        with patch.object(sys, 'argv', argv), patch.object(wrapper.subprocess, 'run', side_effect=AssertionError('subprocess started before clean readiness')):
            try: wrapper.main()
            except ValueError: checks.append('wrapper scope/cleanliness refuses ' + key)
            else: raise AssertionError('wrapper accepted incorrect ' + key)
    review = temporary / 'good.json'; review.write_text(json.dumps(good))
    argv = ['run_guardian.py', '--phase', 'preparation', '--attempt', 'attempt-good', '--review', str(review)]
    seen = []
    def child(command, **kwargs): seen.append(command); return SimpleNamespace(returncode=0)
    with patch.object(sys, 'argv', argv), patch.object(wrapper.subprocess, 'run', child), redirect_stdout(io.StringIO()):
        try: wrapper.main()
        except SystemExit as exc: check(exc.code == 0, 'wrapper retains successful actual outer returncode from declared test double')
    check(len(seen) == 1 and seen[0][2:] == ['--phase', 'preparation', '--attempt', 'attempt-good'], 'wrapper delegates exact reviewed phase')
    check(json.loads((temporary / 'attempt-good-guardian-exit.json').read_text())['returncode'] == 0, 'wrapper saves outer exit receipt')
control_path = OUT / 'preparation_driver_independent_checks.json'; controls = json.loads(control_path.read_bytes())
check(controls['all_checks_passed'] is True and controls['checks'] == 1618, 'full driver pure controls pass')
check(controls['driver']['sha256'] == manifest['extensions']['scripts/ops/autoencoder/prepare_normative_wording_sources.py'],
      'driver fixtures test exactly frozen source')
for filename in ('check_preparation_driver.py', 'preparation_driver_independent_checks.json', 'check_native_adapter.py',
                 'native_adapter_independent_checks.json', 'native_adapter_review.json', 'native_adapter_tests_final.xml',
                 'check_preparation_readiness.py'):
    retain(OUT / filename)
report = dict(schema='normative-wording-phase-readiness/v1', passed=True, findings=[], phase='preparation', dimension=None,
              run_root=str(R.resolve()), reviewed_at=datetime.now(timezone.utc).isoformat(), artifacts=artifacts,
              checks=len(checks), checks_passed=checks, manifest_inputs=len(manifest['inputs']),
              producer_pins=len(manifest['producer_pins']), frozen_extensions=len(manifest['extensions']),
              driver_pure_checks=1618, native_adapter_tests=35, native_adapter_independent_checks=581,
              resource_policy=dict(storage_bytes=100000000, memory_mib=4096, cpu_slots=1, child_process_slots=1,
                                   outer_seconds=1500, driver_seconds=1400, native_operation_seconds=600,
                                   campaign_storage_cap_bytes=145000000000, admission_performed=False,
                                   ownership_scope='owned lease/process group only; no foreign claim release or scheduler reset'),
              source_role_policy=dict(train_paragraphs=48, train_clause_occurrences=180, train_unique_sources=216,
                                      development_single_sources=60, unique_native_sources_per_width=276,
                                      development_recipe_sha256=dev_seal['sealed_recipe_sha256'],
                                      development_reference_bodies_parsed=False, original_target_meanings_previously_exposed=True,
                                      pristine_semantic_holdout_claimed=False),
              vector_inventory_scope=dict(complete_all_available_prior_vector_coverage=False,
                                         checked_frozen_descriptor_count_by_width={k:len(v) for k,v in manifest['prior_vector_rows'].items()},
                                         known_composition64_native384_native768_available=True,
                                         known_composition64_vectors_compared=False,
                                         known_composition64_source_exclusion_complete=True,
                                         historical_composition_native768_profile_limit=8192,
                                         historical_composition_max_actual_tokens=37,
                                         historical_profile_relabelled=False,
                                         explanation='Composition bundle rows store numeric vectors under vector rather than the inherited numeric-input inventory contract. Full64 source exclusion is checked; no claim of complete prior-vector comparison is made.'),
              resolved_findings=['CompletedTRAIN report/context artifacts now persist before dependentDEV encoding; completedDEV report/inputs persist before combined overlap refusal.',
                                 'Outer wrapper now binds reviewed phase/width/run-root and streams1MiB artifact hashing.'],
              limitations=['Guarded native execution is not performed by this review; actual CPU/RSS/storage/lease admission and native token receipts must be recorded by the launched phase.',
                           'Driver native/setup fixture controls and adapter unit checks use explicit test doubles; full actual native embedding fidelity is not established here.',
                           'Authenticated historical dependency snapshot is used for numerical preparation; this does not measure current canonical compiler fidelity.'],
              models_loaded=False, actual_encoder_forward=False, training_executed=False, qualified=False, admitted=False,
              lake_executed=False, checkpoint_promoted=False, downloads_performed=False)
destination = OUT / 'preparation_readiness.json'
with destination.open('x') as stream: json.dump(report, stream, sort_keys=True, indent=2); stream.write('\n')
print(json.dumps(dict(path=str(destination), sha256=binding(destination)['sha256'], passed=True, checks=len(checks),
                     artifacts=len(artifacts), wrapper_sha256=artifacts[str(R / 'run_guardian.py')]['sha256']), sort_keys=True))
