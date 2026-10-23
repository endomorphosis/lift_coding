"""Lossless metadata hydration and bounded source-view reads through DuckDB."""
import json
from pathlib import Path
from intent_io import ROOT,wire,sha,FALSE

def row(kind,payload):
 return {'row_id':sha(wire({'kind':kind,'payload':payload})),'record':payload,**FALSE}

def build_records(*,structural,bodies,instructions,corpus,native,codecs,lineage):
 records={'source_files':[],'codec_views':[],'native_capsules':[],'native_blocks':[],
  'instructions':[],'ast':[],'kg':[],'interfaces':[],'effects':[],'provenance':[],'residuals':[],
  'vectors':[],'contracts':[]}
 for s in structural['sources']:
  records['source_files'].append(row('source',{'path':s['path'],'source_text':bodies[s['path']].decode('utf-8'),
   'source_cid':s['source_cid'],'sha256':s['sha256'],'bytes':s['bytes'],'head':structural['head']}))
  for arm in ['minified','aliased']:
   records['codec_views'].append(row('codec',{'path':s['path'],'arm':arm,'codec':codecs[s['path']][arm]}))
  records['ast'].append(row('ast',{'path':s['path'],'source_cid':s['source_cid'],'ast_cid':s['ast_cid'],'value':s['ast']}))
  for family in ['symbols','scopes','imports','references','calls']:
   records['kg'].extend(row(family,{'path':s['path'],'kind':family,'value':v}) for v in s['ast'][family])
  records['effects'].extend(row('effect',{'path':s['path'],'value':v}) for v in s['ast']['effects'])
  records['interfaces'].extend(row('interface',{'path':s['path'],'value':v}) for v in s['ast']['symbols'] if v['signature'] is not None)
 records['native_capsules']=[row('native-capsule',v) for v in native['capsules']]
 records['native_blocks']=[row('native-block',v) for v in native['blocks']]
 for task in corpus['tasks']:
  records['instructions'].append(row('instruction',{'task_id':task['task_id'],
   'source_text':instructions[task['task_id']].decode('utf-8'),'sha256':task['instruction']['sha256']}))
  records['residuals'].append(row('requirements',{'task_id':task['task_id'],
   'instruction_sha256':task['instruction']['sha256'],'unresolved_spans':[[0,task['instruction']['bytes']]],
   'residual_span_unit':'utf8_bytes',
   'full_instruction_retained':True,'all_requirements_unresolved':True,'full_task_coverage_qualified':False}))
 records['provenance']=[row('lineage',{'lineage':lineage,'head':structural['head'],
  'native_profile':native['profile'],'native_capsules_not_proof_authority':True,'source_body_execution':False})]
 # These families are queried directly. Refuse overflow instead of querying
 # lossless-chunk packet strings as if they were complete original records.
 for family in ['source_files','codec_views']:
  if any(len(wire(value))>240000 for value in records[family]):raise ValueError('direct SQL leaf exceeds declared row bound')
 return records

def select_task_rows(*,metadata_output,native_metadata,task,head):
 import duckdb
 output=Path(metadata_output)
 if output.resolve()!=output or ROOT not in output.parents or output.name!='metadata':raise ValueError('canonical owned metadata output required')
 paths=[pin['path'] for pin in task['sources']]
 if len(paths)!=len(set(paths)) or not 1<=len(paths)<=2:raise ValueError('bounded exact task source selectors required')
 selected_sources={};selected_codecs={}
 # Caller validates the complete owned catalog and lake before and after use.
 # SQL is limited to two known families and at most two canonical source paths.
 cx=duckdb.connect(str(output/'metadata.duckdb'),read_only=True,config={'threads':'1','memory_limit':'128MB'})
 try:
  cx.execute('SET enable_external_access=false')
  sizes=cx.execute("SELECT family,octet_length(encode(payload_json)) FROM metadata_rows "
   "WHERE family IN ('source_files','codec_views') LIMIT 17").fetchall()
  if len(sizes)!=15 or sum(family=='source_files' for family,_ in sizes)!=5 or any(n>262144 for _,n in sizes):
   raise ValueError('complete bounded SQL leaf scope required before payload hydration')
  for path in sorted(paths):
   found=cx.execute("SELECT family,row_id,row_ordinal,payload_sha256,source_snapshot_sha256,payload_json FROM metadata_rows "
    "WHERE family IN ('source_files','codec_views') AND json_extract_string(payload_json,'$.record.path')=? "
    "ORDER BY family,row_ordinal LIMIT 4",[path]).fetchall()
   if len(found)!=3:raise ValueError('complete unique source and two codec SQL rows required')
   codecs={}
   for family,outer_id,ordinal,digest,snapshot,payload_json in found:
    raw=payload_json.encode('utf-8')
    if len(raw)>262144 or 'sha256:'+sha(raw)!=digest or snapshot!=native_metadata['source_snapshot_sha256']:
     raise ValueError('SQL payload or snapshot binding differs')
    payload=json.loads(raw)
    if set(payload)!={'row_id','record',*FALSE} or any(payload.get(k) is not False for k in FALSE):raise ValueError('SQL row promoted evidence authority')
    from benchmarks.agent_supervisor.container_coding import codebase_ir_metadata as native_metadata_api
    rebuilt=native_metadata_api._row(family,payload,ordinal,snapshot)
    if rebuilt['row_id']!=outer_id or rebuilt['payload_sha256']!=digest:raise ValueError('native SQL row identity differs')
    record=payload['record']
    if payload!=row('source' if family=='source_files' else 'codec',record):raise ValueError('declared source/codec row identity differs')
    if record['path']!=path:raise ValueError('SQL source selector differs')
    if family=='source_files':
     if path in selected_sources or record['head']!=head:raise ValueError('SQL source head differs')
     selected_sources[path]=record
    else:
     arm=record['arm']
     if arm not in {'minified','aliased'} or arm in codecs or record['codec']['bindings']['head']!=head:
      raise ValueError('SQL codec head or role differs')
     if record['codec']['expansion_sidecar']['aliases']['enabled'] is not (arm=='aliased'):
      raise ValueError('SQL codec arm/alias policy differs')
     codecs[arm]=record['codec']
   if set(codecs)!={'minified','aliased'} or path not in selected_sources:raise ValueError('SQL source scope incomplete')
   selected_codecs[path]=codecs
 finally:cx.close()
 return selected_sources,selected_codecs
