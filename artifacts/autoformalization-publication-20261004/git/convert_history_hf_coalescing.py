"""Exact unpublished HF substitution, including identical existing references.

An existing adjacent reference is preserved only when its regular-file mode
and Git blob identity equal the selected canonical HF reference. Other
collisions fail. No refs, indexes or working files are changed by this API.
"""
from __future__ import annotations

import hashlib
import types
from pathlib import Path

OWNER = Path(__file__).resolve().parent.parent / 'canonical_git/convert_history_hf_references.py'
OWNER_SHA = 'ba103b5581f20f69f4c09930cdc233cfdd6a021d1162158fc1d94158d190fb0d'
COLLISION_POLICY = 'coalesce_only_existing_identical_reference_blob_and_mode/v1'


def owner():
    with OWNER.open('rb') as stream:
        data = stream.read(32769)
    if len(data) > 32768 or hashlib.sha256(data).hexdigest() != OWNER_SHA:
        raise ValueError('frozen original tree/commit primitives differ')
    module = types.ModuleType('frozen_hf_history_primitives')
    module.__file__ = str(OWNER)
    exec(compile(data, str(OWNER), 'exec'), module.__dict__)
    return module


def rewrite_unpublished(repository, tip, published_commits, references):
    """Return full maps; remove only exact selected raw payload occurrences."""
    base = owner()
    commits = base.git(repository, 'rev-list', '--reverse', '--topo-order', tip,
                       '--not', *published_commits).decode().splitlines()
    objects = base.Objects(repository)
    tree_map, commit_map, occurrences, coalesced = {}, {}, [], []
    try:
        pointer_oids = {path: objects.put('blob', base.canonical(reference) + b'\n')
                        for path, reference in references.items()}

        def transform(oid, prefix=''):
            key = (oid, prefix)
            if key in tree_map:
                return tree_map[key]
            original = objects.read(oid, 'tree')
            entries, result = base.tree_entries(original), []
            by_name = {name: (mode, entry_oid) for mode, name, entry_oid in entries}
            if len(by_name) != len(entries):
                raise ValueError('duplicate historical tree names are unsupported')
            for mode, name, entry_oid in entries:
                path = prefix + name.decode('utf-8', 'surrogateescape')
                if mode == b'40000' and any(target.startswith(path + '/') for target in references):
                    entry_oid = transform(entry_oid, path + '/')
                elif path in references and entry_oid == references[path]['source_git_blob_oid']:
                    adjacent = name + b'.hf.json'
                    if mode not in (b'100644', b'100755'):
                        raise ValueError('artifact is not a regular Git blob')
                    existing = by_name.get(adjacent)
                    if existing is not None and existing != (mode, pointer_oids[path]):
                        raise ValueError('existing adjacent reference differs in mode or selected Git blob identity')
                    occurrences.append({'original_tree_oid': oid, 'path': path,
                                        'source_git_blob_oid': entry_oid})
                    if existing is not None:
                        coalesced.append({'original_tree_oid': oid, 'path': path,
                            'source_git_blob_oid': entry_oid, 'reference_path': path + '.hf.json',
                            'reference_git_blob_oid': pointer_oids[path], 'mode': mode.decode()})
                        continue
                    name, entry_oid = adjacent, pointer_oids[path]
                result.append((mode, name, entry_oid))
            rewritten = base.tree_bytes(result)
            tree_map[key] = oid if rewritten == original else objects.put('tree', rewritten)
            return tree_map[key]

        for oid in commits:
            original = objects.read(oid, 'commit')
            header, separator, message = original.partition(b'\n\n')
            if not separator or b'\ngpgsig ' in header or b'\nmergetag ' in header:
                raise ValueError('unsupported signed or malformed unpublished commit')
            result = []
            for line in header.split(b'\n'):
                if line.startswith(b'tree '):
                    line = b'tree ' + transform(line[5:].decode()).encode()
                elif line.startswith(b'parent '):
                    parent = line[7:].decode()
                    line = b'parent ' + commit_map.get(parent, parent).encode()
                result.append(line)
            rewritten = b'\n'.join(result) + separator + message
            commit_map[oid] = oid if rewritten == original else objects.put('commit', rewritten)
        return {'tip': commit_map.get(tip, tip), 'commit_map': commit_map,
                'tree_map': [{'old': old, 'prefix': prefix, 'new': new}
                             for (old, prefix), new in tree_map.items()],
                'replaced_tree_occurrences': occurrences, 'coalesced_tree_occurrences': coalesced,
                'reference_blob_oids': pointer_oids, 'adjacent_collision_policy': COLLISION_POLICY}
    finally:
        objects.close()
