"""Verify retained real baseline runs, unchanged preimages, and fixed population."""
from pathlib import Path
import hashlib,json,importlib.util
HERE=Path(__file__).resolve().parent;PAPER=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 summary=json.loads((HERE/'baseline_correction_summary.json').read_text());spec=importlib.util.spec_from_file_location('admission',HERE/'code/unchanged_baseline_admission.py');A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
 originals=json.loads((HERE/'qualification/original_visible_nodes.json').read_text())['nodes'];recovered=json.loads((HERE/'qualification/source_recovery_all16.json').read_text());sources={x['task_id']:x for x in recovered['sources']}
 old=[json.loads(l) for l in (HERE.parent/'benchmark/tasks.jsonl').read_text().splitlines() if l.strip()];new=[json.loads(l) for l in (PAPER/'benchmark/tasks.jsonl').read_text().splitlines() if l.strip()];assert len(old)==len(new)==183
 before={r['task_id']:r for r in old};after={r['task_id']:r for r in new};assert before.keys()==after.keys();assert len(summary['baseline_qualifications'])==16
 total=0;skips=0
 for task,q in summary['baseline_qualifications'].items():
  folder=HERE/'executions'/task;inventory=json.loads((folder/'source_inventory.json').read_text());c=json.loads((folder/'collect.observation.json').read_text());e=json.loads((folder/'run.observation.json').read_text());r=json.loads((folder/'report.json').read_text())
  assert inventory['before_sha256']==digest(inventory['before']);assert inventory['after_sha256']==digest(inventory['after'])
  assert sha(folder/'source_inventory.json')==q['source_inventory_sha256'];assert sha(folder/'collect.observation.json')==q['collection_report_sha256'];assert sha(folder/'run.observation.json')==q['execution_report_sha256'];assert sha(folder/'report.json')==q['command_report_sha256'];assert r['capture_plugin_sha256']==sha(HERE/'code/baseline_capture.py')
  for run in r['runs']:
   assert run['returncode']==0 and not run['timed_out'];argv=run['argv'];assert '--network=none' in argv and '--read-only' in argv and q['image'] in argv;assert run['container_id']
   for stream in ['stdout','stderr']:assert sha(folder/Path(run[stream]['path']).name)==run[stream]['sha256']
  actual=A.qualify(c,e,source_before=inventory['before'],source_after=inventory['after'],collect_returncode=r['runs'][0]['returncode'],run_returncode=r['runs'][1]['returncode'])
  for key,value in actual.items():assert q[key]==value
  if originals[task]:assert c['collected']==originals[task]
  assert sources[task]['pre_fix_commit']==q['pre_fix_commit'];assert before[task]['source_snapshot']['pre_fix_commit']==q['pre_fix_commit'];assert digest(c['collected'])==q['collected_node_ids_sha256'];assert after[task]['baseline_qualification_correction']['qualification']==q
  assert after[task]['baseline_qualification_correction']['historical_baseline']==before[task]['baseline']
  for key in before[task]:
   if key!='baseline':assert before[task][key]==after[task][key]
  total+=actual['executed_passed_count'];skips+=actual['upstream_skipped_count']
 for task,row in before.items():
  if task not in summary['baseline_qualifications']:assert row==after[task]
 assert total==summary['actual_passed_total']==4685;assert skips==summary['upstream_skipped_total']==187
 assert sha(PAPER/'benchmark/tasks.jsonl')==sha(HERE/'benchmark/tasks.jsonl')
 print(json.dumps({'all16_unchanged_baselines_qualified':True,'actual_passed_tests':total,'upstream_skips_not_passes':skips,'population_splits_acceptance_and_source_pins_unchanged':True,'historical_receipt_retained':True,'hidden_oracles_read_or_run':False,'new_live_repair_scores':False},sort_keys=True))
if __name__=='__main__':main()
