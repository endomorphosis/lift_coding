"""Frozen candidate A-only lexical retrieval. Public source in; no execution."""
import hashlib,json,re
PROFILE={'schema':'ns-pilot-public-context-selection/v1','arm':'A','window_lines':32,'window_overlap_lines':0,'request_bytes_max':65536,'query_tokens':'ASCII identifiers length>=3, lowercase, deduplicated','ranking':'descending distinct issue-token matches, then editable priority, then UTF-8 path/start line','mandatory':'first window of each editable file and highest-ranked public-test window when available','selection':'mandatory first; deterministic ranked whole windows that fit exact serialized request; never truncate a window','cross_cell_memory':False,'oracle_inputs':False}
CONTRACT={'format':'JSON object with exactly one key edits, a list of {path,old,new}. Every old string must be nonempty and occur exactly once in the complete current named allowed file. Use no other keys, tools, markdown, or added files. Do not execute code. Source snippets are exact public pre-fix spans; omitted spans have not been revealed.','max_edits':32,'max_patch_bytes':16384}
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def digest(x):return hashlib.sha256(canon(x)).hexdigest()
def require(ok,msg):
 if not ok:raise ValueError(msg)
def tokens(s):return set(re.findall(r'[a-z_][a-z0-9_]{2,}',s.lower()))
def select(instruction,files,allowed_edit_paths,public_test_paths):
 require(type(instruction)is str and type(files)is dict and all(type(k)is str and type(v)is str for k,v in files.items()),'typed public context required')
 require(set(allowed_edit_paths)<=set(files)and set(public_test_paths)<=set(files),'missing public authority')
 require(all(k and not k.startswith('/')and '..'not in k.split('/')and '.git'not in k.split('/')for k in files),'unsafe source path')
 query=tokens(instruction);inventory={p:hashlib.sha256(s.encode()).hexdigest()for p,s in sorted(files.items())};windows=[]
 for path,body in sorted(files.items()):
  lines=body.splitlines(keepends=True)
  for start in range(0,len(lines),PROFILE['window_lines']):
   text=''.join(lines[start:start+PROFILE['window_lines']]);windows.append({'path':path,'start_line':start+1,'end_line':min(start+PROFILE['window_lines'],len(lines)),'text':text,'source_sha256':inventory[path],'matched_query_terms':len(query&tokens(text+' '+path))})
 rank=lambda w:(-w['matched_query_terms'],-int(w['path']in allowed_edit_paths),w['path'].encode(),w['start_line'])
 ordered=sorted(windows,key=rank);mandatory=[w for w in windows if w['path']in allowed_edit_paths and w['start_line']==1]
 tests=[w for w in ordered if w['path']in public_test_paths]
 if tests:mandatory.append(tests[0])
 require(mandatory and all(any(w['path']==p for w in mandatory)for p in allowed_edit_paths),'empty or missing editable source')
 def request(selected):
  spec={'instruction':instruction,'public_pre_fix_snippets':[{k:v for k,v in w.items()if k!='matched_query_terms'}for w in selected],'allowed_edit_paths':list(allowed_edit_paths),'complete_public_inventory_sha256':digest(inventory),'context_profile_sha256':digest(PROFILE),'response_contract':CONTRACT}
  return {'model':'grok-4.6','max_tokens':4096,'messages':[{'role':'user','content':canon(spec).decode()}]}
 selected=[];seen=set()
 for w in mandatory:
  key=(w['path'],w['start_line'])
  if key not in seen:selected.append(w);seen.add(key)
 require(len(canon(request(selected)))<=PROFILE['request_bytes_max'],'mandatory public context exceeds frozen cap; no truncation')
 for w in ordered:
  key=(w['path'],w['start_line'])
  if key in seen:continue
  if len(canon(request(selected+[w])))<=PROFILE['request_bytes_max']:selected.append(w);seen.add(key)
 payload=request(selected);wire=canon(payload)
 selected_spans=[{k:v for k,v in w.items()if k!='text'}|{'text_sha256':hashlib.sha256(w['text'].encode()).hexdigest()}for w in selected]
 all_spans=[{k:v for k,v in w.items()if k!='text'}|{'text_sha256':hashlib.sha256(w['text'].encode()).hexdigest()}for w in windows]
 return payload,{'schema':'ns-pilot-A-context-binding/v1','profile_sha256':digest(PROFILE),'complete_public_inventory':inventory,'complete_public_inventory_sha256':digest(inventory),'selected_spans':selected_spans,'omitted_spans':[w for w in all_spans if(w['path'],w['start_line'])not in seen],'request_sha256':hashlib.sha256(wire).hexdigest(),'request_bytes':len(wire),'selection_used_oracle_or_outcomes':False,'arm':'A'}
