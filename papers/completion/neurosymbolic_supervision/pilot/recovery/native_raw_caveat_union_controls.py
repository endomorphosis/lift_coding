"""Actual native packing controls on constructed public metadata; no target execution."""
import sys
sys.dont_write_bytecode=True
import os,json,hashlib,importlib.util,dataclasses,resource,time,unittest
from pathlib import Path
OUT=Path('/qualification-output');CFG=json.loads(Path('/qualification/invocation.json').read_text())
os.environ.update(IPFS_ACCEL_SKIP_CORE='1',IPFS_AUTO_INSTALL='false',IPFS_DATASETS_AUTO_INSTALL='false',IPFS_KIT_AUTO_INSTALL='false',PYTHONDONTWRITEBYTECODE='1')
sys.path[:0]=[CFG[k] for k in ('service_source','accelerate_source','datasets_source','kit_source','runtime_python')]
from ipfs_accelerate_py.agent_supervisor.semantic_state import context_pack as NEW
from ipfs_accelerate_py.agent_supervisor.semantic_state.capsules import admit_capsule,ADMISSION_RAW,ADMISSION_EXACT,ADMISSION_CONSERVATIVE
from ipfs_accelerate_py.agent_supervisor.semantic_state.contracts import HarnessError
from ipfs_accelerate_py.agent_supervisor.semantic_state.wire import cid_for_payload
from ipfs_accelerate_py.agent_supervisor.context.context_contracts import ContextBudget
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(NEW.__file__)==CFG['candidate_context_sha256'];assert sha('/qualification/original_context_pack.py')==CFG['original_context_sha256']
spec=importlib.util.spec_from_file_location('native_caveat_original_qualified', '/qualification/original_context_pack.py');OLD=importlib.util.module_from_spec(spec);sys.modules[spec.name]=OLD;spec.loader.exec_module(OLD)
def cid(s):return cid_for_payload({'public_control_label':s})
def admission(label,confidence='heuristic'):
 capsule={'capsule_cid':cid('capsule-'+label),'stable_symbol_id':'public.'+label,'version_cid':cid('version-'+label),'source_cid':cid('source-'+label),'confidence':confidence}
 assessment=None if confidence in ('heuristic','opaque') else {'freshness':'fresh','admission':ADMISSION_EXACT if confidence=='exact' else ADMISSION_CONSERVATIVE,'caveats':[] if confidence=='exact' else ['confidence:conservative'],'assessment_cid':cid('assessment-'+label)}
 return admit_capsule(capsule,semantic_state_root_cid=cid('root'),assessment=assessment)
def pack(mod,admissions,assumptions=('public context only',)):
 return mod.ContextPacker(budget=ContextBudget(max_input_tokens=50000,reserved_output_tokens=256,reserved_tool_tokens=64)).pack(objective='public constructed packing control',target_source_cid=cid('target'),surrounding_source_cid=cid('surrounding'),test_source_cid=cid('tests'),delta_cid=cid('delta'),dependency_admissions=admissions,assumptions=assumptions)
class Controls(unittest.TestCase):
 def test_original_multicapsule_reproduces_duplicate_failure(self):
  with self.assertRaisesRegex(HarnessError,'assumptions must not contain duplicates'):pack(OLD,[admission('one'),admission('two')])
 def test_shared_caveats_union_preserves_raw_references_and_admissions(self):
  aa=[admission('one'),admission('two')];before=[a.to_dict() for a in aa];result=pack(NEW,aa)
  self.assertEqual(before,[a.to_dict() for a in aa]);self.assertTrue(result.coverage_satisfied);self.assertFalse(result.budget_exceeded)
  self.assertEqual(result.pack.assumptions,tuple(sorted({'public context only'}|{'caveat:'+c for a in aa for c in a.caveats})))
  refs=[r for r in result.references if r.kind=='raw_dependency_source'];self.assertEqual(len(refs),2)
  self.assertEqual({r.referenced_content_id for r in refs},{a.ref.source_cid for a in aa});self.assertTrue(all(r.required and r.metadata['raw_source_required'] for r in refs));self.assertEqual(result.pack.dependency_capsule_cids,())
  for a in aa:
   ref=next(r for r in refs if r.metadata['capsule_cid']==a.ref.capsule_cid);self.assertEqual(ref.metadata['caveats'],a.caveats);self.assertEqual(ref.metadata['confidence'],a.ref.confidence)
 def test_distinct_raw_caveats_projection_and_cid_unchanged(self):
  aa=[dataclasses.replace(admission('one'),caveats=('distinct-one',)),dataclasses.replace(admission('two'),caveats=('distinct-two',))];self.assertEqual(pack(OLD,aa).to_dict(),pack(NEW,aa).to_dict())
 def test_single_raw_cid_and_complete_projection_unchanged(self):
  for conf in ('heuristic','opaque'):
   aa=[admission('single',conf)];self.assertEqual(pack(OLD,aa).to_dict(),pack(NEW,aa).to_dict())
 def test_exact_and_conservative_projection_unchanged(self):
  aa=[admission('exact','exact'),admission('cons1','conservative'),admission('cons2','conservative')];self.assertEqual(pack(OLD,aa).to_dict(),pack(NEW,aa).to_dict())
 def test_multicapsule_order_stable(self):
  aa=[admission('one'),admission('two'),admission('three','opaque')];self.assertEqual(pack(NEW,aa).to_dict(),pack(NEW,list(reversed(aa))).to_dict())
 def test_explicit_assumption_collision_retained_once(self):
  aa=[admission('one')];existing='caveat:'+aa[0].caveats[0];self.assertEqual(pack(NEW,aa,(existing,)).pack.assumptions.count(existing),1)
 def test_duplicate_caller_assumptions_still_rejected(self):
  for mod in [OLD,NEW]:
   with self.assertRaisesRegex(HarnessError,'assumptions must not contain duplicates'):pack(mod,[],('duplicate','duplicate'))
 def test_malformed_caller_assumption_still_rejected(self):
  for mod in [OLD,NEW]:
   with self.assertRaises(HarnessError):pack(mod,[],('',))
 def test_native_admission_duplicate_caveats_still_rejected(self):
  with self.assertRaisesRegex(HarnessError,'caveats must not contain duplicates'):dataclasses.replace(admission('one'),caveats=('duplicate','duplicate'))
if __name__=='__main__':
 start=time.monotonic();cpu=time.process_time();result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
 receipt={'schema':'ns-native-raw-caveat-union-qualification/v1','success':result.wasSuccessful(),'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'native_source_pins':CFG['native_source_pins'],'candidate_context_sha256':sha(NEW.__file__),'original_context_sha256':sha('/qualification/original_context_pack.py'),'native_module_origin':NEW.__file__,'wall_seconds':time.monotonic()-start,'cpu_seconds':time.process_time()-cpu,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'constructed_control_inputs':True,'actual_native_packing_calls':True,'target_source_executed':False,'oracle_read':False,'provider_calls':0,'scorer_calls':0,'scientific_calls':0}
 fd=os.open(OUT/'result.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w')as f:json.dump(receipt,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 print(json.dumps(receipt));raise SystemExit(0 if result.wasSuccessful() else 1)
