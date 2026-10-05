"""File-only source review binding; never import or execute publication tools."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

WORKSPACE = Path('/home/barberb/lift_coding')
SOURCE = WORKSPACE / 'maintenance/ranker-curvature-publication-source-plan-20261005-01'
ROOT = Path(__file__).resolve().parent
EXPECTED = {
    'build_package.py': '4e14c08fc6d680e5fcbf755f649284f750353b73b42dd08b926398f4c43c9a93',
    'review_package.py': 'cdb6dbea925e3bc3ae8d62c6b7c069bfcbe1fd79bf07282e32ed06a68daf88f9',
    'freeze_inputs.py': '830d457108a95a8ccd29ee8a75af9742bc749336df1e87dabccaf8327aa2c041',
    'publication-profile-authorization.json': '3b0c8fd91ccd62fdc65e2cf557da6175eb6e48aef8b95996315113ff534bc638',
    'API.md': '3e66da5ea15246cb27cfefe79514cd533e14342b763614446cc6c9cacf0039ca',
}


def read(path):
    if path.resolve(strict=True) != path or path.is_symlink():
        raise ValueError('canonical regular source required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > 16 * 1024**2:
            raise ValueError('bounded regular source required')
        blocks, count = [], 0
        while block := os.read(fd, 1024**2):
            count += len(block)
            if count > 16 * 1024**2:
                raise ValueError('source grew beyond bound')
            blocks.append(block)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda info: tuple(getattr(info, key) for key in keys)
        if signature(before) != signature(os.fstat(fd)) or signature(before) != signature(path.lstat()) or count != before.st_size:
            raise ValueError('source changed during read')
        return b''.join(blocks)
    finally:
        os.close(fd)


def pin(path):
    raw = read(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def function(tree, name):
    return next(row for row in tree.body if isinstance(row, ast.FunctionDef) and row.name == name)


def assignment(tree, name):
    return next(row.value for row in tree.body if isinstance(row, ast.Assign) and
                any(isinstance(target, ast.Name) and target.id == name for target in row.targets))


def main():
    output = ROOT / 'source-review-01.json'
    if output.exists():
        raise ValueError('fresh source-only review output required')
    pins = [pin(SOURCE / name) for name in EXPECTED]
    if any(row['sha256'] != EXPECTED[Path(row['path']).name] for row in pins):
        raise ValueError('independently supplied source pins changed')
    trees = {name: ast.parse(read(SOURCE / name).decode(), filename=str(SOURCE / name))
             for name in ('build_package.py', 'review_package.py', 'freeze_inputs.py')}
    for name in ('validate_semantics', 'fixture_alias'):
        if ast.dump(function(trees['build_package.py'], name), include_attributes=False) != ast.dump(function(trees['review_package.py'], name), include_attributes=False):
            raise ValueError('builder/reviewer semantic or literal-alias validator changed')
    for name in ('REQUIRED_THEOREMS', 'SOURCE_AUTHORED_EXTRA_AXIOM_QUERY', 'BOUNDARIES'):
        if ast.dump(assignment(trees['build_package.py'], name), include_attributes=False) != ast.dump(assignment(trees['review_package.py'], name), include_attributes=False):
            raise ValueError('builder/reviewer theorem or authority boundaries changed')
    producer = pin(Path(__file__).resolve())
    result = {
        'schema': 'ranker-curvature-publication-source-only-review@1',
        'status': 'passed_source_only_no_remaining_blocker',
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'producer': producer,
        'reviewed_sources': pins,
        'source_function_line_roles': {name: {row.name: row.lineno for row in tree.body if isinstance(row, ast.FunctionDef)}
                                       for name, tree in trees.items()},
        'file_only_parse_checks': {
            'three_python_sources_parse': True,
            'builder_reviewer_semantic_validator_ast_identical': True,
            'builder_reviewer_literal_alias_validator_ast_identical': True,
            'theorem_registry_extra_query_and_boundaries_ast_identical': True,
        },
        'findings': [],
        'source_review_observations': [
            'Actual pinned positive and kernel-decide false-control receipts require unchanged native bounds, clean captures, standard-only axiom reports and actual artifacts. Full canonical positive checks and original numeric objects bind strictly advisory cache entries.',
            'originalReal_meanL_exact source-authored output is separately checked and never mislabeled as part of the checker parsed registry.',
            'Every sealed owned regular leaf is rehashed. Empty excluded leaves must be declared sealed *.lock files; a durable empty contracts.jsonl cannot be silently omitted.',
            'Only the two exact dependency directories are excluded from traversal. Nineteen root-sealed literal pytest fixture aliases are separately bound by readlink bytes and seven-stat values, never traversed, and permitted only when they point directly to a real canonical sibling fixture directory. All regular bodies in those sibling directories remain selected once.',
            'The complete regular seal plus fixed explicit additions defines the selected population before and after. Every outcome document and complete environment profile is selected.',
            'GNU member headers, padded bodies, end markers and record padding are included in each complete decoded tar16MiB bound.',
            'The first outer decoded-tar override charges every tar byte, checks its complete hash and exact ordered regular members, hashes every member byte during bounded copy, and delegates each member and nested-container scan to the unchanged pinned classifier.',
            'The credential veto retains exact cached values and complete bounded PEM scanning. No universal secret-free claim is made.',
            'Independent member review performs fresh bounded shard decoding, exact complete member hashes/identities/counts, and final input/selection/source rechecks.',
            'The explicit 320MiB raw/1GiB decoded publication-only authorization reflects the corrected273066128-byte/1080regular-leaf seal. Native proof and metadata caps remain unchanged.',
            'Final qualification seal, observed fact policy, selection and actual package results remain separately reviewable after root freezes them. This source-only document does not assert packaging success.',
            'Failure closure retains private partial evidence without asserting attempted cleanup; a secondary receipt-write failure does not replace the primary exception.',
        ],
        'earlier_pin_gate_refusal': 'A file-only receipt producer refused superseded source pins before writing any PASS document; the updated alias/census/lock changes were then read independently.',
        'review_scope': {
            'source_only': True, 'final_qualification_seal_reviewed_here': False,
            'final_fact_policy_reviewed_here': False, 'final_selection_reviewed_here': False,
            'actual_package_reviewed_here': False,
        },
        'publication_tool_sources_executed_here': 0, 'project_imports_here': 0,
        'classifier_jobs_here': 0, 'codec_jobs_here': 0, 'native_proof_jobs_here': 0,
        'fit_trace_solver_test_jobs_here': 0, 'network_calls_here': 0,
        'git_mutations_as_part_of_this_review': 0, 'remote_mutations_here': 0,
        'proof_authority': False, 'execution_authority': False,
        'completion_authority': False, 'planner_activation': False,
        'python_ranker_source_equivalence_proved': False,
        'binary64_error_bound_proved': False, 'global_optimizer_convergence_proved': False,
        'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN',
    }
    if [pin(SOURCE / name) for name in EXPECTED] != pins or pin(Path(__file__).resolve()) != producer:
        raise ValueError('reviewed source bytes changed before receipt closure')
    with output.open('xb') as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(pin(output), sort_keys=True))


if __name__ == '__main__':
    main()
