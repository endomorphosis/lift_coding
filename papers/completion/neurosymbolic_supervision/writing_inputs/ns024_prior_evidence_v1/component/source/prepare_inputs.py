"""Freeze the exact, already-authorized prior metadata read set; no outcome discovery."""
import argparse
from pathlib import Path
from common import binding, decode, encoded, read_bytes, write

def prepare(final, paper):
    final, paper = Path(final).absolute(), Path(paper).absolute()
    v3, ab = final.parent, final.parent.parent
    base, pilot = ab.parent, v3 / 'actual_pilot_v3'
    refs = {}
    def add(role, path, sha=None):
        assert role not in refs
        refs[role] = binding(path, sha)
        return decode(read_bytes(path, refs[role]['sha256'])) if str(path).endswith('.json') else None
    def linked(role, ref):
        return add(role, ref['path'], ref['sha256'])
    partial = add('six_ledger_index', final/'resource_lease_continuation_v1/client_analysis_slice_v1/actual009_partial_v1/analysis.private.json', '30702996a5a4f4dd295b9314928a43043fe4600db13a58c24b8596b3fb440acd')
    ledgers = partial['prior_and_preparation_cost_ledgers']
    assert len(ledgers) == 6
    # This document is read only to locate its six historical refs. No final rows enter output.
    for i, row in enumerate(ledgers):
        linked('ledger_%d' % i, row)
    review = add('pilot_root_review', pilot/'delegated_analysis_v1/root_complete24_review.private.json', '83105becb14ab86615f20d526409941d4bbeab5b4c9927803de3c388a195ca5a')
    assert review['accepted_developmental_analysis_and_export'] is True
    linked('pilot_analysis', review['analysis'])
    linked('pilot_export_manifest', review['public_export'])
    add('pilot_analyzer_source', pilot/'delegated_analysis_v1/analyze.py', 'a8bcf67cccb9c4175b1ac1a2186994d9497e176e79c4fae1ad495d4db9d519db')
    add('adopted_results', paper/'pilot/results.jsonl', '5373f74be90552cfcfe12be26ffbe99a77d4112003152233cfd8263ce4ad1d83')
    add('adopted_costs', paper/'pilot/costs.jsonl', 'b4ec79ac6ff315f849fbe58183715f30046cb64b5f0496420c33294d7b250685')
    add('pilot_boundary', paper/'pilot/recovery/final_input_source/pilot_boundary_disclosure.private.json', 'be3b683d284b0d6bd28d2ecfc7d1928521d8de8b5a65322899eeb91eaad702e5')
    prep = add('pilot_preparation', ab/'actual_context_qualification.private.json', '6c44e99a221d596b5bbf73e2ed4ea422978878338157a628b7b8472bc5f7a16f')
    assert len(prep['preparation_attempts']) == 26
    for i, attempt in enumerate(prep['preparation_attempts']):
        linked('pilot_prep_%02d' % i, attempt)
    add('v2_addendum', ab/'response_contract_v2/cost_and_provenance_addendum.private.json', '858b88b9e4527adfcad71aa2ce4fe57fcda54dd3ef346408ba43d40031ddd4ca')
    baseline = decode(read_bytes(refs['ledger_1']['path']))
    assert len(baseline['unit_results']) == 8
    for i, row in enumerate(baseline['unit_results']):
        linked('baseline_old_%02d' % i, row['original128_baseline_report'])
        linked('baseline_32_%02d' % i, row['current32_report'])
    linked('baseline_new_128', baseline['target128_report'])
    registry = add('original_registry', base/'historical_adapter/registry.private.json')
    for i, unit in enumerate(sorted(registry['units'])[4:8]):
        row = registry['units'][unit]
        assert row['split'] == 'pilot'
        directory = 'baseline_qualification_v2' if i < 3 else 'baseline_remaining12_v3'
        add('pilot_baseline_old_%02d'%i, base/'ns_baselines'/directory/unit/'report.json', row['baseline_qualification']['command_report_sha256'])
    final_prep = decode(read_bytes(refs['ledger_0']['path']))
    assert len(final_prep['preparation_attempts']) == 11
    for i, row in enumerate(final_prep['preparation_attempts']):
        linked('final_prep_%02d' % i, row['qualification'])
    recovery = decode(read_bytes(refs['ledger_5']['path']))
    previous_batch = linked('v2_batch', recovery['previous_batch'])
    for i, row in enumerate(recovery['previous_protocol_disposition']['terminal_failures']):
        add('v2_provider_%d'%i, Path(previous_batch['private_root'])/row['cell_id']/'http_proposer/result.json', row['provider_result_sha256'])
    linked('diagnostic_execution', recovery['diagnostic']['execution'])
    linked('diagnostic_accounting', recovery['diagnostic']['separate_accounting'])
    cancels = [linked('cancel_v1', recovery['prior_v1']['cancellation']), linked('cancel_v2', recovery['previous_cancellation'])]
    for version, cancel in enumerate(cancels, 1):
        rows = cancel['consumed_terminal_failures'] if version == 1 else cancel['failed_cells']
        assert len(rows) == 3
        for i, row in enumerate(rows):
            terminal = linked('v%d_terminal_%d' % (version, i), row if version == 1 else row['terminal_observation'])
            linked('v%d_client_%d' % (version, i), terminal['client_result'])
            linked('v%d_client_execution_%d' % (version, i), terminal['client_execution'])
    authority = add('continuation_authority', final/'resource_lease_continuation_v1/authority.approved.private.json', '5dd848ce32081268ab57851e6fbd76b746b3525ee5445d3e81debd631605d154')
    for key in ('old_reservation', 'old_release', 'successor_reservation', 'holder_launch_evidence', 'holder_after_caller_exit_evidence'):
        linked(key, authority[key])
    add('methods_draft', final/'ns022_writing_preparation_v1/methods.tex', '33bcef75e0c176c035170dc8525de48a63242ffea2865a50a6466982056c831e')
    return dict(schema='ns-anonymous-prior-inputs/v1', refs=refs,
                only_prior_and_preparation_projection=True, new_scientific_calls=0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--final', required=True)
    parser.add_argument('--paper', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    write(args.output, encoded(prepare(args.final, args.paper)))
