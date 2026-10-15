#!/usr/bin/env python3
"""Preserve bounded tracked third-party edits without imports or secret export."""
from __future__ import annotations

import ast
import base64
import difflib
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
SOURCES = ROOT / 'external/ipfs_datasets/.tools/ipfs_kit_py/docs'
OUT = Path(__file__).resolve().parent
NAMES = ['filesystem_spec', 'ipfs-docs', 'ipfsspec', 'lighthouse-python-sdk', 'mcp-python-sdk']
EXTRA_SOURCES = {
    'mcp-python-sdk-hallucinate-datasets': ROOT / 'hallucinate_app/ipfs_datasets_py/.tools/ipfs_kit_py/docs/mcp-python-sdk',
    'mcp-python-sdk-hallucinate-accelerate-datasets': ROOT / 'hallucinate_app/ipfs_accelerate_py/ipfs_datasets_py/.tools/ipfs_kit_py/docs/mcp-python-sdk',
}
PATTERNS = {
    'private_key_block': rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'github_token': rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b',
    'hf_token': rb'\bhf_[A-Za-z0-9]{30,}\b',
    'aws_access_key': rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'provider_key': rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{35,}\b',
    'hex_secret_assignment': rb'(?i)(?:private_?key|secret|api_?key)\s*[:=]\s*[\x22\x27](?:0x)?[0-9a-f]{32,}[\x22\x27]',
    'jwt': rb'\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\b',
}


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args])


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe(raw):
    assert b'\0' not in raw
    assert len(raw) <= 1024 * 1024
    assert not any(re.search(pattern, raw) for pattern in PATTERNS.values()), 'secret-like content withheld'


def write(path, raw):
    safe(raw)
    with (OUT / path).open('xb') as handle:
        handle.write(raw)
    (OUT / path).chmod(0o600)
    return {'path': path, 'bytes': len(raw), 'sha256': sha(raw)}


class StripDocstrings(ast.NodeTransformer):
    def strip(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:]
        return node
    visit_Module = visit_ClassDef = visit_FunctionDef = visit_AsyncFunctionDef = strip


