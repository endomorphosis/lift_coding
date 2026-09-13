"""Real native public-source semantic context. No target imports/model/scorer.
Normal native imports occur only in prepare_native; request serialization is stdlib.
"""
import hashlib,json,re,os
from pathlib import Path
import context_selection as L
PROFILE={'schema':'ns-pilot-native-B-context/v1','arm':'B','producer':'native scan_repository -> build_semantic_state -> verified view','consumer':'native assess_capsule_freshness -> admit_capsule -> ContextPacker.pack','max_semantic_symbols':4,'native_objective_normalization':'lossless JSON string with ensure_ascii=True for single-line printable native objective; HTTP instruction retains exact original bytes','analysis_scope':'all allowed editable files plus the common mandatory highest lexical-ranked public-test file; no whole-repository analysis claim','preparation_wall_seconds_max':600,'filesystem_identity':'fixed container /tmp/ns-pilot-native-context/<complete-public-inventory-sha256>; no random path identity','ranking':'descending issue identifier matches in qualified name/path, editable priority, path/name/stable CID','raw_source':'exact same A-selected public spans and all mandatory spans; semantic records add native source-bound structure','representation':'native admitted capsule identity facts and declared confidence; source expansions hash verified','semantic_budget_bytes':12288,'request_bytes_max':65536,'reuse_admitted':False,'routing':'model_first','governed_lifecycle':False,'oracle_inputs':False}
COMMON={'schema':'ns-pilot-AB-common-context/v1','public_universe':'unchanged historical context_paths: permitted editable files, unchanged public test modules, public conftest','window_lines':32,'window_overlap_lines':0,'mandatory':'first32lines each editable plus highest lexical ranked public-test window','raw_context_wire_budget':49152,'max_request_bytes':65536,'same_selected_raw_spans_across_arms':True,'cache':'local_cold','cross_cell_memory':False}
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def digest(x):return sha(canon(x))
def require(ok,msg):
 if not ok:raise ValueError(msg)
def validate_files(files,allowed,tests):
 require(type(files)is dict and all(type(p)is str and type(v)is str for p,v in files.items()),'typed public files required')
 require(set(allowed)<=set(files) and set(tests)<=set(files),'missing public file')
 for p in files:require(p and not p.startswith('/') and '..'not in p.split('/')and '.git'not in p.split('/'),'unsafe public path')
 return {p:sha(v.encode())for p,v in sorted(files.items())}
def common_raw(instruction,files,allowed,tests):
 """Same admitted A lexical algorithm, with explicit pre-outcome common budget."""
 original=L.PROFILE
 try:
  L.PROFILE={**original,'request_bytes_max':COMMON['raw_context_wire_budget']}
  request,binding=L.select(instruction,files,allowed,tests)
 finally:L.PROFILE=original
 spec=json.loads(request['messages'][0]['content'])
 return spec,binding

def objective_text(instruction):
 require(type(instruction)is str and instruction.strip(),'nonempty public instruction required')
 return json.dumps(instruction,ensure_ascii=True,separators=(',',':'))

def native_input_contract(instruction,files,allowed,tests):
 """Run all source-independent native pack contracts before any public scan."""
 from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes,cid_for_structured
 from ipfs_accelerate_py.agent_supervisor.semantic_state.context_pack import ContextPacker
 from ipfs_accelerate_py.agent_supervisor.context.context_contracts import ContextBudget
 inventory=validate_files(files,allowed,tests)
 request(instruction,files,allowed,tests,'A')
 def group(paths):return cid_for_structured({'schema':'ns-public-source-group/v1','files':[[p,cid_for_bytes(files[p].encode())]for p in sorted(paths)]})
 kwargs={'objective':objective_text(instruction),'target_source_cid':group(allowed),'surrounding_source_cid':group(files),'test_source_cid':group(tests),'delta_cid':cid_for_structured({'schema':'ns-historical-public-edit-authority/v1','allowed_edit_paths':list(allowed),'source_inventory':inventory}),'assumptions':['Public pre-fix structural context; no proof reuse or solved-task claims.'],'raw_source_regions':[]}
 packer=ContextPacker(budget=ContextBudget(max_input_tokens=16384,reserved_output_tokens=4096,reserved_tool_tokens=0))
 baseline=packer.pack(**kwargs,dependency_admissions=[])
 require(baseline.coverage_satisfied and not baseline.budget_exceeded,'pre-scan native input contract failed')
 return packer,kwargs,baseline

