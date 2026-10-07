"""Prepare authenticated input metadata without importing numerical code.

Reuse every pin in the repaired1185-input predecessor and independently walk
all recursive physical path/SHA references in its selected E-parent report.
The new protocol, final adapter/driver freeze and phase profiles remain pending.
This is not a launch manifest or an execution readiness receipt.
"""
import hashlib
import json
from pathlib import Path
import stat

W = Path('/home/barberb/lift_coding')
OLD_R = W / 'artifacts/autoencoder-balanced-wording-20261007'
OLD_RUN = W / 'external/ipfs_datasets/workspace/test-logs/decoder-balanced-wording-20261007'
G = W / 'artifacts/autoencoder-dual-bank-replay-20261007/guardian'
INPUTS = {}
BINDINGS = {}


def pin(path, wanted=None):
    path = Path(path).resolve()
    before = path.stat()
    digest = hashlib.sha256(); size = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block); size += len(block)
    after = path.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if not stat.S_ISREG(before.st_mode) or identity(before) != identity(after) or size != before.st_size:
        raise ValueError('artifact changed during streamed hash: ' + str(path))
    value = dict(sha256=digest.hexdigest(), bytes=size)
    if wanted is not None and wanted != value['sha256']:
        raise ValueError('authenticated input differs: ' + str(path))
    if str(path) in INPUTS and INPUTS[str(path)] != value['sha256']:
        raise ValueError('conflicting physical input pin')
    INPUTS[str(path)] = value['sha256']; BINDINGS[str(path)] = value
    return value


def references(value):
    found = {}
    def walk(node):
        if type(node) is dict:
            if type(node.get('path')) is str and type(node.get('sha256')) is str:
                path = str(Path(node['path']).resolve()); wanted = node['sha256']
                if len(wanted) != 64 or any(c not in '0123456789abcdef' for c in wanted):
                    raise ValueError('invalid physical SHA reference')
                if path in found and found[path] != wanted:
                    raise ValueError('conflicting referenced artifact')
                found[path] = wanted
            for nested in node.values(): walk(nested)
        elif type(node) is list:
            for nested in node: walk(nested)
    walk(value)
    return found


