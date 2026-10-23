#!/usr/bin/env python3
"""Read-only metadata inventory; no cohort selection, labels, or inference."""
import argparse,collections,hashlib,json,re,sqlite3
from pathlib import Path
from urllib.parse import urlsplit
import pyarrow.parquet as pq

def sha(path):
 with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def repository(url):
 p=urlsplit(url);host=(p.hostname or '').lower();path=p.path.rstrip('/').removesuffix('.git')
 if host=='github.com':path='/'+'/'.join(path.strip('/').split('/')[:2]).lower()
 if not host or path in ('','/'):return None
 return host+path
def source_file(path):return {'path':str(path.resolve()),'bytes':path.stat().st_size,'sha256':sha(path)}

def discover():
 base=Path('/home/barberb/lift_coding');paper=base/'.worktrees/vericodegen-law_to_action-2026/papers/completion/law_to_action';cache=base/'papers/completion/runtime_bootstrap/la004_source_bridge'
 manifest_path=paper/'benchmark/manifests/sources.json';manifest=json.loads(manifest_path.read_text());old=manifest['source_records']
 excluded_repos={r['ancestry_key'][1] for r in old if r['ancestry_key'][0]=='repository'}
 old_primary={r['source_locator'].get('primary_source_id') for r in old if r['population']=='skill'}
 old_normal={r['normalized_source_sha256'] for r in old}
 exclusions={'manifest':source_file(manifest_path),'split_manifest':source_file(paper/'benchmark/manifests/splits.json'),'families':[{'population':r['population'],'lineage_family_id':r['lineage_family_id'],'ancestry_key':r['ancestry_key']} for r in old],'repository_exclusion_count':len(excluded_repos),'rule':'Exclude every old family and all derivatives; repository aliases/forks and near-duplicates require further audit.'}

 cve_path=cache/'train-00000-of-00003.parquet';file=pq.ParquetFile(cve_path);rows=[]
 for batch in file.iter_batches(columns=['cve_id','hash','repo_url','language'],batch_size=512):rows.extend(batch.to_pylist())
 repos=collections.Counter(repository(r['repo_url']) for r in rows);remaining=[r for r in rows if repository(r['repo_url']) not in excluded_repos and repository(r['repo_url'])]
 cve_repos=collections.Counter(repository(r['repo_url']) for r in remaining)
 artifact=next(a for a in manifest['source_artifacts'] if a['artifact_id']=='cve-first-shard');cve_file=source_file(cve_path)
 cve={'artifact':cve_file,'matches_original_artifact_sha256':cve_file['sha256']==artifact['sha256'],'original_revision':artifact['revision'],'source_uri':artifact['source_uri'],'rows':len(rows),'distinct_repositories':len(repos),'remaining_rows_after_old_repository_union':len(remaining),'remaining_repository_identities':len(cve_repos),'remaining_cve_ids':len({r['cve_id'] for r in remaining}),'repository_inventory':[{'repository':k,'rows':v} for k,v in sorted(cve_repos.items())],'paired_code_columns_present':all(x in file.schema_arrow.names for x in ('vulnerable_code','fixed_code')),'code_bodies_read':False,'rights_status':'Original manifest records dataset Apache-2.0 metadata; upstream repository terms and immutable source pins remain to verify. No source bodies exported.'}

 skill_path=cache/'skillcenter-security.sqlite';connection=sqlite3.connect(skill_path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True);connection.row_factory=sqlite3.Row
 try:skills=[dict(r) for r in connection.execute('SELECT i.*, c.metadata_yaml, c.skill_md FROM skills_index i JOIN skills_content c USING(skill_id) ORDER BY i.skill_id')]
 finally:connection.close()
 eligible=[];old_count=0;other=0
 for row in skills:
  if row.get('source_type')!='github':other+=1;continue
  repo=repository(row['source_url']);primary=row.get('primary_source_id') or row.get('source_id');bodysha=hashlib.sha256(re.sub(r'\s+',' ',row['skill_md']).encode()).hexdigest()
  if repo in excluded_repos or primary in old_primary or bodysha in old_normal:old_count+=1;continue
  eligible.append({'repository':repo,'primary_source_id':primary,'normalized_body_sha256':bodysha,'has_llm_model_metadata':'llm_model:' in (row.get('metadata_yaml') or '')})
 skill_file=source_file(skill_path);skill_artifact=next(a for a in manifest['source_artifacts'] if a['artifact_id']=='skill-security-bundle')
 skill={'artifact':skill_file,'matches_original_artifact_sha256':skill_file['sha256']==skill_artifact['sha256'],'original_revision':skill_artifact['revision'],'source_uri':skill_artifact['source_uri'],'joined_index_content_rows':len(skills),'old_family_rows_excluded':old_count,'non_github_rows_excluded':other,'remaining_rows':len(eligible),'remaining_repository_identities':len({r['repository'] for r in eligible}),'remaining_primary_source_identities':len({r['primary_source_id'] for r in eligible}),'remaining_normalized_body_identities':len({r['normalized_body_sha256'] for r in eligible}),'rows_with_llm_model_metadata':sum(r['has_llm_model_metadata'] for r in eligible),'repository_inventory':eligible,'rights_status':'Bundle packaging and license metadata are not upstream permission verification. Procedures have model-generation metadata and are not independent human judgments. No source bodies exported.'}

 legal_root=Path('/home/barberb/portland-laws.github.io/public/corpus/portland-or/current');raw=legal_root/'raw/pages.parquet';canonical=legal_root/'canonical/STATE-OR.parquet'
 legal_rows=pq.read_table(raw,columns=['url','title_number','chapter_number','section_number','status','timestamp','domain','source']).to_pylist()
 urls={r['url'] for r in legal_rows};titles={str(r['title_number']) for r in legal_rows};chapters={str(r['chapter_number']) for r in legal_rows}
 legal={'raw_artifact':source_file(raw),'canonical_artifact':source_file(canonical),'raw_manifest':source_file(legal_root/'raw/manifest.json'),'canonical_manifest':source_file(legal_root/'canonical/manifest.json'),'artifact_manifest':source_file(legal_root/'artifacts.manifest.json'),'source_url':'https://www.portland.gov/code','rows':len(legal_rows),'unique_source_urls':len(urls),'title_identifiers':len(titles),'chapter_identifiers':len(chapters),'domains':dict(collections.Counter(str(r['domain']) for r in legal_rows)),'statuses':dict(collections.Counter(str(r['status']) for r in legal_rows)),'timestamp_range':[min(str(r['timestamp']) for r in legal_rows),max(str(r['timestamp']) for r in legal_rows)],'old_legal_sections_excluded':[r['ancestry_key'] for r in old if r['population']=='legal'],'identity_disjointness_observation':'Portland municipal URL jurisdiction differs from the six historical US Code section families; this is not a completed derivative/cross-reference or cross-paper exposure audit.','rights_status':'Local metadata identifies an official municipal-code scrape. Exact source edition/provenance and lawful use/redistribution still require preparation verification.','code_or_text_bodies_read':False,'generated_proof_artifacts_used':False,'generated_proof_warning':'Local README describes machine-generated formalizations and simulated educational ZKP metadata; those cannot serve as independent task oracles or proof evidence.'}
 return {'schema':'la-generated-study-local-source-discovery/v1','scope':'Read-only availability and ancestry-exclusion metadata; no cohort selected or released','source_bodies_exported':0,'model_calls':0,'cases_constructed':0,'families_selected':0,'scientific_cells_executed':0,'final_cohort_released':False,'exclusions':exclusions,'cve':cve,'skill':skill,'legal':legal,'remaining_work':['Verify lawful upstream source pins and source completeness','Resolve aliases/forks/cross-population ancestry and exact/normalized/nearest-neighbor overlap','Audit prior model/retrieval/cross-paper exposure','Prospectively define selection criteria before choosing 6/12/12 families','Construct useful source-relative tasks and independent policy-relative oracles','Qualify adequate generated-code and native handler profile','Qualify model/runtime/deadline/resume then freeze complete schedule with final-stage seal']}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();report=discover()
 with a.output.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps({'status':'DISCOVERY_ONLY','cve_remaining_repositories':report['cve']['remaining_repository_identities'],'skill_remaining_repositories':report['skill']['remaining_repository_identities'],'legal_source_urls':report['legal']['unique_source_urls'],'families_selected':0,'model_calls':0}))
