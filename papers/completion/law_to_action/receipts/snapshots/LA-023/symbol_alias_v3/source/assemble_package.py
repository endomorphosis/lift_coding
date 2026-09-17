#!/usr/bin/env python3
"""Assemble the anonymous portable analysis supplement from retained exact inputs."""
from __future__ import annotations
import argparse,hashlib,json,stat,zipfile
from pathlib import Path

PREFIX='law_to_action_final_supplement/'
LEGACY_SHA='95c5dbb5d7023dbccbafb2003985265d7fe68434d580c2334ca8925f55d08b79'
PORTABLE_MANIFEST_SHA='62a11f6bfa91c0b78e1151204a0243c4d579f9c08f129ed560ce336ea8310917'
STYLE_SHA='2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11'
PORTABLE=('README.md','evidence.zip','manifest.json','reproduce.py','licenses/repository.LICENSE','licenses/ipfs_accelerate.LICENSE','licenses/ipfs_datasets.LICENSE','licenses/ipfs_kit.LICENSE')

def require(v,m):
    if not v:raise RuntimeError(m)

def digest(b):return hashlib.sha256(b).hexdigest()
def encoded(v):return (json.dumps(v,indent=2,sort_keys=True)+'\n').encode()

def build(paper:Path,output:Path,code:Path):
    require(not output.exists(),'Choose fresh output');output.mkdir(parents=True,mode=0o700)
    portable=paper/'artifact/recovery_source_v1'
    require(digest((portable/'manifest.json').read_bytes())==PORTABLE_MANIFEST_SHA,'Portable manifest changed')
    pm=json.loads((portable/'manifest.json').read_bytes())
    expected=dict(pm['companion_files']);expected.update({'evidence.zip':pm['sha256'],'reproduce.py':pm['reproduce_sha256'],'manifest.json':PORTABLE_MANIFEST_SHA})
    require(set(expected)==set(PORTABLE),'Portable inventory changed')
    files={}
    for name in PORTABLE:
        b=(portable/name).read_bytes();require(digest(b)==expected[name],'Portable member changed: '+name);files['recovery_source_v1/'+name]=b
    legacy=paper/'receipts/snapshots/LA-023/final_correction/historical_original_compact.zip'
    b=legacy.read_bytes();require(digest(b)==LEGACY_SHA,'Initial rejected LA-023 compact ZIP differs')
    files['historical_compact/anonymous_supplement.zip']=b
    for name in ('README.md','reproduce.py','reproduce.sh','build_pdf.sh'):
        files[name]=(code/name).read_bytes()
    manuscript=paper/'manuscript'
    for f in sorted(manuscript.iterdir()):
        if f.is_file() and f.suffix in ('.tex','.bib','.sty'):files['manuscript/'+f.name]=f.read_bytes()
    if 'manuscript/neurips_2026_vericode.sty' not in files:
        files['manuscript/neurips_2026_vericode.sty']=(paper.parents[1]/'neurips_2026_vericode.sty').read_bytes()
    require(digest(files['manuscript/neurips_2026_vericode.sty'])==STYLE_SHA,'Official style differs')
    for name in ('disclosure.md','compliance_audit.md'):
        f=paper/'submission'/name
        if f.exists():files['submission/'+name]=f.read_bytes()
    alias_raw=(paper/'artifact/symbol_aliases.json').read_bytes();alias_map=json.loads(alias_raw)
    require(alias_map['schema']=='law-public-technical-symbol-aliases/v1' and alias_map['symbol_count']==len(alias_map['aliases'])==8,'Exact technical alias map required')
    files['symbol_aliases.json']=alias_raw
    for alias in alias_map['aliases']:
        location=alias['included_source']
        if 'path' in location:
            rel=location['path'];require(rel.startswith('implementation_sources/')and '..'not in Path(rel).parts and Path(rel).suffix=='.py','Bounded technical source path')
            raw=(paper/'artifact'/rel).read_bytes();require(len(raw)<=1<<20 and digest(raw)==alias['included_source_sha256'],'Technical source binding differs');files[rel]=raw
    scope={'scientific_rows':900,'host_attempts':902,'actual_group_cpu_seconds':1608.817478,'startup_cpu_seconds_counted_once':.118787,'historical_host_false_flags_preserved':[459,560],'historical_startup_failures_preserved':[591,625],'new_scientific_executions':0,'model_calls_in_fixed_action_study':0,'human_agreement':None,'human_fidelity':None,'analysis':'retained modeled-policy sandbox effects and paired family bootstrap; not new physical enforcement or scientific execution'}
    environment={'schema':'law-final-artifact-environment/v1','offline_recovery_analysis':{'python':'3.12 standard library','command':'./reproduce.sh --output /absolute/fresh/output','per_subprocess_limits':{'address_space_bytes':2<<30,'cpu_seconds':60,'wall_seconds':65,'cpu_affinity':'recovery reader: one available CPU; original compact harness: inherited affinity'}},'historical_compact_analysis':'Exact original LA-023 package and its Python 3.12.3 pins remain in the nested ZIP. Its harness smoke tests are constructed controls, not the 900-cell study.','historical_scientific_runtime':{'image_sha256':'74c4a6ff67f397f8a10b058851d218896b2f1ee0f2cddf47741219b734de93a6','physical_profile':'one CPU / singleton cpuset / 2 GiB no swap / 16 PIDs / 20-second wall and CPU with explicit cumulative-active startup amendments / 18000-second study CPU stop','actual_runtime_binaries_included':False,'private_store_and_key_included':False},'pdf_rebuild':{'command':'./build_pdf.sh /absolute/fresh/pdf-output','requires':'latexmk and an installed TeX distribution; no auto-install','official_style_sha256':STYLE_SHA}}
    files['environment.lock']=encoded(environment)
    manifest={'schema':'law-anonymous-final-artifact/v1','scope':scope,'original_LA023_zip_sha256':LEGACY_SHA,'portable_manifest_sha256':PORTABLE_MANIFEST_SHA,'original_LA029_receipt_sha256':'16c60728771f63e1ef2cbc37e7f23e6a97d197e7147bb187b3df7f01850fe595','historical_compact_provenance':'Initial worker-built ZIP rejected by the generic binary proposal gate; its unmodified offline checks passed. Later native LA023 completion used a different directory bundle.','original_receipts_preserved':True,'original_and_portable_hashes_distinct':True,'files':{n:{'bytes':len(b),'sha256':digest(b)}for n,b in sorted(files.items())},'manifest_self_excluded':True}
    files['manifest.json']=encoded(manifest)
    require(len(files)<=200 and sum(map(len,files.values()))<=150_000_000,'Package expanded limit')
    bundle=output/PREFIX[:-1];bundle.mkdir()
    for name,data in files.items():
        f=bundle/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data);f.chmod(0o755 if name.endswith('.sh')else 0o644)
    archive=output/'anonymous_supplement.zip'
    with zipfile.ZipFile(archive,'x')as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(PREFIX+name,date_time=(2026,9,13,0,0,0));info.create_system=3;info.external_attr=(stat.S_IFREG|(0o755 if name.endswith('.sh')else 0o644))<<16
            info.compress_type=zipfile.ZIP_STORED if name.endswith('.zip')else zipfile.ZIP_DEFLATED
            z.writestr(info,data,compresslevel=9)
    require(archive.stat().st_size<=100_000_000,'Workshop ZIP cap')
    report={'schema':'law-final-artifact-build/v1','archive_sha256':digest(archive.read_bytes()),'archive_bytes':archive.stat().st_size,'members':len(files),'expanded_bytes':sum(map(len,files.values())),'manifest_sha256':digest(files['manifest.json']),'scope':scope}
    (output/'build.json').write_bytes(encoded(report));print(json.dumps(report,sort_keys=True))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--paper',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--code',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();build(a.paper.resolve(),a.output.resolve(),a.code.resolve())
if __name__=='__main__':main()
