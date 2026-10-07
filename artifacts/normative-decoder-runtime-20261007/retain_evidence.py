"""Retain explicit replay evidence, excluding weights, vectors and databases."""
import hashlib
import json
from pathlib import Path
import re

SOURCE = Path(__file__).resolve().parent
DESTINATION = Path('/home/barberb/lift_coding/.worktrees/normative-decoder-runtime-root-20261007/artifacts/normative-decoder-runtime-20261007')
FILES = (
    'independent-review.json', 'independent-result-check.json', 'runtime-controls.xml',
    'normative-controls-final.xml', 'prepare_original_assets.py', 'replay_original_assets.py',
    'resolve_registered_selectors.py', 'registered-selector-resolution.json',
    'original-parent-parity.json', 'retain_evidence.py',
)
SECRET = re.compile(rb'(?:hf_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')


def main():
    paths = [SOURCE / name for name in FILES]
    paths += sorted((SOURCE / 'preflight-final').glob('*.json'))
    paths += sorted((SOURCE / 'generation-final').glob('*.json'))
    assert len(paths) == 24 and len(set(paths)) == 24
    entries = []
    for original in paths:
        assert original.is_file() and not original.is_symlink()
        data = original.read_bytes()
        assert 0 < len(data) < 1_000_000 and not SECRET.search(data)
        relative = str(original.relative_to(SOURCE))
        target = DESTINATION / relative
        assert not target.exists() or target.read_bytes() == data
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        if original.suffix == '.json':
            json.loads(data)
        entries.append({'original_path': str(original), 'retained_path': relative,
                        'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    manifest = dict(schema='normative-runtime-evidence-retention/v1', files=entries,
        count=len(entries), bytes=sum(p['bytes'] for p in entries), original_bytes_preserved=True,
        raw_weights_embedding_caches_corpus_and_databases_included=False,
        scope='Reviewed scripts, control/results receipts, metadata plans/options and actual candidate outputs only. Original private custody paths remain historical dependencies.')
    (DESTINATION / 'retention-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({k: v for k, v in manifest.items() if k != 'files'}))


if __name__ == '__main__':
    main()
