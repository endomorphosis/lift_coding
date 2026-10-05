"""Independent bounded source/AST review. Never import or execute target code.

Only this fresh sibling namespace receives the review receipt. Package, codec,
classifier, native, project, Git, and HTTP operations are absent from this audit.
"""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

W = Path('/home/barberb/lift_coding')
OUT = Path(__file__).resolve().parent
S2 = W / 'maintenance/ranker-convergence-publication-20261005-01'
S3 = W / 'maintenance/ranker-source-slices-publication-20261005-01'
R2 = W / 'maintenance/ranker-convergence-publication-root-20261005-01'
R3 = W / 'maintenance/ranker-source-slices-publication-root-20261005-01'
PARENT = 'd6b6e333f3b1bcfe9028a8ca5ac3be6b12256e8a'
OLD_PARENT = '8b7b8c896749e0ca3884114cedbed782a88f4702'
EXPECTED = {
    S3 / 'build_package.py': (27020, 'f1269ff1b2d3e808a8e4c44a292d098a08f5d97adf9477da96e565f107d7618e'),
    S3 / 'freeze_inputs.py': (3233, 'baa46e4be40f7ce3c1cad6cd4aebeb2bfae10312570041553c1dcd3eacfcda56'),
    S3 / 'review_package.py': (18549, '150ac0bbdd63663daace169c668dfe1b0d088d9394c03480e8816c47124c1e3c'),
    R3 / 'scan_final_upload_01.py': (4876, 'b170ec89299076fc88226d28fad891923a33bd7e2fc2ba6facf620e07b123c95'),
    R3 / 'review_hf_readback_01.py': (8935, '231f61b3bc3bc2dfcc1cce54d48bed560e6f7270ae04e461e151cccdf0c1e9f8'),
    R3 / 'prepare_hf_plan_02.py': (10632, 'd4762b7d1d30036caf83965709c7b54d61da781766c5f71669ed2194d7c66e82'),
}
BASELINES = {
    S2 / 'build_package.py': (26997, 'f5ac610e20fa7dab88b8f3de94ee588d47e557cc9209fd4aef8eb13bc8425782'),
    S2 / 'freeze_inputs.py': (3227, '6402eaa0a5d91f93c71f95599a256b06caf2076a991267dffbfb5fd962c8002e'),
    S2 / 'review_package.py': (18537, '313924a164782439d7f7e91a4ea51580e822c19ad221684949427daf4dbb2b70'),
    R2 / 'scan_final_upload_01.py': (4872, '9a688f074ac89a1fee08fd05c71ac287b5bd9c0be330e0b4256277df8812ee8b'),
    R2 / 'review_hf_readback_01.py': (8845, 'b15ed0dfc5a6c4411a0a94c7bcb4b5df4c16e00dee38e6a01454af63cb621b9c'),
}
HF = W / 'maintenance/terminal-ir-publication-20261004-01/huggingface'
HELPERS = {
    HF / 'successor-source-model-package-03/build_package.py': '8c8eab266a053115cdf0ea11a8aea5323611c2ab049ec1541383831618e385ce',
    HF / 'build_evidence_archive_02.py': 'f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036',
    HF / 'classify_and_prepare_public_archive_07.py': 'dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8',
    W / 'maintenance/ranker-curvature-publication-source-plan-20261005-01/build_package.py': '4e14c08fc6d680e5fcbf755f649284f750353b73b42dd08b926398f4c43c9a93',
}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path):
    need(path.is_absolute() and path.resolve(strict=True) == path, 'canonical source required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and first.st_size <= 2 * 1024**2, 'bounded regular source required')
        parts, total = [], 0
        while block := os.read(fd, 65536):
            total += len(block)
            need(total <= 2 * 1024**2, 'source grew beyond cap')
            parts.append(block)
        raw = b''.join(parts)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda row: tuple(getattr(row, key) for key in keys)
        need(signature(first) == signature(os.fstat(fd)) == signature(path.lstat()) and len(raw) == first.st_size, 'source changed while read')
    finally:
        os.close(fd)
    return raw


def descriptor(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def pinned(path, expected):
    raw = read(path)
    row = descriptor(path, raw)
    need((row['bytes'], row['sha256']) == expected, 'independent source pin differs')
    tree = ast.parse(raw, filename=str(path))
    return raw, row, sum(1 for _ in ast.walk(tree))


def replace(raw, old, new):
    need(old in raw, 'declared source adaptation absent')
    return raw.replace(old, new)


def package_adaptation(raw, name):
    raw = replace(raw, b'ranker-convergence-', b'ranker-source-slices-')
    if name != 'freeze_inputs.py':
        raw = replace(raw, b'ranker-real-convergence-', b'ranker-source-semantics-')
    if name == 'build_package.py':
        raw = replace(raw, b'externally sealed convergence increment', b'externally sealed source-slice increment')
        raw = replace(raw, b'new convergence final seal', b'new source-slices final seal')
        raw = replace(raw, OLD_PARENT.encode(), PARENT.encode())
        raw = replace(raw, b'prior curvature bundle', b'prior convergence bundle')
    return raw


def scanner_adaptation(raw):
    raw = replace(raw, OLD_PARENT.encode(), PARENT.encode())
    raw = replace(raw, b'convergence-final-upload-scan-', b'source-slices-final-upload-scan-')
    return replace(raw, b'ranker-convergence-exact-final-upload-scan@1', b'ranker-source-slices-exact-final-upload-scan@1')


def readback_adaptation(raw):
    raw = replace(raw, OLD_PARENT.encode(), PARENT.encode())
    raw = replace(raw, b'ranker-convergence-readback/1', b'ranker-source-slices-readback/1')
    raw = replace(raw, b'227 + args.expected_files - 2', b'276 + args.expected_files - 2')
    raw = replace(raw, b'== 225', b'== 274')
    raw = replace(raw, b'== 227', b'== 276')
    raw = replace(raw,
        b'        chunks = []\n        while block := os.read(fd, 1024**2):\n            chunks.append(block)',
        b'        chunks = []; total = 0\n        while block := os.read(fd, 1024**2):\n            total += len(block)\n            assert total <= 32 * 1024**2\n            chunks.append(block)')
    return replace(raw, b'ranker-convergence-public-HF-readback-join@1', b'ranker-source-slices-public-HF-readback-join@1')


def check_preparer(raw):
    tree = ast.parse(raw)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module)
    need(imports == {'argparse', 'hashlib', 'json', 'os', 'pathlib', 'stat'}, 'HF preparer imports changed')
    # These checks bind the human source review to its exact final pin. They do
    # not import, evaluate, or execute the target AST or generated card text.
    for token in (
        b"need(__debug__,'optimized Python refused')",
        b"('baseline','manifest','package-review','qualification')",
        b"total+=len(block);need(total<=32*1024**2,'input grew beyond bound')",
        b"return json.loads(raw),binding",
        b"if binding['path'] in HELD:need(HELD[binding['path']]==binding",
        b"baseline,baseline_pin=load_bound(R/'HF-parent-preflight-01.json',a.expected_baseline_sha256)",
        b"manifest,manifest_pin=load_bound(P/'package/manifest.json',a.expected_manifest_sha256)",
        b"review,review_pin=load_bound(S/'package-review-01.json',a.expected_package_review_sha256)",
        b"qual,qual_pin=load_bound(Q/'qualified-review-01.json',a.expected_qualification_sha256)",
        b"need(review['package_closure']==closed_pin",
        b"card=read_bound(R/'prior-HF-README-01.md',prior_by_name['prior-HF-README-01.md'])[0]+b",
        b"need(status_pin==prior_by_name['prior-HF-publication-status-01.json']",
        b"'qualified_review':qual_pin",
        b"'decoded_package_review':review_pin",
        b"baseline['complete_regular_file_count']==276",
        b"baseline['prior_immutable_files']==274",
        b"baseline['namespace_unoccupied'] is True",
        b"qual['native_lean_calls']==3",
        b"qual['qualified_positive_native_lean_checks']==2",
        b"qual['inconclusive_native_lean_checks_retained']==1",
        b"qual['qualified_theorem_queries']==21",
        b"qual['metadata_payloads']==4440",
        b"qual['metadata_family_count']==32",
        b"qual['additive_metadata_payloads']==23",
        b"qual['all32_governing_RPI_exits']=='OPEN'",
        b"qual['full_task_satisfaction']=='unknown'",
        b"qual['official_benchmark_score'] is None",
        b"0<len(files)<=100 and len({x['remote'] for x in files})==len(files)",
        b"need(all(x['remote'] not in baseline['files'] for x in files if x['remote'].startswith(NS+'/'))",
        b"need(all(pin(path)==binding for path,binding in list(HELD.items()))",
        b"('prepare_hf_plan_02.py','scan_final_upload_01.py','review_hf_readback_01.py','HF-parent-preflight-01.json')",
        b"supplied original mathematical gradient only",
        b"_objective's gradient computation is still open",
        b"Contracts are not runtime-enforced",
        b"full\\nPython source equivalence, math.fsum/binary64/libm refinement",
        b"the full training loop, general codebase autoencoder convergence and Terminal",
    ):
        need(token in raw, 'reviewed preparer gate/scope text differs')
    save_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'save']
    need(len(save_nodes) == 3, 'only three fresh R3 card/status/plan writes are admitted')


