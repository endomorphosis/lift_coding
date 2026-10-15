"""Curate source changes and public measurements without exporting fixture state."""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

EVIDENCE = Path(__file__).resolve().parent
CHECKOUT = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def save(name: str, value: object) -> None:
    destination = EVIDENCE / name
    if destination.exists():
        raise FileExistsError(destination)
    destination.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


before: dict[str, bytes | None] = {}
provenance: dict[str, str] = {}
root_baseline = json.loads((EVIDENCE / 'baseline.json').read_text())
assert root_baseline['checkout'] == str(CHECKOUT)
for row in root_baseline['files']:
    relative = row['path']
    raw = (EVIDENCE / 'baseline' / relative).read_bytes() if row['exists'] else None
    assert (digest(raw) if raw is not None else None) == row['sha256']
    before[relative] = raw
    provenance[relative] = 'baseline.json'
plumbing = json.loads((EVIDENCE / 'plumbing-baseline.json').read_text())
for relative, row in plumbing['files'].items():
    raw = Path(row['baseline']).read_bytes()
    assert digest(raw) == row['sha256'] and len(raw) == row['bytes']
    assert relative not in before
    before[relative] = raw
    provenance[relative] = 'plumbing-baseline.json'
for relative in plumbing['absent_files']:
    before[relative] = None
    provenance[relative] = 'plumbing-baseline.json'
for row in json.loads((EVIDENCE / 'codec-absent-baseline.json').read_text())['files']:
    assert row['exists'] is False
    before[row['path']] = None
    provenance[row['path']] = 'codec-absent-baseline.json'
public_test = 'benchmarks/agent_supervisor/container_coding/test_terminal_compact_intent_experiment.py'
before[public_test] = None
provenance[public_test] = 'agent /root/advisory_artifact_review confirmed new file'

patch_parts = []
changes = []
scratch = EVIDENCE / 'patch-baseline-check'
scratch.mkdir(exist_ok=False)
for relative, old in sorted(before.items()):
    path = CHECKOUT / relative
    new = path.read_bytes() if path.exists() else None
    if new == old:
        continue
    assert new is not None, 'This focused implementation does not delete source files'
    if relative.endswith('.py'):
        ast.parse(new, filename=relative)
    if old is not None:
        target = scratch / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(old)
    patch_parts.append(''.join(difflib.unified_diff(
        old.decode().splitlines(keepends=True) if old is not None else [],
        new.decode().splitlines(keepends=True),
        fromfile='a/' + relative if old is not None else '/dev/null',
        tofile='b/' + relative)))
    changes.append({'path': relative, 'before_sha256': digest(old) if old is not None else None,
                    'after_sha256': digest(new), 'after_bytes': len(new),
                    'baseline_provenance': provenance[relative]})
patch = ''.join(patch_parts).encode()
assert len(changes) == 16, len(changes)
patch_path = EVIDENCE / 'changes.patch'
assert not patch_path.exists()
patch_path.write_bytes(patch)
check = subprocess.run(['git', 'apply', '--check', '--whitespace=error', str(patch_path)],
                       cwd=scratch, capture_output=True, text=True)
assert check.returncode == 0, check.stderr
save('source-manifest.json', {'schema': 'terminal-compact-context-source-manifest@1',
    'checkout': str(CHECKOUT), 'checkout_base_head': '03eb84149cac3de7e16a99148466e4ad9327cb79',
    'baseline_is_saved_overlay_not_git_head': True, 'files': changes,
    'patch': {'path': str(patch_path), 'bytes': len(patch), 'sha256': digest(patch),
              'apply_check_against_saved_baseline_passed': True},
    'python_source_syntax_parsed': True,
    'fixture_private_state_exported': False, 'committed': False, 'pushed': False,
    'new_runtime_archive_built': False, 'new_runtime_deployed': False})

test_files = ['codec-validation-03.xml', 'plumbing-validation-02.xml', 'comparison-validation-04.xml',
              'worker-validation-01.xml', 'added-controls-validation-02.xml', 'public-fixture-tests-01/tests.xml']
