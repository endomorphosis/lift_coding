"""Actual retained AF018 accounting plus bounded shared-interval rejection controls."""
from pathlib import Path
import copy,hashlib,importlib.util,json,math,sys
HERE=Path(__file__).resolve().parent;PAPER=HERE.parents[2];PATH=PAPER/'evaluation/aggregate_costs.py'
spec=importlib.util.spec_from_file_location('af020_nested_costs',PATH);M=importlib.util.module_from_spec(spec);sys.modules[spec.name]=M;spec.loader.exec_module(M)
T=M.load_telemetry();probe=next(r for r in M.load_jsonl(PAPER/'runs/costs/results.jsonl')if r['record_kind']=='hardware_probe')
paths=[PAPER/'runs/planning/results.jsonl',PAPER/'runs/proof_assistance/results.jsonl'];before={str(p):M.sha256_file(p)for p in paths};raw=M.load_jsonl(paths[1]);unchanged=copy.deepcopy(raw)
attribution,scans=M.shared_af018_policy_scans(raw);assert raw==unchanged and len(scans)==4 and len(attribution)==8
policy=[r for r in raw if r.get('stage')=='policy_scan'];duplicated=math.fsum(r['cost']['elapsed_seconds']for r in policy);unique=math.fsum(s['elapsed_seconds']for s in scans);assert duplicated==2*unique
usage=M.collect_all(T,probe);rows=[r for r in usage if r['task_id']=='AF-018'];setup=next(r for r in rows if r['record_id']=='AF-018:setup:measure.meta');children=[r for r in rows if r['phase'] in ('preparation','proof_reconstruction','validation')and M.measured_elapsed(r)is not None]
planning=M.load_jsonl(paths[0]);raw_total=math.fsum((r.get('cost')or{}).get('elapsed_seconds')or 0.0 for r in planning+raw);expected_unique_child=raw_total-unique;observed_unique_child=math.fsum(M.measured_elapsed(r)for r in children)
# Native ledger cells round to nanoseconds; raw perf_counter values remain in attribution metadata.
assert math.isclose(expected_unique_child,observed_unique_child,abs_tol=5e-9,rel_tol=0)
outer,_=M.meta_elapsed(PAPER/'receipts/snapshots/AF-018/logs/measure.meta.json');assert math.isclose(M.measured_elapsed(setup),outer-observed_unique_child,abs_tol=1e-9,rel_tol=0)
assert math.isclose(math.fsum(M.measured_elapsed(r)or 0 for r in rows),outer,abs_tol=1e-9,rel_tol=0)
assert len(set(r['record_id']for r in usage))==len(usage)
assert len([r for r in children if r['experiment_arm']=='shared_policy_fixture_scan'])==4
leanstral=next(r for r in rows if r['record_id']=='AF-018:leanstral:proof_reconstruction');assert M.measured_elapsed(leanstral)is None
assert len(leanstral['shared_elapsed_attribution'])==4 and leanstral['row_count']==19
controls=[]
for kind in ['unequal_duration','different_source','different_goal','duplicate_arm','wrong_tool','missing_pair','different_status']:
 bad=copy.deepcopy(raw);idx=next(i for i,r in enumerate(bad)if r.get('stage')=='policy_scan');r=bad[idx]
 if kind=='unequal_duration':r['cost']['elapsed_seconds']+=0.000001
 elif kind=='different_source':r['detail']['source_sha256']='0'*64
 elif kind=='different_goal':r['goal_id']='constructed-other-goal'
 elif kind=='duplicate_arm':bad.append(copy.deepcopy(r))
 elif kind=='wrong_tool':r['identities']['tool']='constructed-unreviewed-tool'
 elif kind=='missing_pair':bad.pop(idx)
 elif kind=='different_status':r['execution_status']='constructed-other-status'
 try:M.shared_af018_policy_scans(bad)
 except ValueError:controls.append(kind)
 else:raise AssertionError(kind)
bad=copy.deepcopy(children[0]);bad['elapsed_seconds']['value']=outer+1
try:M.collect_command_setup(T,'AF-018','receipts/snapshots/AF-018/logs/measure.meta.json','planning_assistance','regression',nested_usage=[bad])
except ValueError:controls.append('nested_exceeds_outer')
else:raise AssertionError('invalid nested interval accepted')
assert before=={str(p):M.sha256_file(p)for p in paths}
print(json.dumps({'ok':True,'outer_seconds':outer,'raw_nested_seconds_with_duplicated_scans':raw_total,'duplicated_scan_seconds':duplicated,'unique_scan_seconds':unique,'unique_nested_seconds_raw':expected_unique_child,'unique_nested_seconds_ledger':observed_unique_child,'remainder_seconds':M.measured_elapsed(setup),'af018_total_seconds':math.fsum(M.measured_elapsed(r)or 0 for r in rows),'shared_scan_pairs':4,'preserved_raw_policy_rows':8,'negative_controls':controls,'raw_inputs_unchanged':True,'usage_records':len(usage),'unavailable_leanstral_time_null':True},sort_keys=True))
