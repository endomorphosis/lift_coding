#!/usr/bin/env python3
"""Independent read-only review of the exact wording publication scope.

No fetching, staging, source/model execution or publication occurs. Only this
review receipt is written. Missing final scopes, audits, bundles or metrics fail
closed; retry with a fresh output name to preserve failed review evidence.
"""
import argparse
from difflib import SequenceMatcher
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile

A = Path(__file__).resolve().parent.parent
W = A.parents[1]
P = W/'external/ipfs_datasets'
RUN = P/'workspace/test-logs/decoder-normative-wording-r2-20261006'
PUBLIC = P/'docs/implementation/reports/evidence/decoder-normative-wording-20261006'
PREFIX = A.relative_to(W).as_posix()+'/'
NEW_IMPLEMENTATION = {
    'ipfs_datasets_py/logic/formalization/autoencoder/'+name+'.py' for name in (
        'normative_wording_training_sources','prospective_normative_development',
        'prospective_wording_source_inputs','normative_wording_modality_auxiliary')
} | {'scripts/ops/autoencoder/'+name+'.py' for name in (
    'prepare_normative_wording_sources','benchmark_normative_wording_training',
    'evaluate_normative_wording_development')
} | {'tests/unit/logic/formalization/autoencoder/test_'+name+'.py' for name in (
    'normative_wording_training_sources','prospective_normative_development',
    'prospective_wording_source_inputs','normative_wording_modality_auxiliary',
    'normative_wording_training_runner','normative_wording_development')}
GUIDE = 'docs/autoencoders/normative_wording_training.md'
PRIOR_GUIDE = 'docs/autoencoders/paraphrase_modality_diagnostics.md'
PUBLIC_FILES = {'docs/implementation/reports/evidence/decoder-normative-wording-20261006/'+name
    for name in ('manifest.json','results.json')}
UPSTREAM = ('39f25777d557df1c51b8f98ed0dcd084c35d4d6d',
    '37c2d63f0bf9490e5b019788afcafbc3b806d8c7')
TOP_FILES = {'README.md','development-spec.md','publish_integration.py','publisher_review_tests.py',
    'build_public_evidence.py','initial-git-and-protected-checkpoint.json',
    'evidence-bundle-receipt.json','review-evidence.tar.gz'}
DEVELOPMENT_FILES = {'seal-manifest.json','new-training-source-exclusion.json','tests.xml','audit.py',
    'recipe.json','source-rows.json','codec.json','development-corpus-receipt.json',
    'tests-output.txt','tests.json','original-validation-bank-used.json','prior-source-inventories.json',
    'generate.py','independent-audit.json','development-references.json','reconstruction-transitions.json'}
REVIEW_FILES = {'training_adapter_updated_observer_tests.xml','check_preparation_driver.py',
    'training_adapter_review_tests.xml','postfit_audit_math_smoke.json','native_adapter_independent_checks.json',
    'audit_preflight_training_readiness.py','native_adapter_tests_final.xml','audit_native_preparation.py',
    'audit_completed_fits.py','preparation_driver_independent_checks.json','postfit_observer_integration_review.json',
    'audit_saved_wording_outputs.py','postfit_observer_integration.md','preparation_readiness.json',
    'training_adapter_review.json','check_preflight_readiness.py','native_adapter_review.json',
    'preflight_audit.json','check_preparation_readiness.py','check_native_adapter.py',
    'check_evaluation_readiness.py','native_preparation_audit.json','native_adapter_tests_initial.xml',
    'fit_audit.json','development_results_audit.json','evaluation_readiness.json',
    'training-readiness.json','training_readiness.json','publication_metrics_review.json',
    'final_pure_test_inventory.json','paired_modality_fixes.json',
    'training_sources_tests_final.json','training_sources_tests_final.txt','training_sources_tests_final.xml',
    'prospective_wording_results.md'}
PIPELINE_FILES = {'publisher-synthetic-validation.json','seal_evaluation.py','evaluation-sealer-readiness.json',
    'review_publication.py','publication-scope-independent-review.json'}