case_ids = set()
exact_case_ids = set()
suites = []
for relative in test_files:
    path = EVIDENCE / relative
    raw = path.read_bytes()
    cases = list(ET.fromstring(raw).iter('testcase'))
    exact_identities = {(case.get('classname', ''), case.get('name', '')) for case in cases}
    identities = {(classname.removeprefix('test.') if classname.startswith('test.api.') else classname, name)
                  for classname, name in exact_identities}
    failures = sum(len(case.findall('failure')) for case in cases)
    errors = sum(len(case.findall('error')) for case in cases)
    skips = sum(len(case.findall('skipped')) for case in cases)
    assert failures == errors == skips == 0
    suites.append({'path': str(path), 'sha256': digest(raw), 'testcase_records': len(cases),
                   'unique_test_identities': len(identities),
                   'overlap_with_earlier_suites': len(identities & case_ids),
                   'failures': failures, 'errors': errors, 'skips': skips})
    case_ids |= identities
    exact_case_ids |= exact_identities
save('validation.json', {'schema': 'terminal-compact-context-validation@1',
    'suites': suites, 'unique_passing_test_identities': len(case_ids),
    'exact_classname_name_identities': len(exact_case_ids),
    'passing_testcase_records': sum(row['testcase_records'] for row in suites),
    'deduplication_key': ['classname with optional test. collection prefix removed for api.*', 'name'],
    'failures': 0, 'errors': 0, 'skips': 0,
    'scope': 'Focused codec, route, admission, replay, accounting and public-fixture checks; not the full repository suite',
    'superseded_attempts_preserved': True,
    'post_final_projection_validation': 'added-controls-validation-02 includes four actual expanded/compact router and historical replay cases plus fifteen tamper/fallback cases',
    'comparison_review_fix': 'Planning-expanded/coding-compact calls retain all usage in the compact coding arm',
    'seals_are_fresh_test_databases': True, 'real_provider_calls': 0})

measurement_path = EVIDENCE / 'measurement-attempt-02/measurement.json'
measurement = json.loads(measurement_path.read_text())
pins = measurement['provenance']['producer_pins_after']
pin_matches = {key: digest(Path(row['path']).read_bytes()) == row['sha256'] for key, row in pins.items()}
assert all(pin_matches.values())
comparison = measurement['comparisons']['full_public_block_including_verbatim_instruction']
save('token-reduction-summary.json', {'schema': 'terminal-compact-context-measurement-summary@1',
    'measurement_path': str(measurement_path), 'measurement_sha256': digest(measurement_path.read_bytes()),
    'same_checked_task_context': measurement['canonical_roundtrip'],
    'full_public_appendix': comparison, 'populations': measurement['populations'],
    'tokenizer_scope': measurement['tokenizer']['scope'],
    'producer_pins_match_final_sources': pin_matches,
    'provider_calls': 0, 'actual_full_coding_prompt_measured': False,
    'provider_native_cumulative_usage_measured': False, 'causal_token_advantage_established': False,
    'limitations': measurement['limitations'], 'fixture_state_exported': False})

