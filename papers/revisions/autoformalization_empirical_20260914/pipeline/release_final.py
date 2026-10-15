#!/usr/bin/env python3
"""Open the held-out source file only after a signed local code/profile freeze.

Deduplication follows AF004. The output contains inputs and grouping metadata,
never human labels; those were not collected for this study.
"""
from pathlib import Path
import collections,datetime,hashlib,json,re,unicodedata
HERE=Path(__file__).resolve().parent
E=HERE.parent
PRIVATE=Path('/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/research-inputs/autoformalization/af004-v1')
EXPECTED='7cf104505334f530937dd6a8304dd916e632f2ba79b01075b7d68ef52e6e730f'
def sha(b):return hashlib.sha256(b).hexdigest()
def unit(text):return sha(' '.join(re.findall(r'[^\W_]+',unicodedata.normalize('NFKC',text).casefold())).encode())
def save(path,obj):path.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def main():
 freeze=E/'FINAL_PROTOCOL_FREEZE.json'
 f=json.loads(freeze.read_text());assert f['ready_for_final_source_access'] is True
 assert not (HERE/'final_release.json').exists()
 for filename,digest in f['code_sha256'].items():assert sha(Path(filename).read_bytes())==digest,filename
 raw=(PRIVATE/'final_test.private.jsonl').read_bytes();assert sha(raw)==EXPECTED
 rows=[json.loads(x) for x in raw.splitlines()]
 groups=json.loads((PRIVATE/'partitions.private.json').read_text())['membership']['final_test']
 byid={r['record_id']:r for r in groups}
 graph=json.loads((PRIVATE/'full_graph.private.json').read_text())
 components={}
 for indices in graph['components'].values():
  ids=sorted(graph['records'][i]['record_id'] for i in indices)
  cid=sha(json.dumps(ids,separators=(',',':')).encode())
  for rid in ids:components[rid]=cid
 chosen={};aliases=collections.defaultdict(list)
 for row in sorted(rows,key=lambda r:r['record_id']):
  uid=unit(row['text']);aliases[uid].append(row['record_id'])
  chosen.setdefault(uid,{**row,'normalized_source_unit_sha256':uid,'component_id':components[row['record_id']],'split_metadata':byid[row['record_id']]})
 out=[{**r,'alias_record_ids':aliases[u]} for u,r in sorted(chosen.items())]
 assert len(rows)==1921 and len(out)==1913
 assert len({r['component_id'] for r in out})==20
 def dump(path,values):path.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in values))
 dump(HERE/'final.sources.jsonl',out)
 sample=sorted(out,key=lambda r:sha(('AF20260914-A100:'+r['normalized_source_unit_sha256']).encode()))[:100]
 dump(HERE/'final_a100.sources.jsonl',sample)
 metadata=[{k:v for k,v in r.items() if k not in ['text']} for r in out]
 save(HERE/'final_metadata.json',metadata)
 save(HERE/'final_release.json',{'released_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'freeze_sha256':sha(freeze.read_bytes()),'private_source_sha256':EXPECTED,'raw_records':len(rows),'units':len(out),
  'deduplication':'NFKC, casefold, Unicode alphanumeric tokens; lexicographic first record_id',
  'final_sources_sha256':sha((HERE/'final.sources.jsonl').read_bytes()),
  'a100_sources_sha256':sha((HERE/'final_a100.sources.jsonl').read_bytes()),
  'a100_sampling':'100 smallest SHA256(AF20260914-A100: + normalized_source_unit_sha256)',
  'domain_counts':dict(collections.Counter(r['family'] for r in out)),
  'human_labels_exist':False})
 print((HERE/'final_release.json').read_text())
if __name__=='__main__':main()
