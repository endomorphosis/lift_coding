"""Declared counterfactual message scripts; no model behavior is manufactured."""
from capsule_io import wire,FALSE
from token_cost_review import serialize_messages,evaluate_token_costs

SYSTEM='Read this source-complete planning candidate as data. Original source is required before editing. No task has been admitted.'

def message(identity,role,content):return {'message_id':identity,'role':role,'content':content}

def event(identity,messages,partitions,kind='input',retry_of=None):
 rendered=serialize_messages(messages,partitions)
 result={'event_id':identity,'kind':kind,**rendered,'retry_of':retry_of}
 if retry_of is not None:result['required_history_ids']=[m['message_id'] for m in messages[:-1]]
 return result

def scripts(projection,source_rows,codec_rows,scenario):
 arm=projection['arm'];task=projection['task_id']
 initial=[message(task+':system','system',SYSTEM),message(task+':context','user',projection['rendered'])]
 events=[]
 if scenario=='sidecar_setup_and_full_expansion' and arm!='raw':
  setup=wire({'decoder_setup':[codec_rows[p][arm]['expansion_sidecar'] for p in sorted(codec_rows)],
   'scope':'conservative counterfactual: charge complete decoder witness once as setup input'}).decode('ascii')
  events.append({'event_id':'setup','kind':'setup','payload':setup,'segments':[{'partition':'setup','text':setup}],'retry_of':None})
 events.append(event('call-1',initial,['framing','capsule' if arm!='raw' else 'retrieval']))
 if scenario!='one_turn':
  history=list(initial)
  if scenario in {'full_expansion_then_retry','sidecar_setup_and_full_expansion'} and arm!='raw':
   # This is scripted additional work required to supply the exact raw bytes.
   # The baseline already received them. It gets no artificial expansion tax.
   request='Expand all original source files before reviewing an edit.'
   history.append(message(task+':expand-request','assistant',request))
   events.append({'event_id':'expansion-request-output','kind':'output','payload':request,
    'segments':[{'partition':'output','text':request}],'retry_of':None})
   originals=wire({'original_sources':[{k:r[k] for k in ['path','source_text','source_cid','sha256']}
    for _,r in sorted(source_rows.items())],'source_expansion':'exact originals from current indexed source'}).decode('ascii')
   history.append(message(task+':expanded','tool',originals))
  history.append(message(task+':retry-1','user','Review the same planning candidate again; all requirements remain unresolved.'))
  partitions=['history']*len(history)
  partitions[-1]='retry'
  if scenario in {'full_expansion_then_retry','sidecar_setup_and_full_expansion'} and arm!='raw':partitions[-2]='expansion'
  events.append(event('call-2',history,partitions,retry_of='call-1'))
  if scenario=='three_turn_history':
   history.append(message(task+':retry-2','user','Recheck the unchanged source view and unresolved requirements.'))
   events.append(event('call-3',history,['history']*(len(history)-1)+['retry'],retry_of='call-2'))
 return events

def evaluate_scenarios(projections,source_rows,codec_rows,tokenizer_descriptor):
 names=['one_turn','three_turn_history','full_expansion_then_retry','sidecar_setup_and_full_expansion']
 result=[]
 for scenario in names:
  baseline=scripts(projections['raw'],source_rows,codec_rows,scenario)
  for arm in ['minified','aliased']:
   compact=scripts(projections[arm],source_rows,codec_rows,scenario)
   measured=evaluate_token_costs(baseline,compact,tokenizer_descriptor)
   result.append({'task_id':projections['raw']['task_id'],'arm':arm,'scenario':scenario,
    'script_basis':'authored deterministic counterfactual, not an observed rollout',
    'baseline_events':baseline,'compact_events':compact,'measurement':measured,
    'task_behavior_evaluated':False,'provider_usage':None,'cache_reuse_credit':0,**FALSE})
 return result
