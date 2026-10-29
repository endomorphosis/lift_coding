"""Portable authored supplemental DOM evidence; no operational acceptance."""
import base64
import copy
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE=Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT',Path(__file__).resolve().parents[1]))
SCRIPTS=Path(os.environ.get('SVF_VPC_CANDIDATE_SCRIPTS',BASE/'scripts'))
sys.path.insert(0,str(BASE/'tests'));sys.path.insert(0,str(BASE/'scripts'));sys.path.insert(0,str(SCRIPTS))
import test_svf_final_viewport_coverage as shapes
f=shapes.final

def extra(kind='text',expected='Replay packet trail-note.'):
 return {'op':'assert','probe':{'kind':kind,'selector':'#packet'},'operator':'equals','expected':expected}

def absent_control():
 return {'present':False,'tag':None,'type':None,'visible':False,'enabled':False,'value':None,
  'value_as_number':None,'min':None,'max':None,'step':None}

class SupplementalObservationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir='/dev/shm');self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.fixture=shapes.Fixture(self.root)
  self.patch=patch.object(f,'_node_source_snapshot',side_effect=self.fixture.source_vector);self.patch.start();self.addCleanup(self.patch.stop)
  self.group=self.fixture.group();self.scenario=self.fixture.scenario(self.fixture.apps[0])
  self.scenario['phases']['persist_reopen'].append(extra());self.scenario['phases']['failure_recovery'].append(extra())
  self.publish_scenario()
 def publish_scenario(self):
  self.fixture.write('swissknife/test/e2e/functional-workflows/app-0.json',self.scenario)
  self.group['sources']=f.source_snapshot(self.root,self.fixture.profile,self.group['task'])
  for child in self.group['children']:
   child.update(self.group['sources']);child['supplemental_observations']=[
    {'phase':row['phase'],'step_index':row['step_index'],'probe':copy.deepcopy(row['probe']),
     'observed':{'operator':row['operator'],'actual':copy.deepcopy(row['expected']),'expected':copy.deepcopy(row['expected'])}}
    for row in f.supplemental_descriptors(self.scenario)]
   child['phase_evidence']=self.phase_evidence(child)
  self.fixture.persist(self.group)
 def phase_evidence(self,child):
  observations={(row['phase'],row['step_index']):row['observed']for row in child['semantic_assertions']+child['error_observations']+child.get('supplemental_observations',[])}
  selectors={step['selector']for steps in self.scenario['phases'].values()for step in steps if step['op']in{'click','fill','press','select','check','uncheck'}}
  generation=0;clock=0;phases=[]
  for name,steps in self.scenario['phases'].items():
   phase={'phase':name,'generation_before':generation,'generation_after':None,'steps':[]}
   for index,step in enumerate(steps):
    record={'step_index':index,'step':copy.deepcopy(step),'generation_before':generation,'generation_after':generation+int(step['op']=='reopen_app'),
     'started_ms':clock,'finished_ms':clock+1,'observed':copy.deepcopy(observations.get((name,index))),
     'temporal_samples':[],'media':[],'controls':[],'reopen':{'old_window_disconnected':True}if step['op']=='reopen_app'else None}
    if step.get('checkpoint_id')=='error_observed':record['controls']=[{'selector':selector,'before':None,'after':absent_control()}for selector in sorted(selectors)]
    generation=record['generation_after'];clock+=2;phase['steps'].append(record)
   phase['generation_after']=generation;phases.append(phase)
  return {'schema':f.PHASE_EVIDENCE_SCHEMA,'phases':phases}
 def validate(self):return self.fixture.validated(self.group)
 def refuse_rows(self,change):
  change(self.group['children'][1]['supplemental_observations']);self.fixture.persist(self.group)
  with self.assertRaises(ValueError):self.validate()
 def test_two_supplements_in_each_child_pass_without_role_or_check_credit(self):
  self.validate();projection=f.projection(self.root,self.group['report'])
  for view,child in zip(projection['viewports'],self.group['children']):
   self.assertEqual(view['supplemental_observations'],child['supplemental_observations'])
   self.assertEqual(len(child['semantic_assertions']),3);self.assertEqual(len(child['error_observations']),1);self.assertEqual(len(child['checks']),4)
   self.assertEqual(child['backend_call_count'],0);self.assertEqual(len(child['keyboard_observations']),1)
  self.assertLessEqual(len(f.encoded(projection)),18000)
 def test_missing_extra_duplicate_order_and_foreign_phase_or_probe_refuse(self):
  original=copy.deepcopy(self.group['children'][1]['supplemental_observations'])
  for change in [lambda r:r.pop(),lambda r:r.append(copy.deepcopy(r[0])),lambda r:r.reverse(),
   lambda r:r[0].update(phase='primary_result'),lambda r:r[0].update(step_index=True),
   lambda r:r[0]['probe'].update(selector='#other')]:
   self.group['children'][1]['supplemental_observations']=copy.deepcopy(original)
   self.refuse_rows(change)
 def test_false_actual_operator_expected_type_or_extra_authority_fields_refuse(self):
  original=copy.deepcopy(self.group['children'][1]['supplemental_observations'])
  for change in [lambda r:r[0]['observed'].update(actual='not observed'),lambda r:r[0]['observed'].update(operator='not_equals'),
   lambda r:r[0]['observed'].update(expected=True),lambda r:r[0].update(requirement_id='persist_reopen'),
   lambda r:r[0].update(checkpoint_id='error_observed'),lambda r:r[0].update(passed=True)]:
   self.group['children'][1]['supplemental_observations']=copy.deepcopy(original);self.refuse_rows(change)
 def test_missing_wire_is_closed_when_source_has_supplements(self):
  self.group['children'][1].pop('supplemental_observations');self.fixture.persist(self.group)
  with self.assertRaises(ValueError):self.validate()
 def test_new_supplements_cannot_omit_actual_phase_evidence(self):
  self.group['children'][1].pop('phase_evidence');self.fixture.persist(self.group)
  with self.assertRaisesRegex(ValueError,'phase evidence'):self.validate()
 def test_phase_evidence_must_join_exact_supplemental_actual(self):
  self.group['children'][1]['phase_evidence']['phases'][1]['steps'][-1]['observed']['actual']='borrowed'
  self.fixture.persist(self.group)
  with self.assertRaisesRegex(ValueError,'phase observed'):self.validate()
 def test_parent_child_artifact_or_source_tampering_is_not_supplemental_authority(self):
  self.group['children'][1]['scenario_sha256']='0'*64;self.fixture.persist(self.group)
  with self.assertRaisesRegex(ValueError,'stale'):self.validate()
 def test_missing_duplicate_unknown_or_wrong_phase_original_ids_still_refuse(self):
  for mode in ['missing','duplicate','unknown','wrong_phase']:
   self.set_source_role_case(mode)
 def set_source_role_case(self,mode):
  scenario=copy.deepcopy(self.scenario);source=scenario['phases']['primary_result'][1]
  if mode=='missing':source.pop('requirement_id')
  elif mode=='unknown':source['requirement_id']='result_999'
  elif mode=='duplicate':scenario['phases']['primary_result'].append(copy.deepcopy(source))
  else:scenario['phases']['persist_reopen'].append(scenario['phases']['primary_result'].pop())
  self.fixture.write('swissknife/test/e2e/functional-workflows/app-0.json',scenario)
  sources=f.source_snapshot(self.root,self.fixture.profile,self.group['task']);self.group['sources']=sources
  for child in self.group['children']:child.update(sources)
  self.fixture.persist(self.group)
  with self.assertRaises(ValueError):self.validate()
 def test_null_empty_or_both_identity_keys_do_not_become_supplements(self):
  for fields in [{'requirement_id':None},{'requirement_id':''},{'checkpoint_id':None},{'checkpoint_id':''},
   {'requirement_id':'result_1','checkpoint_id':'error_observed'}]:
   scenario=copy.deepcopy(self.scenario);scenario['phases']['persist_reopen'][-1].update(fields)
   with self.assertRaises(ValueError):f.supplemental_descriptors(scenario)
 def test_backend_media_image_temporal_retention_and_private_attribute_refuse(self):
  for change in [{'probe':{'kind':'backend_result','binding_id':'x','pointer':'/x'}},{'probe':{'kind':'image_state','selector':'#x'}},
   {'probe':{'kind':'media_state','selector':'#x'}},{'probe':{'kind':'dom_property','selector':'#x','property':'value'}},
   {'probe':{'kind':'text','selector':'#x','temporal_ms':50}}, {'retained_from':{'primary_result':1,'persist_reopen':1}},
   {'probe':{'kind':'json_attribute','selector':'#x','attribute':'data-token'}}]:
   scenario=copy.deepcopy(self.scenario);scenario['phases']['persist_reopen'][-1].update(change)
   with self.assertRaises(ValueError):f.supplemental_descriptors(scenario)
 def test_text_value_attribute_scalar_and_all_four_operators(self):
  for kind,operator,actual,expected in [('text','equals',None,None),('value','not_equals',False,0),
   ('text','contains','observed packet','packet'),('json_attribute','at_least',2,1)]:
   scenario=copy.deepcopy(self.scenario);step=scenario['phases']['persist_reopen'][-1]
   step.update(probe={'kind':kind,'selector':'#packet'},operator=operator,expected=expected)
   if kind=='json_attribute':step['probe'].update(attribute='data-summary',pointer='/count')
   rows=[{'phase':row['phase'],'step_index':row['step_index'],'probe':row['probe'],
    'observed':{'operator':row['operator'],'expected':row['expected'],'actual':actual if row['phase']=='persist_reopen'else row['expected']}}
    for row in f.supplemental_descriptors(scenario)]
   self.assertEqual(len(f.validate_supplemental_observations({'supplemental_observations':rows},scenario)),2)
 def test_eight_count_and_descriptor_2048_bounds_are_closed(self):
  scenario=copy.deepcopy(self.scenario);scenario['phases']['primary_result'] +=[extra(expected='x')for _ in range(6)]
  self.assertEqual(len(f.supplemental_descriptors(scenario)),8)
  scenario['phases']['primary_result'].append(extra(expected='x'))
  with self.assertRaisesRegex(ValueError,'eight-check'):f.supplemental_descriptors(scenario)
  scenario=copy.deepcopy(self.scenario)
  for phase in ['persist_reopen','failure_recovery']:scenario['phases'][phase][-1]['probe']['selector']='#'+'x'*500;scenario['phases'][phase][-1]['expected']='x'*500
  with self.assertRaisesRegex(ValueError,'2048'):f.supplemental_descriptors(scenario)
 def test_scalar_512_utf8_finite_and_actual_rows_4096_bounds(self):
  for value in ['é'*256,{'invented':'object'},['array'],float('nan'),float('inf'),10**400]:
   scenario=copy.deepcopy(self.scenario);scenario['phases']['persist_reopen'][-1]['expected']=value
   with self.assertRaises(ValueError):f.supplemental_descriptors(scenario)
  self.assertEqual(len(f._supplemental_encoded('é'*255)),512)
  scenario=copy.deepcopy(self.scenario);scenario['phases']['persist_reopen'][-1]['expected']='é'*255;self.assertEqual(len(f.supplemental_descriptors(scenario)),2)
  scenario=copy.deepcopy(self.scenario);scenario['phases']['primary_result'] +=[extra(expected='x')for _ in range(6)]
  descriptors=f.supplemental_descriptors(scenario)
  rows=[{'phase':r['phase'],'step_index':r['step_index'],'probe':r['probe'],'observed':{'operator':'not_equals','expected':r['expected'],'actual':'a'*500}}for r in descriptors]
  for phase in scenario['phases'].values():
   for step in phase:
    if step.get('op')=='assert'and'requirement_id'not in step and'checkpoint_id'not in step:step['operator']='not_equals'
  with self.assertRaisesRegex(ValueError,'byte bound'):f.validate_supplemental_observations({'supplemental_observations':rows},scenario)
 def test_actual_scalar_type_finiteness_and_size_cannot_be_borrowed(self):
  rows=copy.deepcopy(self.group['children'][1]['supplemental_observations'])
  for value in [True,0,None,{'observed':'invented'},['packet'],float('nan'),float('inf'),'é'*256]:
   current=copy.deepcopy(rows);current[0]['observed']['actual']=value
   with self.assertRaises(ValueError):f.validate_supplemental_observations({'supplemental_observations':current},self.scenario)
 def test_projection_codec_retains_all_typed_supplemental_facts(self):
  self.scenario['phases']['persist_reopen'][-1]['expected']='Unicode packet é 😀 '*12
  self.scenario['phases']['failure_recovery'][-1]['expected']='Unicode packet é 😀 '*12
  self.publish_scenario();self.validate();projection=f._expand_projection(f.projection(self.root,self.group['report']))
  for view,child in zip(projection['viewports'],self.group['children']):
   self.assertEqual(view['supplemental_observations'],child['supplemental_observations'])
 def test_projection_oversize_fails_without_fact_truncation(self):
  noise=''.join(chr(33+(i*31)%90)for i in range(18000))
  for child in self.group['children']:
   child['viewports'][0]['raw_diagnostic']=noise
   name=child['viewport']['name'];layout={k:v for k,v in child['viewports'][0].items()if k!='name'}
   target=self.group['folder']/name/(name+'-layout.json');self.fixture.write(str(target.relative_to(self.root)),layout)
   ref=f.reference(self.root,target)
   child['artifacts']=[ref if a['path']==ref['path']else a for a in child['artifacts']]
  self.fixture.persist(self.group);self.validate()
  with self.assertRaisesRegex(ValueError,'bounded prompt share'):f.projection(self.root,self.group['report'])
  self.assertEqual(self.group['children'][0]['supplemental_observations'][0]['observed']['actual'],'Replay packet trail-note.')
 def test_native_js_number_step_wire_matches_only_new_supplemental_domain(self):
  for value,wire in [(1.0,1),(1e20,100000000000000000000),(-0.0,0)]:
   self.scenario['phases']['persist_reopen'][-1]['expected']=value
   self.publish_scenario()
   for child in self.group['children']:
    actual=child['supplemental_observations'][0]['observed'];actual.update(actual=wire,expected=wire)
    record=child['phase_evidence']['phases'][1]['steps'][-1]
    record['step']['expected']=wire;record['observed'].update(actual=wire,expected=wire)
   self.fixture.persist(self.group);self.validate()
  child=self.group['children'][1];child['phase_evidence']['phases'][1]['steps'][-1]['step']['expected']=False
  self.fixture.persist(self.group)
  with self.assertRaises(ValueError):self.validate()
 def test_historical_nonsupplemental_phase_step_comparison_stays_strict(self):
  self.group['children'][1]['phase_evidence']['phases'][0]['steps'][1]['step']['expected']=50
  self.fixture.persist(self.group)
  with self.assertRaisesRegex(ValueError,'phase action'):self.validate()
 def test_js_number_canonicalization_and_boolean_domain(self):
  cases=[(1.0,b'1'),(-0.0,b'0'),(1e-7,b'1e-7'),(1e20,b'100000000000000000000'),(1e-6,b'0.000001'),(1e21,b'1e+21')]
  for value,expected in cases:self.assertEqual(f._supplemental_encoded(value),expected)
  self.assertTrue(f._supplemental_equal(1.0,1));self.assertTrue(f._supplemental_equal(-0.0,0));self.assertFalse(f._supplemental_equal(True,1))
 def test_historical_no_supplement_v2_missing_or_empty_wire_and_projection_unchanged(self):
  for phase in ['persist_reopen','failure_recovery']:self.scenario['phases'][phase].pop()
  self.publish_scenario()
  for child in self.group['children']:child.pop('supplemental_observations')
  self.fixture.persist(self.group);self.validate();first=f.projection(self.root,self.group['report'])
  self.assertTrue(all('supplemental_observations'not in view for view in first['viewports']))
  for child in self.group['children']:child['supplemental_observations']=[]
  self.fixture.persist(self.group);self.validate();second=f.projection(self.root,self.group['report'])
  for a,b in zip(first['viewports'],second['viewports']):a.pop('original');b.pop('original')
  first.pop('original');second.pop('original');self.assertEqual(first,second)


 def png_order_case(self,position):
  from test_svf_request_proof_handoff import ErrorImageRetentionTests
  self.scenario=self.fixture.scenario(self.fixture.apps[0]);self.scenario['fixture_scope']='svf-supplemental-order'
  for phase in ['primary_result','persist_reopen']:
   self.scenario['phases'][phase][1].update(probe={'kind':'image_state','selector':'#saved','pointer':'/natural_width'},expected=2)
  phases=self.scenario['phases'];steps=phases['failure_recovery']
  retained={'op':'assert','checkpoint_id':'error_image_retained','retained_from':{'primary_result':1,'persist_reopen':1},
   'probe':{'kind':'image_state','selector':'#saved','pointer':'/natural_width'},'operator':'equals','expected':2}
  steps.insert(2,copy.deepcopy(retained));post=copy.deepcopy(retained);post['checkpoint_id']='recovery_image_retained';steps.append(post)
  if position=='primary':phases['primary_result'].append(extra())
  elif position=='pre_window':steps.insert(2,extra())
  elif position=='result_to_post':steps.insert(5,extra())
  elif position=='after_post':steps.append(extra())
  elif position=='wait_capture_after':steps.extend([{'op':'wait_ms','milliseconds':0},{'op':'capture','label':'after-png'}])
  elif position=='wait_before_post':steps.insert(5,{'op':'wait_for','selector':'#saved','state':'visible','timeout_ms':50})
  else:raise AssertionError(position)
  raw=ErrorImageRetentionTests.png(2);source=hashlib.sha256(b'data:image/png;base64,'+base64.b64encode(raw)).hexdigest()
  texts={'result_1':'Observed arithmetic result','persist_reopen':'Restored result','failure_recovery':'Observed invalid input Recovery: Clear and calculate again'}
  for child in self.group['children']:
   child['semantic_assertions']=[];child['error_observations']=[];child['image_observations']=[]
   target=self.group['folder']/child['viewport']['name']/'saved.png';self.fixture.write(str(target.relative_to(self.root)),raw);ref=f.reference(self.root,target)
   child['artifacts']=[record for record in child['artifacts']if not record['path'].endswith('/saved.png')]+[ref]
   for phase,originals in phases.items():
    for index,step in enumerate(originals):
     if step['op']!='assert':continue
     record={'phase':phase,'step_index':index,'probe':copy.deepcopy(step['probe']),
      'observed':{'operator':step['operator'],'actual':step['expected'],'expected':step['expected']}}
     if 'requirement_id'in step:
      role=step['requirement_id'];child['semantic_assertions'].append({**record,'requirement_id':role,'requirement_text':texts[role],'passed':True})
     elif 'checkpoint_id'in step:child['error_observations'].append({**record,'checkpoint_id':step['checkpoint_id']})
     if step['probe']['kind']=='image_state':child['image_observations'].append({'phase':phase,'step_index':index,'selector':'#saved','decoded':True,
      'natural_width':2,'natural_height':2,'visible_area':100,'source_sha256':source,'content_sha256':ref['sha256'],'image_artifact':ref})
  runner=Path(os.environ.get('SVF_SUPPLEMENTAL_RUNNER',BASE/'swissknife/scripts/run-visual-functional-workflow.mjs'))
  for name,path in [('swissknife/scripts/run-visual-functional-workflow.mjs',runner),
   ('swissknife/scripts/capture-visual-functional-baseline.mjs',BASE/'swissknife/scripts/capture-visual-functional-baseline.mjs'),
   ('swissknife/scripts/lib/pick-free-port.mjs',BASE/'swissknife/scripts/lib/pick-free-port.mjs')]:self.fixture.write(name,path.read_bytes())
  self.publish_scenario()
 def test_named_png_windows_match_real_public_parser_worker_and_full_consumer(self):
  class BeforeRunner(BaseException):pass
  worker=shapes.worker;name='swissknife/test/e2e/functional-workflows/app-0.json'
  for position in ['primary','pre_window','wait_before_post','wait_capture_after','result_to_post','after_post']:
   with self.subTest(position=position):
    self.png_order_case(position);accepted=position not in {'result_to_post','after_post'}
    task={**self.group['task'],'kind':'verify','edit_paths':[name]}
    if accepted:
     worker.validate_proposed_scenarios(self.root,self.fixture.profile,task,{name:f.encoded(self.scenario)});self.validate()
    else:
     with self.assertRaises(ValueError):worker.validate_proposed_scenarios(self.root,self.fixture.profile,task,{name:f.encoded(self.scenario)})
     with self.assertRaisesRegex(ValueError,'recovery checkpoint'):self.validate()
    with patch.object(worker,'ROOT',self.root),patch.object(worker,'assert_no_campaign_hold'),patch.object(worker,'assert_storage_available'),patch.object(worker,'run',side_effect=BeforeRunner)as run:
     if accepted:
      with self.assertRaises(BeforeRunner):worker.workflow(self.fixture.profile,task,self.group['folder'])
      self.assertEqual(run.call_count,1);self.assertIn('--independent-viewports',run.call_args.args[0])
     else:
      with self.assertRaisesRegex(ValueError,'INVALID_SCENARIO'):worker.workflow(self.fixture.profile,task,self.group['folder'])
      run.assert_not_called()

if __name__=='__main__':unittest.main()
