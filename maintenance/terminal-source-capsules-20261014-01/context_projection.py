"""Source-complete, candidate-only projections into the real context compiler."""
import json
from capsule_io import wire,sha,FALSE

ARMS=('raw','minified','aliased')

def compile_task_context(*,task,instruction,head,source_rows,codec_rows,capsule_summaries,tokenizer,arm,budget_tokens=20000):
 from ipfs_accelerate_py.agent_supervisor.context.context_contracts import ContextBudget,ContextReference,ContextTier
 from ipfs_accelerate_py.agent_supervisor.context.context_compiler import ContextCompiler,render_context_capsule
 from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
 from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes
 from capsule_codec import expand_capsule_codec
 if type(head) is not dict or CodebaseHead.from_dict(head).to_dict()!=head:raise ValueError('complete typed native head required')
 if arm not in ARMS or type(instruction) is not bytes or len(instruction)!=task['instruction']['bytes'] or sha(instruction)!=task['instruction']['sha256']:
  raise ValueError('complete pinned instruction and known source-view arm required')
 expected={p['path']:p for p in task['sources']}
 if set(source_rows)!=set(expected) or set(codec_rows)!=set(expected):raise ValueError('complete task source scope required')
 references=[];source_views={};dictionaries=[]
 for path,pin in sorted(expected.items()):
  source=source_rows[path];codec=codec_rows[path]['minified' if arm=='raw' else arm]
  raw=source['source_text'].encode('utf-8')
  if source['path']!=path or source['head']!=head or sha(raw)!=pin['sha256'] or len(raw)!=pin['bytes'] or codec['bindings']['path']!=path or cid_for_bytes(raw)!=source['source_cid']:
   raise ValueError('source or codec path/content scope differs')
  if codec['bindings']['source_bytes']!=len(raw) or codec['bindings']['span']!={'start_byte':0,'end_byte':len(raw)}:
   raise ValueError('source-complete context requires the whole-file codec span')
  if codec['expansion_sidecar']['aliases']['enabled'] is not (arm=='aliased'):
   raise ValueError('codec alias policy differs from the declared arm')
  if expand_capsule_codec(codec,head,pin['sha256'],source['source_cid'],expected_path=path)!=raw:
   raise ValueError('complete source decoder replay differs')
  text=source['source_text'] if arm=='raw' else codec['view_text']
  aliases=codec['expansion_sidecar']['aliases']['dictionary'] if arm=='aliased' else []
  display={'path':path,'source_cid':source['source_cid'],'source_sha256':pin['sha256'],
   'full_source_bytes':len(raw),'view_kind':arm,'view_text':text,'display_only':True,
   'raw_source_required_before_edit':True,'runtime_equivalence_claimed':False}
  if arm=='aliased':
   display['alias_dictionary']=aliases
   display['alias_guidance']='Display encoding only. Decode each NAME alias through the dictionary; never execute this view.'
   dictionaries.append(aliases)
  # The string starts/ends with JSON punctuation, preserving embedded source
  # and instruction whitespace through native contracts' text normalization.
  summary=wire(display).decode('ascii');source_views[path]=display
  references.append(ContextReference(reference_id='source:'+sha(path.encode())[:16],kind='source-view',
   tier=ContextTier.INVARIANT,content_id=source['source_cid'],repository_id=head['repository_id'],
   tree_id=head['snapshot_cid'],path=path,summary=summary,byte_count=len(summary.encode()),
   metadata={'required':True,'coverage_ids':['source:'+pin['sha256']],
    'raw_source_required_before_edit':True,'completion_authority':False}))
 capsules={'schema':'terminal-native-capsule-task-summary@1','capsules':capsule_summaries,
  'all_task_sources_represented':True,'raw_source_required_before_edit':True,
  'current_head':head,'native_capsules_are_structural_only':True,'proof_authority':False}
 summary=wire(capsules).decode('ascii')
 references.append(ContextReference(reference_id='native-capsules',kind='structural-capsules',
  tier=ContextTier.INVARIANT,content_id=sha(summary.encode()),repository_id=head['repository_id'],
  tree_id=head['snapshot_cid'],summary=summary,byte_count=len(summary.encode()),metadata={'required':True}))
 compiler=ContextCompiler(ContextBudget(max_input_tokens=budget_tokens,reserved_output_tokens=256,
  reserved_tool_tokens=64,max_items=128,max_item_bytes=32768,max_serialized_bytes=262144,
  max_text_bytes=16384,max_depth=12),tokenizer=tokenizer,
  provider_context_window=32768,provider_max_input_tokens=budget_tokens)
 result=compiler.compile(repository_id=head['repository_id'],tree_id=head['snapshot_cid'],
  objective_id=task['task_id'],objective_revision=task['instruction']['sha256'],
  policy_id='source-complete-display-context',policy_revision='1',caller='terminal-public-capsule-experiment',
  stage='planning-candidate',goal={'instruction_json':wire({'instruction':instruction.decode('utf-8')}).decode('ascii'),
   'instruction_sha256':sha(instruction)},authority=FALSE,
  scope={'head':head,'source_paths':sorted(expected),'view_only':True,
   'all_instruction_requirements_unresolved':True,'raw_source_required_before_edit':True},
  acceptance={'instruction_sha256':sha(instruction),'status':'not_evaluated',
   'requirement_residual_spans':[[0,len(instruction)]],'requirement_residual_span_unit':'utf8_bytes',
   'source_semantics_verified':False},evidence=references)
 compiler.verify_compile_result(result)
 rendered=render_context_capsule(result.capsule)
 core=json.loads(rendered)
 decoded=json.loads(core['goal']['instruction_json'])['instruction'].encode('utf-8')
 if decoded!=instruction or len(result.capsule.evidence)!=len(references) or result.capsule.expansion_references:
  raise ValueError('required source or full instruction was weakened')
 actual_tokens=len(tokenizer.encode(rendered))
 if actual_tokens>result.capsule.input_tokens:raise ValueError('native reserved budget undercounts rendered input')
 return {'schema':'terminal-source-complete-context-projection@1','task_id':task['task_id'],'arm':arm,
  'rendered':rendered,'native_capsule':result.capsule.to_record(),
  'native_reserved_input_tokens':result.capsule.input_tokens,'rendered_local_bpe_tokens':actual_tokens,'source_views':source_views,
  'all_instruction_bytes_preserved':True,'all_source_syntax_present_as_display':True,
  'requirement_coverage_qualified':False,'raw_source_required_before_edit':True,**FALSE}

def task_capsule_summaries(capsules,paths):
 result=[]
 for wrapper in capsules:
  capsule=wrapper['capsule']
  if capsule['source_slice_path'] in paths:
   result.append({k:capsule[k] for k in ['stable_symbol_id','capsule_cid','source_slice_path','source_cid']})
 return sorted(result,key=lambda r:r['stable_symbol_id'])
