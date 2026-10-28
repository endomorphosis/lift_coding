"""Authored native-PNG post-retry joins; no browser/provider or acceptance claims."""
import copy
import os
from pathlib import Path
import sys
import unittest

ROOT=Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT',Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(ROOT/'tests'))
import test_svf_request_proof_handoff as shapes
f=shapes.f

class RecoveryImageRetentionTests(unittest.TestCase):
 png=staticmethod(shapes.ErrorImageRetentionTests.png)
 def setUp(self):
  shapes.ErrorImageRetentionTests.setUp(self)
  steps=self.scenario['phases']['failure_recovery']
  steps.append({'op':'assert','requirement_id':'failure_recovery','probe':{'kind':'text','selector':'#result'},'operator':'equals','expected':'retry succeeded'})
  steps.append({'op':'assert','checkpoint_id':'recovery_image_retained','probe':copy.deepcopy(steps[1]['probe']),'operator':'equals','expected':2,'retained_from':{'primary_result':0,'persist_reopen':0}})
  self.child['semantic_assertions'].append({'phase':'failure_recovery','step_index':3,'requirement_id':'failure_recovery','passed':True,'observed':{'operator':'equals','actual':'retry succeeded','expected':'retry succeeded'}})
  post=copy.deepcopy(self.child['image_observations'][-1]);post['step_index']=4;self.child['image_observations'].append(post)
  self.child['error_observations'][0]['checkpoint_id']='error_image_retained'
  self.child['error_observations'].insert(0,{'phase':'failure_recovery','step_index':0,'checkpoint_id':'error_observed','observed':{'operator':'contains','actual':'bad CID','expected':'bad'}})
  self.child['error_observations'].append({'phase':'failure_recovery','step_index':4,'checkpoint_id':'recovery_image_retained','observed':{'operator':'equals','actual':2,'expected':2}})
 def check(self):return f.validate_decoded_images(self.root,self.child,self.scenario,self.report)
 def grammar(self):return f._scenario_error_checkpoints(self.scenario)
 def test_four_independent_native_image_rows_join_exact_saved_png_only(self):
  rows=self.check();self.assertEqual(len(rows),4);self.assertEqual([r['step_index']for r in rows],[0,0,1,4]);self.assertEqual(len(self.grammar()),3)
  self.assertEqual({r['content_sha256']for r in rows},{self.ref['sha256']})
 def test_post_only_is_legal_without_claiming_an_error_time_snapshot(self):
  self.scenario['phases']['failure_recovery'].pop(1);self.child['image_observations'].pop(2)
  for row in self.child['image_observations']:
   if row['phase']=='failure_recovery':row['step_index']-=1
  for row in self.child['semantic_assertions']:
   if row['phase']=='failure_recovery':row['step_index']-=1
  self.child['error_observations']=[row for row in self.child['error_observations']if row['checkpoint_id']!='error_image_retained']
  self.child['error_observations'][-1]['step_index']=3
  self.assertEqual(len(self.check()),3);self.assertEqual([r[2]['checkpoint_id']for r in self.grammar()],['error_observed','recovery_image_retained'])
 def test_legacy_pre_only_has_no_post_requirement(self):
  self.scenario['phases']['failure_recovery'].pop();self.child['image_observations'].pop();self.child['error_observations'].pop();self.assertEqual(len(self.check()),3)
 def test_post_cannot_precede_original_semantic_completion(self):
  steps=self.scenario['phases']['failure_recovery'];steps[3],steps[4]=steps[4],steps[3]
  with self.assertRaises(ValueError):self.grammar()
 def test_original_recovery_assertion_and_actual_ui_action_required(self):
  baseline=copy.deepcopy(self.scenario)
  for modify in (lambda s:s[3].pop('requirement_id'),lambda s:s[2].update(op='wait_ms'),lambda s:s[3].update(op='capture')):
   self.scenario=copy.deepcopy(baseline);modify(self.scenario['phases']['failure_recovery'])
   with self.assertRaises(ValueError):self.grammar()
 def test_ui_owner_or_semantic_action_between_semantic_and_post_refused(self):
  baseline=copy.deepcopy(self.scenario)
  for step in ({'op':'click'},{'op':'fill'},{'op':'reopen_app'},{'op':'assert','probe':{'kind':'backend_result'}},{'op':'assert','requirement_id':'another'}):
   self.scenario=copy.deepcopy(baseline);self.scenario['phases']['failure_recovery'].insert(4,step)
   with self.assertRaises(ValueError):self.grammar()
 def test_ui_owner_or_semantic_action_after_post_refused(self):
  baseline=copy.deepcopy(self.scenario)
  for step in ({'op':'click'},{'op':'press'},{'op':'assert','probe':{'kind':'backend_result'}},{'op':'assert','requirement_id':'another'}):
   self.scenario=copy.deepcopy(baseline);self.scenario['phases']['failure_recovery'].append(step)
   with self.assertRaises(ValueError):self.grammar()
 def test_passive_wait_capture_after_post_is_not_another_recovery(self):
  self.scenario['phases']['failure_recovery'] += [{'op':'wait_ms','milliseconds':0},{'op':'capture','label':'after-png'}];self.assertEqual(len(self.grammar()),3)
 def test_duplicate_unknown_or_nonimage_post_is_closed(self):
  baseline=copy.deepcopy(self.scenario)
  for modify in (lambda s:s.append(copy.deepcopy(s[-1])),lambda s:s[-1].update(checkpoint_id='recovery_image_observed'),lambda s:s[-1]['probe'].update(kind='text'),lambda s:s[-1]['probe'].update(temporal_ms=100),lambda s:s[-1].update(requirement_id='failure_recovery'),lambda s:s[-1].update(checkpoint_id={})): 
   self.scenario=copy.deepcopy(baseline);modify(self.scenario['phases']['failure_recovery'])
   with self.assertRaises(ValueError):self.grammar()
 def test_post_requires_exact_original_primary_reopen_refs(self):
  baseline=copy.deepcopy(self.scenario)
  for refs in ({'primary_result':True,'persist_reopen':0},{'primary_result':64,'persist_reopen':0},{'primary_result':0},{'primary_result':0,'persist_reopen':0,'error_image_retained':1}):
   self.scenario=copy.deepcopy(baseline);self.scenario['phases']['failure_recovery'][-1]['retained_from']=refs
   with self.assertRaises(ValueError):self.grammar()
 def test_post_missing_duplicate_wrong_phase_or_selector_native_row_refused(self):
  baseline=copy.deepcopy(self.child)
  for modify in (lambda d:d['image_observations'].pop(),lambda d:d['image_observations'].append(copy.deepcopy(d['image_observations'][-1])),lambda d:d['image_observations'][-1].update(phase='persist_reopen'),lambda d:d['image_observations'][-1].update(selector='#different')):
   self.child=copy.deepcopy(baseline);modify(self.child)
   with self.assertRaises(ValueError):self.check()
 def test_post_does_not_infer_success_from_png_or_app_flags(self):
  baseline=copy.deepcopy(self.child)
  for modify in (lambda d:d['semantic_assertions'][-1].update(passed=False),lambda d:d['semantic_assertions'].pop(),lambda d:d['semantic_assertions'][-1].update(step_index=2),lambda d:d['semantic_assertions'].append(copy.deepcopy(d['semantic_assertions'][-1]))):
   self.child=copy.deepcopy(baseline);modify(self.child)
   with self.assertRaises(ValueError):self.check()
 def test_forged_post_source_content_dimensions_or_actual_refused(self):
  baseline=copy.deepcopy(self.child)
  for key,value in [('source_sha256','0'*64),('content_sha256','0'*64),('natural_width',3),('image_artifact',None)]:
   self.child=copy.deepcopy(baseline);self.child['image_observations'][-1][key]=value
   with self.assertRaises(ValueError):self.check()
  self.child=copy.deepcopy(baseline);self.child['error_observations'][-1]['observed']['actual']=3
  with self.assertRaises(ValueError):self.check()
 def test_valid_other_png_after_retry_does_not_match_original_saved_image(self):
  raw=shapes.ErrorImageRetentionTests.png(2,b'\x00\x00\xff\xff');target=self.directory/'post-other.png';target.write_bytes(raw);ref=f.reference(self.root,target);self.child['artifacts'].append(ref)
  import hashlib,base64
  self.child['image_observations'][-1].update(content_sha256=hashlib.sha256(raw).hexdigest(),source_sha256=hashlib.sha256(b'data:image/png;base64,'+base64.b64encode(raw)).hexdigest(),image_artifact=ref)
  with self.assertRaisesRegex(ValueError,'changed between'):self.check()
 def test_other_viewport_cannot_supply_post_png_artifact(self):
  sibling=self.root/'mobile';sibling.mkdir();target=sibling/'retained.png';target.write_bytes(self.raw);ref=f.reference(self.root,target);self.child['artifacts'].append(ref);self.child['image_observations'][-1]['image_artifact']=ref
  with self.assertRaises(ValueError):self.check()

if __name__=='__main__':unittest.main()
