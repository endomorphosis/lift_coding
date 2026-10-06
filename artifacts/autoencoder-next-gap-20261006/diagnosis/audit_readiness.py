"""Independent saved-artifact and cold-driver review; no model/package imports."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET

W = Path('/home/barberb/lift_coding')
P = W / 'external/ipfs_datasets'
R = P / 'workspace/test-logs/decoder-paraphrase-modality-margins-r2-20261006'
A = W / 'artifacts/autoencoder-next-gap-20261006'
OUT = A / 'diagnosis'
SCRIPT = 'scripts/ops/autoencoder/diagnose_paraphrase_modality_margins.py'
TEST = 'tests/unit/logic/formalization/autoencoder/test_paraphrase_modality_margins.py'
ARTIFACTS = {}
CHECKS = []


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def retain(path, expected=None):
    path = Path(path).resolve()
    value = file_sha(path)
    assert expected is None or value == expected, 'Changed reviewed artifact: ' + str(path)
    ARTIFACTS[str(path)] = {'sha256': value, 'bytes': path.stat().st_size}
    return path


def read(path, expected=None):
    return json.loads(retain(path, expected).read_bytes())


def check(value, description):
    assert value, description
    CHECKS.append(description)


manifest = read(R / 'diagnostic-manifest.json')
plan = read(R / 'diagnostic-plan.json', manifest['plan_sha256'])
check(manifest['schema'] == 'paraphrase-modality-margin-diagnostic-manifest/v1', 'Exact manifest schema')
check(plan['input_sha256'] == manifest['inputs'], 'Exact plan input closure')
for name, expected in manifest['inputs'].items():
    retain(name, expected)
for relative, expected in manifest['extensions'].items():
    retain(R / 'experiment-source' / relative, expected)
check(plan['dimensions'] == [384, 768] and plan['roles'] == ['selected']
    and plan['arms'] == ['paraphrase-modality-zero', 'paraphrase-modality-ce']
    and plan['panel_count'] == 4, 'Four unique selected endpoints')
check(plan['context_tokens'] == plan['output_tokens'] == 512 and plan['temperature'] == 0
    and plan['vocabulary_size'] == 32 and plan['batch_size'] == 8
    and plan['optimizer_steps'] == 0 and plan['workers'] == 1,
    'Fixed limits and zero-training full-vocabulary observation')
check(plan['bridge_names'] == [] and plan['legal_ir_evaluate_provers'] is False
    and plan['metric_disk_cache_used'] is False, 'Warm decoder diagnostic telemetry scope')

tests = read(A / 'runner_review/tests-r2-receipt.json')
for relative, expected in tests['source_sha256'].items():
    retain(P / relative, expected)
    check(manifest['extensions'][relative] == expected, 'Tests bind exact frozen source: ' + relative)
retain(A / 'runner_review/tests-r2.log', tests['tests_log_sha256'])
xml = retain(A / 'runner_review/tests-r2.xml', tests['tests_xml_sha256'])
case_nodes = ET.parse(xml).getroot().findall('.//testcase')
check(tests['returncode'] == 0 and len(case_nodes) == 73
    and all(not any(node.find(k) is not None for k in ('failure','error','skipped')) for node in case_nodes),
    '73 pure driver tests completed with no failures or skips')
check(any(node.attrib.get('name') == 'test_import_is_cold_and_executes_no_package_or_torch' for node in case_nodes),
    'Pure suite includes guarded cold import')

training = read(manifest['training_manifest'])
style = read(manifest['style_manifest'])
summary = read(manifest['style_summary'])
read(manifest['style_plan'], style['plan_sha256'])
check(summary['complete'] is True and summary['all_predictions_persisted_before_reference_load'] is True,
    'Completed source-first predecessor evaluation')
expected_keys = {f'{d}-{a}-selected' for d in plan['dimensions'] for a in plan['arms']}
check(set(manifest['archived_predictions']) == expected_keys, 'Exact four archived selected prediction bindings')
states = []
for dimension in plan['dimensions']:
    terminal = manifest['training_terminals'][str(dimension)]
    check(read(terminal['child_exit'])['returncode'] == 0
        and read(terminal['resources_final'])['status'] == 'released', 'Released completed width: ' + str(dimension))
    width_summary = read(manifest['training_summaries'][str(dimension)])
    for item in width_summary['runs']:
        run = read(item['summary_path'], item['summary_sha256'])
        check(run['dimension'] == dimension and run['arm'] in plan['arms'] and run['budget_completed'] is True
            and run['seed'] == 1729, 'Authenticated completed endpoint: ' + str(dimension) + '-' + run['arm'])
        selected, last = run['states']['selected'], run['states']['last-attempt']
        selected_state = read(selected['path'], selected['sha256'])
        last_state = read(last['path'], last['sha256'])
        check(selected['tensor_sha256'] == last['tensor_sha256'] == selected_state['tensor_sha256'] == last_state['tensor_sha256']
            and selected_state['weights_sha256'] == digest(selected_state['model_state'])
            and last_state['weights_sha256'] == digest(last_state['model_state'])
            and selected_state['model_state'] == last_state['model_state'], 'Selected/last alias verified without model restoration')
        archived_ref = manifest['archived_predictions'][f'{dimension}-{run["arm"]}-selected']
        panel = [v for v in summary['panels'] if (v['dimension'],v['arm'],v['role']) == (dimension,run['arm'],'selected')]
        check(len(panel) == 1 and panel[0]['state_ref'] == selected and panel[0]['predictions_ref'] == archived_ref,
            'Exact predecessor panel-to-state binding')
        prediction = read(archived_ref['path'], archived_ref['sha256'])
        check(prediction['model_tensor_sha256'] == selected['tensor_sha256'] and len(prediction['predictions']) == 48
            and prediction['generation_reference_access'] is False and prediction['generation_temperature'] == 0
            and prediction['max_target_tokens'] == 512, 'Archived source-only temperature-zero policy')
        source = read(manifest['source_inputs'][str(dimension)])
        check(source['targets_attached'] is False and source['target_access'] is False
            and all(set(row) == {'id','source_text','input'} for row in source['rows'])
            and source['inputs_sha256'] == digest({k:v for k,v in source.items() if k != 'inputs_sha256'})
            and prediction['source_rows_sha256'] == digest(source['rows'])
            and prediction['source_contexts_sha256'] == digest(source['source_contexts']),
            'Authenticated closed cached source-only rows and contexts')
        states.append({'dimension':dimension,'arm':run['arm'],'selected_tensor_sha256':selected['tensor_sha256']})

# Inspect the existing owner's actual FALSE inheritance without importing it.
auto = 'ipfs_datasets_py/logic/formalization/autoencoder/'
core_candidates = [p for p in training['producer_pins'] if p.endswith('/'+auto+'decoder_distillation_experiment.py')]
core_path = retain(core_candidates[0], training['producer_pins'][core_candidates[0]])
core_tree = ast.parse(core_path.read_text())
core_false = next(n.value for n in core_tree.body if isinstance(n,ast.Assign)
    and any(isinstance(t,ast.Name) and t.id == 'FALSE' for t in n.targets))
owner_false = {kw.arg:ast.literal_eval(kw.value) for kw in core_false.keywords}
boundary_candidates = [p for p in training['producer_pins'] if p.endswith('/'+auto+'generated_boundary_training.py')]
boundary_path = retain(boundary_candidates[0], training['producer_pins'][boundary_candidates[0]])
boundary_tree = ast.parse(boundary_path.read_text())
boundary_false = next(n.value for n in boundary_tree.body if isinstance(n,ast.Assign)
    and any(isinstance(t,ast.Name) and t.id == 'FALSE' for t in n.targets))
owner_false.update({kw.arg:ast.literal_eval(kw.value) for kw in boundary_false.keywords})
observer_candidates = [p for p,h in training['producer_pins'].items()
    if p.endswith('/'+auto+'generated_scalar_observation.py') and h == plan['observer_sha256']]
check(bool(observer_candidates), 'Existing tested observer pin in training producer closure')
for path in observer_candidates:
    retain(path, plan['observer_sha256'])
driver = R / 'experiment-source' / SCRIPT
tree = ast.parse(driver.read_text())
trace_flags = ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)
    and any(isinstance(t,ast.Name) and t.id == 'TRACE_FALSE_FLAGS' for t in n.targets)))
check(set(trace_flags) == set(owner_false) and all(owner_false[k] is False for k in trace_flags),
    'Trace false flags match real frozen owner rather than fabricated outer flags')

published_path = P / 'docs/implementation/reports/evidence/decoder-paraphrase-modality-20261004/manifest.json'
published = read(published_path)
blob = subprocess.check_output(['git','show','60f5c2951ac34231f05b54e50f2725296871c5b9:'+str(published_path.relative_to(P))],cwd=P)
check(hashlib.sha256(blob).hexdigest() == file_sha(published_path), 'Predecessor publication manifest matches published Git commit')
archive_hash = hashlib.sha256(); archive_bytes = 0
for index, part in enumerate(published['archive_parts'], 1):
    path = retain(published_path.parent / part['path'], part['sha256'])
    check(path.stat().st_size == part['bytes'] and part['path'].endswith('part-'+str(index).zfill(3)), 'Exact ordered publication archive part')
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):
            archive_hash.update(block);archive_bytes += len(block)
check(published['archive']['bytes'] == archive_bytes and published['archive']['sha256'] == archive_hash.hexdigest(), 'Whole predecessor logical archive authenticated')
for name, ref in manifest['archived_predictions'].items():
    member = published['original_artifact_archive_paths'][ref['path']]
    check(published['members'][member]['sha256'] == ref['sha256'], 'Archived predictions match published member: '+name)

code = '''import builtins,importlib.util,sys
original=builtins.__import__
def guarded(name,*args,**kwargs):
    if name == 'torch' or name.startswith('ipfs_datasets_py'):
        raise RuntimeError('forbidden package/model import during independent cold preflight')
    return original(name,*args,**kwargs)
builtins.__import__=guarded
spec=importlib.util.spec_from_file_location('_independent_frozen_driver',sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.validate_plan(module.FIXED)
assert module.FIXED['panel_count']==4
assert not any(k == 'torch' or k.startswith('ipfs_datasets_py') for k in sys.modules)
print('frozen driver cold import passed without package/model imports')
'''
result = subprocess.run([sys.executable,'-B','-c',code,str(driver)],text=True,capture_output=True,check=False)
check(result.returncode == 0, 'Independent exact frozen driver cold import succeeded')
cold = OUT / 'independent-cold-preflight.json'
cold.write_text(json.dumps({'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,
    'frozen_driver_sha256':file_sha(driver),'package_imported':False,'torch_imported':False,
    'model_executed':False,'encoder_executed':False},indent=2)+'\n')
retain(cold)
retain(Path(__file__))
output = OUT / 'independent-readiness.json'
output.write_text(json.dumps({'schema':'independent-paraphrase-modality-margin-readiness/v1',
    'passed':True,'findings':[],'checks':CHECKS,'artifacts':ARTIFACTS,'states':states,
    'actual_frozen_observer_false':owner_false,'review_scope':'Saved-artifact verification, static source review, exact frozen cold import',
    'new_pure_tests':73,'inherited_owner_tests_rerun':False,'model_executed':False,
    'encoder_executed':False,'training_executed':False,'resource_ledger_written':False,
    'qualification_granted':False,'admission_granted':False},indent=2,sort_keys=True)+'\n')
print(json.dumps({'path':str(output),'sha256':file_sha(output),'checks':len(CHECKS),'artifacts':len(ARTIFACTS),'passed':True}))