def main():
    manifest = {'schema': 'third-party-local-edit-preservation/v1',
        'scope': 'Five nested third-party origins plus two distinct MCP SDK variants; preserved artifacts, not approved changes or upstream contributions.',
        'source_repositories_mutated': False, 'upstream_pushes': False,
        'behavioral_tests_run': False, 'package_imports': False,
        'repositories': [], 'outputs': [], 'checks': []}
    for name in NAMES + list(EXTRA_SOURCES):
        repo = EXTRA_SOURCES[name] if name in EXTRA_SOURCES else SOURCES / name
        head = git(repo, 'rev-parse', 'HEAD').decode().strip()
        status = git(repo, 'status', '--porcelain=v1', '-z')
        files = git(repo, 'diff', '--name-only', head).decode().splitlines()
        assert not git(repo, 'ls-files', '--others', '--exclude-standard').strip()
        assert all(not Path(f).is_absolute() and '..' not in Path(f).parts for f in files)
        row = {'name': name, 'source_path': str(repo.relative_to(ROOT)), 'base_commit': head,
            'origin': git(repo, 'remote', 'get-url', 'origin').decode().strip(),
            'files': [], 'excluded_files': [], 'upstream_status': 'All edited files differ from locally tracked upstream bytes; no broad remote history search performed.'}
        ref = 'origin/master' if name == 'filesystem_spec' else 'origin/main'
        row['tracked_upstream_commit'] = git(repo, 'rev-parse', ref).decode().strip()
        row['head_ahead_behind_tracked_upstream'] = [int(x) for x in git(repo, 'rev-list', '--left-right', '--count', 'HEAD...' + ref).split()]
        row['advertised_upstream'] = git(repo, 'ls-remote', 'origin', 'refs/heads/' + ref.split('/')[-1]).decode().strip()
        patch_files = []
        for file in files:
            path = repo / file
            assert path.is_file() and not path.is_symlink()
            before = git(repo, 'show', head + ':' + file)
            after = path.read_bytes()
            assert len(before) <= 1024 * 1024 and len(after) <= 1024 * 1024
            assert b'\0' not in before + after
            info = {'path': file, 'base_bytes': len(before), 'base_sha256': sha(before),
                'result_bytes': len(after), 'result_sha256': sha(after)}
            if file.endswith('.py'):
                a, b = ast.parse(before), ast.parse(after)
                info['ast_comparison'] = 'identical' if ast.dump(a) == ast.dump(b) else (
                    'identical_after_removing_docstrings' if ast.dump(StripDocstrings().visit(a)) == ast.dump(StripDocstrings().visit(b)) else 'different')
            if name == 'lighthouse-python-sdk' and file == 'tests/test_get_api_key.py':
                # Never repeat the existing literal. Record only nonmatching edits.
                edits = []
                for tag, a0, a1, b0, b1 in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
                    if tag == 'equal':
                        continue
                    inserted = after[b0:b1]
                    safe(inserted)
                    assert not re.search(rb'(?:0x)?[0-9a-fA-F]{32,}', inserted)
                    edits.append({'offset': a0, 'delete_bytes': a1 - a0, 'insert_base64': base64.b64encode(inserted).decode()})
                rebuilt = before
                for edit in reversed(edits):
                    offset = edit['offset']
                    rebuilt = rebuilt[:offset] + base64.b64decode(edit['insert_base64']) + rebuilt[offset + edit['delete_bytes']:]
                assert rebuilt == after
                recipe = {'schema': 'exact-base-byte-edits/v1', 'base_commit': head,
                    'path': file, 'base_sha256': sha(before), 'result_sha256': sha(after),
                    'reason': 'The original file contains a preexisting private-key-shaped literal. No literal is copied; apply edits to independently obtained exact base bytes only.',
                    'edits': edits, 'local_reconstruction_verified': True}
                filename = name + '-test-get-api-key.byte-edits.json'
                manifest['outputs'].append(write(filename, json.dumps(recipe, indent=2, sort_keys=True).encode() + b'\n'))
                info['preservation'] = filename
                info['omitted_from_patch_reason'] = 'Preexisting private-key-shaped literal omitted from all exported artifacts.'
            else:
                patch_files.append(file)
                info['preservation'] = name + '.patch'
            row['files'].append(info)
        patch = git(repo, 'diff', '--binary', '--full-index', head, '--', *patch_files)
        assert b'GIT binary patch' not in patch
        manifest['outputs'].append(write(name + '.patch', patch))
        if name == 'ipfs-docs':
            readme = git(repo, 'show', head + ':README.md')
            start = readme.index(b'## License')
            text = readme[start:]
            end = text.find(b'\n## ', 1)
            if end >= 0:
                text = text[:end]
            license_file = name + '.license-excerpt.txt'
            row['license_provenance'] = {'source_file': 'README.md', 'base_commit': head,
                'source_sha256': sha(readme), 'verbatim_section': 'License',
                'note': 'Preserved verbatim: source description and linked CC license differ; no independent license interpretation supplied.'}
        else:
            source_file = 'LICENSE.md' if name == 'lighthouse-python-sdk' else 'LICENSE'
            text = git(repo, 'show', head + ':' + source_file)
            license_file = name + '.LICENSE.txt'
            row['license_provenance'] = {'source_file': source_file, 'base_commit': head, 'source_sha256': sha(text)}
        manifest['outputs'].append(write(license_file, text))
        row['license_copy'] = license_file
        if name.startswith('mcp-python-sdk'):
            row['review_warning'] = 'Formatting changed MkDocs snippet include delimiters. Patch is preserved unapproved and must not be applied as an endorsed documentation fix.'
        else:
            row['review_note'] = 'Observed edits are formatting-oriented; Python AST comparisons are recorded per file. This is not behavioral validation.'
        assert git(repo, 'rev-parse', 'HEAD').decode().strip() == head
        assert git(repo, 'status', '--porcelain=v1', '-z') == status
        assert all(sha((repo / item['path']).read_bytes()) == item['result_sha256'] for item in row['files'])
        manifest['checks'].append({'repository': name, 'source_unchanged': True, 'bounded_text_only': True, 'export_secret_scan_passed': True})
        manifest['repositories'].append(row)
    manifest['total_repositories'] = len(manifest['repositories'])
    manifest['total_modified_files_preserved'] = sum(len(row['files']) for row in manifest['repositories'])
    manifest['patch_file_count'] = len(manifest['repositories'])
    manifest['files_preserved_as_patches'] = manifest['total_modified_files_preserved'] - 1
    manifest['files_preserved_as_secret_free_edit_recipes'] = 1
    manifest['total_patch_bytes'] = sum(row['bytes'] for row in manifest['outputs'] if row['path'].endswith('.patch'))
    write('manifest.json', json.dumps(manifest, indent=2, sort_keys=True).encode() + b'\n')
    print(json.dumps({key: manifest[key] for key in ['total_repositories', 'total_modified_files_preserved', 'patch_file_count', 'files_preserved_as_patches', 'files_preserved_as_secret_free_edit_recipes', 'total_patch_bytes']}, indent=2))


if __name__ == '__main__':
    main()