def prepare_native(scan_root,instruction,files,allowed,tests,phase=None):
 phase=phase or (lambda name:None)
 require(type(instruction)is str and instruction.strip(),'nonempty public instruction required')
 native_objective=objective_text(instruction)
 phase('native_imports_started')
 import sys
 sys.dont_write_bytecode=True
 from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes,cid_for_structured
 from ipfs_datasets_py.logic.software_contracts.semantic_index import scan_repository
 from ipfs_datasets_py.logic.software_contracts.semantic_state import build_semantic_state,verify_semantic_state_bundle,view_semantic_state_bundle,assess_capsule_freshness
 from ipfs_datasets_py.logic.software_contracts.semantic_state.source import read_required_source
 from ipfs_accelerate_py.agent_supervisor.semantic_state.capsules import admit_capsule
 from ipfs_accelerate_py.agent_supervisor.semantic_state.context_pack import ContextPacker
 from ipfs_accelerate_py.agent_supervisor.context.context_contracts import ContextBudget
 phase('native_imports_finished');inventory=validate_files(files,allowed,tests);root=Path(scan_root)
 packer,pack_kwargs,input_contract=native_input_contract(instruction,files,allowed,tests);phase('public_inputs_and_native_pack_validated')
 require(root==Path('/tmp/ns-pilot-native-context')/digest(inventory)and root.resolve()==root and not root.exists(),'fresh frozen content-bound public scan root required')
 root.mkdir(mode=0o700,parents=True)
 _,shared=common_raw(instruction,files,allowed,tests)
 test_path=next((x['path']for x in shared['selected_spans']if x['path']in tests),None)
 require(test_path is not None,'mandatory unchanged public-test file missing')
 analysis_paths=sorted(set(allowed)|{test_path});unindexed_paths=sorted(set(files)-set(analysis_paths))
 for rel in analysis_paths:
  body=files[rel]
  p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body);p.chmod(0o600)
 # Filesystem snapshot; all Git discovery stays outside any checkout.
 phase('scan_started');state=scan_repository(root);phase('scan_finished')
 bundle=build_semantic_state(state);verify_semantic_state_bundle(bundle);view=view_semantic_state_bundle(bundle);phase('bundle_verified')
 blobs={cid_for_bytes(body.encode()):body.encode()for body in files.values()}
 query=L.tokens(instruction)
 symbols=sorted((s for s in state.symbols if s.module_path in files and s.source_cid in blobs),key=lambda s:(-len(query&L.tokens(s.qualified_name+' '+s.module_path)),-int(s.module_path in allowed),s.module_path,s.qualified_name,s.stable_id))
 require(symbols,'no native public source symbols; B unavailable')
 admissions=[];records=[];source_proofs=[];capsule_bytes={};failures=[];phase('admissions_started')
 for symbol in symbols:
  if len(records)>=PROFILE['max_semantic_symbols']:break
  materialized=read_required_source(state,symbol.stable_id,expected_producer_state_cid=state.state_cid,read_source_blob=lambda cid:blobs[cid])
  require(materialized.source_bytes==blobs[symbol.source_cid],'native source materialization differs')
  capsule=view.capsule(symbol.stable_id)
  assessment=assess_capsule_freshness(capsule,current_state=view)
  admitted=admit_capsule(capsule,semantic_state_root_cid=bundle.root.root_cid,assessment=assessment)
  payload=capsule.to_dict();capsule_bytes[capsule.capsule_cid]=payload
  # Native facts remain exact retained capsule data; the compact public request
  # projects explicit structural fields, with confidence/caveats intact.
  record={'stable_symbol_id':symbol.stable_id,'version_cid':symbol.version_cid,'source_cid':symbol.source_cid,'path':symbol.module_path,'name':symbol.qualified_name,'kind':symbol.kind,'confidence':symbol.confidence,'span':symbol.span.to_dict()if symbol.span else None,'signature':symbol.to_dict()['signature'],'capsule_cid':capsule.capsule_cid,'admission':admitted.admission,'caveats':list(admitted.caveats),'relations':[{'relation':e.relation,'target_id':e.target_id,'confidence':e.confidence,'extraction_method':e.extraction_method}for e in state.edges if e.source_id==symbol.stable_id][:8]}
  if len(canon(records+[record]))>PROFILE['semantic_budget_bytes']:break
  admissions.append(admitted);records.append(record);source_proofs.append(materialized.evidence.to_dict())
 require(records,'native records do not fit frozen semantic bound');phase('admissions_finished')
 pack=packer.pack(**pack_kwargs,dependency_admissions=admissions)
 require(pack.coverage_satisfied and not pack.budget_exceeded,'native pack coverage/budget failed');phase('pack_finished')
 current={p:sha((root/p).read_bytes())for p in analysis_paths};require(current=={p:inventory[p]for p in analysis_paths},'source changed during native context preparation')
 return {'schema':'ns-native-semantic-context-preparation/v1','profile':PROFILE,'profile_sha256':digest(PROFILE),'common_profile_sha256':digest(COMMON),'inventory':inventory,'instruction_sha256':sha(instruction.encode()),'native_objective_normalization':{'operation':'json.dumps string ensure_ascii=True (lossless)','original_instruction_sha256':sha(instruction.encode()),'native_objective_sha256':sha(native_objective.encode()),'http_instruction_preserved_exactly':True},'allowed_edit_paths':list(allowed),'public_test_paths':list(tests),'producer_state_cid':state.state_cid,'semantic_state_root_cid':bundle.root.root_cid,'native_pack':pack.to_dict(),'pre_scan_native_input_contract':{'pack_cid':input_contract.pack_cid,'coverage_satisfied':input_contract.coverage_satisfied,'budget_exceeded':input_contract.budget_exceeded},'records':records,'admissions':[x.to_dict()for x in admissions],'source_proofs':source_proofs,'capsules':capsule_bytes,'analysis_paths':analysis_paths,'unindexed_public_paths':unindexed_paths,'analysis_scope_is_complete_repository':False,'preparation_shared_across_repetitions':True,'index_counts':{'symbols':len(state.symbols),'edges':len(state.edges),'records_selected':len(records)},'native_analysis_dependency_frontier':[e.to_dict()for e in state.edges if e.target_id not in {x.stable_id for x in state.symbols}],'source_before_after_equal':True,'target_source_executed':False,'oracle_read':False,'normal_native_imports':True}