W_ALLOWED = {PREFIX+name for name in TOP_FILES} | {
    PREFIX+'development/'+name for name in DEVELOPMENT_FILES} | {
    PREFIX+'review/'+name for name in REVIEW_FILES} | {
    PREFIX+'pipeline/'+name for name in PIPELINE_FILES}
AUTHORITY = ('qualified','admitted','proof_authority','formalized','roundtrip_ok',
    'checkpoint_promoted','convergence_proven','fresh_holdout','lake_executed')
ARMS = ('normative-wording-zero','normative-wording-ce')
ROLES = ('selected','last-attempt')
ALLOWED_EXTENSIONS = {'.py','.md','.json','.jsonl','.xml','.log','.txt'}


def strict_pairs(pairs):
    value = {}
    for key,item in pairs:
        if key in value:
            raise ValueError('duplicate JSON key: '+key)
        value[key] = item
    return value


def read(path):
    return json.loads(Path(path).read_bytes(),object_pairs_hook=strict_pairs,
        parse_constant=lambda value:(_ for _ in ()).throw(ValueError('nonfinite JSON: '+value)))


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda:stream.read(1048576),b''):
            result.update(data)
    return result.hexdigest()


def git(repo,*args):
    return subprocess.check_output(['git','-c','core.hooksPath=/dev/null','-C',str(repo),*args],
        stderr=subprocess.PIPE)


class Reviewer:
    def __init__(self):
        self.checks = 0
        self.artifacts = {}
    def check(self,value,message):
        if not value:
            raise ValueError(message)
        self.checks += 1
    def bind(self,path,wanted=None,bytes=None):
        path = Path(path)
        self.check(path.is_file() and not path.is_symlink(),'regular publication artifact required: '+str(path))
        observed = sha(path)
        self.check(wanted is None or observed == wanted,'publication artifact changed: '+str(path))
        self.check(bytes is None or path.stat().st_size == bytes,'publication byte count differs: '+str(path))
        resolved = str(path.resolve())
        self.check(resolved not in self.artifacts or self.artifacts[resolved] == observed,
            'artifact changed during review: '+str(path))
        self.artifacts[resolved] = observed
        return observed
    def read(self,path):
        self.bind(path)
        return read(path)
    def relative(self,value):
        self.check(type(value) is str and value and str(PurePosixPath(value)) == value and
            not PurePosixPath(value).is_absolute() and not any(part in ('.','..','.git')
                for part in PurePosixPath(value).parts),'closed relative publication path required')
        return value
    def reviewed(self,path):
        value = self.read(path)
        self.check(value.get('passed') is True and not value.get('findings'),'required audit failed: '+str(path))
        for artifact,item in value.get('artifacts',{}).items():
            self.bind(artifact,item if type(item) is str else item['sha256'],
                None if type(item) is str else item.get('bytes'))
        return value


def reject_weights(value,reviewer):
    if type(value) is dict:
        reviewer.check(not any(key in value for key in ('model_state','state_dict','optimizer_state_dict',
            'last_complete_attempt_state_dict')),'private tensor state embedded in publication JSON')
        for child in value.values():
            reject_weights(child,reviewer)
    elif type(value) is list:
        for child in value:
            reject_weights(child,reviewer)


def file_is_evidence(path,reviewer):
    path = PurePosixPath(path)
    reviewer.check(not path.name.endswith(('-state.json','.state.json')) and
        not set(path.parts).intersection({'model-assets','model_assets','snapshots','weight-cache','weights'}),
        'private weights/model assets selected for publication: '+str(path))
    reviewer.check(path.suffix in ALLOWED_EXTENSIONS,'unexpected evidence file type: '+str(path))


def review_prior_paragraph(scope,reviewer):
    if PRIOR_GUIDE not in scope['datasets']['files']:
        return
    original = git(P,'show',scope['datasets']['parent']+':'+PRIOR_GUIDE).decode()
    current = (P/PRIOR_GUIDE).read_text()
    old,new = original.strip().split('\n\n'),current.strip().split('\n\n')
    changes = [item for item in SequenceMatcher(a=old,b=new,autojunk=False).get_opcodes() if item[0] != 'equal']
    reviewer.check(len(changes) == 1 and changes[0][0] == 'insert' and
        changes[0][4]-changes[0][3] == 1,'prior diagnostic guide must retain all original paragraphs')
    paragraph = new[changes[0][3]]
    reviewer.check(len(paragraph) <= 2200 and '\n#' not in paragraph and not paragraph.startswith('#')
        and 'normative_wording_training.md' in paragraph,'one bounded followup paragraph/link required')


