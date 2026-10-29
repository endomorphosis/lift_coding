"""Readonly foundation context uses exact declared bytes and bounded public APIs."""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,sys,tempfile,unittest
from unittest.mock import patch
STAGE=Path(__file__).resolve().parents[1];LIVE=Path.cwd().resolve()
if not(LIVE/'config/swissknife_visual_functional_tasks.json').is_file():LIVE=STAGE
sys.path[:0]=[str(STAGE/'scripts'),str(LIVE/'scripts')]
import swissknife_visual_functional_native_context as context

class FoundationContext(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tasks={t['task_id']:t for t in json.loads((LIVE/'config/swissknife_visual_functional_tasks.json').read_text())['tasks']if t['task_id']in context.FOUNDATIONS}
 def fixture(self,task_id='SVF-043'):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);root=Path(temporary.name);task=copy.deepcopy(self.tasks[task_id]);rule=context.FOUNDATIONS[task_id]
  for name in {context.FOUNDATION_DOC,context.OWNERSHIP,context.OBSERVER,*rule['full'],*rule['api']}:
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((LIVE/name).read_bytes())
  return root,task
 def assert_fragments(self,root,projection):
  lines=(root/projection['path']).read_text().splitlines(keepends=True)
  for part in projection['fragments']:self.assertEqual(part['text'],''.join(lines[part['start_line']-1:part['end_line']]))
 def test_only_exact_declared_backend_foundations_are_selected(self):
  for task_id in context.FOUNDATIONS:
   task=self.tasks[task_id]
   for changed in [{'task_id':'other'},{'kind':'implementation'},{'app_id':'agent-supervisor'}]:
    self.assertIsNone(context.load_native_foundation_context(LIVE,{**task,**changed}))
 def test_readonly_scope_must_be_declared_and_cannot_be_edited(self):
  root,task=self.fixture();task['execution_inputs'].remove(context.OBSERVER)
  with self.assertRaisesRegex(ValueError,'not declared'):context.load_native_foundation_context(root,task)
  task['execution_inputs'].append(context.OBSERVER);task['edit_paths'].append(context.OBSERVER)
  with self.assertRaisesRegex(ValueError,'cannot be an edit'):context.load_native_foundation_context(root,task)
 def test_exact_full_readonly_inputs_and_original_source_fences(self):
  for task_id in context.FOUNDATIONS:
   with self.subTest(task=task_id):
    task=self.tasks[task_id];before=copy.deepcopy(task);bundle=context.load_native_foundation_context(LIVE,task)
    self.assertEqual(bundle['full_inputs'],list(context.FOUNDATIONS[task_id]['full']));self.assertFalse(set(bundle['full_inputs'])&set(task['edit_paths']))
    for row in bundle['sources']:
     raw=(LIVE/row['path']).read_bytes();self.assertEqual(row,{'path':row['path'],'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
    self.assertEqual(task,before)
 def test_all_api_and_engineering_fragments_are_exact_original_lines(self):
  for task_id in context.FOUNDATIONS:
   with self.subTest(task=task_id):
    value=context.load_native_foundation_context(LIVE,self.tasks[task_id])['context'];self.assert_fragments(LIVE,value['engineering_contract'])
    for item in value['protected_helper_api']:self.assert_fragments(LIVE,item)
    for item in value['sdk_public_api']:
     for cls in item['classes']:self.assert_fragments(LIVE,{'path':item['path'],'fragments':cls['fragments']})
    self.assertLessEqual(len(json.dumps(value['protected_helper_api']).encode()),4096);self.assertLessEqual(len(json.dumps(value['sdk_public_api']).encode()),16384)
 def test_other_capability_does_not_displace_required_contract(self):
  pub=context.load_native_foundation_context(LIVE,self.tasks['SVF-043'])['context']['engineering_contract']['fragments'][0]['text'];sup=context.load_native_foundation_context(LIVE,self.tasks['SVF-044'])['context']['engineering_contract']['fragments'][0]['text']
  self.assertIn('Protected SVF-043 pubsub contract',pub);self.assertNotIn('Protected R13 supervisor fixture',pub);self.assertIn('Protected R13 supervisor fixture',sup);self.assertNotIn('Protected SVF-043 pubsub contract',sup)
 def test_missing_edit_targets_are_explicitly_forbidden_as_evidence(self):
  root,task=self.fixture();value=context.load_native_foundation_context(root,task)['context'];policy=value['proposal_evidence_policy']
  self.assertEqual(policy['missing_edit_targets_are_not_evidence'],task['edit_paths']);self.assertFalse(set(policy['allowed_existing_source_paths'])&set(task['edit_paths']));self.assertIn('CURRENT existing physical file',policy['instruction'])
 def test_symlink_source_and_parent_directory_are_refused(self):
  root,task=self.fixture();p=root/context.PINNED_IPFS;data=p.read_bytes();p.unlink();destination=root/'foreign.py';destination.write_bytes(data);p.symlink_to(destination)
  with self.assertRaisesRegex(ValueError,'physical checkout'):context.load_native_foundation_context(root,task)
 def test_fifo_is_refused_without_waiting_for_a_writer(self):
  root,task=self.fixture();p=root/context.PINNED_IPFS;p.unlink();os.mkfifo(p)
  with self.assertRaisesRegex(ValueError,'exact bound'):context.load_native_foundation_context(root,task)
 def test_empty_oversized_invalid_utf8_and_missing_class_refuse(self):
  root,task=self.fixture();p=root/context.PINNED_IPFS
  for raw in [b'',b'x'*1048577,b'\xff',b'class Different: pass\n']:
   with self.subTest(size=len(raw)):
    p.write_bytes(raw)
    with self.assertRaises((ValueError,UnicodeError)):context.load_native_foundation_context(root,task)
 def test_missing_between_capability_source_marker_refuses(self):
  root,task=self.fixture();doc=root/context.FOUNDATION_DOC;doc.write_text(doc.read_text().replace('Source snapshot: SUPERVISOR-CONTRACT.md;','Removed section boundary:'))
  with self.assertRaisesRegex(ValueError,'boundary'):context.load_native_foundation_context(root,task)
 def test_missing_engineering_section_or_sdk_method_refuses(self):
  root,task=self.fixture();doc=root/context.FOUNDATION_DOC;doc.write_text('No protected sections\n')
  with self.assertRaisesRegex(ValueError,'sections'):context.load_native_foundation_context(root,task)
  doc.write_bytes((LIVE/context.FOUNDATION_DOC).read_bytes());sdk=root/context.PINNED_IPFS;sdk.write_text('class LivePinnedIpfsAdapter:\n def __init__(self): pass\n')
  with self.assertRaisesRegex(ValueError,'public SDK interface'):context.load_native_foundation_context(root,task)
 def test_source_changed_between_read_and_path_recheck_refuses(self):
  root,task=self.fixture();real=os.fstat;counter=[0]
  def changed(fd):
   value=real(fd);counter[0]+=1
   if counter[0]==2:
    # Return a changed stat identity while retaining all normal fields.
    class Changed:
     def __getattr__(self,name):return getattr(value,name)
     st_mtime_ns=value.st_mtime_ns+1
    return Changed()
   return value
  with patch.object(context.os,'fstat',side_effect=changed):
   with self.assertRaisesRegex(ValueError,'changed during'):context.load_native_foundation_context(root,task)
 def test_actual_worker_requires_complete_readonly_bundle_before_provider(self):
  root,task=self.fixture();task['edit_paths']=['editable.py'];(root/'editable.py').write_text('existing = 1\n');task['context_paths']=[context.FOUNDATION_DOC];(root/'contracts.json').write_text('{"apps":[]}')
  profile={'runtimeRoot':'data/agent_supervisor/swissknife_visual_functional','appContractPath':'contracts.json','taskSpecPath':'tasks.json','humanPlanPath':'plan.md','llm':{'provider':'grok_cli','model':'grok-4.7','repairReadPolicy':'inline_only','allowLocalFallback':False,'allowCrossProviderFallback':False}}
  spec=importlib.util.spec_from_file_location('foundation_context_worker',STAGE/'scripts/swissknife_visual_functional_worker.py');worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
  import swissknife_visual_functional_llm as adapter
  import swissknife_visual_functional_blocked as blocked
  output=root/profile['runtimeRoot']/'tasks/SVF-043/repair.json';observed=[]
  input_names=[context.FOUNDATION_DOC,'editable.py']
  if getattr(self,'producer_feedback',False):
   producer=output.parent/'failure-1.txt';producer.parent.mkdir(parents=True);producer.write_text('Authored actual check-output shape, not live qualification\n');input_names.append(str(producer.relative_to(root)))
  class InspectedBeforeProvider(Exception):pass
  def inspect(*args,**kwargs):
   inputs=kwargs['input_paths'];body=json.loads((root/inputs[0]).read_text());observed.append(body)
   self.assertEqual('proposal_scope_fingerprint'in body,not getattr(self,'producer_feedback',False))
   if 'proposal_scope_fingerprint'in body:self.assertRegex(body['proposal_scope_fingerprint'],r'^[0-9a-f]{64}$')
   self.assertNotIn('canonical_apps',body);self.assertIn('native_foundation_context',body);self.assertEqual(kwargs['predicted_files'],['editable.py']);self.assertNotIn(context.FOUNDATION_DOC,inputs)
   for name in context.FOUNDATIONS['SVF-043']['full']:self.assertIn(name,inputs);self.assertEqual((root/name).read_bytes(),(LIVE/name).read_bytes())
   raise InspectedBeforeProvider()
  with patch.object(worker,'ROOT',root),patch.object(worker,'load',return_value=(profile,{'tasks':[task]})),patch.object(worker,'assert_no_campaign_hold'),patch.object(worker,'assert_storage_available'),patch.object(worker,'workflow_fixtures',return_value=None),patch.object(worker,'load_execution_failure',return_value=None),patch.object(worker,'load_repair_feedback',return_value=None),patch.object(adapter,'invoke_task_model',side_effect=inspect),patch.object(blocked,'build_proposal_scope',wraps=blocked.build_proposal_scope)as builder:
   with self.assertRaises(InspectedBeforeProvider):worker.model('profile.json',task,'repair',input_names,[],output)
  self.assertEqual(len(observed),1);self.assertEqual(builder.call_count,0 if getattr(self,'producer_feedback',False)else 1)
 def test_actual_check_feedback_is_not_cached_as_a_no_producer_decline(self):
  self.producer_feedback=True
  self.test_actual_worker_requires_complete_readonly_bundle_before_provider()
if __name__=='__main__':unittest.main()
