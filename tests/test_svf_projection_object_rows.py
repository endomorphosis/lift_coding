"""Portable authored codec tests; no browser, owner or provider evidence."""
import copy,importlib.util,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
candidate=ROOT/'scripts/swissknife_visual_functional_final_coverage.py'
if not candidate.exists():candidate=Path(__file__).resolve().parents[1]/'scripts/swissknife_visual_functional_final_coverage.py'
spec=importlib.util.spec_from_file_location('svf_object_rows_under_test',candidate)
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)

class ObjectRowsTests(unittest.TestCase):
 def value(self):
  return {'viewports':[{'name':view,'session_id':view+'-different-session',
    'original':{'path':'tasks/'+view+'/workflow.json','sha256':str(index)*64,'bytes':321+index},
    'result_screenshot':{'path':'tasks/'+view+'/result.png','sha256':str(index+2)*64,'bytes':123+index},
    'facts':[{'long_first_field':number,'long_second_field':view,'long_third_field':[-0.0,0,0.0,False,True,None,'雪\n']}for number in range(6)],
    'backend_observations':[{'owner':'ipfs_kit_py','result_assertion':{'actual':{'@':[0,'native literal'],'~':'native literal','review_ref':'r0','object_schemas':None},'expected':None,'operator':'not_equals'}}]}
   for index,view in enumerate(('desktop','mobile'))]}
 def factored(self):return f._factor_projection_objects(self.value())
 def test_exact_typed_roundtrip_is_deterministic(self):
  value=self.value();result=self.factored();self.assertIn('object_schemas',result)
  self.assertEqual(f.encoded(f._expand_projection_objects(result)),f.encoded(value))
  self.assertEqual(f.encoded(result),f.encoded(self.factored()))
 def test_opaque_asserted_payload_and_distinct_sessions_refs_remain_exact(self):
  value=self.value();result=self.factored();self.assertNotEqual(result['object_row_marker'],'@')
  decoded=f._expand_projection_objects(result)
  for before,after in zip(value['viewports'],decoded['viewports']):
   for key in ('name','session_id','original','result_screenshot','backend_observations'):
    self.assertEqual(f.encoded(before[key]),f.encoded(after[key]))
 def test_short_existing_literal_marker_preserves_literal_table_and_tree(self):
  value=self.value();value['repeat']=['long-fact-'+('x'*100)]*4
  old=f._factor_review_literals(value);short=f._shorten_projection_literal_marker(old)
  self.assertEqual(old['shared_review_literals'],short['shared_review_literals'])
  self.assertEqual(f.encoded(f._expand_review_literals(short)),f.encoded(value))
  self.assertLess(len(f.encoded(short)),len(f.encoded(old)))
  self.assertNotEqual(short['shared_review_literals_reference_key'],'~')
 def test_metadata_absence_compatible_but_null_or_partial_refused(self):
  value={'viewports':[]};self.assertEqual(f._expand_projection_objects(value),value)
  for bad in [{'object_schemas':None},{key:None for key in f._OBJECT_ROWS_FIELDS},
              {'object_row_marker':'@'},{'object_rows_semantics':f._OBJECT_ROWS_SEMANTICS}]:
   with self.subTest(bad=bad),self.assertRaises(ValueError):f._expand_projection_objects({**value,**bad})
 def test_unknown_schema_bool_index_arity_and_mixed_marker_refused(self):
  value=self.factored();marker=value['object_row_marker']
  for row in [[999],[True],[0],[0,*([None]*100)]]:
   bad=copy.deepcopy(value);bad['injected']={marker:row}
   with self.subTest(row=row[:2]),self.assertRaises(ValueError):f._expand_projection_objects(bad)
  bad=copy.deepcopy(value);bad['injected']={marker:[0], 'other':'collision'}
  with self.assertRaises(ValueError):f._expand_projection_objects(bad)
 def test_duplicate_unsorted_and_delimiter_injected_schema_refused(self):
  value=self.factored()
  for schema in ['a|a|b','z|y|x','a|b|@','a|b','a||b']:
   bad=copy.deepcopy(value);bad['object_schemas'][0]=schema
   with self.subTest(schema=schema),self.assertRaises(ValueError):f._expand_projection_objects(bad)
  bad=copy.deepcopy(value);bad['object_schemas'].append(bad['object_schemas'][0])
  with self.assertRaises(ValueError):f._expand_projection_objects(bad)
 def test_unused_schema_bad_caption_and_marker_refused(self):
  value=self.factored();bad=copy.deepcopy(value);bad['object_schemas'].append('authored_a|authored_b|authored_c')
  with self.assertRaises(ValueError):f._expand_projection_objects(bad)
  for key,item in [('object_rows_semantics','different'),('object_row_marker','bad-marker')]:
   bad=copy.deepcopy(value);bad[key]=item
   with self.assertRaises(ValueError):f._expand_projection_objects(bad)
 def test_actual_payload_active_marker_is_literal_not_a_protocol_row(self):
  value=self.value();value['opaque']={'actual':None};result=f._factor_projection_objects(value)
  marker=result['object_row_marker'];result['opaque']['actual']={marker:[999,'native-data']}
  self.assertEqual(f._expand_projection_objects(result)['opaque']['actual'],{marker:[999,'native-data']})
 def test_fitting_projection_and_legacy_literal_codec_are_unchanged(self):
  value={'viewports':[],'literal':[False,0,-0.0,None]}
  self.assertIs(f._factor_projection(value),value)
  old=f._factor_review_literals({**self.value(),'repeat':['same'*50]*4})
  self.assertTrue(old['shared_review_literals_reference_key'].startswith('review_ref'))
  self.assertEqual(f.encoded(f._expand_projection(old)),f.encoded({**self.value(),'repeat':['same'*50]*4}))
 def test_full_fallback_retains_owner_fields_and_all_original_data(self):
  value=self.value()
  for view in value['viewports']:
   view['backend_observations']=[{'owner':'ipfs_kit_py','binding_id':'app.ipfs_kit_py.persist_artifact','transport':'http',
    'correlation_id':view['name']+'-'+str(i),'receipt_verified':True,'semantic_result_verified':True,
    'receipt_artifact':{'path':'backend/receipt-'+str(i)+'.json','sha256':str(i%10)*64,'bytes':3000+i},
    'result_assertion':{'actual':'unique-'+view['name']+str(i)+('x'*200),'expected':None,'operator':'not_equals'}}for i in range(30)]
  result=f._factor_projection(value)
  self.assertIn('object_schemas',result)
  self.assertEqual(f.encoded(f._expand_projection(result)),f.encoded(value))
  self.assertLess(len(f.encoded(result)),len(f.encoded(value)))

if __name__=='__main__':unittest.main()
