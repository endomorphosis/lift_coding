"""Reconcile NS020 only after actual complete, reviewed NS017 and NS019 evidence.

Uses the exact NS019 input/signature reader and deterministic results renderer.
No service/native import, original private-path access, candidate code, or oracle.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path

P = Path('papers/completion/neurosymbolic_supervision')
PREPARATION = P / 'writing_inputs/ns020_boundary_preparation_v2'
RENDERER_SHA256 = '16da76bbe3fe032cde70599790ad8ad1e52d9eb1baf4ea799cf4856d23410251'
PREPARATION_SHA256 = {
    'README.md': 'ded611c18a7a04caf8a6edc5548b758b0dc279c2ce4f8986cd0d14b05a0d6053',
    'boundary_witnesses.json': 'd4c402839086e2eb6b089a58ccfe775947caa7cfcb3f9647e19c621dfa83ad90',
    'failure_cases.md': 'ad3f954f1a337d377f0ae71d7748450980c319f3dba2d2909a88ffe5ea539016',
    'final_claim_evidence_matrix.json': 'b8f850530295251187d4760c71ed551dc3c95d40f113050056201c27212d2d5e',
    'source_evidence.json': '2d2edeede2454e431cfd5fec227c9189f09ae14eee8e142f49821e6e53bd2b25',
    'table18.tex': '3fa332e34627a5825f6065623ac39bd3f0a5041627375d167e3fd397f33e2495',
}
BOUNDARY_IDS = ['F-HTTP', 'F-custody', 'F-score', 'F-lease', 'F-failure']
DERIVED_ZERO_CHANGE = 'derived_zero_change_candidate_metadata'
CORE = ('number', 'cell_id', 'unit', 'arm', 'repetition', 'cache', 'terminal', 'outcome', 'useful_completion')
TIMES = ('provider_child_elapsed_seconds', 'http_wrapper_elapsed_seconds',
         'gateway_proposal_elapsed_seconds', 'gateway_score_elapsed_seconds',
         'gateway_score_elapsed_scope', 'grant_to_terminal_elapsed_seconds', 'end_to_end_scope',
         'client_poll_wall_seconds', 'client_poll_cpu_seconds', 'operator_review_effort_cost',
         'operator_review_effort_unknown_reason')
DISPOSITION = {
    'conditional_design_only': 'conditional_design_not_empirically_established',
    'source_presence_not_integration': 'source_presence_and_distinct_runtime_epochs_not_complete_deployment',
    'bounded_component_qualification': 'retained_historical_constructed_qualification_only',
    'broader_claim_not_established_by_this_pack': 'broader_lifecycle_claim_unestablished',
    'withdrawn_or_unavailable': 'withdrawn_unavailable_or_untested_as_declared',
    'legacy_preliminary_only_not_current_measurement': 'historical_estimate_excluded_from_current_measured_results',
    'original_design_superseded_by_frozen32': 'original_design_superseded_bounded_actual_AB_cold_comparison',
    'deferred_complete32': 'partially_measured_AB_outcomes_separate_costs_no_false_admission_estimate',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def renderer(repository):
    # This exact reviewed module imports only standard-library modules at import.
    # Its main, plotting function and all service/native sources are not executed.
    path = repository / P / 'analysis/analyze.py'
    require(path.resolve() == path and not path.is_symlink(), 'Canonical NS019 source required')
    raw = path.read_bytes()
    require(digest(raw) == RENDERER_SHA256, 'Reviewed NS019 reader source changed')
    scope = {'__name__': 'ns020_hash_bound_ns019_reader', '__file__': str(path)}
    exec(compile(raw, str(path), 'exec'), scope)
    return scope


def preparation(repository, reader):
    raw = {name: reader['read'](repository / PREPARATION / name, sha)
           for name, sha in PREPARATION_SHA256.items()}
    witness = reader['decode'](raw['boundary_witnesses.json'])
    matrix = reader['decode'](raw['final_claim_evidence_matrix.json'])
    require([r['id'] for r in witness['final_empirical_boundary_joins']] == BOUNDARY_IDS,
            'Exact five prepared final boundaries required')
    require(len(witness['table18_rows']) == 6 and len(matrix['claims']) == 32,
            'Six historical boundaries and 32 original claims required')
    return raw, witness, matrix


def object_reader(repository, manifest, reader):
    by_hash = {x['sha256']: x for x in manifest['retained_objects']}
    by_label = {x['label']: x for x in manifest['retained_objects']}

    def bytes_by_hash(sha):
        require(sha in by_hash, 'Required metadata object absent from actual NS017 bundle')
        item = by_hash[sha]
        raw = reader['read'](repository / item['repo_path'], sha, 64 << 20)
        require(len(raw) == item['bytes'], 'Retained metadata size differs')
        return raw

    def reference(ref):
        require(set(ref) == {'path', 'sha256'}, 'Exact original provenance reference required')
        return reader['decode'](bytes_by_hash(ref['sha256']))

    def metadata(label, optional=False):
        if optional and label not in by_label:
            return None, None
        require(label in by_label, 'Required retained metadata label absent: ' + label)
        item = by_label[label]
        return reader['decode'](bytes_by_hash(item['sha256'])), {
            'repository_path': item['repo_path'], 'sha256': item['sha256'],
            'label': label, 'body_read_and_hash_verified': True,
        }

    def commitment(sha, original_paths=()):
        item = by_hash.get(sha)
        return {'sha256': sha, 'original_paths_provenance_only': list(original_paths),
                'repository_path': None if item is None else item['repo_path'],
                'retained_object_available': item is not None,
                'body_read_by_this_helper': False,
                'scope': 'Original digest commitment checked by retained strict analysis/root review; private paths are never followed.'}

    return reference, metadata, commitment


def disclosure_rows(disclosures, analysis, commitment):
    rows = {r['cell_id']: r for r in analysis['rows']}
    result = {cid: [] for cid in rows}
    seen = set()
    for item in disclosures['records']:
        row = rows[item['cell_id']]
        key = (item['cell_id'], item['category'])
        require(key not in seen, 'Duplicate additive disclosure')
        seen.add(key)
        require(item['original_signed_receipt_sha256'] == row['original_signed_receipt_sha256']
                and item['signed_outcome'] == row['outcome']
                and item['useful_completion'] is row['useful_completion'], 'Disclosure changes signed outcome')
        require(item['sanitized_only'] is True and item['hidden_names_source_or_raw_logs_included'] is False
                and item['evidence'] and isinstance(item['statement'], str), 'Sanitized disclosure scope required')
        if item['category'] == 'incomplete_hidden_validation_import_failure':
            require(row['hidden_collected'] == 0 and item['hidden_assertion_failure_observed'] is False
                    and item['infrastructure_fault_proven'] is False, 'Collection failure is not a hidden assertion or proved infrastructure fault')
        public = copy.deepcopy({k: v for k, v in item.items() if k != 'evidence'})
        public['evidence'] = [commitment(x['sha256'], [x['path']]) for x in item['evidence']]
        result[item['cell_id']].append(public)
    return result


def candidate_metadata(row, body, entry, metadata, disclosures):
    cid = row['cell_id']
    review, review_ref = metadata('final/' + cid + '/operator_review.json', optional=True)
    if body.get('candidate_sha256') is None:
        require(entry == {'candidate_present': False, 'reason': 'no_candidate_in_original_signed_receipt'},
                'Absent original candidate must remain absent')
        require(review is None, 'Candidate review without original signed candidate')
        return {'candidate_present': False, 'reason': entry['reason'], 'candidate_review': None,
                'candidate_binding_metadata': None, 'derived_metadata_provenance': []}
    require(entry['candidate_present'] is True and entry['public_edit_payloads_only'] is True,
            'Actual root-reviewed candidate metadata required')
    cb, cb_ref = metadata('candidate/' + cid + '/candidate_binding.json')
    require(cb_ref['sha256'] == entry['candidate_binding']['sha256']
            and cb['sha256'] == body['candidate_sha256'] == digest(canonical(cb['files'])),
            'Signed candidate inventory identity differs')
    require(type(cb['patch_bytes']) is int and cb['patch_bytes'] >= 0
            and cb['patch_bytes'] == body['patch_bytes']
            and len(cb['changed_paths']) == len(set(cb['changed_paths']))
            and set(cb['changed_paths']) == set(entry['changed_files'])
            and cb['patch_sha256'] == entry['patch']['sha256'], 'Candidate patch metadata differs')
    derived = []
    if review is not None:
        require(review['schema'] == 'operator-historical-final-candidate-review/v1'
                and review['reviewer_kind'] == 'ai_operator'
                and review['trust_scope'] == 'specific_reviewed_final_candidate_only'
                and review['human_annotation'] is False
                and review['automatic_adversarial_scorer_integrity_qualified'] is False,
                'AI candidate review cannot become human or general adversarial assurance')
        rb = review['binding']
        require(rb['cell_id'] == cid and rb['candidate_sha256'] == cb['sha256']
                and rb['candidate_binding_sha256'] == digest(canonical(cb))
                and rb['patch_sha256'] == cb['patch_sha256']
                and rb['grant_sha256'] == body['grant_sha256'], 'Exact candidate review binding differs')
        if body.get('operator_review_sha256') is not None:
            require(body['operator_review_sha256'] == review_ref['sha256'], 'Signed score cites a different review')
        require(entry['review_scope'] == 'actual_retained_ai_candidate_review', 'Candidate manifest review scope differs')
        reviewed = {'reference': review_ref, 'approved': review['approved'], 'reviewed_at': review['reviewed_at'],
                    'binding': rb, 'scope': review['trust_scope'], 'human_annotation': False,
                    'comprehensive_adversarial_scorer_qualification': False}
        origin = 'retained_candidate_binding_metadata_bound_to_actual_AI_review'
    else:
        require(row['disposition_class'] == 'known_proposal_failure'
                and (body.get('scorer') or {}).get('executed') is False
                and entry['review_scope'] == 'no_candidate_review_before_original_proposal_failure',
                'A missing candidate review cannot be invented')
        derived = [d for d in disclosures if d['category'] == DERIVED_ZERO_CHANGE]
        require(len(derived) <= 1, 'Ambiguous reconstructed candidate metadata disclosure')
        marked_derived = entry.get('candidate_binding_metadata_origin') == 'derived_zero_change_after_failed_proposal'
        require(not marked_derived or len(derived) == 1,
                'A marked reconstructed binding needs separate root-reviewed derivation provenance')
        if derived:
            require(cb['changed_paths'] == [] and cb['patch_bytes'] == 0
                    and cb['patch_sha256'] == digest(b''), 'Reconstructed baseline metadata must describe exact zero changes')
        reviewed = None
        origin = ('root_reviewed_reconstructed_zero_change_metadata_after_failed_proposal_not_original_binding_file'
                  if derived else 'root_reviewed_candidate_binding_metadata_original_file_existence_not_claimed_here')
    return {'candidate_present': True, 'signed_candidate_inventory_sha256': body['candidate_sha256'],
            'candidate_binding_metadata': cb_ref, 'candidate_binding_metadata_origin': origin,
            'patch_sha256': cb['patch_sha256'], 'patch_bytes': cb['patch_bytes'],
            'changed_paths': cb['changed_paths'], 'candidate_code_or_patch_read': False,
            'candidate_review': reviewed, 'review_after_grant_expiry': row['candidate_review_after_grant_expiry'],
            'derived_metadata_provenance': derived}


def cell_joins(manifest, analysis, disclosures, operator_rows, reference, metadata, commitment):
    refs = manifest['private_original_refs']
    bindings = reference(refs['analysis_bindings'])
    authority = reference(refs['export_cells'])
    candidates = reference(refs['candidate_payload_manifest'])
    contract = reference(manifest['runtime_continuation']['contract_binding'])
    require(candidates['schema'] == 'ns-final32-reviewed-candidate-payloads/v1'
            and candidates['actual_complete32'] is True
            and candidates['ordered_cells'] == manifest['ordered_cells']
            and candidates['analysis']['sha256'] == refs['analysis']['sha256'], 'Complete reviewed candidate manifest required')
    require(contract['ordered_cells'] == manifest['ordered_cells']
            and contract['consumed_cells'] == manifest['ordered_cells'][:7]
            and contract['remaining_cells'] == manifest['ordered_cells'][7:], 'Original seven / continued 25 runtime order differs')
    by_disclosure = disclosure_rows(disclosures, analysis, commitment)
    outputs = []
    for row in analysis['rows']:
        cid = row['cell_id']
        cell_authority = authority['cells'][cid]
        name = 'proposal.json' if row['original_receipt_filename'] == 'proposal_result.json' else 'response.json'
        original, original_ref = metadata('final/' + cid + '/' + name)
        body = original['receipt']
        require(original_ref['sha256'] == row['original_signed_receipt_sha256'], 'Original signed receipt identity differs')
        disposition, disposition_ref = metadata('final/' + cid + '/disposition.json', optional=True)
        terminal_ref = disposition_ref if row['disposition_class'] is not None else original_ref
        require(terminal_ref is not None and terminal_ref['sha256'] == cell_authority['terminal_sha256'],
                'Signed terminal identity differs from exported authority')
        require(bindings[row['signed_terminal_path']] == row['signed_terminal_sha256'],
                'Operator observation is not the signed response/disposition')
        original_epoch = cid in contract['consumed_cells']
        source_map = contract['original_frozen_source_bindings'] if original_epoch else contract['effective_source_bindings']
        if original_epoch:
            require('runtime_continuation' not in body and 'frozen_source_bindings' not in body,
                    'Original prefix relabeled as successor runtime')
            if 'source_bindings' in body:
                require(body['source_bindings'] == source_map, 'Original source bindings differ')
        else:
            require(body['source_bindings'] == source_map
                    and body['frozen_source_bindings'] == contract['original_frozen_source_bindings']
                    and body['runtime_continuation'] == contract['runtime_continuation'],
                    'Continued signed runtime bindings differ')
        require(body['provider_termination']['termination_proven'] is True, 'Unknown termination cannot enter complete boundary table')
        source_records = [{'role': Path(path).name, 'binding': commitment(sha, [path])}
                          for path, sha in sorted(source_map.items())]
        observation = commitment(row['signed_terminal_sha256'], [row['signed_terminal_path']])
        observation['scope'] = 'Operator terminal observation, a distinct original byte object from the signed response/disposition.'
        lookup = lambda sha: commitment(sha, [p for p, h in bindings.items() if h == sha])
        current_disclosures = by_disclosure[cid]
        candidate = candidate_metadata(row, body, candidates['cells'][cid], metadata, current_disclosures)
        failure_account, failure_ref = metadata('final/' + cid + '/operator_disposition.json', optional=True)
        failure = None
        if row['disposition_class'] is not None:
            require(disposition is not None and failure_account is not None, 'Failure disposition/accounting absent')
            d = disposition['receipt']
            require(d['classification'] == row['disposition_class'] and d['success_credit'] is False
                    and d['retry_allowed'] is False and row['useful_completion'] is False, 'Failure must retain no credit and no retry')
            failure = {'classification': d['classification'], 'signed_disposition': disposition_ref,
                       'operator_accounting': failure_ref, 'accounting_reviewed_at': failure_account.get('reviewed_at'),
                       'success_credit': False, 'retry_allowed': False,
                       'retained_accounting_statement': row['retained_operator_accounting_statement']}
        outputs.append({
            **{k: row[k] for k in CORE},
            'references': {'original_signed_receipt': original_ref, 'signed_terminal': terminal_ref,
                           'operator_terminal_observation': observation, 'grant': lookup(body['grant_sha256']),
                           'provider_cleanup': lookup(body['provider_termination']['cleanup_sha256'])},
            'runtime': {'row_provenance': row['runtime_source_provenance'],
                        'source_epoch': 'original_resource_lease' if original_epoch else 'prospective_resource_lease_continuation',
                        'source_files': source_records, 'native_source_versions': manifest['source_versions'],
                        'cooperative_lease_not_physical_exclusivity': True, 'current_liveness_rechecked': False},
            'http': {k: row.get(k) for k in ('actual_provider_posts', 'provider_status', 'http_status',
                     'served_model', 'served_revision', 'parse_error', 'unknown_external_charge')},
            'candidate': candidate,
            'score': {k: row.get(k) for k in ('raw_scorer_success', 'raw_cold_classification', 'actual_cold_completed',
                      'scorer_reservation_exists', 'visible_passed', 'visible_collected', 'hidden_passed', 'hidden_collected')},
            'time_and_resources': {'clocks': {k: row.get(k) for k in TIMES},
                                   'signed_resource_compliance': row['resource_compliance'],
                                   'operator_phases': [r for r in operator_rows if r['cell_id'] == cid],
                                   'clock_grand_total': None, 'overlapping_clocks_summed': False},
            'termination': {'provider_termination_proven': True,
                            'root_reviewed_all_client_cleanup_verified': True,
                            'full_original_cleanup_bodies_replayed_here': False},
            'failure_accounting': failure,
            'validation_and_operational_disclosures': current_disclosures,
            'human_annotation': False,
        })
    return outputs


def reconcile(prep, witness, matrix, manifest, analysis, results, cell_rows, provenance):
    require(len(cell_rows) == 32 and [r['cell_id'] for r in cell_rows] == manifest['ordered_cells']
            and all(r['terminal'] is True for r in cell_rows), 'Complete original-order actual boundary rows required')
    w = copy.deepcopy(witness)
    w.update(schema='ns020-complete32-boundary-reconciliation/v1', preparation_only=False,
             final_claim_reconciliation_complete=True, native_completion_claimed=False,
             actual_final32_reconciliation=provenance,
             original_preparation_digest=PREPARATION_SHA256['boundary_witnesses.json'],
             original_destination_preimages_are_historical=True)
    fields = {
        'F-HTTP': ('http',), 'F-custody': ('candidate',), 'F-score': ('score',),
        'F-lease': ('time_and_resources', 'termination'),
        'F-failure': ('http', 'score', 'failure_accounting', 'termination'),
    }
    claims = {
        'F-HTTP': 'Actual original-order provider outcomes and missingness are retained. One-call limits and observed POST counts do not prove production routing efficacy.',
        'F-custody': 'Exact signed candidate identities, retained AI review metadata and separately disclosed reconstructed zero-change metadata are joined. No human semantic fidelity or comprehensive malicious-candidate guarantee is inferred.',
        'F-score': 'Original signed cold-score/failure evidence is joined to the existing useful-completion policy; incomplete validation, hidden assertion outcomes and missing scoring remain distinct.',
        'F-lease': 'Original and successor source epochs, measured compliance, termination and separate clocks are retained. This replay establishes neither current lease liveness nor exclusive physical capacity.',
        'F-failure': 'All 32 terminal cells remain in original order and denominator; consumed failures retain no credit, no retry and unknown charges, with additive operational disclosures.'
    }
    for boundary in w['final_empirical_boundary_joins']:
        bid = boundary['id']
        boundary['historical_preparation_claim'] = boundary['claim']
        boundary['claim'] = claims[bid]
        boundary['empirical_final_evidence_status'] = 'actual_complete32_root_reviewed_and_NS019_recomputed'
        boundary['empirical_final_rows'] = []
        for row in cell_rows:
            selected = {k: copy.deepcopy(row[k]) for k in CORE}
            selected.update(references=copy.deepcopy(row['references']), runtime=copy.deepcopy(row['runtime']),
                            validation_and_operational_disclosures=copy.deepcopy(row['validation_and_operational_disclosures']))
            selected.update({k: copy.deepcopy(row[k]) for k in fields[bid]})
            selected['boundary_source_roles'] = [s for s in row['runtime']['source_files'] if s['role'] in boundary['source_roles']]
            selected['declared_roles_absent_in_this_epoch'] = sorted(set(boundary['source_roles']) - {s['role'] for s in selected['boundary_source_roles']})
            selected['source_role_absence_scope'] = 'lease_continuation.py is intentionally absent in the original seven-cell epoch; no executed source is invented.'
            boundary['empirical_final_rows'].append(selected)
    m = copy.deepcopy(matrix)
    m.update(schema='ns020-complete32-final-claim-evidence-matrix/v1', preparation_only=False,
             all_final_claims_resolved=True, final_scientific_results_deferred=False,
             resolution_means='Every original claim has an explicit retained/narrowed/conditional/withdrawn disposition; it does not mean every original claim was proved.',
             boundary_witnesses_file='../analysis/boundary_witnesses.json',
             source_evidence_file='../writing_inputs/ns020_boundary_preparation_v2/source_evidence.json',
             actual_final32_reconciliation=provenance,
             outside_reviewers_are_not_completion_gate=True)
    endpoint = {k: copy.deepcopy(results[k]) for k in ('useful_completions', 'arm_useful_fixed16',
                'mean_B_minus_A_useful', 'bootstrap', 'outcomes', 'resource_summaries', 'observed_api_usage')}
    endpoint.update(fixed_cells=32, independent_families=8, nested_repetitions_per_family_arm=2,
                    isolated_false_admission_estimate=None, net_cost_grand_total=None, human_semantic_fidelity=None,
                    scope='Descriptive frozen A/B cold comparison; resource clocks are separate and unknown costs remain unknown.')
    for claim in m['claims']:
        require(claim['preparation_disposition'] in DISPOSITION, 'Original claim disposition lacks a final scope')
        claim['final_disposition'] = DISPOSITION[claim['preparation_disposition']]
        claim['historical_allowed_wording'] = claim['allowed_current_wording']
        claim['final_evidence'] = {'historical_evidence_ids': claim['evidence_ids'],
                                   'historical_source_evidence_sha256': PREPARATION_SHA256['source_evidence.json']}
        if claim['original_claim_id'] in ('C-ABS-01', 'C-19'):
            claim['empirical_final_outcome'] = copy.deepcopy(endpoint)
            claim['final_evidence']['NS019_results'] = provenance['NS019_results']
            claim['allowed_current_wording'] = (
                'Report the root-reviewed frozen eight-family A/B cold32 outcomes and conditional descriptive interval from NS019. '
                'The two repetitions are nested identifiers, not independent families or served-API seed claims. '
                'Separate measured clock/usage scopes do not establish net settled cost; isolated false-admission, human fidelity, '
                'C/D, warm/reuse/publication benefits and the original confirmatory comparisons remain unmeasured or withdrawn.')
        else:
            require(claim['empirical_final_outcome'] is None, 'Broad original claim cannot acquire fabricated final outcome')
    m['narrow_final_boundary_observations'] = [{'id': b['id'], 'claim': b['claim'], 'boundary_witness_file': m['boundary_witnesses_file'],
                                             'actual_ordered_cell_count': 32, 'scientific_success_inferred_from_controls': False}
                                            for b in w['final_empirical_boundary_joins']]
    text = '# Actual complete32 failure and boundary reconciliation\n\n'
    text += 'All 32 original-order terminal cells are retained. This report uses the exact NS019 input reader and reproduces its bound results. It performs no new provider, scorer, native admission, historical qualification, or human annotation.\n\n'
    text += 'The five final boundary joins are in `boundary_witnesses.json`. Original signed response/disposition digests and operator-observation digests remain separate. A private-original digest commitment is not a claim that its body is in this bundle or was reopened here.\n\n'
    text += '| Cell | Family | Arm | Outcome | Useful | Signed resource compliant |\n|---:|---|---|---|---|---|\n'
    for row in cell_rows:
        text += '| ' + ' | '.join(str(x).replace('|', '\\|') for x in (row['number'], row['unit'], row['arm'], row['outcome'], row['useful_completion'], row['time_and_resources']['signed_resource_compliance']['compliant'])) + ' |\n'
    text += '\nAdditive disclosures preserve their original outcome and custody bindings:\n\n'
    for row in cell_rows:
        for item in row['validation_and_operational_disclosures']:
            text += f"- Cell {row['number']} / `{item['category']}`: {item['statement']}\n"
    text += '\nReconstructed zero-change candidate metadata is labeled separately, with the root derivation review retained through additive disclosures. It does not establish that a candidate-binding file existed after the original failed proposal. A missing pre-score review remains missing.\n\n'
    text += 'Provider, child, wrapper, gateway, scorer, client and operator clocks retain separate endpoints and missingness; no grand total is created. Authentication headroom and administrative recovery disclosures do not alter the frozen resource predicates or original success credit. Incomplete hidden collection is not an observed hidden assertion failure or a proven infrastructure fault.\n\n'
    text += 'Historical false reuse remains one of all 26 attempts. The four NS027 correction invocations retain 48 attempted cases and 47 completed rows, with two separate 34-test public baselines. No passing control becomes a repair result, universal safety proof, routing/reuse gain or distributed exactly-once guarantee.\n\n'
    text += '## Retained historical preparation and limitations\n\nThe section below is the exact earlier preparation text. Its references to deferred final rows and later workers describe that historical preparation; the completed joins and original-order rows above are the current reconciliation. All original limitations remain in force.\n\n'
    text += prep['failure_cases.md'].decode()
    return {'analysis/boundary_witnesses.json': encoded(w),
            'manuscript/generated/table18.tex': prep['table18.tex'],
            'audit/final_claim_evidence_matrix.json': encoded(m),
            'analysis/failure_cases.md': text.encode()}


def inputs(repository, manifest_sha, ablation_sha, results_sha):
    repository = Path(repository).resolve()
    reader = renderer(repository)
    # Existing reader refuses partial manifests before opening any cell metadata.
    values = reader['inputs'](repository, manifest_sha, ablation_sha)
    manifest, analysis, summary, policy, disclosures, operator_rows, prior, ablation, source_provenance = values
    result_raw = reader['read'](repository / P / 'analysis/results.json', results_sha)
    require(result_raw == reader['render'](*values)['analysis/results.json'], 'NS019 results differ from exact retained reader/render output')
    results = reader['decode'](result_raw)
    prep, witness, matrix = preparation(repository, reader)
    reference, metadata, commitment = object_reader(repository, manifest, reader)
    cell_rows = cell_joins(manifest, analysis, disclosures, operator_rows, reference, metadata, commitment)
    provenance = {'NS017_manifest': {'repository_path': str(P / 'runs/main/manifest.json'), 'sha256': manifest_sha},
                  'NS019_results': {'repository_path': str(P / 'analysis/results.json'), 'sha256': results_sha},
                  'NS019_renderer_source_sha256': RENDERER_SHA256, 'NS019_reverified_provenance': source_provenance,
                  'original_ordered_cells': manifest['ordered_cells'], 'frozen_policy_unchanged': True,
                  'root_review_reference': manifest['private_original_refs']['root_complete_review'],
                  'actual_terminal_cells': 32, 'historical_table_rows_changed': False,
                  'original_claim_ids_and_text_changed': False, 'preparation_files_sha256': PREPARATION_SHA256,
                  'new_provider_calls': 0, 'new_scorer_calls': 0, 'new_native_calls': 0,
                  'human_annotation': False, 'publication_authorized': False}
    return prep, witness, matrix, manifest, analysis, results, cell_rows, provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--ablation-manifest-sha256', required=True)
    parser.add_argument('--results-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    output = args.output
    require(output.is_absolute() and output.resolve() == output and not output.exists(), 'Fresh canonical output directory required')
    values = inputs(args.repository, args.manifest_sha256, args.ablation_manifest_sha256, args.results_sha256)
    files = reconcile(*values)
    output.mkdir(mode=0o700)
    for name, raw in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    print(json.dumps({'complete32': True, 'native_completion_claimed': False, 'scientific_calls': 0,
                      'output': str(output), 'files': sorted(files)}))


if __name__ == '__main__':
    main()
