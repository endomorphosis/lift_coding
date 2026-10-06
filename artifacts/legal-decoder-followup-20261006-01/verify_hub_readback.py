"""Verify append-only remote Git/LFS identities and exact weight downloads."""
from pathlib import Path
from hashlib import sha1, sha256
import json

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.hf_api import RepoFile

OUT = Path(__file__).resolve().parent
pub = json.loads((OUT / 'hub-upload.json').read_text())
api = HfApi()


def inventory(revision):
    return {item.path: item for item in api.list_repo_tree(pub['repo'], revision=revision, recursive=True)
            if isinstance(item, RepoFile)}


old, new = inventory(pub['previous_revision']), inventory(pub['revision'])
assert set(old) <= set(new)
changed = [p for p, v in old.items() if v.blob_id != new[p].blob_id or v.size != new[p].size]
assert set(changed) <= {'.gitattributes'}, changed
if changed:
    old_attrs = Path(hf_hub_download(pub['repo'], '.gitattributes', revision=pub['previous_revision'])).read_text().splitlines()
    new_attrs = Path(hf_hub_download(pub['repo'], '.gitattributes', revision=pub['revision'])).read_text().splitlines()
    assert set(old_attrs) <= set(new_attrs)
files = {str(p.relative_to(OUT / 'hub-stage')): p for p in (OUT / 'hub-stage').rglob('*') if p.is_file()}
for relative, path in files.items():
    item = new[pub['prefix'] + '/' + relative]
    raw = path.read_bytes()
    assert item.size == len(raw)
    if item.lfs:
        assert item.lfs.sha256 == sha256(raw).hexdigest(), relative
    else:
        assert item.blob_id == sha1(('blob ' + str(len(raw)) + '\0').encode() + raw).hexdigest(), relative
assert set(new) - set(old) == {pub['prefix'] + '/' + p for p in files}
downloads = {}
for arm in ('original_negatives', 'position_local_negatives'):
    filename = pub['prefix'] + '/checkpoints/' + arm + '/checkpoint.json'
    path = Path(hf_hub_download(pub['repo'], filename, revision=pub['revision'], local_dir=str(OUT / 'hub-roundtrip')))
    assert path.read_bytes() == (OUT / 'hub-stage/checkpoints' / arm / 'checkpoint.json').read_bytes()
    downloads[arm] = str(path)
receipt = {'schema': 'grouped-boundary-hub-readback/v1', 'revision': pub['revision'], 'repo': pub['repo'],
    'prefix': pub['prefix'], 'files_verified': len(files), 'old_files_retained': len(old), 'old_files_changed': changed,
    'old_attributes_only_additive': True, 'checkpoint_downloads': downloads, 'both_downloaded_checkpoints_byte_exact': True}
(OUT / 'hub-readback.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: v for k, v in receipt.items() if k != 'checkpoint_downloads'}))
