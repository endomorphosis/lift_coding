"""Independent source/JSON-only audit; never import or execute the target helper."""
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import stat

WORKSPACE = Path('/home/barberb/lift_coding')
OUT = Path(__file__).resolve().parent
NEW = WORKSPACE / 'maintenance/ranker-convergence-publication-root-20261005-01/review_hf_readback_01.py'
OLD_ROOT = WORKSPACE / 'maintenance/ranker-curvature-publication-root-20261005-01'
OLD = OLD_ROOT / 'review_hf_readback_01.py'
PLAN = NEW.parent / 'hf-plan-01.json'
SCAN = NEW.parent / 'final-upload-scan-01.json'
INVOCATION = NEW.parent / 'hf-publication-invocation-01.json'
PARENT = '8b7b8c896749e0ca3884114cedbed782a88f4702'
PLAN_SHA = 'af77746e72284e0adaf75839ee03a797f5f6a260b25aac9bfc146644344d15a1'
MUTABLE = {'README.md', 'releases/20261004-terminal-codebase-ir-evidence-v1/publication-status.json'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    path = Path(path).absolute()
    require(path.resolve(strict=True) == path, 'aliased input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= 32 * 1024**2, 'input bound/type')
        chunks = []
        while block := os.read(fd, 1024**2):
            chunks.append(block)
        raw = b''.join(chunks)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        sig = lambda row: tuple(getattr(row, key) for key in keys)
        require(sig(before) == sig(os.fstat(fd)) == sig(path.lstat()), 'input changed during read')
        require(len(raw) == before.st_size, 'input byte mismatch')
        return raw
    finally:
        os.close(fd)


def pin(path, raw=None):
    raw = read(path) if raw is None else raw
    return {'path': str(Path(path).absolute()), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def expr(source):
    return ast.dump(ast.parse(source, mode='eval').body, include_attributes=False)


def main():
    held = {}
    def hold(path):
        raw = read(path)
        held[Path(path)] = raw
        return raw
    new_raw, old_raw = hold(NEW), hold(OLD)
    require(pin(NEW, new_raw)['sha256'] == 'b15ed0dfc5a6c4411a0a94c7bcb4b5df4c16e00dee38e6a01454af63cb621b9c', 'owner-pinned final source hash')
    new_text, old_text = new_raw.decode(), old_raw.decode()
    new_ast, old_ast = ast.parse(new_text), ast.parse(old_text)
    prior = json.loads(hold(OLD_ROOT / 'hf-public-readback-01.json'))
    require(prior['status'] == 'passed' and prior['commit'] == PARENT, 'prior accepted readback')
    require(prior['producer'] == pin(OLD, old_raw), 'prior producer binding')
    imports = []
    for node in ast.walk(new_ast):
        if isinstance(node, ast.Import):
            imports.extend(x.name for x in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
    require(sorted(imports) == sorted(['argparse', 'collections', 'datetime', 'hashlib', 'json', 'os', 'pathlib', 'stat', 'urllib.request']), 'target import surface')
    require(not any(isinstance(n, (ast.AsyncFunctionDef, ast.Await)) for n in ast.walk(new_ast)), 'unexpected asynchronous execution')
    calls = [ast.unparse(n.func) for n in ast.walk(new_ast) if isinstance(n, ast.Call)]
    require(not set(calls) & {'eval', 'exec', 'compile', '__import__', 'os.system', 'os.execv', 'os.spawnv'}, 'unexpected dynamic/process execution')
    assertions = {ast.dump(n.test, include_attributes=False) for n in ast.walk(new_ast) if isinstance(n, ast.Assert)}
    gates = [
        'path.resolve(strict=True) == path',
        'stat.S_ISREG(before.st_mode) and before.st_size <= 32 * 1024**2',
        'signature(before) == signature(os.fstat(fd)) == signature(path.lstat())',
        'len(raw) == before.st_size',
        'actual == expected',
        'len(COMMIT) == 40 and all(c in "0123456789abcdef" for c in COMMIT)',
        '0 < args.expected_files <= 100',
        'before_pins[0]["sha256"] == args.expected_plan_sha256',
        'before_pins[2]["sha256"] == args.expected_invocation_sha256',
        'plan["repo_id"] == REPO and plan["expected_parent_commit"] == PARENT',
        'scan["status"] == "passed" and scan["candidate_hits"] == 0',
        'scan["plan"] == before_pins[0]',
        'outer["status"] == "closed_phase" and outer["returncode"] == 0',
        'outer["input_pins_unchanged"] and outer["cleanup_errors"] == []',
        'closed["status"] == "PUBLISHED_AND_VERIFIED" and closed["remote_readback_verified"]',
        'closed["commit"] == observed["commit"] == verified["commit"] == COMMIT',
        'closed["parent"] == observed["parent"] == before["commit"] == PARENT',
        'closed["prior_immutable_remote_files_preserved"] == 225',
        'len(expected) == len(plan["files"]) == len(verified["files"]) == args.expected_files',
        'sum(row["bytes"] for row in expected.values()) == args.expected_bytes',
        'set(actual) == set(expected)',
        'pin(binding["path"]) == binding == row["expected"]',
        'row["remote"]["bytes"] == binding["bytes"]',
        'row["remote"]["lfs_sha256"] == binding["sha256"]',
        'row["verification_method"] == "committed_LFS_SHA256_and_size"',
        'row["verification_method"] == "downloaded_small_file_SHA256_and_size"',
        'main_info["sha"] == COMMIT',
        'not response.headers.get("Link")',
        'len(raw) <= 4 * 1024**2',
        'len(mutable) == 2 and len(before["files"]) == 227',
        'remote["size"] == row["bytes"] and remote["oid"] == row["blob_id"]',
        'remote.get("lfs", {}).get("oid") == row["lfs_sha256"]',
        'preserved == 225',
        'remote["size"] == binding["bytes"]',
        'remote["oid"] == actual[name]["remote"]["blob_id"]',
        'remote.get("lfs", {}).get("oid") == actual[name]["remote"]["lfs_sha256"]',
        'len(tree) == 227 + args.expected_files - 2',
        '[pin(path) for path in documents] == before_pins',
        'pin(binding["path"]) == binding',
        'final_main_info["sha"] == COMMIT',
    ]
    missing = [gate for gate in gates if expr(gate) not in assertions]
    require(not missing, 'missing source gates: ' + repr(missing))
    # These final direct joins are manually checked as statements as well as
    # checked here by AST-normalized assertion text after the owner strengthens
    # its source. They are never exercised by importing or executing that source.
    additional = [
        'closed["plan"] == before_pins[0]',
        'closed["files"] == args.expected_files and closed["selected_bytes"] == args.expected_bytes',
        'scan["selected_files"] == args.expected_files and scan["selected_bytes"] == args.expected_bytes',
        '[{"local": row["local"], "remote": row["remote"]} for row in scan["files"]] == plan["files"]',
        'mutable == set(expected) & set(before["files"]) == {"README.md", "releases/20261004-terminal-codebase-ir-evidence-v1/publication-status.json"}',
        'set(tree) == set(before["files"]) | set(expected)',
    ]
    missing = [gate for gate in additional if expr(gate) not in assertions]
    require(not missing, 'missing direct receipt/tree joins: ' + repr(missing))
    for literal in ['if not __debug__:', 'os.O_RDONLY | os.O_NOFOLLOW', 'path.open("xb")', 'response.read(4 * 1024**2 + 1)', 'timeout=30', '"/tree/" + COMMIT + "?recursive=true&expand=false"', '"raw_SDK_logs_read": False', '"remote_mutations": 0', '"model_training_calls": 0', '"prover_calls": 0', '"proof_authority": False', '"execution_authority": False', '"completion_authority": False']:
        require(literal in new_text, 'missing bounded/read-only source feature ' + literal)
    requests = [n for n in ast.walk(new_ast) if isinstance(n, ast.Call) and ast.unparse(n.func) == 'urllib.request.Request']
    require(len(requests) == 2 and all(len(n.args) == 1 and {k.arg for k in n.keywords} == {'headers'} for n in requests), 'network request GET-only/default no data')
    plan_raw = hold(PLAN)
    require(pin(PLAN, plan_raw)['sha256'] == PLAN_SHA, 'external frozen upload plan hash')
    plan = json.loads(plan_raw)
    require(plan['repo_id'] == 'Publicus/codebase-ir-proof-index' and plan['expected_parent_commit'] == PARENT, 'frozen repository/parent')
    files = plan['files']
    require(len(files) == 51 and len({x['remote'] for x in files}) == 51, 'exact unique upload population')
    require(sum(x['local']['bytes'] for x in files) == 27316939, 'exact upload byte population')
    scan = json.loads(hold(SCAN))
    require(scan['status'] == 'passed' and scan['candidate_hits'] == 0 and scan['plan'] == pin(PLAN, plan_raw), 'actual final scan joins frozen plan')
    require([{'remote': x['remote'], 'local': x['local']} for x in scan['files']] == files, 'actual scan complete exact selection')
    invocation_raw = hold(INVOCATION)
    invocation = json.loads(invocation_raw)
    require('--expected-plan-sha256' in invocation['argv'] and PLAN_SHA in invocation['argv'] and PARENT in invocation['argv'], 'actual invocation plan/parent args')
    preflight = json.loads(hold(NEW.parent / 'HF-parent-preflight-01.json'))
    require(preflight['status'] == 'passed' and preflight['parent_commit'] == PARENT and len(preflight['complete_remote_files']) == 227, 'prior full-tree census')
    require(set(preflight['complete_remote_files']) & {x['remote'] for x in files} == MUTABLE, 'actual two mutable overlap')
    for row in files:
        raw = hold(Path(row['local']['path']))
        require(pin(row['local']['path'], raw) == row['local'], 'current frozen local upload pin')
    require(all(read(path) == raw for path, raw in held.items()), 'source/JSON/local inputs changed across review')
    diff = ''.join(difflib.unified_diff(old_text.splitlines(True), new_text.splitlines(True), fromfile=str(OLD), tofile=str(NEW)))
    report = {
        'schema': 'ranker-convergence-public-HF-readback-independent-source-review@1',
        'status': 'passed_source_only_review',
        'outstanding_issues': [],
        'review_source': pin(Path(__file__).resolve()),
        'reviewed_source': pin(NEW, new_raw),
        'prior_accepted_source': pin(OLD, old_raw),
        'prior_accepted_readback': pin(OLD_ROOT / 'hf-public-readback-01.json'),
        'source_diff_sha256': hashlib.sha256(diff.encode()).hexdigest(),
        'source_diff': diff,
        'required_ast_assertion_gates': gates + additional,
        'input_pins_before_after_unchanged': [pin(path, raw) for path, raw in held.items()],
        'frozen_plan': pin(PLAN, plan_raw),
        'frozen_publication_invocation': pin(INVOCATION, invocation_raw),
        'expectations': {'parent_commit': PARENT, 'uploaded_regular_files': 51, 'uploaded_bytes': 27316939, 'prior_regular_files': 227, 'prior_immutable_files': 225, 'committed_regular_files': 276, 'mutable_paths': sorted(MUTABLE), 'actual_new_commit': 'not assumed; actual durable OID supplied by caller'},
        'findings': ['Prior accepted receipt binds the prior reviewed source bytes.', 'CLI-bound plan/invocation and same-body pinned JSON loads prevent cross-plan receipt substitution.', 'Exact scan and publication receipt plan/count/bytes joins gate the selected population.', 'Whole committed tree equals prior names union selected names; only the two explicit shared paths are mutable.', 'All selected local file pins are checked before and after GET-only public tree readback; prior immutable blob/LFS OIDs and sizes are preserved.', 'Public main is checked before and after fixed-commit recursive-tree readback; pagination is rejected.', 'No SDK logs, credential cache, project imports, codecs, models, subprocesses, native jobs, or remote mutations occur in the target helper.'],
        'scope': {'source_only': True, 'target_helper_execution': False, 'target_helper_import': False, 'public_network_readback_execution': False, 'SDK_logs_read': False, 'native_jobs': 0, 'codec_jobs': 0, 'model_jobs': 0, 'remote_mutations': 0, 'protected_input_writes': 0, 'proof_authority': False, 'execution_authority': False, 'completion_authority': False},
    }
    destination = OUT / 'review-receipt.json'
    with destination.open('xb') as stream:
        stream.write((json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': report['status'], 'reviewed_source': report['reviewed_source'], 'receipt': pin(destination)}))


if __name__ == '__main__':
    main()
