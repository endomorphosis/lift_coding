"""Seal only this stage's four nominated source changes against captured bytes."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess

STAGE = Path(__file__).resolve().parent
CHECKOUT = STAGE.parent / 'terminal-token-reduction-20261007-01/checkout'
FILES = (
    'ipfs_accelerate_py/agent_supervisor/runtime/code_source_inspection.py',
    'test/api/test_code_source_inspection.py',
    'ipfs_accelerate_py/agent_supervisor/runtime/codex_usage_receipt.py',
    'test/api/test_codex_usage_session_ledger.py',
)
EXPECTED = (
    'c50440ed2d7ee26add066655374d52e3bf6282f140579551aa9673c44b0ec196',
    '3577e666b201b9bbf40b5a217bcf59defc0161475610e6a6796d077dbb7886f9',
    '9a5b1bddbecb4d374c579f93067039991fb1d4420e7cdc31caeca8b8ff2caa18',
    '36786b21091e9fd1b51f4cd83f21950b310da1488dc71b91d9b7ac2177a3c9f8',
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    baseline = json.loads((STAGE / 'beginning-source-pins.json').read_text())
    captured = {entry['path']: entry for entry in baseline['files']}
    pieces, files = [], []
    for name, expected in zip(FILES, EXPECTED, strict=True):
        raw = (CHECKOUT / name).read_bytes()
        assert digest(raw) == expected, name
        compile(raw, name, 'exec')
        new = name not in captured
        old = b'' if new else (STAGE / 'baseline' / name).read_bytes()
        if not new:
            assert digest(old) == captured[name]['sha256']
            assert len(old) == captured[name]['bytes']
        pieces.append(f'diff --git a/{name} b/{name}\n')
        if new:
            pieces.append('new file mode 100644\n')
        pieces.extend(difflib.unified_diff(old.decode().splitlines(True),
            raw.decode().splitlines(True), fromfile='/dev/null' if new else f'a/{name}',
            tofile=f'b/{name}'))
        files.append({'path': name, 'absolute_path': str(CHECKOUT / name),
            'absent_before': new, 'before_sha256': None if new else digest(old),
            'bytes': len(raw), 'sha256': digest(raw)})
    patch = ''.join(pieces).encode()
    patch_path = STAGE / 'changes.patch'
    with patch_path.open('xb') as output:
        output.write(patch)
    scratch = STAGE / 'patch-qualification-01'
    scratch.mkdir()
    changed = FILES[2]
    target = scratch / changed
    target.parent.mkdir(parents=True)
    target.write_bytes((STAGE / 'baseline' / changed).read_bytes())
    subprocess.run(['git', 'init', '-q', str(scratch)], check=True)
    subprocess.run(['git', 'apply', '--check', str(patch_path)], cwd=scratch, check=True)
    subprocess.run(['git', 'apply', str(patch_path)], cwd=scratch, check=True)
    for entry in files:
        assert (scratch / entry['path']).read_bytes() == (CHECKOUT / entry['path']).read_bytes()
    receipt = {
        'schema': 'source-inspector-and-ledger-source-manifest@1',
        'checkout': str(CHECKOUT), 'files': files,
        'patch_basis': 'One reader delta against exact captured bytes; three new files absent before this stage. Earlier dirty overlays excluded.',
        'patch_path': str(patch_path), 'patch_bytes': len(patch), 'patch_sha256': digest(patch),
        'all_four_python_syntax_checked': True,
        'patch_applies_cleanly_to_captured_baseline': True,
        'applied_changed_bytes_match_checkout': True,
        'original_dirty_checkout_or_git_index_mutated': False,
        'coding_prompt_inspector_integration': False,
        'native_reader_session_ledger_integration': True,
        'runtime_archive_built_or_installed': False,
        'whole_repository_test_pass_claimed': False,
    }
    path = STAGE / 'source-manifest.json'
    with path.open('x') as output:
        json.dump(receipt, output, indent=2, sort_keys=True)
        output.write('\n')
    print(json.dumps({'source_files': len(files), 'patch_bytes': len(patch),
        'patch_sha256': digest(patch), 'clean_apply': True}))


if __name__ == '__main__':
    main()
