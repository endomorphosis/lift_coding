"""Retain only reviewed probe metadata, outputs, controls and reproduction scripts."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path('/home/barberb/lift_coding')
HERE=Path(__file__).resolve().parent
DESTINATION=ROOT/'.worktrees/dual-bank-wording-adapter-root-20261007/artifacts/dual-bank-wording-adapter-20261007'
FILES=['independent-review.json','independent-result-check.json','dual-bank-controls.xml','legacy-owner-controls.xml',
       'retained-bank-preparation.json','retained-bank-forward-observations.json','probe_retained_banks.py',
       'source-github-byte-readback.json','retain_evidence.py']


def pin(path):
    raw=path.read_bytes()
    return dict(path=str(path.resolve(strict=True)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def main():
    for name in ['independent-review.json','independent-result-check.json']:
        result=json.loads((HERE/name).read_text());assert result['approved'] is True and result['findings']==[]
    DESTINATION.mkdir(parents=True,exist_ok=True)
    records=[]
    for name in FILES:
        source=HERE/name;destination=DESTINATION/name;source_pin=pin(source)
        assert 0<source_pin['bytes']<8*1024*1024
        shutil.copyfile(source,destination);copied_pin=pin(destination)
        assert copied_pin['sha256']==source_pin['sha256'] and copied_pin['bytes']==source_pin['bytes']
        records.append(dict(relative_path=name,source_pin=source_pin,publication_pin=copied_pin))
    manifest=dict(schema='dual-bank-adapter-evidence-retention/v1',complete=True,files=records,
        raw_model_weights_or_embeddings_copied=False,database_or_secret_copied=False,
        optimizer_or_encoder_executed=False,new_fitted_checkpoint_created=False,
        fresh_semantic_holdout_qualified=False,proof_authority=False)
    (DESTINATION/'retention-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(complete=True,retained_files=len(records))))


if __name__=='__main__':main()
