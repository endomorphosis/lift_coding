#!/usr/bin/env python3
"""Bind derived input identities after parent authorizes frozen final execution."""
import argparse,json
from pathlib import Path
from extract_heads import digest_file

def main():
 p=argparse.ArgumentParser();p.add_argument('--profile',required=True,type=Path);p.add_argument('--profile-sha256',required=True);p.add_argument('--sources',required=True,type=Path);p.add_argument('--embeddings',required=True,type=Path);p.add_argument('--parent-protocol-sha256',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 if digest_file(a.profile)!=a.profile_sha256:raise ValueError('Scientific profile changed')
 profile=json.load(open(a.profile));receipt=json.load(open(Path(str(a.embeddings)+'.receipt.json')))
 if receipt['consumer_sha256']!=profile['encoder_source_sha256'] or receipt['sources_sha256']!=digest_file(a.sources) or receipt['embeddings_sha256']!=digest_file(a.embeddings) or receipt['model_files']!=profile['encoder_model_files']:raise ValueError('Encoder output custody mismatch')
 if receipt['count']!=1913 or receipt['split']!='final':raise ValueError('Final embedding population incomplete')
 profile.update({'scientific_profile_sha256':a.profile_sha256,'parent_protocol_sha256':a.parent_protocol_sha256,'final_sources_sha256':digest_file(a.sources),'source_embeddings_sha256':digest_file(a.embeddings),'encoder_receipt_sha256':digest_file(Path(str(a.embeddings)+'.receipt.json')),'binding_scope':'Derived input identities only, no algorithm/model/configuration change'})
 with a.output.open('x') as f:json.dump(profile,f,sort_keys=True,indent=2);f.write('\n')
 print(digest_file(a.output))
if __name__=='__main__':main()
