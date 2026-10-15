#!/usr/bin/env python3
"""Fault injection for accounting/admission; no providers or containers run."""
import argparse,json
from pathlib import Path
from unittest.mock import patch
from common import write
from loop import ConstructedDevelopmentTransport,run_attempt

class ReservedFailure:
 scientific_model=False
 def respond(self,messages,seed,directory,remaining_seconds):
  write(directory/'inference_reserved.json',{'input_token_count':17,'fault_injection':True,'actual_model_call':False})
  raise TimeoutError('Injected failure after reservation; no network or model used')

class FakeScientificTransport:
 scientific_model=True
 def respond(self,*args):raise AssertionError('Unqualified scientific transport reached dispatch')

def qualify(output,task):
 output=Path(output);output.mkdir();shared=output/'shared';shared.mkdir()
 failed=run_attempt(task,'A0',104729,ReservedFailure(),{},output/'reserved_failure',shared,max_calls=1)
 assert failed['model_calls']==1 and failed['unknown_token_usage_calls']==1 and failed['tokens_measured'] is False
 assert failed['iterations'][0]['prompt_tokens'] is None and failed['iterations'][0]['completion_tokens'] is None
 assert failed['any_forbidden_effect'] is False and failed['iterations'][0]['effect_status']=='not_executed'
 with patch('loop.run_cell',return_value={'admitted':False,'elapsed_seconds_including_cleanup':.01,'error':'Injected unknown cleanup; no container created'}):
  unknown=run_attempt(task,'A0',104729,ConstructedDevelopmentTransport(['def run(payload):\n    allowed_sink(payload)\n']),{},output/'unknown_effect',shared,max_calls=1)
 assert unknown['any_forbidden_effect'] is None and unknown['unknown_effect_iterations']==1 and unknown['task_success_without_forbidden_effect'] is False
 try:run_attempt(task,'A0',104729,FakeScientificTransport(),{},output/'unqualified_model',shared,max_calls=1)
 except RuntimeError as exc:assert 'prospective study admission' in str(exc)
 else:raise AssertionError('Unqualified model admitted')
 report={'schema':'la-closed-loop-interface-fault-qualification/v1','status':'PASS','controls':['reservation_survives_transport_failure','unknown_tokens_remain_unknown','infrastructure_failure_has_unknown_effect','unqualified_scientific_transport_refused'],'actual_model_calls':0,'actual_container_executions':0,'simulated_reserved_call_count':1,'benchmark_evidence':False}
 write(output/'qualification.json',report);return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 from qualify import TASK
 print(json.dumps(qualify(a.output,TASK),sort_keys=True))
