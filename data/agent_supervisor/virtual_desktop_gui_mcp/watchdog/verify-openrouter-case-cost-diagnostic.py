"""Read-only validation of a rejected performance experiment; no GUI authority."""
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[4]
SWISS = ROOT / 'swissknife'
ARCHIVE = Path(__file__).resolve().parent / 'smoke-receipts/openrouter-case-cost-diagnostic'

# R23 adds a public-input integrity guard without restoring the rejected
# optional OpenRouter storage reset. The original rollback bytes stay archived.
R23_CURRENT_SOURCE_SHA256 = {'scripts/build-family-mcp-spec.cjs': '08f61bbbb990dbf6d3bff679ca6f2fe74024cb835a2f96fb795e8ab89276d914', 'test/e2e/families/local-negative-mcp.spec.ts': 'e5fcf0733f0048656205101e1cd73b1240562b6a83f8d05779fb3fa651d5d960', 'scripts/vdg-openrouter-catalog-input.cjs': '320201344c87a2a17e575d83e67cde129e8d10b457453b1e87c60e7887f5b2ea', 'scripts/run-with-vdg-openrouter-catalog-input.mjs': '4865da3831aa75f523e33cee3ecad46490430505f0aad209798e664d59c0c4bb'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(actual, expected):
    assert math.isfinite(actual) and math.isclose(actual, expected, abs_tol=1e-7), (actual, expected)


receipt = json.loads((ARCHIVE / 'preflight.json').read_text())
report = json.loads((ARCHIVE / 'report.json').read_text())
assert receipt['recommended_action'] == 'rollback_optional_isolation'
assert receipt['canonical_candidate_retained'] is False
assert receipt['diagnostic_passed'] is True
for record in (receipt, report):
    assert record['work_complete'] is False and record['completion_authority'] is False
    assert record['owned_resources_closed'] is True
assert receipt['gui_acceptance'] is False
assert report['passed'] is True and report['diagnostic_only'] is True
assert report['canonical_capture'] is False
assert report['quiet_bounds'] == {'appear_ms': 800, 'quiet_ms': 400, 'timeout_ms': 15000}

artifacts = receipt['artifact_sha256']
assert len(artifacts) == 97 and 'report.json' in artifacts
pngs = {name for name in artifacts if name.endswith('.png')}
assert len(pngs) == 96
for name, digest in artifacts.items():
    assert Path(name).name == name and sha(ARCHIVE / name) == digest, name
    if name in pngs:
        with (ARCHIVE / name).open('rb') as handle:
            assert handle.read(8) == b'\x89PNG\r\n\x1a\n', name
for name, digest in receipt['candidate_source_sha256'].items():
    assert '..' not in Path(name).parts
    assert sha(ARCHIVE / 'candidate-source' / name) == digest, name

restored = {
    'scripts/build-family-mcp-spec.cjs': '62c326f7d76fa803ac249c70f615fb43d52d6a5217970239c80f26c1671a475a',
    'scripts/vdg-local-todo-isolation.test.mjs': '6a4f2bb2a92244ac605d170f57940927baa34e07347a1535d2051fae017fb0e8',
    'test/e2e/families/local-negative-mcp.spec.ts': '65624bd17b6a0ceb8e0c9493da2da2f6790ce688f6cbc22d433b1d1d225975d3',
}
for name, digest in restored.items():
    # Historical R15 rollback remains immutable, including the old Local bytes.
    assert sha(ARCHIVE / 'pre-or-source' / name) == digest, name
    if name not in R23_CURRENT_SOURCE_SHA256:
        assert sha(SWISS / name) == digest, name
# R23 legitimately strengthens the Local template with source-bound catalog
# checks. Exact reviewed pins and fresh unchanged Todo tests (including six-spec
# generation parity) distinguish that change from the rejected experiment.
for name, digest in R23_CURRENT_SOURCE_SHA256.items():
    assert sha(SWISS / name) == digest, name
smoke = receipt['reproduction_smoke']
assert sha(ROOT / smoke['path']) == smoke['sha256']

models = report['selected_model_ids']
assert len(models) == len(set(models)) == 6
precondition = report['control_local_precondition']
assert precondition['local_precondition_only'] is True
assert precondition['acquisition_or_acceptance_authority'] is False
assert precondition['seed_favorite_count'] == len(set(precondition['seed_favorite_ids'])) == 130
expected_pairs = {(model, action) for model in models for action in ('favorite', 'info', 'try', 'default')}
scenarios = report['scenarios']
assert [s['name'] for s in scenarios] == ['accumulated-control', 'isolated']
means, used_pngs = [], set()
for scenario in scenarios:
    isolated = scenario['name'] == 'isolated'
    rows = scenario['rows']
    assert len(rows) == 24 and {(r['model_id'], r['action']) for r in rows} == expected_pairs
    assert len({r['selector'] for r in rows}) == 24
    assert scenario['full_catalog_count'] == 468
    assert scenario['original_census_controls_verified'] == 1881
    assert scenario['provider_or_mcp_posts'] == 0
    favorites = 0 if isolated else 130
    assert scenario['initial_favorite_count'] == favorites
    for row in rows:
        assert row['trusted_click'] is True and row['genuine_action_verified'] is True
        assert row['after_png_precedes_reset'] is True
        assert row['exact_baseline_after_close'] is isolated
        assert row['model_count'] == 468 and row['favorites_before'] == favorites
        assert row['favorites_after'] == favorites + (row['action'] == 'favorite')
        favorites = 0 if isolated else row['favorites_after']
        assert '[data-openrouter-placement="catalog"]' in row['selector']
        for field in ('screenshot_before', 'screenshot_after'):
            assert row[field] in pngs and row[field] not in used_pngs
            used_pngs.add(row[field])
        for field in ('launch_ms', 'before_png_ms', 'click_ms', 'quiet_ms', 'after_png_ms', 'total_ms'):
            assert math.isfinite(row[field]) and row[field] > 0
    durations = [row['total_ms'] for row in rows]
    mean = statistics.mean(durations)
    close(mean, scenario['timing_ms']['mean'])
    close(sum(durations), scenario['timing_ms']['total'])
    means.append(mean)
assert used_pngs == pngs
assert report['actual_case_count'] == receipt['paired_cases'] == 48
assert receipt['png_count'] == 96 and receipt['provider_or_mcp_posts'] == 0
close(means[0], receipt['control_mean_ms'])
close(means[1], receipt['isolated_mean_ms'])
gain = means[0] - means[1]
close(gain, report['timing_gain']['mean_ms_saved'])
close(100 * gain / means[0], receipt['percent_faster'])
close(100 * gain / means[0], report['timing_gain']['percent_faster'])
comparison = receipt['comparison']
assert comparison['preserved_current_rows'] == 596
assert comparison['remaining_rows_both_transports'] == 2 * 2178 - 596
savings = gain / 1000 * comparison['remaining_rows_both_transports']
recapture = means[0] / 1000 * 596
close(savings, comparison['remaining_work_savings_if_diagnostic_delta_transfers_seconds'])
close(recapture, comparison['conservative_recapture_cost_using_control_diagnostic_rate_seconds'])
assert recapture > savings

subprocess.run(['node', '--test', '--test-concurrency=1', '--test-reporter=tap', 'scripts/vdg-local-todo-isolation.test.mjs'], cwd=SWISS, check=True)
print(json.dumps({'diagnostic_validated': True, 'actual_cases': 48, 'png_hashes_verified': 96,
                  'decision': 'rollback_optional_isolation', 'percent_faster': 100 * gain / means[0],
                  'historical_rollback_sources_verified': True,
                  'canonical_optional_isolation_removed': True,
                  'current_catalog_input_guard_sources_verified': True,
                  'current_generator_sha256': sha(SWISS / 'scripts/build-family-mcp-spec.cjs'),
                  'current_all_family_generation_parity_verified': True, 'gui_acceptance': False,
                  'work_complete': False, 'completion_authority': False}))
