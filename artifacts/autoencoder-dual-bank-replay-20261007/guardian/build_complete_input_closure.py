"""Add the sealed new protocol and archival numerical references to seed-r1.

Historical compact audits are bound as immutable reports, not recursively
treated as current producer dependencies: their observer snapshots may name
mutable shared ledgers. Archived numerical summaries do close all physical
path/SHA references recursively. No numerical module is imported.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

W = Path('/home/barberb/lift_coding')
G = W / 'artifacts/autoencoder-dual-bank-replay-20261007/guardian'
PROTOCOL = G.parent / 'predeclared-protocol.json'
PROTOCOL_SHA = '75d4d01893578265c2be3bcc53ed96ca661fdb03781704a074b9df56e6bf30d2'


def main():
    helper_path = G / 'build_input_closure_seed.py'
    spec = importlib.util.spec_from_file_location('_dual_readonly_input_closure', helper_path)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    original_path = G / 'input-closure-seed.json'
    helper.pin(original_path, 'c05fd1f26845269da07cba96f3cf96965ab0aca321491245452b50c90230580c')
    original = json.loads(original_path.read_bytes())
    for path, wanted in original['input_sha256'].items(): helper.pin(path, wanted)
    helper.pin(PROTOCOL, PROTOCOL_SHA)
    protocol = json.loads(PROTOCOL.read_bytes())
    if protocol['schema'] != 'dual-bank-replay-comparison-protocol/v1':
        raise ValueError('exact new preregistered protocol required')
    direct_refs = helper.references(protocol)
    for path, wanted in direct_refs.items(): helper.pin(path, wanted)
    # Parent and archived control numerical summaries are operationally frozen
    # objects. Compact review reports remain archival evidence only.
    numerical_queue = [Path(protocol['archived_control']['path'])]
    walked = set(); numerical_refs = {}; report_walk = []
    while numerical_queue:
        path = numerical_queue.pop()
        if path in walked: continue
        if len(walked) >= 128: raise ValueError('bounded archived numerical closure exceeded')
        walked.add(path)
        wanted = helper.INPUTS.get(str(path.resolve()))
        binding = helper.pin(path, wanted)
        if path.suffix != '.json': continue
        if binding['bytes'] > 128 * 1024 * 1024: raise ValueError('bounded archived numerical JSON required')
        refs = helper.references(json.loads(path.read_bytes()))
        report_walk.append(dict(path=str(path), sha256=binding['sha256'], physical_refs=len(refs)))
        for ref, digest in refs.items():
            if ref in numerical_refs and numerical_refs[ref] != digest:
                raise ValueError('conflicting archived physical reference')
            numerical_refs[ref] = digest; helper.pin(ref, digest)
            if Path(ref).suffix == '.json': numerical_queue.append(Path(ref))
    additions = {path: sha for path, sha in helper.INPUTS.items() if path not in original['input_sha256']}
    if any(helper.INPUTS.get(path) != sha for path, sha in original['input_sha256'].items()):
        raise ValueError('original authenticated seed changed')
    result = dict(schema='dual-bank-replay-authenticated-input-closure-seed/v2', complete=True,
                  previous_seed=dict(path=str(original_path), **helper.BINDINGS[str(original_path)]),
                  all1203_seed_r1_pins_unchanged=True, all1185_predecessor_pins_unchanged=True,
                  sealed_protocol=dict(path=str(PROTOCOL), **helper.BINDINGS[str(PROTOCOL)]),
                  protocol_direct_physical_refs=len(direct_refs),
                  archived_numerical_recursive_physical_refs=len(numerical_refs),
                  archived_numerical_reports_walked=report_walk,
                  exact_added_pins=additions, authenticated_input_count=len(helper.INPUTS),
                  input_sha256=helper.INPUTS, artifacts=helper.BINDINGS,
                  archival_review_metadata_references_not_reinterpreted_as_live_dependencies=True,
                  models_imported=False, numerical_modules_imported=False, models_executed=False,
                  fresh_encoder_executed=False, shared_state_written=False,
                  execution_readiness_granted=False, qualified=False, admitted=False,
                  source_semantics_verified=False, Lake_executed=False,
                  Constitution_formalized=False, checkpoint_promoted=False,
                  pending=['final driver and dual adapter freeze', 'strict phase profiles',
                           'root independent source/readiness review', 'completed own preflight audit before training'])
    target = G / 'input-closure-seed-r2.json'
    with target.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps(dict(path=str(target), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                          bytes=target.stat().st_size, inputs=len(helper.INPUTS),
                          protocol_direct_refs=len(direct_refs), archived_recursive_refs=len(numerical_refs),
                          new_pins=len(additions))))


if __name__ == '__main__': main()