def request(instruction,files,allowed,tests,arm,prepared=None):
 inventory=validate_files(files,allowed,tests);require(arm in ('A','B'),'unsupported arm')
 spec,raw=common_raw(instruction,files,allowed,tests)
 spec['context_profile_sha256']=digest(COMMON);spec['common_context_profile']=COMMON
 if arm=='B':
  require(type(prepared)is dict and prepared.get('schema')=='ns-native-semantic-context-preparation/v1','actual native B preparation required')
  require(prepared['inventory']==inventory and prepared['instruction_sha256']==sha(instruction.encode())and prepared['allowed_edit_paths']==list(allowed)and prepared['public_test_paths']==list(tests),'native preparation public authority changed')
  require(prepared['profile_sha256']==digest(PROFILE)and prepared['common_profile_sha256']==digest(COMMON),'native B policy drift')
  require(prepared['records']and prepared['native_pack']['coverage_satisfied']and not prepared['native_pack']['budget_exceeded'],'native context unavailable')
  spec['native_semantic_context']={'profile_sha256':digest(PROFILE),'producer_state_cid':prepared['producer_state_cid'],'semantic_state_root_cid':prepared['semantic_state_root_cid'],'pack_cid':prepared['native_pack']['pack_cid'],'records':prepared['records'],'interpretation':'Source-derived structural facts with explicit confidence/caveats; required raw source remains unchanged.'}
 import http_proposer as F
 payload=F.request_envelope(spec);wire=canon(payload)
 require(len(wire)<=65536,'complete request exceeds common cap; no truncation')
 return payload,{'schema':'ns-pilot-AB-context-binding/v1','arm':arm,'common_profile_sha256':digest(COMMON),'mechanism_profile_sha256':digest(PROFILE)if arm=='B'else digest(L.PROFILE),'native_preparation_sha256':digest(prepared)if arm=='B'else None,'complete_public_inventory':inventory,'selected_spans':raw['selected_spans'],'omitted_spans':raw['omitted_spans'],'request_sha256':sha(wire),'request_bytes':len(wire),'selection_used_oracle_or_outcomes':False,'same_raw_source_selection':True}