def review_scope(scope,reviewer):
    reviewer.check(scope.get('passed') is True and scope.get('reviewed') is True,'sealed intended publication scope required')
    reviewer.check('pipeline/publication-scope-independent-review.json' in scope['required_reviews'],
        'publisher must require this exact independent scope review')
    selected = set(scope['datasets']['files'])
    reviewer.check(NEW_IMPLEMENTATION|PUBLIC_FILES|{GUIDE} <= selected,
        'all13 implementation paths plus guide/public evidence required')
    reviewer.check(selected <= NEW_IMPLEMENTATION|PUBLIC_FILES|{GUIDE,PRIOR_GUIDE},
        'datasets scope exceeds closed implementation/document whitelist')
    reviewer.check(set(scope['workspace']['files']) <= W_ALLOWED,
        'workspace scope exceeds selected wording artifact whitelist')
    reviewer.check(PREFIX+'review-evidence.tar.gz' in scope['workspace']['files'], 'review archive must be in workspace scope')
    reviewer.check('external/ipfs_datasets' not in scope['workspace']['files'],
        'datasets gitlink must be supplied automatically after package publication')
    for commit in UPSTREAM:
        result = subprocess.run(['git','-C',str(P),'merge-base','--is-ancestor',commit,
            scope['datasets']['parent']],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        reviewer.check(result.returncode == 0,'publication parent would omit upstream contextual runtime: '+commit)
    for label,repository in (('datasets',P),('workspace',W)):
        parent = scope[label]['parent']
        reviewer.check(re.fullmatch('[0-9a-f]{40}',parent) is not None,'immutable publication parent required')
        for relative,item in scope[label]['files'].items():
            reviewer.relative(relative)
            file = repository/relative
            reviewer.check(file.resolve().is_relative_to(repository.resolve()),'publication path escapes repository')
            reviewer.bind(file,item['sha256'],item['bytes'])
            reviewer.check(item.get('mode','100644') in ('100644','100755'),'regular publication mode required')
            old = git(repository,'--literal-pathspecs','ls-tree','-z',parent,'--',relative)
            if old:
                head,_ = old.rstrip(b'\0').split(b'\t',1)
                mode,kind,oid = head.decode().split()
                reviewer.check(mode in ('100644','100755') and kind == 'blob','regular upstream preimage required')
                previous = hashlib.sha256(git(repository,'cat-file','blob',oid)).hexdigest()
            else:
                previous = None
            reviewer.check(item['parent_sha256'] == previous,'scope preimage differs from immutable parent: '+relative)
    review_prior_paragraph(scope,reviewer)


def required_members():
    prefix = RUN.relative_to(W).as_posix()+'/'
    values = {prefix+'preparation-r1/results/'+name for name in (
        'source-rows.json','training-references.json','clause-training-references.json',
        'training-corpus-receipt.json','prior-source-inventories.json','pre-native-source-seal.json',
        'production-384.json','production-768.json','development-production-384.json',
        'development-production-768.json','development-inputs-384.json','development-inputs-768.json')}
    for width in (384,768):
        for arm in ARMS:
            folder = prefix+f'training-{width}-r1/results/{arm}/'
            values |= {folder+'training.json',folder+'summary.json',folder+'parent-paraphrase-readout.json'}
            for role in ROLES:
                values.add(folder+role+'/paraphrase-modality-readout.json')
                stem = prefix+f'evaluation-r1/results/{width}-{arm}/{role}'
                values |= {stem+'-'+suffix+'.json' for suffix in (
                    'predictions','source-head-trace','source-head-score','source-head-formula-join','score')}
    values |= {prefix+'evaluation-r1/results/'+name for name in ('summary.json','predictions-complete.json')}
    failed = (RUN.parent/'decoder-normative-wording-20261006').relative_to(W).as_posix()+'/'
    values |= {failed+'preparation-seal-failure.json',failed+'seal_preparation.py'}
    return values


def review_archive(manifest,reviewer):
    archive = W/manifest['archive_path']
    reviewer.bind(archive,manifest['archive_sha256'],manifest['archive_bytes'])
    reviewer.check(archive.stat().st_size < 75000000,'bounded evidence archive required')
    declared = manifest['members']
    reviewer.check(manifest['member_count'] == len(declared) and required_members() <= set(declared),
        'archive omits new native features/traces/fit reports/readouts/failure evidence')
    reviewer.check(sum(row['bytes'] for row in declared.values()) < 300000000,'bounded uncompressed archive required')
    allowed_prefix = (PREFIX,RUN.relative_to(W).as_posix()+'/')
    allowed_single = {str((P/GUIDE).relative_to(W)),str((PUBLIC/'results.json').relative_to(W))}
    failed_prefix = (RUN.parent/'decoder-normative-wording-20261006').relative_to(W).as_posix()+'/'
    allowed_single |= {failed_prefix+'preparation-seal-failure.json',failed_prefix+'seal_preparation.py'}
    seen = set()
    with tarfile.open(archive,'r:gz') as stream:
        for item in stream:
            reviewer.relative(item.name)
            reviewer.check(item.isfile() and not item.issym() and not item.islnk() and item.name not in seen,
                'archive contains duplicate/link/nonregular member')
            reviewer.check(item.name in declared and (item.name.startswith(allowed_prefix) or
                item.name in allowed_single),'transitive historical tree or undeclared archive member')
            file_is_evidence(item.name,reviewer)
            reviewer.check(0 <= item.size < 50000000 and item.size == declared[item.name]['bytes'],
                'archive member byte bound differs')
            body = stream.extractfile(item).read()
            reviewer.check(hashlib.sha256(body).hexdigest() == declared[item.name]['sha256'],
                'archive member digest differs')
            reviewer.bind(W/item.name,declared[item.name]['sha256'],item.size)
            if item.name.endswith('.json'):
                reject_weights(json.loads(body,object_pairs_hook=strict_pairs),reviewer)
            seen.add(item.name)
    reviewer.check(seen == set(declared),'archive declaration and actual members differ')
    reviewer.check(all(manifest.get(name) is False for name in ('private_checkpoint_tensors_bundled',
        'model_assets_bundled','predecessor_source_trees_bundled')),
        'archive must explicitly exclude tensors/assets/historical trees')
    reviewer.check(manifest['first_preparation_seal_failure_preserved'] is True and
        manifest['first_preparation_launched'] is False,'initial seal failure must remain explicit')


def review_metrics(results,reviewer):
    reviewer.check(results.get('complete') is True and len(results['panels']) == 8,'complete public8-panel comparison required')
    reviewer.check(all(results.get(name) is False for name in AUTHORITY if name in results),
        'public results gained admission/convergence authority')
    reviewer.check(results['original_development_meanings_previously_exposed'] is True and
        results['composition64_prior_vector_comparison_complete'] is False,
        'prior DEV exposure and incomplete composition-vector scope must remain explicit')
    reviewer.check(results['encoder_context_tokens'] == results['decoder_output_limit_tokens'] == 512 and
        results['temperature'] == 0 and results['bridge_names'] == [] and
        results['legal_ir_evaluate_provers'] is False and results['metric_disk_cache'] is False and
        results['workers_per_width'] == 1,'fixed context/bridge/prover/cache/worker settings differ')
    for name in ('fit_audit','development_audit','native_preparation_audit'):
        reviewer.check(results[name]['passed'] is True and not results[name].get('findings'),
            'public nested audit failed: '+name)
    summary = reviewer.read(RUN/'evaluation-r1/results/summary.json')
    actual = {(row['dimension'],row['arm'],row['role']):row for row in summary['panels']}
    reviewer.check(len(actual) == 8,'unique saved endpoint panel identities required')
    for row in results['panels']:
        saved = actual[row['dimension'],row['arm'],row['role']]
        reviewer.check(all(row[key] == saved[key] for key in saved),'public metric/prediction reference differs from saved observer')
        reviewer.check(row['sample_count'] == 60 and row['generation_seconds_per_span'] == row['generation_seconds']/60,
            'public timing denominator differs')
        reviewer.check(all(row['source_head_by_field'][field]['reference_rows'] == 60 and
            row['source_head_by_field'][field]['visited']+row['source_head_by_field'][field]['unvisited'] == 60
            for field in ('actor','action','modality','object')),'full60 source-head denominator required')
    document = (P/GUIDE).read_text()
    reviewer.check('Composition64' in document and 'not an untouched semantic holdout' in document and
        'Only the applicable successful `lake build <Lib>` grants Lean admission.' in document,
        'guide omits provenance or Lake-only admission limits')
    # The completed section must retain one row per selected width/arm. The
    # source-only numeric table is checked without running any source decoder.
    lines = [line for line in document.splitlines() if line.strip().startswith('|')]
    training = {width:{row['arm']:row for row in results['training'][str(width)]} for width in (384,768)}
    for width in (384,768):
        for arm in ARMS:
            panel = actual[width,arm,'selected']
            candidates = [line for line in lines if re.search(r'\b'+str(width)+r'(?:D)?\b',line)
                and (arm in line or ('zero' if arm.endswith('zero') else '0.05') in line)]
            reviewer.check(len(candidates) == 1,'one explicit selected metric row required: '+str((width,arm)))
            line = candidates[0]
            cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
            reviewer.check(len(cells) == 8,'closed eight-column completed metric table required')
            head = panel['source_head_by_field']['modality']
            run = training[width][arm]
            readout = run['full180_postfit_readouts']['selected']
            reviewer.bind(readout['path'],readout['sha256'])
            train_score = read(readout['path'])
            expected = [str(width)+'D','zero' if arm.endswith('zero') else '0.05 auxiliary',
                str(train_score['groups']['all']['correct'])+'/180',str(panel['ordered_exact'])+'/60',
                str(head['source_correct'])+'/60',format(panel['token_cross_entropy'],'.10f'),
                format(run['training_call_elapsed_seconds'],'.3f'),
                format(panel['generation_seconds']/60*1000,'.4f')]
            reviewer.check(cells == expected,'completed metric table cells differ: '+str((width,arm)))
            reviewer.check(line in (A/'README.md').read_text(),'workspace and package metric tables differ')


def review(args):
    reviewer = Reviewer()
    findings = []
    try:
        scope = reviewer.read(args.scope)
        review_scope(scope,reviewer)
        for name in ('review/fit_audit.json','review/development_results_audit.json','review/native_preparation_audit.json'):
            reviewer.reviewed(A/name)
        for name in scope['required_reviews']:
            if name != 'pipeline/publication-scope-independent-review.json':
                reviewer.reviewed(A/reviewer.relative(name))
        results = reviewer.read(PUBLIC/'results.json')
        manifest = reviewer.read(PUBLIC/'manifest.json')
        review_metrics(results,reviewer)
        review_archive(manifest,reviewer)
        for path,wanted in reviewer.artifacts.items():
            reviewer.check(sha(path) == wanted,'reviewed artifact changed before completion: '+path)
    except Exception as error:
        findings.append(dict(error_type=type(error).__name__,message=str(error)))
    result = dict(schema='normative-wording-publication-independent-review/v1',passed=not findings,
        findings=findings,checks=reviewer.checks,artifacts=reviewer.artifacts,
        exact13_implementation_whitelist=True,upstream_contextual_runtime_commits=list(UPSTREAM),
        archive_weights_assets_and_historical_trees_excluded=not findings,
        scope_only_read=True,git_read_only=True,fetch_performed=False,push_performed=False,
        model_executed=False,source_owner_executed=False,checkpoint_promoted=False,
        qualified=False,admitted=False,lake_executed=False)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n')
    print(json.dumps({key:result[key] for key in ('passed','findings','checks')},sort_keys=True))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope',type=Path,default=A/'publication-scope.json')
    parser.add_argument('--output',type=Path,default=A/'pipeline/publication-scope-independent-review.json')
    args = parser.parse_args()
    raise SystemExit(0 if review(args)['passed'] else 1)


if __name__ == '__main__':
    main()