plan = {
 'schema': 'terminal-metadata-token-reduction-plan@1',
 'objective': 'Reduce total provider tokens per independently verified Terminal-Bench success while preserving source-grounded task requirements, proof scope and native admission.',
 'status': 'Compact task-IntentIR transport implemented and locally measured; bounded metadata dispatch and live evaluation remain proposed.',
 'flow': ['literal public prompt', 'source-spanned IntentIR requirements',
          'join against current repository AST/symbols/contracts and indexed observations',
          'independently checked symbolic plan and bounded proof obligations',
          'local checked operators or unresolved residual work',
          'bounded task capsule plus verified expansion handles',
          'lossless compact wire projection', 'model candidate',
          'native validation/publication plus independent task verifier'],
 'database_roles': [
  {'component': 'DuckDB', 'role': 'Local indexed catalog, task/context joins and cache lookups',
   'existing_sources': ['runtime/supervisor_meta_index.py', 'context/database_context.py'],
   'new_dispatch_integration': 'proposed'},
  {'component': 'Quack', 'role': 'Typed owner access to closed state commands and transactional coordination',
   'existing_sources': ['task_sources/quack_state_client.py', 'task_sources/typed_state_owner.py'],
   'unrestricted_model_sql_required': False},
  {'component': 'DuckLake', 'role': 'Persistent observational metadata, learning-catalog and publication projections',
   'existing_sources': ['runtime/supervisor_meta_index.py'],
   'proof_or_task_completion_authority': False}],
 'canonical_records_to_retain_outside_prompt': ['source bytes and exact tree/file/symbol versions',
    'ASTs and source selectors', 'knowledge graph edges and dependency/impact closure',
    'vector embeddings and retrieval provenance', 'declared contracts and open obligations',
    'formal projections with exact translator and logic-family versions',
    'checked proof receipts, assumptions, scope, toolchain/kernel identity and invalidation edges',
    'codebase-IR training checkpoints and empirical evaluation records'],
 'stages': [
  {'order': 1, 'status': 'implemented', 'change': 'Compact task-IntentIR requirements independently of semantic capsule transport',
   'sources': ['runtime/compact_intent_requirements.py', 'runtime/router_public_instruction.py',
               'runtime/router_implementation_runner.py'],
   'checks': ['literal instruction preserved', 'exact canonical decode equals independently replayed native context',
              'source spans and hashes/CID unchanged', 'decoding guidance and tables included in byte-benefit gate',
              'expanded default and explicit full-indexed contract requirement',
              'recorded transport retained through every control boundary without mixing experiment groups'],
   'evidence': 'token-reduction-summary.json'},
  {'order': 2, 'status': 'proposed', 'change': 'Route required semantic/world/retrieval evidence through bounded database manifests',
   'sources': ['todo_daemon/implementation_daemon.py::_semantic_implementation_references',
               'todo_daemon/implementation_daemon.py::_code_retrieval_implementation_references',
               'context/database_context.py::DatabaseContextManifest',
               'context/database_context.py::LLMContextFrontier',
               'context/context_compiler.py::ContentAddressedContextStore'],
   'packet_contents': ['admitted task and requirement/dependency/prohibition closure',
                       'exact relevant source/edit spans and impacted symbols',
                       'unresolved questions and open obligations',
                       'latest distinct failure', 'owner-selected exact validation commands',
                       'verified fact/proof-scope references and explicit omitted frontier'],
   'checks': ['budgets apply after all wrappers and decoding guidance',
              'no mandatory acceptance facts silently dropped',
              'each expansion question and handle bound to source/tree and admissible task scope',
              'tampered, stale, deleted and inaccessible references fail before use',
              'absent metadata remains an explicit unresolved obligation rather than a fabricated fact'],
   'measurements': ['final complete prompt bytes/local tokenizer counts',
                    'retrieved row/byte counts and expansion calls', 'cold hydration and warm query cost']},
  {'order': 3, 'status': 'proposed', 'change': 'Avoid residual model calls through reusable checked local operators and bounded proof-cache queries',
   'sources': ['proof/proof_scope_index.py', 'proof/doctor_proof_cache.py',
               'planning/intent_symbolic_planning.py', 'semantic_state/context_pack_selector.py'],
   'checks': ['proof states distinguish proposed, translated, kernel checked, unknown and invalidated',
              'proof hits bind premises and semantic scope, not just vector similarity',
              'supported effects and impact closure checked independently before native publication',
              'unsupported or unproved effects keep the existing residual model route'],
   'measurements': ['eligible proof hits and invalidations', 'actual avoided model calls',
                    'provider tokens including all residual attempts', 'independent task success']},
  {'order': 4, 'status': 'proposed', 'change': 'Train codebase-IR encoders to nominate relevant facts/operators and compact evidence, with explicit semantic qualification',
   'checks': ['preserve canonical AST/source/contracts as ground truth',
              'split held-out functions/tasks/repository revisions before training',
              'track reconstruction and retrieval error separately from task/proof results',
              'neural latent codes and decreasing loss grant no translation/proof authority',
              'formal family projections require typed translations and pinned Lean/kernel checks where supported',
              'source-to-model equivalence requires independently proved supported semantics and explicit unsupported residuals',
              'any convergence theorem names its model, objective, assumptions and certified optimization steps; empirical loss decrease alone is insufficient'],
   'measurements': ['cold training cost', 'held-out retrieval recall and reconstruction',
                    'supported semantic projection/proof coverage', 'total tokens and verified task success']},
  {'order': 5, 'status': 'proposed', 'change': 'Build a fresh pinned runtime and evaluate compact and bounded-retrieval treatments',
   'controls': ['runtime source archive and exact CLI/code-mode-host digests',
                'same public contract and planning/Doctor policy', 'same code source, learning checkpoint and retrieval policy',
                'same model, reasoning, time budgets and verifier policy'],
   'matrix': {'intent_requirements_transport': ['expanded', 'compact'],
              'semantic_transport': ['native', 'identifiers']},
   'checks': ['offline exact historical replay before any live inference',
              'retain failed setups and incomplete usage as unknown, never zero',
              'distinguish exact same-context comparisons from fresh-ID or independently planned trials',
              'include planning, coding, tool-heavy iterations and failed/retried attempts',
              'cached input is a subset of input and is never added twice',
              'retain native completion separately from official verifier success'],
   'primary_measurement': 'All-attempt provider input plus output tokens per official verifier success, only with complete usage and known rewards',
   'secondary_measurements': ['call count, input/cache/output distributions', 'successful full-task rate',
                             'cold/warm wall time and training/proof cost', 'repeat variability and context-audit coverage']}],
 'cache_reuse_key': ['repository/tree/file/symbol identities', 'task CID/revision and intent watermark',
    'objective and policy revisions', 'interface/schema/toolchain/environment identities',
    'query/retrieval configuration identity', 'artifact/manifest digests',
    'proof premises/translation/solver/kernel identities and declared scope'],
 'invalidate_on': ['changed/deleted/renamed source or impact closure', 'changed task/policy/query',
                   'changed assumptions, proof translator or toolchain', 'superseded publication or evidence watermark'],
 'claims_not_established': ['provider-native total token reduction', 'full task behavioral satisfaction from compact serialization',
                            'whole-program or arbitrary source-to-model equivalence', 'neural model convergence theorem'],
 'next_implementation': 'Bounded required evidence dispatch, after offline task-coverage and source/impact checks, through the existing manifest/frontier interfaces.'
}
save('metadata-retrieval-plan.json', plan)
save('implementation.json', {'schema': 'terminal-compact-context-implementation@1',
 'checkout': str(CHECKOUT), 'changed_source_files': len(changes),
 'change': 'Opt-in lossless compact task IntentIR appendix with native validation, end-to-end controls, replay and isolated benchmark accounting',
 'default_intent_requirements_transport': 'expanded', 'opt_in_cli': '--intent-requirements-transport compact',
 'compact_requires': ['full indexed arm', 'explicit native-admitted public requirement contract', 'coding phase'],
 'authority': {'proof': False, 'execution': False, 'completion': False},
 'source_manifest': 'source-manifest.json', 'reviewable_patch': 'changes.patch',
 'validation': 'validation.json', 'unique_passing_test_identities': len(case_ids),
 'local_measured_token_reduction_fraction': comparison['LOCAL_saved_token_fraction'],
 'measurement_summary': 'token-reduction-summary.json', 'next_plan': 'metadata-retrieval-plan.json',
 'docs': str(CHECKOUT / 'benchmarks/agent_supervisor/container_coding/SUPERVISION_INTEGRATION.md'),
 'actual_provider_calls_in_this_work': 0, 'live_compact_trial_run': False,
 'new_runtime_archive_built_or_deployed': False, 'committed_or_pushed': False,
 'scope': 'Edits restricted to the isolated checkout and this evidence directory; existing original repository changes preserved.',
 'limitations': measurement['limitations']})
print(json.dumps({'changed_files': len(changes), 'patch_apply_check': True,
                  'unique_passing_test_identities': len(case_ids), 'measurement_producer_pins_match': all(pin_matches.values())}))
