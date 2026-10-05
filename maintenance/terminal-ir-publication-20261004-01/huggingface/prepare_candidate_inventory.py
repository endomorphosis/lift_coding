"""Closed-archive metadata only; never prints credential/body bytes."""
import hashlib,json,re,sqlite3,time
from pathlib import Path
R=Path('/home/barberb/lift_coding/maintenance/terminal-ir-publication-20261004-01/huggingface')

def pin(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):
 with p.open('xb') as s:s.write((json.dumps(v,sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode())
 return pin(p)

def main():
 output=R/'candidate-inventory-01';output.mkdir(exist_ok=False);start=time.monotonic();state={'schema':'terminal-ir-closed-archive-candidate-metadata-attempt@1','status':'running','original_body_reads':0,'archive_decodes':0,'remote_mutations':0,'native_SQL_or_product_imports':0}
 save(output/'started.json',state);db=None
 try:
  manifest=R/'archive-build-01/public/archive-manifest.json';binding=pin(manifest)
  if binding['sha256']!='ae1ccb2e390ef9d542f56d3a2895a38591618e926a425499192dc615f359c28e':raise ValueError('closed archive pin')
  db=sqlite3.connect('file:'+str(R/'archive-build-01/private/path-index.sqlite')+'?mode=ro',uri=True)
  candidates=[];unique={};parts=[]
  for namespace,relative,source,encoded in db.execute("SELECT namespace,relative_path,source,private_record FROM nodes WHERE status LIKE 'quarantined%' OR relative_path LIKE '%.part-%'"):
   record=json.loads(encoded)
   if record['status'].startswith('quarantined'):
    entry={'namespace':namespace,'path':relative,'source_path':source,'status':record['status'],'file_sha256':record.get('full_sha256'),'bytes':record.get('bytes'),'credential_candidates':record.get('credential_candidates',[])}
    candidates.append(entry)
    if entry['file_sha256']:
     target=unique.setdefault(entry['file_sha256'],{'file_sha256':entry['file_sha256'],'bytes':entry['bytes'],'credential_candidates':entry['credential_candidates'],'paths':[]});target['paths'].append({'namespace':namespace,'path':relative,'source_path':source})
   if record.get('full_sha256') and re.search(r'\.part-\d+$',relative):parts.append({'namespace':namespace,'path':relative,'sha256':record['full_sha256'],'bytes':record['bytes']})
  report={'schema':'terminal-ir-raw-candidate-file-inventory@1','archive_manifest':binding,'path_count':len(candidates),'unique_file_count':len(unique),'candidates':candidates,'unique_files':sorted(unique.values(),key=lambda v:v['file_sha256']),'values_printed':False,'public_provenance_classified':False}
  inventory=save(output/'candidate-files.json',report)
  parts_pin=save(output/'captured-split-part-population.json',{'schema':'terminal-ir-captured-split-part-population@1','archive_manifest':binding,'files':parts,'scope':'Complete selected captured path population only; original upstream terminal-part completeness is not asserted.'})
  gen=R.parent/'datasets/hf-generated-paths-02.json';genpin=pin(gen);document=json.loads(gen.read_bytes())
  groups=[]
  for namespace in sorted({p['namespace'] for p in parts}):
   for prefix in sorted({re.sub(r'\d+$','',p['path']) for p in parts if p['namespace']==namespace}):
    use_gen=namespace=='datasets_generated_preserved';source=document if use_gen else {'files':parts};rows=[{k:item[k] for k in ['path','sha256','bytes']} for item in source['files'] if (use_gen or item['namespace']==namespace) and item['path'].startswith(prefix) and re.search(r'\.part-\d+$',item['path'])]
    rows.sort(key=lambda item:int(re.search(r'\d+$',item['path']).group()))
    groups.append({'namespace':namespace,'path_prefix':prefix,'ordered_parts':rows,'source_manifest':genpin if use_gen else parts_pin,'expected_source_schema':document['schema'] if use_gen else 'terminal-ir-captured-split-part-population@1','source_manifest_field':'files','completeness_scope':'full generated-preservation manifest population' if use_gen else 'captured archive membership; upstream original count not independently established'})
  group_pin=save(output/'split-groups.json',{'schema':'terminal-ir-explicit-archive-split-groups@1','groups':groups,'archive_manifest':binding})
  state.update({'status':'closed_metadata_only','candidate_inventory':inventory,'candidate_paths':len(candidates),'candidate_unique_files':len(unique),'split_group_manifest':group_pin,'split_groups':len(groups),'split_part_paths':len(parts),'archive_manifest':binding})
 except BaseException as error:state.update({'status':'failed_preserved','primary_error_type':type(error).__name__});raise
 finally:
  if db:db.close()
  state['elapsed_seconds']=time.monotonic()-start;save(output/'closed.json',state)
 print(json.dumps({'status':state['status'],'candidate_paths':state['candidate_paths'],'candidate_unique_files':state['candidate_unique_files'],'split_groups':state['split_groups'],'elapsed_seconds':state['elapsed_seconds']}))

if __name__=='__main__':main()