def main():
    manifest_path = OLD_RUN / 'training-manifest.json'
    pin(manifest_path, '3dbbc5490293010cf8e045d7a7062ddb3d00308435ddcdd1e63c54ffceafdf57')
    manifest = json.loads(manifest_path.read_bytes())
    if len(manifest['inputs']) != 1185:
        raise ValueError('repaired1185-input predecessor required')
    for path, wanted in manifest['inputs'].items(): pin(path, wanted)
    pin(OLD_RUN / 'training-plan.json', manifest['plan_sha256'])
    for relative, wanted in manifest['extensions'].items():
        pin(OLD_RUN / 'experiment-source' / relative, wanted)
    parent = Path(manifest['parent_summary']).resolve()
    queue = [parent]; walked = set(); physical_refs = {}; report_walk = []
    while queue:
        path = queue.pop()
        if path in walked: continue
        if len(walked) >= 128:
            raise ValueError('bounded selected-parent reference closure exceeded')
        walked.add(path)
        binding = pin(path, manifest['inputs'].get(str(path)))
        if path.suffix != '.json': continue
        if binding['bytes'] > 128 * 1024 * 1024:
            raise ValueError('parent JSON exceeds bounded reference inspection')
        rows = references(json.loads(path.read_bytes()))
        report_walk.append(dict(path=str(path), sha256=binding['sha256'], physical_refs=len(rows)))
        for ref, wanted in rows.items():
            if ref in physical_refs and physical_refs[ref] != wanted:
                raise ValueError('conflicting recursive parent artifact reference')
            physical_refs[ref] = wanted
            pin(ref, wanted)
            if Path(ref).suffix == '.json': queue.append(Path(ref))
    refs_outside_repaired_manifest = {path: sha for path, sha in physical_refs.items()
                                      if manifest['inputs'].get(path) != sha}
    # The repaired predecessor closes every top-level selected-parent summary
    # reference. A deeper physical producer receipt may add further artifacts;
    # preserve all1185 pins and explicitly report that exact archival superset.
    top_level_refs = references(json.loads(parent.read_bytes()))
    if any(manifest['inputs'].get(path) != wanted for path, wanted in top_level_refs.items()):
        raise ValueError('repaired selected-parent summary closure incomplete')
    # Authentic banks, their original pairing and same-budget two-bank schedule.
    explicit = [OLD_RUN / 'preflight-384-r2/results' / name for name in (
        'control-bank.json', 'balanced-bank.json', 'paired-source-schedule.json',
        'control-paired-cache-receipt.json', 'balanced-paired-cache-receipt.json')]
    explicit += [OLD_R / 'next-retention-plan' / name for name in (
        'dual_bank_retention.py', 'proposed-dual-bank-schedule.json', 'source-results-freeze.json',
        'implementation-contract.json', 'pure-validation.json', 'schedule-census-proof.json')]
    for path in explicit: pin(path)
    bank_paths = {role: OLD_RUN / 'preflight-384-r2/results' / (role + '-bank.json')
                  for role in ('control', 'balanced')}
    banks = {role: json.loads(path.read_bytes()) for role, path in bank_paths.items()}
    schedule = json.loads((OLD_R / 'next-retention-plan/proposed-dual-bank-schedule.json').read_bytes())
    if schedule['bank_sha256'] != {role: bank['bank_sha256'] for role, bank in banks.items()}:
        raise ValueError('authentic native-bank canonical hashes differ from dual schedule')
    result = dict(schema='dual-bank-replay-authenticated-input-closure-seed/v1', complete=True,
                  repaired_predecessor_input_count=1185,
                  repaired_predecessor_manifest=dict(path=str(manifest_path), **BINDINGS[str(manifest_path)]),
                  original_1185_inputs_unchanged=True, input_sha256=INPUTS, artifacts=BINDINGS,
                  authenticated_input_count=len(INPUTS),
                  recursive_selected_parent_ref_count=len(physical_refs),
                  recursive_parent_json_reports_walked=len(report_walk),
                  recursive_parent_reference_walk=report_walk,
                  required_parent_summary_refs_all_in_repaired1185_map=True,
                  recursive_parent_refs_added_beyond_repaired1185=refs_outside_repaired_manifest,
                  recursive_parent_refs_all_in_new_seed=True,
                  authentic_bank_paths={role: str(path) for role, path in bank_paths.items()},
                  authentic_bank_canonical_sha256=schedule['bank_sha256'],
                  immutable_native384_inputs=dict(manifest['source_inventories'],
                                                 balanced_source_inputs=manifest['balanced_source_inputs']),
                  explicit_extra_inputs=[str(path) for path in explicit],
                  pending_before_training_manifest=['new preregistered protocol and physical SHA',
                      'reviewed final dual adapter/driver/helper source freeze and exact extension map',
                      'new phase profiles and exact strict driver constants',
                      'independent source-only review, then completed preflight audit for training readiness'],
                  pending_before_evaluation_manifest=['completed own dual training report and recursive physical refs',
                      'new one-arm8-panel evaluator/profile/source freeze',
                      'v3 reference binding restricted to posthoc scoring'],
                  old_source_and_finished_attempts_modified=False, model_or_encoder_imported=False,
                  native_vectors_recomputed=False, executed_models=False, tensor_cache_adopted=False,
                  semantic_compiler_executed=False, historical_schema_callbacks_only=True,
                  execution_readiness_granted=False, qualified=False, admitted=False,
                  source_semantics_verified=False, Lake_executed=False,
                  Constitution_formalized=False, checkpoint_promoted=False)
    target = G / 'input-closure-seed.json'
    with target.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps(dict(path=str(target), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                          bytes=target.stat().st_size, inputs=len(INPUTS),
                          recursive_parent_refs=len(physical_refs), recursive_parent_reports=len(report_walk))))


if __name__ == '__main__': main()
