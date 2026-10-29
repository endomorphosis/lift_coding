"""Canonical SDK execution and failed-RPC diagnostics; no SDK/service calls."""
from pathlib import Path
import hashlib,importlib.util,json,os,tempfile,unittest,uuid
from unittest.mock import patch
STAGE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('execution_diagnostic_gate',STAGE/'scripts/svf_backends/validate_supervisor_foundation.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
class ExecutedArgv(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name).resolve();self.binary=self.root/'registered-python';self.binary.write_bytes(b'authored pinned interpreter bytes; never executed\n');self.binary.chmod(0o755)
  self.alias=self.root/'external/ipfs_datasets/.venv/bin/python';self.alias.parent.mkdir(parents=True);self.alias.symlink_to(self.binary)
  self.path=self.root/'config/swissknife_visual_functional_foundation_owners.json';self.path.parent.mkdir();self.cfg={'schema':'swissknife.foundation-service-registration.v1','status':'REGISTERED','root':str(self.root),'units':{'swissknife-visual-functional-native-accelerate.service':{'argv':[str(self.alias),'-B','protected-entry.py'],'binary_sha256':hashlib.sha256(self.binary.read_bytes()).hexdigest()}}};self.save()
  self.argv=[str(self.alias),'-I','-B',str(self.root/'scripts/fixed.py'),'--runtime-root',str(self.root/'runtime'),'--run-id',str(uuid.uuid4()),'--stage','a','--challenge','a'*32,'--mode','normal']
 def save(self):self.path.write_text(json.dumps(self.cfg));self.path.chmod(0o600)
 def test_only_argv_zero_is_canonicalized_to_the_pinned_binary(self):
  original=list(self.argv);result=gate.executed_argv(self.argv,root=self.root);self.assertEqual(result,[str(self.binary),*original[1:]]);self.assertEqual(self.argv,original)
 def test_script_flags_and_data_are_not_path_normalized(self):
  self.argv[3]=str(self.root/'scripts/../fixed.py');result=gate.executed_argv(self.argv,root=self.root);self.assertEqual(result[1:],self.argv[1:]);self.assertIn('/../',result[3]);changed=list(result);changed[1]='-S';self.assertNotEqual(changed,gate.executed_argv(self.argv,root=self.root))
 def test_arbitrary_executable_is_rejected_even_with_same_bytes(self):
  other=self.root/'other-alias';other.symlink_to(self.binary)
  with self.assertRaisesRegex(ValueError,'registered Python alias'):gate.executed_argv([str(other),*self.argv[1:]],root=self.root)
 def test_changed_binary_bytes_fail_the_registered_sha(self):
  self.binary.write_bytes(b'different executable bytes')
  with self.assertRaisesRegex(ValueError,'binary changed'):gate.executed_argv(self.argv,root=self.root)
 def test_changed_registration_pin_or_alias_refuses(self):
  self.cfg['units']['swissknife-visual-functional-native-accelerate.service']['binary_sha256']='0'*64;self.save()
  with self.assertRaisesRegex(ValueError,'binary changed'):gate.executed_argv(self.argv,root=self.root)
  self.cfg['units']['swissknife-visual-functional-native-accelerate.service']['argv']=[];self.save()
  with self.assertRaisesRegex(ValueError,'pin differs'):gate.executed_argv(self.argv,root=self.root)
 def test_unsafe_registration_and_executable_modes_refuse(self):
  self.path.chmod(0o666)
  with self.assertRaisesRegex(ValueError,'unsafe executable registration'):gate.executed_argv(self.argv,root=self.root)
  self.path.chmod(0o600);self.binary.chmod(0o777)
  with self.assertRaisesRegex(ValueError,'unsafe registered executable'):gate.executed_argv(self.argv,root=self.root)
 def test_fixed_argv_keeps_the_literal_alias_for_database_and_sdk_entry(self):
  with patch.object(gate,'SDK_ROOT',self.root),patch.object(gate,'HERE',self.root/'scripts/svf_backends'):
   expected=gate.fixed_argv(self.root/'runtime','run','a','challenge');self.assertEqual(expected[0],str(self.alias));self.assertNotEqual(expected[0],gate.executed_argv(expected,root=self.root)[0])
 def test_canonical_result_still_requires_an_independent_kernel_witness(self):
  raw={'schema':'ipfs_accelerate_py/agent-supervisor/verification-process-runner@1','process_started':True,'lease_id':'resource-lease:authored','command_argv':gate.executed_argv(self.argv,root=self.root),'pid':99999999,'process_group_id':99999999}
  original=gate.executed_argv
  with patch.object(gate,'sdk_artifact',return_value=raw),patch.object(gate,'fixed_argv',return_value=self.argv),patch.object(gate,'executed_argv',side_effect=lambda argv:original(argv,root=self.root)):
   with self.assertRaisesRegex(ValueError,'independent kernel'):gate.check_execution({'execution':{'producer':{},'validator':{}}},self.root/'run',self.root,'run','a','challenge',[])

class RpcDiagnostics(unittest.TestCase):
 def call(self,make,*,allow_error=False,args=None):
  args=args or {'fixture_mode':gate.MODE,'action':'dispatch','run_id':str(uuid.UUID(int=4)),'task_key':'a','dry_run':False};seen=[]
  class Response:
   def __init__(self,data):self.data=data
   def __enter__(self):return self
   def __exit__(self,*a):return False
   def read(self,maximum):self.maximum=maximum;return self.data
  def respond(request,timeout):
   packet=json.loads(request.data);value=make(packet);seen.append(value);return Response(value if type(value)is bytes else json.dumps(value).encode())
  with patch.object(gate.urllib.request,'urlopen',side_effect=respond):
   try:return gate.rpc('http://127.0.0.1:18315/mcp',gate.ALIAS,args,allow_error=allow_error),seen
   except ValueError as error:error.observed=seen;raise
 def failed(self,make,**kwargs):
  with self.assertRaises(ValueError)as error:self.call(make,**kwargs)
  message=str(error.exception);self.assertTrue(message.startswith('real supervisor MCP operation failed: '));self.assertLessEqual(len(message.encode()),4096)
  return json.loads(message.split(': ',1)[1]),error.exception.observed[-1]
 def test_actual_jsonrpc_error_message_is_kept_with_raw_response_hash(self):
  summary,value=self.failed(lambda p:{'jsonrpc':'2.0','id':p['id'],'error':{'code':-32000,'message':"[Errno 2] No such file: '/owned/run/attempts/uuid'"}})
  self.assertEqual(summary['jsonrpc_error']['code_text'],'-32000');self.assertIn('attempts/uuid',summary['jsonrpc_error']['message']);self.assertEqual(summary['response_sha256'],hashlib.sha256(json.dumps(value).encode()).hexdigest());self.assertFalse(summary['completion_authority'])
 def test_native_mcp_error_code_and_text_are_kept(self):
  summary,_=self.failed(lambda p:{'jsonrpc':'2.0','id':p['id'],'result':{'isError':True,'content':[{'type':'json','json':{'error':{'code':'supervisor_failed','message':'actual fixture failed'}}}]}})
  self.assertTrue(summary['mcp_is_error']);self.assertEqual(summary['native_error']['code_text'],'supervisor_failed');self.assertEqual(summary['native_error']['message'],'actual fixture failed')
 def test_text_mcp_error_is_kept(self):
  summary,_=self.failed(lambda p:{'jsonrpc':'2.0','id':p['id'],'result':{'isError':True,'content':[{'type':'text','text':'specific actual owner exception'}]}});self.assertIn('specific actual owner exception',summary['mcp_text'])
 def test_multibyte_and_escape_heavy_messages_stay_bounded(self):
  summary,_=self.failed(lambda p:{'jsonrpc':'2.0','id':p['id'],'error':{'code':-1,'message':'😀\\"\n'*2000},'result':{'isError':True,'content':[{'type':'text','text':'😀\\"\n'*2000}]}});self.assertLessEqual(len(json.dumps(summary,separators=(',',':'),ensure_ascii=False).encode()),3500)
 def test_sensitive_labels_and_url_credentials_are_redacted(self):
  summary,_=self.failed(lambda p:{'jsonrpc':'2.0','id':p['id'],'error':{'code':-1,'message':'api_key=hidden password=private authorization: Bearer token http://name:pass@example.invalid/'}});text=json.dumps(summary);self.assertNotIn('hidden',text);self.assertNotIn('private',text);self.assertNotIn('Bearer token',text);self.assertNotIn('name:pass',text);self.assertIn('<redacted>',text)
 def test_lone_surrogate_error_does_not_hide_the_original_failure(self):
  summary,_=self.failed(lambda p:{'jsonrpc':'2.0','id':p['id'],'error':{'code':-1,'message':'bad\ud800message'}});self.assertIn('bad?message',summary['jsonrpc_error']['message'])
 def test_expected_refusal_returns_the_unchanged_envelope_without_new_diagnostic(self):
  with patch.object(gate,'rpc_failure_context',side_effect=AssertionError('expected refusal must not be recategorized')):
   result,seen=self.call(lambda p:{'jsonrpc':'2.0','id':p['id'],'error':{'code':-1,'message':'expected'}},allow_error=True)
  self.assertIsNone(result[0]);self.assertEqual(result[1]['response'],seen[0])
 def test_success_and_unexpected_success_keep_original_semantics(self):
  maker=lambda p:{'jsonrpc':'2.0','id':p['id'],'result':{'isError':False,'content':[{'type':'json','json':{'actual':'unchanged'}}]}}
  result,_=self.call(maker);self.assertEqual(result[0],{'actual':'unchanged'})
  with self.assertRaisesRegex(ValueError,'expected refusal was accepted'):self.call(maker,allow_error=True)
 def test_unverified_identity_and_oversized_response_still_refuse_first(self):
  with patch.object(gate,'rpc_failure_context',side_effect=AssertionError('unverified owner data cannot become diagnostics')):
   with self.assertRaisesRegex(ValueError,'RPC identity mismatch'):self.call(lambda p:{'jsonrpc':'2.0','id':'foreign','error':{'message':'no'}})
   with self.assertRaisesRegex(ValueError,'oversized MCP response'):self.call(lambda p:b'x'*262145)
if __name__=='__main__':unittest.main()
