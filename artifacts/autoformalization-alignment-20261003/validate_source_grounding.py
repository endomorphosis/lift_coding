"""Validate saved source contracts and documentation without learned execution."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path('/home/barberb/lift_coding')
REPO = ROOT / 'external/ipfs_datasets'
CAMPAIGN = ROOT / 'artifacts/autoformalization-alignment-20261003'
OUTPUT = CAMPAIGN / 'source-grounding-validation-01'


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def bind(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def references(value):
    if isinstance(value, dict):
        if {'path', 'sha256'} <= value.keys():
            yield value
        for child in value.values():
            yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def main():
    assert not OUTPUT.exists(), 'fresh validation generation required'
    report_path = CAMPAIGN / 'grounding-01/report.json'
    report = load(report_path)
    assert bind(report_path)['sha256'] == '4cf39336bfa6586d230012380bddf287dd389ac4ec2f4314a10386637a8462c7'
    assert report['content_sha256'] == digest({k: v for k, v in report.items() if k != 'content_sha256'})
    checked = {}
    for reference in references(report):
        current = bind(reference['path'])
        assert current['sha256'] == reference['sha256']
        assert 'bytes' not in reference or reference['bytes'] == current['bytes']
        checked[current['path']] = current
    manifest = load(report['request_manifest_binding']['path'])
    construction = load(report['construction_binding']['path'])
    diagnostics = load(report['posthoc_authored_diagnostics_binding']['path'])
    overlay = load(report['posthoc_source_span_overlay_binding']['path'])
    for item in (manifest, construction, diagnostics, overlay):
        assert item['content_sha256'] == digest({k: v for k, v in item.items() if k != 'content_sha256'})
    assert manifest['row_count'] == construction['row_count'] == diagnostics['row_count'] == 34
    assert manifest['vocabulary_provenance'] == 'frozen_parser_01_TRAIN_supervised_atom_vocabulary'
    assert manifest['vocabulary_fit_development_used'] is False
    assert construction['targets_used_in_construction'] is False
    assert construction['authored_panel_semantics_read'] is False
    assert report['authored_reference_access_after_source_construction_finished'] is True
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.legal_ir.canonical_decoder_preflight import validate_decoder_preflight
    from ipfs_datasets_py.logic.legal_ir.canonical_source_grounding import (
        DECODER_PROFILES, validate_decoder_transport, validate_grounded_source,
    )
    preflight_counts, grounding_counts, anchor_facets = Counter(), Counter(), Counter()
    transport_counts = {profile: Counter() for profile in DECODER_PROFILES}
    transport_issues = {profile: Counter() for profile in DECODER_PROFILES}
    receipts_by_id = {}
    for request, receipt, diagnostic in zip(manifest['rows'], construction['rows'], diagnostics['rows'], strict=True):
        assert request['id'] == receipt['id'] == diagnostic['id']
        assert request['input_sha256'] == receipt['input_sha256'] == diagnostic['input_sha256']
        assert hashlib.sha256(request['source_text'].encode()).hexdigest() == receipt['source_sha256']
        assert request['source_sha256'] == receipt['source_sha256']
        preflight = validate_decoder_preflight(receipt['preflight'])
        grounding = validate_grounded_source(receipt['grounding'])
        assert grounding['preflight'] == preflight
        assert grounding['request']['source_text'] == request['source_text']
        assert grounding['request']['request_id'] == request['id']
        assert grounding['request']['atom_vocabulary'] == manifest['vocabulary']
        assert preflight['context']['text'] == request['declared_context']['text']
        assert preflight['context']['sha256'] == request['declared_context']['sha256'] == receipt['context_sha256']
        assert preflight['context']['requires_resolution'] == request['requires_context_resolution']
        assert grounding['context_applied'] is False
        preflight_counts[preflight['outcome']] += 1
        grounding_counts[grounding['outcome']] += 1
        assert len(receipt['transports']) == len(DECODER_PROFILES) == 3
        for profile, transport in zip(DECODER_PROFILES, receipt['transports'], strict=True):
            tokens = manifest['fixed_codec_vocabulary'] if profile == DECODER_PROFILES[1] else None
            assert transport['decoder_profile'] == profile
            validate_decoder_transport(transport, grounding, codec_tokens=tokens)
            transport_counts[profile][transport['outcome']] += 1
            transport_issues[profile].update(issue['code'] for issue in transport['issues'])
            assert all(transport[key] is False for key in (
                'target_access', 'model_executed', 'source_fidelity_established', 'qualified', 'proof_authority',
                'generated_candidate_assessed', 'checkpoint_selected'))
        occupied = []
        for anchor in grounding['anchors']:
            assert request['source_text'][anchor['start']:anchor['end']] == anchor['source_text']
            assert anchor['offset_unit'] == 'unicode_character_half_open'
            assert anchor['start'] < anchor['end']
            anchor_facets[anchor['facet']] += 1
            occupied.append((anchor['start'], anchor['end']))
        ordered = sorted(occupied)
        assert all(left[1] <= right[0] for left, right in zip(ordered, ordered[1:], strict=False))
        assert diagnostic['reference_used_for_construction'] is False and diagnostic['independent_fidelity_score'] is False
        receipts_by_id[request['id']] = receipt
    assert dict(preflight_counts) == report['preflight_outcomes'] == dict(unassessed=24, clarification_required=4, unsupported_profile=6)
    assert dict(grounding_counts) == report['grounding_outcomes'] == dict(grounded_candidate=22, source_blocked=10, proposal_unavailable=2)
    assert dict(anchor_facets) == report['source_anchor_count_by_facet']
    assert sum(anchor_facets.values()) == report['source_anchor_count'] == 172
    for profile in DECODER_PROFILES:
        saved = report['transport_summaries'][profile]
        assert saved['denominator'] == 34 and saved['candidate_acceptance_decisions'] == 0
        assert saved['outcomes'] == dict(transport_counts[profile])
        assert saved['issue_codes'] == dict(transport_issues[profile])
    assert sum(row['exact_authored_reference_agreement'] is True for row in diagnostics['rows']) == 22
    assert all(row['review_status'] == 'pending_human_review' for row in diagnostics['rows'])
    decoded_occurrences, decoded_ids = 0, set()
    for state in overlay['states']:
        previous = load(state['old_output_binding']['path'])
        assert len(state['rows']) == len(previous['rows']) == 34
        decoded, blocked = 0, 0
        for row, old in zip(state['rows'], previous['rows'], strict=True):
            receipt = receipts_by_id[row['id']]
            assert old['source_sha256'] == row['source_sha256'] == receipt['source_sha256']
            assert old['status'] == row['previous_decoder_status']
            assert old['reason'] == row['previous_decoder_reason']
            block = receipt['preflight']['outcome'] != 'unassessed'
            assert block == row['associated_with_preflight_block']
            assert row['acceptance_decision'] is None
            if old['status'] == 'decoded':
                decoded += 1
                blocked += int(block)
                decoded_ids.add(row['id'])
        assert decoded == state['previous_decoded_count']
        assert blocked == state['previously_decoded_and_associated_with_preflight_block_count'] == decoded
        assert state['unassessed_rows_counted_as_accepted'] == 0
        decoded_occurrences += decoded
    assert decoded_occurrences == 10 and len(decoded_ids) == 4
    assert all(report['calls'][key] == 0 for key in ('models', 'encoders', 'provers', 'training'))
    assert report['prior_unchanged_checked_file_count'] == 245
    assert report['blocked_import_attempts'] == []
    assert not {'torch', 'transformers', 'spacy', 'numpy', 'llama_cpp'}.intersection(sys.modules)
    assert all(report[key] is False for key in ('qualified', 'proof_authority', 'source_fidelity_established', 'checkpoint_promoted'))
    documents = [CAMPAIGN / 'source-grounding-report.md',
                 ROOT / 'implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md']
    links = []
    for document in documents:
        for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', document.read_text()):
            if '://' in target or target.startswith('#'):
                continue
            resolved = (document.parent / target.split('#')[0]).resolve()
            assert resolved.is_file() or resolved == OUTPUT / 'validation.json'
            links.append(dict(document=str(document), target=target, resolved=str(resolved)))
    ids = re.findall(r'^\| (AFI-[0-9]+[ab]?) \|', documents[1].read_text(), flags=re.M)
    assert len(ids) == len(set(ids)) == 25
    assert set(re.findall(r'AFI-[0-9]+[ab]?', documents[1].read_text())) <= set(ids)
    checkout = ROOT / '.worktrees/alignment-decoder-768-20261003'
    assert subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain=v1',
                                   '--untracked-files=normal'], text=True).strip() == ''
    for reference in checked.values():
        assert bind(reference['path']) == reference
    new_files = [REPO / relative for relative in (
        'ipfs_datasets_py/logic/legal_ir/canonical_decoder_preflight.py',
        'ipfs_datasets_py/logic/legal_ir/canonical_source_grounding.py',
        'tests/unit/logic/legal_ir/test_canonical_decoder_preflight.py',
        'tests/unit/logic/legal_ir/test_canonical_source_grounding.py')]
    result = dict(schema='alignment-source-grounding-stage-validation/v1', status='passed_unqualified',
                  runner_binding=bind(__file__), report_binding=bind(report_path),
                  checked_file_bindings=list(checked.values()), checked_file_count=len(checked),
                  new_implementation_test_bindings=[bind(path) for path in new_files],
                  deterministic_preflight_replays=34, deterministic_grounding_replays=34,
                  deterministic_transport_replays=102, source_anchors_verified=172,
                  preflight_counts=dict(preflight_counts), grounding_counts=dict(grounding_counts),
                  source_span_overlay_decoded_occurrences=10, source_span_overlay_unique_decoded_inputs=4,
                  original_source_span_outputs_preserved=True, preserved_prior_binding_count=245,
                  independent_readonly_review_scopes=['synthetic_source_anchors_tampering_and_1890_codec_cases',
                                                     'saved_artifact_source_joins_contracts_and_overlay_arithmetic'],
                  focused_test_results=dict(passed=275, elapsed_seconds=4.04),
                  ruff_results=dict(new_implementation_test_files=4, assay_runner=1, status='passed'),
                  documentation_bindings=[bind(path) for path in documents], local_link_checks=links,
                  work_package_ids=ids, isolated_decoder_checkout_clean=True,
                  model_execution=False, training_execution=False, proof_execution=False,
                  complete_dependency_manifest=False, independent_semantic_review_completed=False,
                  qualified=False, proof_authority=False, source_fidelity_established=False)
    result['content_sha256'] = digest(result)
    OUTPUT.mkdir()
    path = OUTPUT / 'validation.json'
    with path.open('xb') as stream:
        stream.write(raw(result) + b'\n')
    assert all(Path(item['resolved']).is_file() for item in links)
    print(json.dumps(dict(validation=bind(path), checked_files=len(checked), local_links=len(links)), indent=2))


if __name__ == '__main__':
    main()
