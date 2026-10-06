"""Read-only readiness of the sealed postfit phase; no model or future labels."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path('/home/barberb/lift_coding')
DEFAULT_RUN=ROOT/'external/ipfs_datasets/workspace/test-logs/decoder-normative-wording-r2-20261006'
SEALER=ROOT/'artifacts/autoencoder-wording-fit-20261006/pipeline/seal_evaluation.py'
OBSERVER='scripts/ops/autoencoder/evaluate_normative_wording_development.py'
OBSERVER_SHA='6be7e03656087fa9b5607b7e82b4a0a1244ca920cad8a81d64510f140962cfc6'
SOWNER='ipfs_datasets_py/logic/formalization/autoencoder/generated_scalar_observation.py'
S_SHA='1f1d35f7fd90df0396f3222676f2ffd11f17e2b1b2c79c0a79f1600488eb08d8'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root',type=Path,default=DEFAULT_RUN)
    parser.add_argument('--fit-audit',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();r=args.run_root.resolve()
    checks=[];artifacts={}
    def check(value,label):
        if not value:raise ValueError(label)
        checks.append(label)
    def bind(path,wanted=None):
        path=Path(path).resolve();h=hashlib.sha256();size=0
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1048576),b''):
                h.update(block);size+=len(block)
        record=dict(sha256=h.hexdigest(),bytes=size)
        check(wanted is None or record['sha256']==wanted,'bound file '+str(path))
        check(str(path) not in artifacts or artifacts[str(path)]==record,'stable reviewed artifact '+str(path))
        artifacts[str(path)]=record
        return record
    def read(path,wanted=None):
        bind(path,wanted)
        return json.loads(Path(path).read_bytes())
    manifest=read(r/'evaluation-manifest.json');plan=read(r/'evaluation-plan.json',manifest['plan_sha256'])
    seal=read(r/'evaluation-seal-receipt.json')
    check(seal['complete'] is True and seal['all_four_fits_completed'] is True
        and seal['reference_json_parsed'] is False and seal['model_executed'] is False,
        'source-only completed evaluation sealer receipt')
    check(manifest['reference_json_parsed_by_sealer'] is False
        and plan['input_sha256']==manifest['inputs'],'exact no-reference-parse evaluation seal')
    for path,wanted in manifest['inputs'].items():bind(path,wanted)
    for relative,wanted in manifest['extensions'].items():bind(r/'experiment-source'/relative,wanted)
    for path,wanted in manifest['producer_pins'].items():bind(path,wanted)
    fit=read(args.fit_audit)
    check(fit.get('passed') is True and not fit.get('findings'),'independent actual four-fit/controls audit passed')
    preflight=[]
    for d in (384,768):
        for name in (f'preflight-{d}-r1-guardian-exit.json',f'preflight-{d}-r1/child-exit.json'):
            check(read(r/name)['returncode']==0,'actual successful bounded preflight '+str(d))
        check(read(r/f'preflight-{d}-r1/resources-final.json')['status']=='released',
            'owned preflight lease released '+str(d))
        terminal=manifest['training_terminals'][str(d)]
        check(read(terminal['child_exit'])['returncode']==0
            and read(terminal['resources_final'])['status']=='released','released successful actual width fit '+str(d))
        preflight.append(d)
        summary=read(manifest['training_summaries'][str(d)])
        check(summary['complete'] is True and summary['phase']=='training' and summary['dimension']==d
            and len(summary['runs'])==2,'both complete arms at width '+str(d))
        for item in summary['runs']:
            run=read(item['summary_path'],item['summary_sha256'])
            check(run['budget_completed'] is True and run['dimension']==d
                and all(run[k] is False for k in ('qualified','admitted','checkpoint_promoted')),
                'unchanged admission flags for actual fit')
            if run['arm']=='normative-wording-zero':
                check(run['zero_arm_archived_replay_verified'] is True,'actual exact M2 zero replay')
            for role in ('selected','last-attempt'):
                ref=run['states'][role];bind(ref['path'],ref['sha256'])
            check(len(run['postfit']['selected'])==len(run['postfit']['last-attempt'])==9,
                'all original nine control panels at both endpoints')
        path=manifest['source_inputs'][str(d)]
        cache=read(path,manifest['inputs'][str(Path(path).resolve())])
        check(cache['schema']=='prospective-wording-source-inputs/v1' and cache['complete'] is True
            and cache['dimension']==d and len(cache['rows'])==len(cache['clause_cache'])==60
            and all(set(row)=={'id','source_text','input'} for row in cache['rows']),
            'complete warm source-only sixty-row prospective input cache')
    bind(r/'experiment-source'/OBSERVER,OBSERVER_SHA)
    spec=importlib.util.spec_from_file_location('_readiness_postfit_recipe',r/'experiment-source'/OBSERVER)
    observer=importlib.util.module_from_spec(spec);spec.loader.exec_module(observer)
    observer.validate_plan(plan)
    check(plan['panel_count']==8 and plan['samples_per_panel']==60 and plan['vocabulary_size']==32
        and plan['source_head_trace_same_greedy_pass'] is True
        and plan['extra_source_head_evaluations']==0
        and plan['predictions_fsynced_before_reference_load'] is True,
        'eight60-row full32V same-pass traces and durable barrier')
    check(plan['context_tokens']==plan['output_tokens']==512 and plan['temperature']==0
        and plan['used_for_selection'] is False and plan['fresh_holdout'] is False,
        'fixed limits and honest observation/selection policy')
    scalar=[p for p,s in manifest['inputs'].items() if p.endswith('/'+SOWNER) and s==S_SHA]
    check(len(scalar)==1 and manifest['producer_pins'][scalar[0]]==S_SHA,
        'exact same-pass scalar owner source in numerical producer closure')
    check(str(Path(manifest['references']).resolve()) in manifest['inputs']
        and str(Path(manifest['development_receipt']).resolve()) in manifest['inputs'],
        'future reference artifacts hash-bound for eventual barrier entry')
    # Reference body files are not passed to read() in this readiness review.
    for path in (r/'run_guardian.py',r/'run_reserved.py',SEALER,
            ROOT/'artifacts/autoencoder-wording-fit-20261006/review/postfit_observer_integration_review.json',
            ROOT/'artifacts/autoencoder-wording-fit-20261006/review/postfit_audit_math_smoke.json'):
        bind(path)
    check(read(r/'preparation-r1-guardian-exit.json')['returncode']==0
        and read(r/'preparation-r1/child-exit.json')['returncode']==0
        and read(r/'preparation-r1/resources-final.json')['status']=='released',
        'actual native preparation succeeded and released')
    report=dict(schema='normative-wording-independent-phase-readiness/v1',passed=True,findings=[],
        phase='evaluation',dimension=None,run_root=str(r),artifacts=artifacts,
        checks=len(checks),check_labels=checks,created_utc=datetime.now(timezone.utc).isoformat(),
        actual_fit_audit_path=str(args.fit_audit.resolve()),actual_four_fits_complete=True,
        actual_two_preflights_complete=True,actual_native_preparation_complete=True,
        warm_native_source_rows_per_panel=60,panel_count=8,source_head_same_greedy_pass=True,
        full32V_vocabulary_retained=True,source_only_reference_barrier=True,
        prospective_reference_json_parsed_by_reviewer=False,model_executed=False,encoder_executed=False,
        no_source_edits=True,no_git_mutations=True,resource_admission_performed=False,
        original_meanings_previously_exposed=True,composition64_vector_comparison_complete=False,
        reconstructed_input_mse_measured=False,old_identity_mse_is_learned_reconstruction=False,
        admitted=False,qualified=False,lake_executed=False,checkpoint_promoted=False,
        caveats=['Composition64 source strings are excluded, but numeric-vector comparison to its cached bundles is incomplete.',
            'Prospective wordings are new; their authored target meanings and original DEV sources were previously exposed.',
            'Guarded evaluation must still obtain fresh resources and execute all eight same-pass observations successfully.',
            'This is restricted32V decoder-head reconstruction; no richer-family or Lean qualification is inferred.'])
    report['content_sha256']=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()).hexdigest()
    path=args.output or r/'review/evaluation-readiness.json'
    with path.open('x') as stream:
        json.dump(report,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(dict(passed=True,checks=len(checks),artifacts=len(artifacts),output=str(path))))


if __name__=='__main__':main()
