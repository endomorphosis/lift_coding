"""Publish only bounded metadata, candidate outputs, scripts and review records."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path('/home/barberb/lift_coding')
HERE = Path(__file__).resolve().parent
DESTINATION = ROOT / '.worktrees/normative-cache-input-root-20261007/artifacts/normative-retained-cache-runtime-20261007'
TOP_LEVEL = ['prepare_retained_assets.py', 'replay_retained_assets.py', 'retain_evidence.py',
    'independent-review.json', 'independent-result-check.json', 'test-and-source-review.json',
    'legacy-runtime-controls.xml', 'retained-cache-controls.xml', 'archived-output-parity.json',
    'source-github-byte-readback.json']


def pin(path):
    data = path.read_bytes()
    return dict(path=str(path.resolve(strict=True)), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main():
    review = json.loads((HERE / 'independent-review.json').read_text())
    result = json.loads((HERE / 'independent-result-check.json').read_text())
    assert review['approved'] is True and review['findings'] == []
    assert result['approved'] is True and result['findings'] == []
    files = [HERE / name for name in TOP_LEVEL]
    files += sorted((HERE / 'preflight').glob('*.json'))
    files += sorted((HERE / 'generation').glob('*.json'))
    assert len(files) == 24 and all(p.is_file() and p.stat().st_size < 1024 * 1024 for p in files)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    records = []
    for path in files:
        relative = path.relative_to(HERE)
        destination = DESTINATION / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        source_pin = pin(path)
        shutil.copyfile(path, destination)
        copied_pin = pin(destination)
        assert (source_pin['bytes'],source_pin['sha256']) == (copied_pin['bytes'],copied_pin['sha256'])
        records.append(dict(relative_path=str(relative), source_pin=source_pin, publication_pin=copied_pin))
    manifest = dict(schema='normative-retained-cache-evidence-retention/v1', complete=True,
        script_pin=pin(Path(__file__)), files=records, source_files=review['source_file_pins'],
        weights_or_raw_vectors_copied=False, databases_or_secrets_copied=False,
        model_training_or_encoder_executed=False, fresh_holdout_qualified=False, proof_authority=False)
    destination = DESTINATION / 'retention-manifest.json'
    destination.write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(complete=True, retained_files=len(files), manifest_pin=pin(destination))))


if __name__ == '__main__':
    main()
