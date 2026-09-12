"""Admission requires successful actual unchanged-test execution, never a path flag."""
from collections import Counter
class BaselineAdmissionError(ValueError):pass
def qualify(collection,execution,*,source_before,source_after,collect_returncode,run_returncode):
 if source_before != source_after:raise BaselineAdmissionError('baseline_source_changed')
 if collect_returncode != 0 or run_returncode != 0:raise BaselineAdmissionError('nonzero_command_exit')
 if collection.get('exitstatus') != 0 or execution.get('exitstatus') != 0:raise BaselineAdmissionError('pytest_nonzero_exit')
 if collection.get('collection_errors') or execution.get('collection_errors'):raise BaselineAdmissionError('collection_errors')
 nodes=collection.get('collected',[]);actual=execution.get('collected',[])
 if not nodes or len(nodes)!=len(set(nodes)):raise BaselineAdmissionError('empty_or_duplicate_collection')
 if nodes!=actual:raise BaselineAdmissionError('collection_execution_mismatch')
 reports=execution.get('reports',[])
 if any(r.get('nodeid') not in set(nodes) for r in reports):raise BaselineAdmissionError('unknown_report_node')
 if any(r.get('outcome')=='failed' for r in reports):raise BaselineAdmissionError('failed_test_or_lifecycle')
 by={n:[] for n in nodes}
 for r in reports:by[r['nodeid']].append(r)
 passed=[];skipped=[]
 for n,rs in by.items():
  if any(r.get('outcome') not in {'passed','skipped'} or r.get('when') not in {'setup','call','teardown'} for r in rs):raise BaselineAdmissionError('unknown_test_outcome')
  counts=Counter(r['when'] for r in rs)
  if any(v>1 for v in counts.values()):raise BaselineAdmissionError('duplicate_lifecycle_report')
  if any(r['outcome']=='skipped' for r in rs):
   if not any(r['when']=='teardown' and r['outcome']=='passed' for r in rs):raise BaselineAdmissionError('skipped_test_teardown_unverified')
   skipped.append(n)
  elif len(rs)==3 and set(counts)=={'setup','call','teardown'} and all(r['outcome']=='passed' for r in rs):passed.append(n)
  else:raise BaselineAdmissionError('incomplete_executed_lifecycle')
 if not passed:raise BaselineAdmissionError('zero_actual_passes')
 return {'schema':'unchanged-baseline-admission/v1','admitted':True,'collected_count':len(nodes),'executed_passed_count':len(passed),'upstream_skipped_count':len(skipped),'skips_counted_as_passes':False,'nonempty_actual_baseline':True,'unchanged_source':True}
