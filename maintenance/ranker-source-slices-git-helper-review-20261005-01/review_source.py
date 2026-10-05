"""Independent source/AST review of the fresh source-slice Git helpers.

Only this new sibling review namespace is written. Targets and classifier
helpers are never imported or executed. No Git or remote command is run.
"""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

W = Path('/home/barberb/lift_coding')
R = W / 'maintenance/ranker-source-slices-private-git-preparation-20261005-01'
OLD = W / 'maintenance/ranker-convergence-private-git-preparation-20261005-02'
OUT = Path(__file__).resolve().parent
EXPECTED = {
    R / 'prepare_compact_selection_01.py': (13796, 'b9378beff7404d8253ec86403c052ae05a9fcaea70dc44e508e34fdaad242c27'),
    R / 'stage_verified_increment_01.py': (14349, '96bdce1359839d8ddced226037691d9b5ac41839fd2918d6ab230ce0275c8421'),
    R / 'publish_git_increment_01.py': (15374, '409c835d2ee50ce987c0c24ff98ecd0d6200a0df44a0164971c7da79d5fdfd7b'),
    R / 'publication-policy.json': (2885, '3628d49b2281a7cfe6cfc3c70e7ccaa24b1154ba0326a7d93304fc93cdcaa09c'),
}
BASELINES = {
    OLD / 'prepare_compact_selection_01.py': (10251, '586c4793281ab06317927fef07b4c1c10287d9da7fff36e2b1a9187bbd041e8f'),
    OLD / 'stage_verified_increment_01.py': (12619, '2b9d7cc540e7905004392ce2edb74b0921a5924827805e1e44b91c786b21ba8f'),
    OLD / 'publish_git_increment_01.py': (15194, '84f16b2b734319c5547e9468e617894a9f895ba187f8bb64d58366b220e93bd1'),
}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path):
    need(path.is_absolute() and path.resolve(strict=True) == path, 'canonical input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and first.st_size <= 2 * 1024**2, 'bounded regular source required')
        chunks, size = [], 0
        while block := os.read(fd, 65536):
            size += len(block)
            need(size <= 2 * 1024**2, 'review input grew beyond cap')
            chunks.append(block)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda row: tuple(getattr(row, key) for key in keys)
        need(signature(first) == signature(os.fstat(fd)) == signature(path.lstat()) and size == first.st_size, 'review input changed while read')
        return b''.join(chunks)
    finally:
        os.close(fd)


def pin(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def functions(tree):
    return {node.name: ast.dump(node, include_attributes=False) for node in tree.body if isinstance(node, ast.FunctionDef)}


def contains(raw, tokens):
    for token in tokens:
        need(token in raw, 'reviewed gate token absent: ' + token.decode())


def main():
    need(OUT == W / 'maintenance/ranker-source-slices-git-helper-review-20261005-01', 'authorized new review namespace required')
    own_raw = read(Path(__file__).resolve())
    own = pin(Path(__file__).resolve(), own_raw)
    held, rows, trees = {}, [], {}
    for path, expected in {**EXPECTED, **BASELINES}.items():
        raw = read(path)
        row = pin(path, raw)
        need((row['bytes'], row['sha256']) == expected, 'independent source pin differs')
        held[path] = raw
        if path.suffix == '.py':
            tree = ast.parse(raw, filename=str(path))
            trees[path] = tree
            row['ast_nodes'] = sum(1 for _ in ast.walk(tree))
        else:
            json.loads(raw)
        rows.append(row)
    inherited = {}
    for name, wanted in {
        'prepare_compact_selection_01.py': ('git', 'guards', 'need', 'pin', 'read', 'wire'),
        'stage_verified_increment_01.py': ('git', 'need'),
        'publish_git_increment_01.py': ('ancestor', 'fetch_main', 'git', 'guards', 'need', 'pin', 'timestamp', 'tree_links', 'verify_commit', 'write_new'),
    }.items():
        old_functions, new_functions = functions(trees[OLD / name]), functions(trees[R / name])
        need(all(old_functions[key] == new_functions[key] for key in wanted), 'inherited guard/publication utility changed')
        inherited[name] = list(wanted)
    selector = held[R / 'prepare_compact_selection_01.py']
    stage = held[R / 'stage_verified_increment_01.py']
    publisher = held[R / 'publish_git_increment_01.py']
    contains(selector, (
        b"PARENT = None", b"CLOSURE_SHA = None", b"EXPECTED_SELECTION_COUNT = None", b"EXPECTED_SELECTION_BYTES = None",
        b"21a459ac9bfcf399132943708e32445c93cb66fa0fab8fb2878beeb01dcf8b65",
        b"39c403afd19b5972a28281813c23fdd13eddea1c32fa63747b4dd3258b07e550",
        b"return json.loads(raw), row",
        b"seal, seal_pin = document(seal_path, SEAL_SHA)",
        b"review, review_pin = document(review_path, REVIEW_SHA)",
        b"closure, closure_pin = document(S3 / 'closed-inputs.json', CLOSURE_SHA)",
        b"selection, selection_pin = document(S3 / 'final-selection.json', closure['final_selection']['sha256'])",
        b"plan, plan_pin = document(S3 / 'plan.json', closure['plan']['sha256'])",
        b"need(selection_pin == closure['final_selection']",
        b"need(plan_pin == closure['plan']",
        b"seal['review'] == review_pin",
        b"== 299", b"== 86451989",
        b"('environment-manifest.json', 'metadata-inputs.json')",
        b"path.suffix not in ('.py', '.lean', '.md', '.json', '.xml')",
        b"path.suffix == '.json' and row['bytes'] > 1024**2",
        b"('source-plan.json', 'source-bindings.json', 'ir-interface.json')",
        b"'explicitly_authorized_next_phase_original_with_frozen_capture'",
        b"'source_only_uncompiled_unqualified_objective_IR_plan'",
        b"'authorized source-only planning original/captured byte join required'",
        b"need(pin(Path(row['path'])) == {key: row[key] for key in ('path', 'bytes', 'sha256')}",
        b"'final parsed document pins changed'",
        b"need(len(links) == 9", b"need(before == after",
    ))
    contains(stage, (
        b"BASE_SHA = None", b"raw = read_bounded(path)",
        b"candidate_raw = read_bounded(ROOT / 'compact-candidate-selection-01.json')",
        b"need(size <= 16*1024**2, 'source grew beyond read bound')",
        b"hashlib.sha256(candidate_raw).hexdigest() == args.expected_candidate_selection_sha256",
        b"hashlib.sha256(base_raw).hexdigest() == BASE_SHA",
        b"before == base['original_guard_after']",
        b"'maintenance/ranker-source-slices-publication-root-20261005-01'",
        b"type(public.get('prior_immutable_files_preserved')) is int and public['prior_immutable_files_preserved'] == 274",
        b"part.casefold() in {'.cache','cache','caches','download-cache','compiled-cache','datasets-cache'}",
        b"part.casefold().endswith('-cache')", b"part.casefold().startswith('cache-')",
        b"row['bytes'] <= 1024**2", b"not any('private' in part or part == '__pycache__'",
        b"all(gate[key] in list(sources.values()) for key in ('publication_closed', 'public_readback', 'ledger'))",
        b"need(budget.decoded == 0 and budget.members == 0",
        b"'only exact complete new additions may be staged'",
        b"links == base['parent_gitlinks']", b"'staged blob differs from scanned source'",
        b"validate_HF_gate(api,gate)",
    ))
    contains(publisher, (
        b"STAGE_SHA = None", b"need(size <= 16 * 1024**2, 'source grew beyond read bound')",
        b"hashlib.sha256(stage_raw).hexdigest() == STAGE_SHA",
        b"before == stage['original_guard_after']",
        b"hf_public['prior_immutable_files_preserved'] == 274",
        b"'maintenance/ranker-source-slices-publication-root-20261005-01'",
        b"'durable_before_any_push': True, 'push_calls': 0",
        b"'remote parent advanced before push; retain observed commit and renew a fresh reviewed checkout'",
        b"['git', '-C', str(REPO), 'push', 'origin', 'HEAD:refs/heads/main']",
        b"'normal push failed or remote parent advanced; retained attempt requires a fresh reviewed checkout'",
        b"verify_commit(remote, stage, check_parent=False)",
        b"committed_rows == remote_rows", b"'force_push_calls': 0",
        b"'sealed_Q4_P5_S3_mutations': 0", b"'proof_authority': False",
    ))
    # Commands are inspected as AST data; none is called by this reviewer.
    for tree in trees.values():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'git' and node.args:
                if isinstance(node.args[0], ast.Constant):
                    need(node.args[0].value != 'rebase', 'rebase command forbidden')
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                need(node.value not in ('--force', '-f', '--force-with-lease'), 'force flag forbidden')
    policy = json.loads(held[R / 'publication-policy.json'])
    need(policy['schema'] == 'ranker-source-slices-private-Git-publication-policy@1' and policy['status'] == 'source_preparation_not_executed', 'source-only policy role required')
    need(policy['expected_prior_HF_commit'] == 'd6b6e333f3b1bcfe9028a8ca5ac3be6b12256e8a' and policy['expected_prior_immutable_HF_files'] == 274, 'current HF parent policy required')
    need(policy['Q4_sealed_regular_files'] == 299 and policy['Q4_sealed_regular_bytes'] == 86451989 and policy['native_attempts_retained'] == 3 and policy['native_accepted_modules'] == 2 and policy['native_accepted_theorem_queries'] == 21, 'actual narrow qualification policy required')
    need(policy['P6_original_planning_documents'] == ['source-plan.json', 'source-bindings.json', 'ir-interface.json'], 'only three P6 originals authorized')
    need(all(policy[key] is False for key in ('force_push_allowed', 'rebase_allowed', 'host_parser_correctness_theorem_proved', 'python_ranker_source_equivalence_proved', 'binary64_error_bound_proved', 'full_objective_semantics_proved', 'full_preparation_semantics_proved', 'full_training_semantics_proved', 'whole_IR_semantic_preservation_proved', 'global_autoencoder_convergence_proved', 'proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')), 'scope/authority overclaim refused')
    need(policy['full_task_satisfaction'] == 'unknown' and policy['official_benchmark_score'] is None, 'task frontier required')
    for path, raw in held.items():
        need(read(path) == raw, 'source changed during independent review')
    need(read(Path(__file__).resolve()) == own_raw, 'review producer changed')
    result = {
        'schema': 'ranker-source-slices-independent-Git-helper-source-review@1',
        'status': 'passed_source_only',
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reviewer': own,
        'reviewed_sources_and_policy': [row for row in rows if Path(row['path']).is_relative_to(R)],
        'pinned_prior_sources': [row for row in rows if Path(row['path']).is_relative_to(OLD)],
        'unchanged_inherited_function_ASTs': inherited,
        'findings': [],
        'resolved_findings': [
            'Selector parsed seal/review/closure/selection/plan bytes now produce and validate the same-buffer descriptors, with final document and selected/captured/original rechecks.',
            'Stager candidate/helper reads now use bounded O_NOFOLLOW regular-file reads and same-read signatures; publisher enforces the running 16MiB read cap.',
            'Safe extra receipt paths now explicitly veto cache directories and preserve the private/raw-log/binary exclusions.',
        ],
        'source_assessments': [
            'No stale prior parent/source SHA hardcoding remains; parent/closure/full-census and candidate/base/final-stage pins are supplied explicitly.',
            'The selector imported by stager provides read/guards/omitted_reason without using its PARENT=None main-only context.',
            'Compact sources use .py/.lean/.md/.json/.xml and JSON<=1MiB; environment manifests, metadata input bodies, raw native metadata bodies, objects/chunks/databases/archive/log/lock suffixes remain excluded from Git and retained in the HF denominator.',
            'Exactly three authorized original P6 planning JSON documents require byte-identical frozen captured copies, are tagged uncompiled/unqualified source-only plans, and do not add the original extractor.py.',
            'Both mutation helpers require the actual pinned HF closed/public readback/ledger commit join with 274 prior immutable files preserved and authority false.',
            'Original root/child HEAD/index and original Git links remain guarded; staging and commit verify the complete exact new regular blobs and preserve all nine fresh-parent Git links.',
            'Only fresh private checkout/index/refs are mutation targets; no forced push or rebase command exists. An advanced remote parent stops the attempt for a fresh reviewed checkout.',
            'Observed commit receipts and directory entries are fsynced before any normal push; all new blobs are compared with refreshed remote main before a publication closure.',
            'Explicit need gates survive optimized Python; pinned archive/classifier sources were previously inspected and have no assertion-dependent gates.',
            'Source/Python/binary64/_objective/full-loop/AE/task authority claims remain conditional/open/false as recorded by the publication policy.',
        ],
        'limitations': [
            'Source and AST inspection only. No target/helper import or execution occurred.',
            'No Git command, staging, classifier, codec, native, model, test, or remote job ran in this audit.',
            'No private checkout or actual HF/final candidate/base/stage/publication gate was admitted by this source receipt; those require separate actual pinned evidence before execution.',
        ],
        'target_imports_or_executions': 0,
        'Git_commands': 0,
        'classifier_codec_native_model_jobs': 0,
        'remote_reads_or_mutations': 0,
        'proof_authority': False,
        'execution_authority': False,
        'completion_authority': False,
        'planner_activation': False,
        'full_task_satisfaction': 'unknown',
    }
    target = OUT / 'review-receipt.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': result['status'], 'receipt': pin(target, read(target)), 'reviewer': own}))


if __name__ == '__main__':
    main()
