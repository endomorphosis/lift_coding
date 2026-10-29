"""Deadline feedback remains diagnostic and asks for bounded patches, never salvage."""
from pathlib import Path
import importlib.util,json,sys,tempfile,unittest
from unittest.mock import patch
STAGE=Path(__file__).resolve().parents[1];LIVE=Path.cwd().resolve();sys.path[:0]=[str(STAGE/'scripts'),str(LIVE/'scripts')]
import swissknife_visual_functional_worker as worker
import swissknife_visual_functional_llm as adapter
class TimeoutRetryContext(unittest.TestCase):
 def inspect(self,codes,expected):
  with tempfile.TemporaryDirectory()as temp:
   root=Path(temp);(root/'app.py').write_text('existing = 1\n');(root/'contracts.json').write_text('{"apps":[]}')
   task={'task_id':'SVF-TIMEOUT','kind':'repair','edit_paths':['app.py'],'checks':[['python3','app.py']]};profile={'runtimeRoot':'data/agent_supervisor/swissknife_visual_functional','appContractPath':'contracts.json','taskSpecPath':'tasks.json','humanPlanPath':'plan.md','llm':{'provider':'grok_cli','model':'grok-4.7','allowLocalFallback':False,'allowCrossProviderFallback':False,'repairReadPolicy':'inline_only'}}
   output=root/profile['runtimeRoot']/'tasks/SVF-TIMEOUT/proposal-1.json';seen=[]
   class StopBeforeProvider(Exception):pass
   def invoke(*args,**kwargs):
    body=json.loads((root/kwargs['input_paths'][0]).read_text());seen.append(body)
    self.assertEqual(body['last_repair_error']['error']['codes'],codes);self.assertEqual('smallest useful exact patch'in body['retry_instruction'],expected)
    if expected:self.assertIn('partial provider output was not applied',body['retry_instruction'])
    self.assertEqual(kwargs['predicted_files'],['app.py']);self.assertEqual((root/'app.py').read_text(),'existing = 1\n');raise StopBeforeProvider()
   with patch.object(worker,'ROOT',root),patch.object(worker,'load',return_value=(profile,{'tasks':[task]})),patch.object(worker,'assert_no_campaign_hold'),patch.object(worker,'assert_storage_available'),patch.object(worker,'workflow_fixtures',return_value=None),patch.object(worker,'load_execution_failure',return_value=None),patch.object(worker,'load_repair_feedback',return_value={'error':{'codes':codes}}),patch.object(adapter,'invoke_task_model',side_effect=invoke):
    with self.assertRaises(StopBeforeProvider):worker.model('profile.json',task,'repair',['app.py'],[],output)
   self.assertEqual(len(seen),1);self.assertFalse((output.parent/'receipt.json').exists())
 def test_timeout_without_response_requests_a_small_patch(self):self.inspect(['provider_timeout_without_response'],True)
 def test_timeout_with_activity_also_requests_a_small_patch_without_salvage(self):self.inspect(['provider_timeout_with_activity'],True)
 def test_other_provider_failures_keep_existing_feedback_behavior(self):self.inspect(['provider_or_response_contract_failure'],False)
if __name__=='__main__':unittest.main()