def main():
    need(OUT == W / 'maintenance/ranker-source-slices-publication-source-review-20261005-01', 'fresh sibling review namespace required')
    own_raw = read(Path(__file__).resolve())
    own = descriptor(Path(__file__).resolve(), own_raw)
    sources, baseline_rows, raw_sources, raw_baselines = [], [], {}, {}
    for path, expected in EXPECTED.items():
        raw, row, nodes = pinned(path, expected)
        raw_sources[path] = raw
        sources.append({**row, 'ast_nodes': nodes, 'target_execution': False})
    for path, expected in BASELINES.items():
        raw, row, nodes = pinned(path, expected)
        raw_baselines[path] = raw
        baseline_rows.append({**row, 'ast_nodes': nodes})
    for name in ('build_package.py', 'freeze_inputs.py', 'review_package.py'):
        need(package_adaptation(raw_baselines[S2 / name], name) == raw_sources[S3 / name], 'undeclared package-tool source change')
    need(scanner_adaptation(raw_baselines[R2 / 'scan_final_upload_01.py']) == raw_sources[R3 / 'scan_final_upload_01.py'], 'undeclared scanner source change')
    need(readback_adaptation(raw_baselines[R2 / 'review_hf_readback_01.py']) == raw_sources[R3 / 'review_hf_readback_01.py'], 'undeclared readback source change')
    check_preparer(raw_sources[R3 / 'prepare_hf_plan_02.py'])
    helper_rows = []
    for path, expected in HELPERS.items():
        raw = read(path)
        row = descriptor(path, raw)
        need(row['sha256'] == expected, 'inherited helper source pin changed')
        helper_rows.append(row)
    for path, raw in {**raw_sources, **raw_baselines}.items():
        need(read(path) == raw, 'reviewed source changed during audit')
    for row in helper_rows:
        need(descriptor(Path(row['path']), read(Path(row['path']))) == row, 'helper source changed during audit')
    need(read(Path(__file__).resolve()) == own_raw, 'review producer changed')
    result = {
        'schema': 'ranker-source-slices-publication-independent-source-review@1',
        'status': 'passed_source_only',
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reviewer': own,
        'reviewed_sources': sources,
        'pinned_baseline_sources': baseline_rows,
        'pinned_inherited_helpers_rehashed_without_import': helper_rows,
        'five_inherited_tools_exact_declared_adaptations_only': True,
        'new_HF_plan_preparer02_independent_source_review': True,
        'findings': [],
        'source_assessments': [
            'Fixed independent plan/builder/closure/manifest pins and same-read parsed-buffer hash checks remain unchanged.',
            'Full owned Q4 regular census equals seal leaves plus seal self-file; complete P5 source-plan census and explicit public tools/policy remain selected.',
            'Failed attempts, full compiled objects/chunks, and zero-byte locks retain the inherited census rules.',
            'Raw 256MiB, per-file and per-shard raw sum 14MiB, complete decoded tar 16MiB, charged aggregate decode 1GiB, 180s, 10000 members, depth6, 64 shards, zstd T1/3 stay unchanged.',
            'Native 20s CPU/wall, 262144 input, 65536 output, and 16MiB workspace gates stay unchanged.',
            'Pinned complete-container/complete-PEM/cached-credential classifier and same-first-decoded member readback retain the inherited implementation; no duplicate budget exemption was introduced.',
            'Only new owned S3 package paths receive package writes; no old Q2/Q3/S2 evidence mutation was introduced.',
            'R3 readback pins plan/invocation, joins scan/closed/observed/verified/local bytes, uses bounded 4MiB HTTP JSON reads, and rejects pagination.',
            'R3 requires parent d6b6e333f3b1bcfe9028a8ca5ac3be6b12256e8a, complete 276-file prior tree, exact mutable two, all 274 immutable identity/LFS joins, and final tree size 276+selected-2.',
            'The new HF preparer binds baseline/manifest/decoded-review/qualification to externally pinned same-read buffers, binds the closed package descriptor to its review, and holds all parsed/selected/prior-body descriptors through final rechecks.',
            'The HF preparer appends prior README bytes, preserves prior status fields, selects only new immutable namespace files plus the exact mutable two, and requires actual 3 attempts/2 accepted/1 inconclusive/21 queries/4440 payloads/32 families/23 additions.',
            'The new card/status limit source claims to typed dot/update arithmetic and exactReal projection with supplied mathematical gradient; host-parser correctness, full Python, _objective, binary64/libm, feature preparation, full loop, AE, and Terminal Bench remain open.',
            'Operational/full-task authority flags stay false/unknown, no score is claimed, and all32 RPI exits stay OPEN.',
        ],
        'limitations': [
            'Source/AST inspection only. None of the reviewed sources or inherited helpers was imported or executed.',
            'No package/classifier/codec/native/model/test/Git/HTTP/remote job ran in this audit.',
            'Final S3 required-facts/plan/selection/package and actual R3 scan/publication/readback receipts are outside this source-only review.',
            'Preserved preparer01 is an unexecuted superseded draft; the reviewed preparation entry point is preparer02 only.',
        ],
        'target_imports_or_executions': 0,
        'project_jobs': 0,
        'remote_reads': 0,
        'remote_mutations': 0,
        'proof_authority': False,
        'execution_authority': False,
        'completion_authority': False,
        'planner_activation': False,
        'full_task_satisfaction': 'unknown',
        'all32_governing_RPI_exits': 'OPEN',
    }
    target = OUT / 'review-receipt.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': result['status'], 'receipt': descriptor(target, read(target)), 'reviewer': own}))


if __name__ == '__main__':
    main()
