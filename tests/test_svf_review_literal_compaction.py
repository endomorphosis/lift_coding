"""Portable typed presentation codec tests; no browser/provider/acceptance."""
import copy
import os
from pathlib import Path
import sys
import unittest

BASE = Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT', str(Path(__file__).resolve().parents[1])))
sys.path.insert(0, str(Path(os.environ.get('SVF_VPC_CANDIDATE_SCRIPTS', str(BASE / 'scripts')))))
import swissknife_visual_functional_final_coverage as final

class ReviewLiteralCompactionTests(unittest.TestCase):
    def evidence(self):
        metadata={'requirement_text':'Keep the actual edited source and decoded native result, then restore exact persisted bytes. '*25,
                  'probe':{'kind':'json_attribute','selector':'[data-native-result]','pointer':'/source'},
                  'observed':{'operator':'equals','actual':{'cid':'bafkreia'+'a'*52,'sha256':'7'*64,'bytes':1552,'size':[64,48],
                     'typed':[0,1,1.0,-0.0,False,True,None,'雪\\"\n'],'native':{'review_ref':'r0','review_ref_1':'native-value',
                       'shared_review_literals':{'ordinary_native_data':True},'shared_review_literals_semantics':'ordinary text'}},
                     'expected':{'saved':True}}}
        views=[]
        for index,name in enumerate(('desktop','mobile')):
            views.append({'name':name,'session_id':str(index)+'-distinct-native-session',
                'semantic_assertions':[copy.deepcopy(metadata)for _ in range(3)],
                'backend_observations':[{'result_assertion':copy.deepcopy(metadata['observed']),
                    'receipt_artifact':{'path':'runtime/'+name+'/actual-receipt.json','sha256':str(index)*64,'bytes':501}}],
                'additional_backend_phase_proofs':[{'request_phase':{'phase':'failure_recovery','step_index':7},'result_assertion':copy.deepcopy(metadata['observed']),'artifact_indexes':[3,4]}],
                'native_seek':{'time':index+0.12345678901234,'is_trusted':True,'events':[0.5,1.25]}})
        return {'schema':'swissknife.visual-functional-review-input.v2','projection_only':True,'viewports':views,
                'unique_context':'z'*5000,'authority':'authored codec vector only'}

    def compact(self):
        original=self.evidence();self.assertGreater(len(final.encoded(original)),18000)
        result=final._factor_projection(original);self.assertLess(len(final.encoded(result)),18000)
        return original,result

    def find_ref(self,result):
        marker=result['shared_review_literals_reference_key']
        def visit(item):
            if type(item)is dict:
                if marker in item:return item
                for key,value in item.items():
                    if key not in {'shared_review_literals','shared_review_literals_semantics'}:
                        found=visit(value)
                        if found is not None:return found
            if type(item)is list:
                for value in item:
                    found=visit(value)
                    if found is not None:return found
        return marker,visit(result)

    def test_exact_typed_roundtrip_preserves_every_native_field_and_reference(self):
        original,result=self.compact();expanded=final._expand_projection(result)
        self.assertEqual(final.encoded(expanded),final.encoded(original))
        for old,compacted in zip(original['viewports'],result['viewports']):
            self.assertEqual(final.encoded(old['backend_observations']),final.encoded(compacted['backend_observations']))
            self.assertEqual(final.encoded(old['additional_backend_phase_proofs']),final.encoded(compacted['additional_backend_phase_proofs']))
        for old,new in zip(original['viewports'],expanded['viewports']):
            self.assertEqual(old['session_id'],new['session_id']);self.assertEqual(old['native_seek'],new['native_seek'])
            self.assertEqual(old['backend_observations'],new['backend_observations'])
        values=expanded['viewports'][0]['semantic_assertions'][0]['observed']['actual']['typed']
        self.assertIs(type(values[0]),int);self.assertIs(type(values[2]),float);self.assertIs(values[4],False)
        self.assertEqual(final.encoded(values[3]),b'-0.0')

    def test_all_native_marker_and_metadata_keys_remain_literal(self):
        original,result=self.compact();marker=result['shared_review_literals_reference_key']
        self.assertEqual(marker,'review_ref_2');self.assertNotIn(marker,final._review_dictionary_keys(original))
        expanded=final._expand_projection(result);native=expanded['viewports'][0]['semantic_assertions'][0]['observed']['actual']['native']
        self.assertEqual(native,original['viewports'][0]['semantic_assertions'][0]['observed']['actual']['native'])

    def test_no_table_preserves_even_marker_shaped_native_json_unchanged(self):
        value={'viewports':[],'owner_actual':{'review_ref':'r0','extra':False,'nested':{'shared_review_literals':'native'}}}
        self.assertEqual(final.encoded(final._expand_projection(value)),final.encoded(value))
        self.assertIs(final._factor_projection(value),value)

    def test_unknown_reference_refused(self):
        _,result=self.compact();marker,reference=self.find_ref(result);reference[marker]='r999'
        with self.assertRaises(ValueError):final._expand_projection(result)

    def test_reference_cannot_silently_add_or_delete_fields(self):
        _,result=self.compact();_,reference=self.find_ref(result);reference['unexpected']='discarded?'
        with self.assertRaises(ValueError):final._expand_projection(result)

    def test_nested_reference_or_cycle_in_literal_table_refused(self):
        _,result=self.compact();marker,_=self.find_ref(result);key=next(iter(result['shared_review_literals']))
        result['shared_review_literals'][key]={marker:key}
        with self.assertRaises(ValueError):final._expand_projection(result)

    def test_unused_values_and_changed_semantics_refused(self):
        _,result=self.compact();changed=copy.deepcopy(result);changed['shared_review_literals']['r63']='unreachable'
        with self.assertRaises(ValueError):final._expand_projection(changed)
        result['shared_review_literals_semantics']='assume matching sessions'
        with self.assertRaises(ValueError):final._expand_projection(result)

    def test_metadata_without_table_refused(self):
        value={'viewports':[],'shared_review_literals_reference_key':'review_ref'}
        with self.assertRaises(ValueError):final._expand_projection(value)

    def test_deterministic_fresh_key_and_no_input_mutation(self):
        original=self.evidence();before=final.encoded(original);first=final._factor_projection(original);second=final._factor_projection(copy.deepcopy(original))
        self.assertEqual(final.encoded(first),final.encoded(second));self.assertEqual(final.encoded(original),before)

    def test_unique_evidence_is_not_dropped_to_force_budget_acceptance(self):
        value={'viewports':[],'unique_native_payload':'u'*19000}
        result=final._factor_review_literals(value)
        self.assertIs(result,value);self.assertGreater(len(final.encoded(result)),18000)
        self.assertEqual(final.encoded(final._expand_projection(result)),final.encoded(value))

if __name__=='__main__':unittest.main()
