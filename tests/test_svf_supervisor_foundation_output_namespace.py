"""Actual gate admission accepts the declared relative root; unsafe paths refuse."""
from pathlib import Path
import importlib.util,json,os,sys,tempfile,unittest
from unittest.mock import patch
STAGE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('strict_output_gate',STAGE/'scripts/svf_backends/validate_supervisor_foundation.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
QUALIFICATION='data/agent_supervisor/swissknife_visual_functional/tasks/SVF-044/qualification'
class BeforeOwnedServiceAdmission(Exception):pass
class OutputNamespace(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve();self.namespace=self.root/QUALIFICATION
  p=self.root/'config/swissknife_visual_functional_supervisor.json';p.parent.mkdir();p.write_text('{}')
 def accepted_before_control(self,output):
  calls=[]
  def stop(*args,**kwargs):calls.append((args,kwargs));raise BeforeOwnedServiceAdmission()
  with patch.object(gate,'protected_module',side_effect=stop),patch.object(gate.subprocess,'run',side_effect=AssertionError('no subprocess control')),patch.object(gate.urllib.request,'urlopen',side_effect=AssertionError('no backend request')):
   with self.assertRaises(BeforeOwnedServiceAdmission):gate.verify_live('config/swissknife_visual_functional_supervisor.json',output,root=self.root)
  self.assertEqual(len(calls),1);self.assertEqual(calls[0][0],(self.root,'scripts/svf_backends/foundation_service_ownership.py'))
 def refused_before_control(self,output):
  with patch.object(gate,'protected_module',side_effect=AssertionError('foreign path reached owner control'))as owner,patch.object(gate.subprocess,'run',side_effect=AssertionError('no subprocess')),patch.object(gate.urllib.request,'urlopen',side_effect=AssertionError('no backend request')):
   with self.assertRaisesRegex(ValueError,'unregistered qualification output namespace'):gate.verify_live('config/swissknife_visual_functional_supervisor.json',output,root=self.root)
  owner.assert_not_called()
 def test_actual_taskboard_relative_argument_reaches_owned_admission(self):
  live=Path.cwd();task=next(t for t in json.loads((live/'config/swissknife_visual_functional_tasks.json').read_text())['tasks']if t['task_id']=='SVF-044');command=task['checks'][-1];value=command[command.index('--output-root')+1]
  self.assertEqual(value,QUALIFICATION);self.accepted_before_control(value);self.assertEqual(len(list(self.namespace.glob('attempt-*'))),1)
 def test_previous_absolute_physical_namespace_remains_valid(self):self.accepted_before_control(str(self.namespace))
 def test_absolute_descendant_remains_valid(self):self.accepted_before_control(str(self.namespace/'nested'))
 def test_relative_argument_is_rooted_at_checkout_not_current_directory(self):
  elsewhere=self.root/'elsewhere';elsewhere.mkdir();previous=Path.cwd()
  try:os.chdir(elsewhere);self.accepted_before_control(QUALIFICATION)
  finally:os.chdir(previous)
  self.assertTrue(self.namespace.is_dir());self.assertFalse((elsewhere/QUALIFICATION).exists())
 def test_relative_traversal_is_rejected(self):self.refused_before_control('../foreign')
 def test_internal_relative_traversal_is_rejected(self):self.refused_before_control(QUALIFICATION+'/../escape')
 def test_absolute_traversal_is_rejected_even_if_it_returns_to_namespace(self):self.refused_before_control(str(self.namespace/'x/../attempt'))
 def test_outside_absolute_path_is_rejected_without_creation(self):
  outside=self.root.parent/('foreign-'+self.root.name);self.assertFalse(outside.exists());self.refused_before_control(str(outside));self.assertFalse(outside.exists())
 def test_prefix_lookalike_namespace_is_rejected(self):self.refused_before_control(QUALIFICATION+'-foreign')
 def test_other_task_namespace_is_rejected(self):self.refused_before_control(QUALIFICATION.replace('SVF-044','SVF-043'))
 def test_symlink_leaf_is_rejected_even_inside_owned_namespace(self):
  self.namespace.mkdir(parents=True);target=self.namespace/'physical';target.mkdir();alias=self.namespace/'alias';alias.symlink_to(target,target_is_directory=True);self.refused_before_control(str(alias));self.assertFalse(list(target.glob('attempt-*')))
 def test_dangling_symlink_is_rejected(self):
  self.namespace.mkdir(parents=True);alias=self.namespace/'alias';alias.symlink_to(self.root/'missing',target_is_directory=True);self.refused_before_control(str(alias));self.assertFalse((self.root/'missing').exists())
 def test_symlink_parent_is_rejected(self):
  target=self.root/'outside';target.mkdir();p=self.root/'data';p.symlink_to(target,target_is_directory=True);self.refused_before_control(QUALIFICATION);self.assertFalse(list(target.rglob('attempt-*')))
 def test_empty_root_and_unrelated_relative_output_are_rejected(self):
  for output in ('','.', 'qualification','data/foreign'):
   with self.subTest(output=output):self.refused_before_control(output)
if __name__=='__main__':unittest.main()
