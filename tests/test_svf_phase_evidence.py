"""Authored RAM phase-evidence vectors; no real browser/provider acceptance."""
import copy
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE=Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT',str(Path(__file__).resolve().parents[1])))
SCRIPTS=Path(os.environ.get('SVF_VPC_CANDIDATE_SCRIPTS',str(BASE/'scripts')))
sys.path.insert(0,str(BASE/'tests'));sys.path.insert(0,str(BASE/'scripts'));sys.path.insert(0,str(SCRIPTS))
import test_svf_final_viewport_coverage as shapes
final=shapes.final
CID='bafkreiedh65a7kpxnldwlbhv4hszsqyld2l4gg3ybe4jq77dp2tnyzuhla'

def media(time_value=.5):
 return {'present':True,'tag':'VIDEO','visible':True,'decoded_cid':CID,'src_sha256':'a'*64,'current_time':time_value,
         'duration':3.0,'ready_state':4,'paused':True,'ended':False,'seeking':False,'video_width':320,'video_height':240}

def control(selector,value=None,enabled=True):
 is_range=selector=='#seek';is_input=selector in {'#cid','#seek'}
 return {'present':True,'tag':'INPUT'if is_input else'BUTTON','type':'range'if is_range else'text'if is_input else'button',
         'visible':True,'enabled':enabled,'value':value,'value_as_number':float(value)if is_range and value is not None else None,
         'min':0.0 if is_range else None,'max':3.0 if is_range else None,'step':.1 if is_range else None}


class PhaseEvidenceTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir='/dev/shm');self.addCleanup(self.temp.cleanup);self.addCleanup(patch.stopall)
  self.root=Path(self.temp.name);self.f=shapes.Fixture(self.root)
  patch.object(final,'_node_source_snapshot',side_effect=self.f.source_vector).start()
  self.group=self.f.group()
  probe={'kind':'media_state','selector':'#video','pointer':'/current_time','temporal_ms':250}
  self.scenario={'schema':'swissknife.visual-functional-scenario.v1','app_id':'app-0','backend_bindings':[], 'phases':{
   'primary_result':[{'op':'fill','selector':'#cid','value':CID},{'op':'press','selector':'#seek','key':'Home'},
     {'op':'press','selector':'#seek','key':'ArrowRight'},{'op':'assert','requirement_id':'result_1','probe':probe,'operator':'at_least','expected':.05}],
   'persist_reopen':[{'op':'reopen_app'},{'op':'assert','requirement_id':'persist_reopen','probe':{'kind':'text','selector':'#saved'},'operator':'contains','expected':CID}],
   'failure_recovery':[{'op':'fill','selector':'#cid','value':'unavailable-source'},
     {'op':'assert','checkpoint_id':'error_observed','probe':{'kind':'text','selector':'#status'},'operator':'contains','expected':'Open failed'},
     {'op':'fill','selector':'#cid','value':CID},{'op':'press','selector':'#play','key':'Enter'},
     {'op':'assert','requirement_id':'failure_recovery','probe':probe,'operator':'at_least','expected':.05}]}}
  self.f.write('swissknife/test/e2e/functional-workflows/app-0.json',self.scenario)
  self.group['sources']=final.source_snapshot(self.root,self.f.profile,self.group['task'])
  for child in self.group['children']:
   child.update(self.group['sources']);child['semantic_assertions']=[];child['error_observations']=[];child['temporal_observations']=[]
   for phase,steps in self.scenario['phases'].items():
    for index,step in enumerate(steps):
     if step['op']!='assert':continue
     sample={'before':1.0,'after':1.25,'sample_ms':250}
     actual=sample['after']-sample['before']if'temporal_ms'in step['probe']else step['expected']
     row={'phase':phase,'step_index':index,'probe':step['probe'],'observed':{'operator':step['operator'],'actual':actual,'expected':step['expected']}}
     if'requirement_id'in step:
      role=step['requirement_id'];text={'result_1':'Observed arithmetic result','persist_reopen':'Restored result','failure_recovery':'Observed invalid input Recovery: Clear and calculate again'}[role]
      child['semantic_assertions'].append({**row,'passed':True,'requirement_id':role,'requirement_text':text})
     else:child['error_observations'].append({**row,'checkpoint_id':'error_observed'})
     if'temporal_ms'in step['probe']:child['temporal_observations'].append(sample)
   child['keyboard_observations']=[{'phase':'primary_result','step_index':2,'key':'ArrowRight','focused':True,'inside_app':True,'semantic_requirement_id':'result_1'}]
   child['phase_evidence']=self.evidence(child)
  self.f.persist(self.group)

 def evidence(self,child):
  observations={(a['phase'],a['step_index']):a['observed']for a in child['semantic_assertions']+child['error_observations']}
  phases=[];generation=0;time=0
  for name,steps in self.scenario['phases'].items():
   phase={'phase':name,'generation_before':generation,'generation_after':None,'steps':[]}
   for index,step in enumerate(steps):
    row={'step_index':index,'step':copy.deepcopy(step),'generation_before':generation,'generation_after':generation+(step['op']=='reopen_app'),
         'started_ms':time,'finished_ms':time+10,'observed':copy.deepcopy(observations.get((name,index))), 'temporal_samples':[], 'media':[], 'controls':[], 'reopen':None}
    row['generation_after']=int(row['generation_after']);generation=row['generation_after'];time+=20
    if step['op']=='assert'and'temporal_ms'in step['probe']:row['temporal_samples']=[{'before':1.0,'after':1.25,'sample_ms':250}]
    if name=='primary_result'and index==2:
     row['media']=[{'selector':'#video','before':media(.2),'after':media(.6),'same_element':True,'seeked_events':[{'current_time':.6,'is_trusted':True}]}]
     row['controls']=[{'selector':'#seek','before':control('#seek','.2'),'after':control('#seek','.6')}]
    if step['op']=='reopen_app':
     row['reopen']={'old_window_disconnected':True};row['media']=[{'selector':'#video','before':media(.6),'after':media(.6),'same_element':True,'seeked_events':[]}]
    if step.get('checkpoint_id')=='error_observed':
     row['controls']=[{'selector':selector,'before':None,'after':control(selector,'unavailable-source'if selector=='#cid'else'0'if selector=='#seek' else None,enabled=selector=='#cid')}for selector in ['#cid','#seek','#play']]
    if name=='failure_recovery'and index==2:row['controls']=[{'selector':'#cid','before':control('#cid','unavailable-source'),'after':control('#cid',CID)}]
    phase['steps'].append(row)
   phase['generation_after']=generation;phases.append(phase)
  return {'schema':final.PHASE_EVIDENCE_SCHEMA,'phases':phases}

 def validate(self):return self.f.validated(self.group)
 def changed(self,mutate):
  mutate(self.group['children'][1]['phase_evidence']);self.f.persist(self.group)
  with self.assertRaises((ValueError,TypeError)):self.validate()

 def test_positive_exact_phase_evidence_and_rich_projection(self):
  self.validate();view=final.projection(self.root,self.group['report'])['viewports'][0]['phase_evidence']
  self.assertEqual(view['seek']['before']['current_time'],.2);self.assertEqual(view['seek']['after']['current_time'],.6)
  self.assertTrue(view['seek']['seeked_events'][0]['is_trusted']);self.assertEqual(view['reopen']['generation_after'],1)
  self.assertEqual(view['reopen']['media'][0]['after']['decoded_cid'],CID)
  controls={c['selector']:c['after']for c in view['failure_controls']['controls']}
  self.assertFalse(controls['#play']['enabled']);self.assertTrue(controls['#cid']['enabled'])
  self.assertEqual(view['retry_source_values'][0]['observed_after']['value'],CID)
  self.assertEqual(view['probe_temporal_samples'][0]['sample_ms'],250)
  self.assertEqual(view['probe_temporal_samples'][0]['before'],1.0)
  self.assertEqual(view['probe_temporal_samples'][0]['after'],1.25)
  self.assertLess(len(final.encoded(final.projection(self.root,self.group['report']))),18000)

 def test_historical_v2_without_optional_extension_unchanged(self):
  for child in self.group['children']:child.pop('phase_evidence')
  self.f.persist(self.group);self.validate()
  self.assertNotIn('phase_evidence',final.projection(self.root,self.group['report'])['viewports'][0])

 def test_action_selector_or_value_substitution(self):self.changed(lambda e:e['phases'][0]['steps'][0]['step'].update(value='fake-source'))
 def test_step_order_is_exact(self):self.changed(lambda e:e['phases'][0]['steps'].reverse())
 def test_missing_step_refused(self):self.changed(lambda e:e['phases'][0]['steps'].pop())
 def test_generation_jump_refused(self):self.changed(lambda e:e['phases'][0]['steps'][1].update(generation_after=1))
 def test_bool_step_index_refused(self):self.changed(lambda e:e['phases'][0]['steps'][0].update(step_index=False))
 def test_nonmonotonic_capture_times_refused(self):self.changed(lambda e:e['phases'][0]['steps'][2].update(started_ms=0))
 def test_nonfinite_native_time_refused(self):self.changed(lambda e:e['phases'][0]['steps'][2]['media'][0]['after'].update(current_time=float('inf')))
 def test_nonoriginal_media_selector_refused(self):self.changed(lambda e:e['phases'][0]['steps'][2]['media'][0].update(selector='#private'))
 def test_synthetic_trusted_flag_refused(self):self.changed(lambda e:e['phases'][0]['steps'][2]['media'][0]['seeked_events'][0].update(is_trusted=1))
 def test_temporal_actual_delta_forgery_refused(self):self.changed(lambda e:e['phases'][0]['steps'][3]['temporal_samples'][0].update(after=8.0))
 def test_actual_probe_value_rebinding_refused(self):self.changed(lambda e:e['phases'][0]['steps'][3]['observed'].update(actual=9.0))
 def test_error_checkpoint_missing_retry_control_refused(self):self.changed(lambda e:e['phases'][2]['steps'][1]['controls'].pop())
 def test_missing_reopen_window_disconnection_refused(self):self.changed(lambda e:e['phases'][1]['steps'][0]['reopen'].update(old_window_disconnected=False))
 def test_numeric_reopen_flag_cannot_impersonate_boolean(self):self.changed(lambda e:e['phases'][1]['steps'][0]['reopen'].update(old_window_disconnected=1))
 def test_missing_reopen_media_refused(self):self.changed(lambda e:e['phases'][1]['steps'][0].update(media=[]))
 def test_phase_version_unknown_refused(self):self.changed(lambda e:e.update(schema='unknown'))
 def test_control_value_bound_refused(self):self.changed(lambda e:e['phases'][2]['steps'][2]['controls'][0]['after'].update(value='x'*8193))
 def test_untrusted_events_do_not_claim_meaningful_native_seek(self):
  for child in self.group['children']:child['phase_evidence']['phases'][0]['steps'][2]['media'][0]['seeked_events'][0]['is_trusted']=False
  self.f.persist(self.group);self.validate();self.assertIsNone(final.projection(self.root,self.group['report'])['viewports'][0]['phase_evidence']['seek'])
 def test_other_phase_hashes_cannot_supply_missing_probe_samples(self):self.changed(lambda e:e['phases'][2]['steps'][4].update(temporal_samples=[]))

 def test_same_fake_CID_markers_remain_raw_but_are_not_projected_as_identity_pairs(self):
  child=self.group['children'][0]
  for phase in child['phase_evidence']['phases']:
   for row in phase['steps']:
    for item in row['media']:
     for key in ['before','after']:
      if item[key]and item[key]['present']:item[key]['decoded_cid']='same-fake-marker'
  self.f.persist(self.group);self.validate();p=final.phase_projection(child,self.scenario)
  self.assertIsNone(p['seek']);self.assertEqual(p['reopen']['identity_pairs'],[])
  self.assertEqual(p['reopen']['media'][0]['before']['decoded_cid'],'same-fake-marker')

 def test_canonical_different_CID_does_not_join_actual_owner_result(self):
  import base64
  other='b'+base64.b32encode(b'\x01\x55\x12\x20'+bytes(32)).decode().rstrip('=').lower()
  self.assertTrue(final._phase_raw_cid(other));child=self.group['children'][0]
  child['backend_observations']=[{'result_assertion':{'actual':other,'expected':other}}]
  p=final.phase_projection(child,self.scenario);self.assertIsNone(p['seek']);self.assertEqual(p['reopen']['identity_pairs'],[])
  self.assertEqual(p['owner_result_cids'],[other]);self.assertEqual(p['reopen']['media'][0]['before']['decoded_cid'],CID)

 def test_canonical_exact_owner_CID_joins_selected_pair(self):
  child=self.group['children'][0];child['backend_observations']=[{'result_assertion':{'actual':CID,'expected':CID}}]
  p=final.phase_projection(child,self.scenario);self.assertIsNotNone(p['seek']);self.assertEqual(p['reopen']['identity_pairs'][0]['decoded_cid'],CID)

 def test_expected_only_CID_is_not_a_returned_owner_identity(self):
  import base64
  actual='b'+base64.b32encode(b'\x01\x55\x12\x20'+bytes(32)).decode().rstrip('=').lower()
  child=self.group['children'][0];child['backend_observations']=[{'result_assertion':{'operator':'not_equals','actual':actual,'expected':CID}}]
  p=final.phase_projection(child,self.scenario);self.assertEqual(p['owner_result_cids'],[actual])
  self.assertIsNone(p['seek']);self.assertEqual(p['reopen']['identity_pairs'],[])

 def test_native_event_presentation_is_bounded_without_losing_raw_events(self):
  child=self.group['children'][0];record=child['phase_evidence']['phases'][0]['steps'][2]['media'][0]
  record['seeked_events']*=8
  p=final.phase_projection(child,self.scenario);self.assertEqual(len(p['seek']['seeked_events']),1)
  self.assertEqual(p['seek']['native_event_count'],8);self.assertEqual(len(record['seeked_events']),8)

 def test_local_null_CID_native_source_identity_needs_no_backend_call(self):
  child=self.group['children'][0]
  for phase in child['phase_evidence']['phases']:
   for row in phase['steps']:
    for item in row['media']:
     for key in ['before','after']:
      if item[key]and item[key]['present']:item[key]['decoded_cid']=None
  p=final.phase_projection(child,self.scenario);self.assertIsNotNone(p['seek']);self.assertEqual(p['owner_result_cids'],[])
  self.assertIsNone(p['reopen']['identity_pairs'][0]['decoded_cid'])

 def test_native_empty_source_never_promotes_stale_decoded_marker(self):
  child=self.group['children'][0]
  for phase in child['phase_evidence']['phases']:
   for row in phase['steps']:
    for item in row['media']:
     for key in ['before','after']:
      if item[key]and item[key]['present']:item[key].update(ready_state=0,src_sha256=None)
  p=final.phase_projection(child,self.scenario);self.assertIsNone(p['seek']);self.assertEqual(p['reopen']['identity_pairs'],[])

 def test_secret_control_contents_are_not_accepted(self):
  self.changed(lambda e:e['phases'][2]['steps'][2]['controls'][0]['after'].update(type='password',value='unacceptable-secret'))

 def test_review_compaction_preserves_all_values_and_other_modes_literal_bytes(self):
  value={'schema':'swissknife.visual-functional-review-input.v2','projection_only':True,'facts':{'raw_cid':CID,'actual':[0.2,0.6],'text':'spaces and\nnewlines stay literal'}}
  raw=(json.dumps(value,indent=2)+'\n').encode();compacted=shapes.llm._review_input_text(raw,'review')
  self.assertEqual(json.loads(compacted),value);self.assertLess(len(compacted.encode()),len(raw))
  self.assertEqual(shapes.llm._review_input_text(raw,'repair'),raw.decode())
  self.assertEqual(shapes.llm._review_input_text(b'not JSON\n','review'),'not JSON\n')
  legacy=json.dumps({'schema':'swissknife.visual-functional-review-input.v1','projection_only':True},indent=2).encode()
  self.assertEqual(shapes.llm._review_input_text(legacy,'review'),legacy.decode())

 def test_typed_review_compaction_refuses_duplicate_and_nonfinite_fields(self):
  for suffix in ['"value":1,"value":2','"value":NaN','"value":1e999']:
   raw=('{"schema":"swissknife.visual-functional-review-input.v2","projection_only":true,'+suffix+'}').encode()
   with self.subTest(value=suffix),self.assertRaises(shapes.llm.ModelAdapterError):shapes.llm._review_input_text(raw,'review')

 def test_actual_adapter_prompt_budget_is_checked_before_provider_with_caps_unchanged(self):
  profile=copy.deepcopy(self.f.profile);profile['llm'].update(timeoutSeconds=600,maxTurns=24,maxOutputTokens=16384)
  self.f.write('config/swissknife_visual_functional_supervisor.json',profile)
  sources=final.source_snapshot(self.root,profile,self.group['task']);self.group['sources']=sources
  for child in self.group['children']:child.update(sources)
  self.f.persist(self.group);validated=final.validate_dual_workflow(self.root,profile,self.group['task'],self.group['report'],observation_validator=shapes.worker.validate_observed,backend_validator=shapes.worker.validate_backend_observation)
  directory=self.group['folder']/'model-inputs/authored-budget'
  context=self.f.write(str((directory/'context.json').relative_to(self.root)),{'task':self.group['task'],'final_workflow_evidence':final.binding(self.group['task'],validated)})
  evidence=self.f.write(str((directory/'evidence-0.json').relative_to(self.root)),final.projection(self.root,self.group['report']))
  raw_evidence=evidence.read_bytes();raw_sha=shapes.hashlib.sha256(raw_evidence).hexdigest()
  class BeforeProvider(Exception):pass
  captured=[]
  def refuse_provider(_root):
   frame=inspect.currentframe().f_back
   while frame is not None and 'prompt' not in frame.f_locals:frame=frame.f_back
   self.assertIsNotNone(frame);prompt=frame.f_locals['prompt'];settings=frame.f_locals['settings'];captured.append(len(prompt.encode()))
   self.assertLessEqual(len(prompt.encode()),32768);self.assertEqual(settings['maxTurns'],8);self.assertEqual(settings['maxOutputTokens'],12288);self.assertEqual(settings['modelContextBytes'],32768)
   self.assertIn('seeked_events',prompt);self.assertIn(CID,prompt);self.assertIn('observed_after',prompt)
   retained=next(record for record in frame.f_locals['records']if record['path']==str(evidence.relative_to(self.root)))
   self.assertEqual(retained['sha256'],raw_sha);self.assertEqual(evidence.read_bytes(),raw_evidence)
   raise BeforeProvider()
  with patch.object(shapes.llm,'_load_backend',side_effect=refuse_provider):
   with self.assertRaises(BeforeProvider):
    shapes.llm.invoke_task_model('config/swissknife_visual_functional_supervisor.json',self.group['task']['task_id'],'review',root=self.root,input_paths=[str(context.relative_to(self.root)),str(evidence.relative_to(self.root))],screenshot_paths=[c['result_screenshot']['path']for c in self.group['children']],predicted_files=[])
  self.assertEqual(len(captured),1);self.prompt_bytes=captured[0]

if __name__=='__main__':unittest.main()
