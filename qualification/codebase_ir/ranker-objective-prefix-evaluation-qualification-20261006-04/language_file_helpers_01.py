"""Frozen source-only bounded margins diagnostic; root alone invokes Lean.

Candidate04 adds localized hidden-goal logging to the known rejected proof. It
is not a claimed repair. Accepted Success keeps original root01/source/gate;
three rejected Margins predecessors stay sealed and cannot supply imports.
Exact diagnostic source gate/count are frozen; root alone may invoke bounded Lean after tooling review.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
WORKSPACE=ROOT.parents[2]
Q5=ROOT.with_name('ranker-objective-ir-candidate-20261005-01')
P7_PIN={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-qualification-20261006-03/language_file_helpers_01.py', 'bytes': 32266, 'sha256': '69062ec7257a0fb87a1e46ad59d8db802b978a5d021c3f1a60b984a7d3e31b9f'}
P7_TOOLING_GATE={'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-evaluation-tooling-source-review-20261006-03/review-receipt-01.json', 'bytes': 32990, 'sha256': 'b26f1170df9696cc9e5a8b8adc388074ef1e1323b162f41090d07dbd30e41ad9'}
PRIOR_REQUEST={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-qualification-20261006-03/preparation/lean-original-prefix-margins-01-request.json', 'bytes': 853868, 'sha256': '066830814c09c698ff0956d23dacf782691004f52af3a35811b32600f3a0718b'}
PRIOR_SEAL={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-qualification-20261006-03/file-only-seal-01.json', 'bytes': 9032, 'sha256': '9ffc1cf73c80e894234104ebe111c8efdee8ab4bc6e8f7f134f17703c4ce6d30'}
P7_REVIEW={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-qualification-20261006-03/failed-review-01.json', 'bytes': 2314, 'sha256': 'b8563a460b626e16f7f0c6f0cc527a393c079522df735295b0b5030c9b1bcac7'}
P7_SOURCE_SEAL={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-candidate-20261006-03/file-only-seal-01.json', 'bytes': 1831, 'sha256': 'a6ca32c167c0cc444b3fde1b905fa83a36c7df70cbbe77f5afdcbc4a0d7dc641'}
MODULES={'lean-original-prefix-margins-01': {'direct_imports': ['ObjectiveSourceContainerSuccess', 'ObjectiveOriginalPrefixParts'], 'module': 'OriginalPrefixMarginsEvaluation', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01', 'lean-container-evaluation-bridge-01', 'lean-source-scalar-lift-01', 'lean-original-prefix-parts-01', 'lean-source-container-success-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-qualification-20261006-04', 'queries': ['RankerObjectiveOriginalMarginsEvaluation.actual_margins_source_decomposition', 'RankerObjectiveOriginalMarginsEvaluation.actual_data_source_scalar_body_join', 'RankerObjectiveOriginalMarginsEvaluation.actual_factors_source_scalar_body_join', 'RankerObjectiveOriginalMarginsEvaluation.dot_source_success', 'RankerObjectiveOriginalMarginsEvaluation.margins_source_success', 'RankerObjectiveOriginalMarginsEvaluation.actual_weights_binding', 'RankerObjectiveOriginalMarginsEvaluation.actual_differences_binding', 'RankerObjectiveOriginalMarginsEvaluation.actual_margins_eval_success'], 'source': {'bytes': 8827, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-candidate-20261006-04/math/OriginalPrefixMarginsEvaluation.lean', 'sha256': '863bbb3ec2eaffa1fa1c0ca8a3f10e7778f6091fec8a5a9402428e89cd68804e'}}, 'lean-source-container-success-01': {'direct_imports': ['ObjectiveContainerEvaluationBridge'], 'module': 'ObjectiveSourceContainerSuccess', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-evaluation-bridge-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-qualification-20261006-01', 'queries': ['RankerObjectiveSourceContainerSuccess.eval_source_mapRows_success', 'RankerObjectiveSourceContainerSuccess.eval_source_mapVector_success', 'RankerObjectiveSourceContainerSuccess.eval_source_zipMap_min_success', 'RankerObjectiveSourceContainerSuccess.eval_source_zipRowsMap_min_success', 'RankerObjectiveSourceContainerSuccess.eval_source_rangeMap_success', 'RankerObjectiveSourceContainerSuccess.eval_source_fsum_success', 'RankerObjectiveSourceContainerSuccess.eval_source_lengthVector_success', 'RankerObjectiveSourceContainerSuccess.eval_source_lengthMatrix_success', 'RankerObjectiveSourceContainerSuccess.eval_source_indexVector_success', 'RankerObjectiveSourceContainerSuccess.eval_source_natToScalar_success'], 'source': {'bytes': 8191, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-candidate-20261006-01/math/ObjectiveSourceContainerSuccess.lean', 'sha256': '860982d7e67954d782d776915f5d06bb0fe51de0c03763c10e23c524a750f7a2'}}}
DEPENDENCY_MODULES={'lean-container-generated-prefix-01': {'direct_imports': ['ObjectiveContainerPreservation'], 'module': 'ObjectiveContainerPrefixGenerated', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01', 'queries': ['GeneratedOriginalObjectiveContainerPrefix.emitted_prefix_compiles', 'GeneratedOriginalObjectiveContainerPrefix.emitted_prefix_preserves'], 'source': {'bytes': 8046, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/ObjectiveContainerPrefixGenerated.lean', 'sha256': '31bc24c08296302aa15c8067df2cae7e7aa9f3d3b28b63145d661f82f1d3ccbb'}}, 'lean-container-evaluation-bridge-01': {'direct_imports': ['ObjectiveContainerPreservation'], 'module': 'ObjectiveContainerEvaluationBridge', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01', 'queries': ['RankerObjectiveContainerEvaluationBridge.vectorOfList_ofFn', 'RankerObjectiveContainerEvaluationBridge.mapToVector_ofFn_success', 'RankerObjectiveContainerEvaluationBridge.zipMapExact_eq_mapExact_zipWith', 'RankerObjectiveContainerEvaluationBridge.zipWith_ofFn_min', 'RankerObjectiveContainerEvaluationBridge.zipMapExact_ofFn_min_success', 'RankerObjectiveContainerEvaluationBridge.zipToVector_ofFn_min_success', 'RankerObjectiveContainerEvaluationBridge.orderedFsum_ofFn_eq_sum', 'RankerObjectiveContainerEvaluationBridge.orderedFsum_map_success', 'RankerObjectiveContainerEvaluationBridge.orderedFsum_zip_success'], 'source': {'bytes': 7680, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-eval-bridge-candidate-20261006-01/math/ObjectiveContainerEvaluationBridge.lean', 'sha256': 'b39d3c585c5cbbe9da30f932000ce2428d2cc754849e1c9dbd43b6912c3a4587'}}, 'lean-original-prefix-parts-01': {'direct_imports': ['ObjectiveSourceScalarLift'], 'module': 'ObjectiveOriginalPrefixParts', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01', 'lean-source-scalar-lift-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-qualification-20261006-02', 'queries': ['RankerObjectiveOriginalPrefixParts.emitted_prefix_decomposition', 'RankerObjectiveOriginalPrefixParts.emitted_loss_body_scalar_injection', 'RankerObjectiveOriginalPrefixParts.emitted_factor_body_scalar_injection', 'RankerObjectiveOriginalPrefixParts.emitted_loss_body_success', 'RankerObjectiveOriginalPrefixParts.emitted_factor_body_success'], 'source': {'bytes': 8913, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-candidate-20261006-03/math/ObjectiveOriginalPrefixParts.lean', 'sha256': 'a8921ca1035c71f5aa22066777084f27a85dc5f71e8200469f7c9e61b322cf08'}}, 'lean-source-scalar-lift-01': {'direct_imports': ['ObjectiveContainerPrefixGenerated'], 'module': 'ObjectiveSourceScalarLift', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-qualification-20261006-02', 'queries': ['RankerObjectiveSourceScalarLift.eval_lift_scalar_source', 'RankerObjectiveSourceScalarLift.named_stable_loss_success', 'RankerObjectiveSourceScalarLift.named_stable_factor_success'], 'source': {'bytes': 5735, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-candidate-20261006-03/math/ObjectiveSourceScalarLift.lean', 'sha256': '0ecadf24c5e8d23f4904da8fbd4260b8b0488d90fae9643d6dc8bfab14dae89e'}}, 'lean-source-container-success-01': {'direct_imports': ['ObjectiveContainerEvaluationBridge'], 'module': 'ObjectiveSourceContainerSuccess', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-evaluation-bridge-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-qualification-20261006-01', 'queries': ['RankerObjectiveSourceContainerSuccess.eval_source_mapRows_success', 'RankerObjectiveSourceContainerSuccess.eval_source_mapVector_success', 'RankerObjectiveSourceContainerSuccess.eval_source_zipMap_min_success', 'RankerObjectiveSourceContainerSuccess.eval_source_zipRowsMap_min_success', 'RankerObjectiveSourceContainerSuccess.eval_source_rangeMap_success', 'RankerObjectiveSourceContainerSuccess.eval_source_fsum_success', 'RankerObjectiveSourceContainerSuccess.eval_source_lengthVector_success', 'RankerObjectiveSourceContainerSuccess.eval_source_lengthMatrix_success', 'RankerObjectiveSourceContainerSuccess.eval_source_indexVector_success', 'RankerObjectiveSourceContainerSuccess.eval_source_natToScalar_success'], 'source': {'bytes': 8191, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-candidate-20261006-01/math/ObjectiveSourceContainerSuccess.lean', 'sha256': '860982d7e67954d782d776915f5d06bb0fe51de0c03763c10e23c524a750f7a2'}}}
DEPENDENCY_SOURCE_GATES={'lean-container-generated-prefix-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-source-review-20261006-01/review-receipt-01.json', 'bytes': 53525, 'sha256': 'e2bd9c412ca4545a68a85ebe33560522ce53ce7932f9c7f840bca1137f0ae7a6'}, 'lean-container-evaluation-bridge-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-source-review-20261006-01/review-receipt-01.json', 'bytes': 53525, 'sha256': 'e2bd9c412ca4545a68a85ebe33560522ce53ce7932f9c7f840bca1137f0ae7a6'}, 'lean-original-prefix-parts-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-source-model-source-review-20261006-01/review-receipt-02.json', 'bytes': 26037, 'sha256': 'd2f8de49eee73c2b00615501a855b206a46ec80b3fd318ed47efa81b51fa72c8'}, 'lean-source-scalar-lift-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-source-model-source-review-20261006-01/review-receipt-02.json', 'bytes': 26037, 'sha256': 'd2f8de49eee73c2b00615501a855b206a46ec80b3fd318ed47efa81b51fa72c8'}, 'lean-source-container-success-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-evaluation-source-review-20261006-01/review-receipt-01.json', 'bytes': 16600, 'sha256': '56d36c189a4ac0e7c93119b21363a78bb3ace9fe59a169da166e4f43c59a8fb5'}}
ACCEPTED_CHECK_PINS={'lean-container-generated-prefix-01': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01/evidence/lean-container-generated-prefix-01/check-result.json', 'bytes': 16026, 'sha256': '2194c2152ffaaffb94099dd1a4306c1c08fec22fce1077caef22196ee8441c3e'}, 'lean-container-evaluation-bridge-01': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01/evidence/lean-container-evaluation-bridge-01/check-result.json', 'bytes': 15476, 'sha256': 'e90c43fb19b44daf5d2e9d5fee9506204c43154a7d21e59a7f739767de0184ed'}, 'lean-original-prefix-parts-01': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-qualification-20261006-02/evidence/lean-original-prefix-parts-01/check-result.json', 'bytes': 13909, 'sha256': '396f30b42dab78ebc88229e0bdef551779ad43a6b1f41f94558043be766e4ae0'}, 'lean-source-scalar-lift-01': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-qualification-20261006-02/evidence/lean-source-scalar-lift-01/check-result.json', 'bytes': 14701, 'sha256': '87ffaddd1a02986f5c0f116233d56caa8edb983244461f437454db1dbb1fdc14'}, 'lean-source-container-success-01': {'bytes': 15589, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-qualification-20261006-01/evidence/lean-source-container-success-01/check-result.json', 'sha256': '27e9598373b6831812abe235b5a806f5183b1b68876e3e1d93c9695eea3444cc'}}
FAILED_MARGINS_CHECK={'bytes': 14577, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-qualification-20261006-03/evidence/lean-original-prefix-margins-01/check-result.json', 'sha256': '059fbec9cc7ca18eda14dabfaa25f4e334c66c25418a852662bee9da99488017'}
CORE_PINS={'candidate-interface.json': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-candidate-20261006-04/candidate-interface.json', 'bytes': 4814, 'sha256': 'edb578dbadbba737a65b0d37682304f57f9e92c1a75e2b4abeacc0e24254398b'}, 'math/ObjectiveSourceContainerSuccess.lean': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-candidate-20261006-04/math/ObjectiveSourceContainerSuccess.lean', 'bytes': 8191, 'sha256': '860982d7e67954d782d776915f5d06bb0fe51de0c03763c10e23c524a750f7a2'}, 'math/OriginalPrefixMarginsEvaluation.lean': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-candidate-20261006-04/math/OriginalPrefixMarginsEvaluation.lean', 'bytes': 8827, 'sha256': '863bbb3ec2eaffa1fa1c0ca8a3f10e7778f6091fec8a5a9402428e89cd68804e'}, 'obligations.json': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-candidate-20261006-04/obligations.json', 'bytes': 2443, 'sha256': 'bc3453f5832fe2de8d21ff5e75a5f0541583a887711abdf5f0e351205f8b2305'}}
CONTEXT_PINS=[{'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-qualification-20261006-04/module-map-01.json', 'bytes': 3365, 'sha256': 'f5a09bdc3e518837596c57b59ec13c3ac4877a38b0ded8560a6e17a6dd8a0c3c'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-evaluation-input-review-20261006-03/original-margins-review-receipt-01.json', 'bytes': 2256, 'sha256': 'a5bc805acb01a1e7cadb30649d2e15c34035c097883d75286c38643805ebec6a'}]
PRIOR_IMPORTS=[{'check_result': {'bytes': 14071, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-source-01/check-result.json', 'sha256': 'ca7ed3da92fbae947f595bfde1a8eb1025bc9758ebdd58eaf11210b2d125c0bf'}, 'mode': 'lean-container-source-01'}, {'check_result': {'bytes': 15524, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-typed-01/check-result.json', 'sha256': 'cfb690034025ad99470dad89ab537952955ddb4b14b1ed3675bf8181dfcfad63'}, 'mode': 'lean-container-typed-01'}, {'check_result': {'bytes': 13707, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-semantics-01/check-result.json', 'sha256': '8650075e9f209aa2d61d284d043b51200a866611703ad40739ce29af3f05d62b'}, 'mode': 'lean-container-semantics-01'}, {'check_result': {'bytes': 12509, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-compiler-01/check-result.json', 'sha256': '43276551bd5488e8575cd07a810c5156f6178d75b4924a0bcf677906d2e520df'}, 'mode': 'lean-container-compiler-01'}, {'check_result': {'bytes': 24686, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-preservation-01/check-result.json', 'sha256': '803036eae98f65a373574b00b3434edcdbcf43847be65e7c7e799e0c99dee0b8'}, 'mode': 'lean-container-preservation-01'}]
SOURCE_GATE={'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-evaluation-source-review-20261006-01/review-receipt-04.json', 'bytes': 52040, 'sha256': '5f48b3b402e888dcc3140e79a252400350c7b12db117b5052385231ef9902aa1'}
STRICT_GUARD_COUNT=3260
NATIVE_LIMITS={'wall_seconds':20,'cpu_seconds':20,'output_bytes':65536,'workspace_bytes':16777216}
ROOT_LEASE={'cpu_slots':1,'memory_mb':2048,'child_process_slots':4}
PRESSURE={'memory_percent':2.0,'cpu_percent':50.0,'io_percent':10.0}
AUTHORITY={k:False for k in ('proof_authority','execution_authority','completion_authority','planner_activation')}

def _parent():
    p=Path(P7_PIN['path'])
    if p.resolve(strict=True)!=p or p.is_symlink():raise ValueError('canonical reviewed parent required')
    with p.open('rb') as stream:raw=stream.read(P7_PIN['bytes']+1)
    if len(raw)!=P7_PIN['bytes'] or hashlib.sha256(raw).hexdigest()!=P7_PIN['sha256']:
        raise ValueError('immutable reviewed parent differs')
    ns={'__file__':str(p),'__name__':'held_prefix_evaluation_retry_parent_file_helpers'}
    exec(compile(raw,str(p),'exec'),ns)
    ns['exact'](P7_PIN);gate=ns['document'](P7_TOOLING_GATE)
    ns['need'](gate['status']=='passed_source_only' and gate['findings']==[]
        and P7_PIN in gate['reviewed_sources'] and gate['reviewed_modules']==ns['MODULES']
        and all(gate[k] is False for k in AUTHORITY),'exact reviewed parent source and tooling required')
    return ns

P7=_parent()
need,pin,exact,fixed,parse,document,write,read_pin,verify_held=(P7[k] for k in
    ('need','pin','exact','fixed','parse','document','write','read_pin','verify_held'))
BASE_PROFILE=P7['BASE_PROFILE']


def module(mode):
    need(type(mode) is str and mode in MODULES,'only two selected frozen mixed-root prefix-evaluation modes admitted')
    return MODULES[mode]


def dependency_module(mode):
    need(type(mode) is str and mode in DEPENDENCY_MODULES,'only fixed generated/bridge/scalar/parts/accepted-success dependencies admitted')
    return DEPENDENCY_MODULES[mode]


def source_gate(mode):
    selected=module(mode)
    need(bool(SOURCE_GATE) and STRICT_GUARD_COUNT>3225,'actual source gate and exact denominator not frozen')
    gate=document(SOURCE_GATE)
    need(gate['status']=='passed_source_only' and gate['findings']==[]
        and gate['candidate_pins']==CORE_PINS and gate['reviewed_modules']==MODULES
        and gate['candidate_compiled'] is False and gate['actual_new_qualified_queries']==0
        and all(gate[k] is False for k in AUTHORITY),'exact four-file independent mixed-root source gate required')
    for row in CORE_PINS.values():exact(row)
    if mode=='lean-source-container-success-01':
        old_gate=document(P7['P6']['P5']['SOURCE_GATE']);accepted=document(ACCEPTED_CHECK_PINS[mode])
        copied=CORE_PINS['math/ObjectiveSourceContainerSuccess.lean']
        need(selected==P7['MODULES'][mode]==old_gate['reviewed_modules'][mode]
            and selected['qualification_root']==str(ROOT.with_name('ranker-objective-prefix-evaluation-qualification-20261006-01'))
            and old_gate['status']=='passed_source_only' and old_gate['findings']==[]
            and accepted['status']=='passed' and accepted['native_lean_returncode']==0
            and accepted['source']['bytes']==selected['source']['bytes']==copied['bytes']
            and accepted['source']['sha256']==selected['source']['sha256']==copied['sha256']
            and [r['theorem'] for r in accepted['theorem_axiom_output']]==selected['queries']
            and all(old_gate[k] is accepted[k] is False for k in AUTHORITY),
            'reused Success must keep its actual accepted original source/root/gate and unchanged copied body')
        exact(selected['source'])
    else:
        need(selected['source'] in CORE_PINS.values(),'fresh Margins source absent from candidate source gate')
    return gate


def seal_census(row):
    return P7['seal_census'](row)


def complete_guard_union():
    parent_rows,unused=P7['complete_guard_union']()
    need(len(parent_rows)==P7['STRICT_GUARD_COUNT']==3225,'exact complete third-attempt cohort required')
    inherited=document(PRIOR_REQUEST);P7['validate_guard_union'](inherited)
    seal=seal_census(PRIOR_SEAL);review=document(P7_REVIEW);source=seal_census(P7_SOURCE_SEAL)
    failed=document(FAILED_MARGINS_CHECK)
    need(seal['scope_root']==str(ROOT.with_name('ranker-objective-prefix-evaluation-qualification-20261006-03'))
        and seal['regular_file_count']==26 and seal['regular_file_bytes']==11323201
        and seal['native_attempts']==1 and seal['failed_native_attempts']==1
        and seal['qualified_native_checks']==seal['qualified_theorem_queries']==0
        and seal['review']==P7_REVIEW and review['status']=='failed_native_preserved_not_admitted'
        and review['strict_guard_count']==3225 and review['parent_accepted_queries']==39
        and review['qualified_native_checks']==review['qualified_theorem_queries']==0
        and review['new_whole_objects']==review['new_retained_chunks']==0
        and review['check_result']==FAILED_MARGINS_CHECK and review['native_returncode']==1
        and review['reused_success_requalified'] is False
        and failed['status']=='inconclusive' and failed['native_lean_returncode']==1
        and failed['compiled_artifacts']==[]
        and source['scope_root']==str(ROOT.with_name('ranker-objective-prefix-evaluation-candidate-20261006-03'))
        and source['regular_file_count']==4 and source['regular_file_bytes']==24057
        and source['qualified_theorem_queries']==0
        and all(seal[k] is source[k] is review[k] is False for k in AUTHORITY),
        'all rejected-zero predecessors persist; diagnostic cannot admit failed Margins or rerun accepted Success')
    need(bool(SOURCE_GATE),'actual bounded diagnostic source gate not frozen')
    rows={r['path']:r for r in parent_rows}
    additions=[*seal['files'],PRIOR_SEAL,*source['files'],P7_SOURCE_SEAL,
        P7_PIN,P7_TOOLING_GATE,PRIOR_REQUEST,P7_REVIEW,*CONTEXT_PINS,*CORE_PINS.values(),SOURCE_GATE]
    for row in additions:
        need(row['path'] not in rows or rows[row['path']]==row,'overlapping guarded body differs')
        exact(row);rows[row['path']]=row
    need(len(rows)==STRICT_GUARD_COUNT,'exact bounded diagnostic additive guard denominator differs')
    return [rows[p] for p in sorted(rows)],inherited


def validate_guard_union(request):
    rows,inherited=complete_guard_union()
    need(request['strict_old_inputs']==rows and request['strict_guard_count']==STRICT_GUARD_COUNT
        and request['protected_live_sources']==inherited['protected_live_sources']
        and request['original_checkout_guards']==inherited['original_checkout_guards']
        and request['prior_language_context_request']==PRIOR_REQUEST
        and request['prior_language_context_seal']==PRIOR_SEAL,'exact sealed partial parent and margins retry guard join required')


def qualified_module(name,profile,check_row=None):
    return P7['qualified_module'](name,profile,check_row)

def _append_imports(base,imports):
    """Only dependency-prefix modules with whole native objects may be added."""
    need(type(imports) is list and len(imports)<=len(DEPENDENCY_MODULES),'finite declared dependency population required')
    new=dict(base)
    new['source_import_modules']=list(base['source_import_modules'])
    new['local_checked_modules']=list(base['local_checked_modules'])
    new['lean_path']=list(base['lean_path'])
    new['requested_imports']=list(base['requested_imports'])
    files={r['path']:r for r in base['files']};joined=[];seen=set()
    for row in imports:
        need(type(row) is dict and set(row)=={'mode','check_result'} and row['mode'] not in seen,
             'unique closed dependency mode descriptors required')
        seen.add(row['mode']);selected=dependency_module(row['mode']);name=selected['module']
        stage_root=Path(selected['qualification_root'])
        need(stage_root in (ROOT.with_name('ranker-objective-prefix-evaluation-qualification-20261006-01'),
                            ROOT.with_name('ranker-objective-container-prefix-qualification-20261006-01'),
                            ROOT.with_name('ranker-objective-source-model-qualification-20261006-02')),
             'only independently frozen accepted stage roots are permitted')
        expected=stage_root/'evidence'/row['mode']/'check-result.json'
        need(row['check_result']['path']==str(expected),'exact prior-stage qualified check path required')
        need(row['mode'] not in ACCEPTED_CHECK_PINS or row['check_result']==ACCEPTED_CHECK_PINS[row['mode']],
             'exact accepted prior-stage check descriptor required')
        check=document(row['check_result'])
        owned_row=pin(expected.with_name('closed.json'))
        outer_row=pin(stage_root/'evidence'/(row['mode']+'-closed.json'))
        owned=document(owned_row);outer=document(outer_row)
        invocation_row=pin(stage_root/'preparation'/(row['mode']+'-invocation.json'))
        invocation=document(invocation_row)
        need(invocation['mode']==row['mode'] and owned['mode']==row['mode']
             and owned['invocation']==outer['invocation']==invocation_row
             and owned['native_proof_checks']==[row['check_result']]
             and owned['native_checker_attempts']==[{'specification':invocation['specification'],
                                                    'native_invocations_observed':1}]
             and invocation['specification']['path']==str(stage_root/'preparation'/(row['mode']+'-check-specification.json')),
             'exact check/owned/outer/invocation staged execution joins required')
        specification=document(invocation['specification'])
        source_gate_row=DEPENDENCY_SOURCE_GATES[row['mode']];gate=document(source_gate_row)
        need(specification['selected_module']==selected
             and specification['independent_core_source_review']==source_gate_row
             and gate['status']=='passed_source_only' and gate['findings']==[]
             and gate['reviewed_modules'][row['mode']]==selected
             and all(gate[k] is False for k in AUTHORITY),
             'exact declared dependency source-review/selected-module join required')
        inherited=document(PRIOR_REQUEST)
        need(check['source']==specification['source'] and check['environment_manifest']==specification['environment_manifest']
             and check['actual_root_lease']==owned['root_lease']
             and owned['root_lease']['owner_pid']==outer['child_pid']
             and owned['original_checkout_guards_before']==owned['original_checkout_guards_after']==inherited['original_checkout_guards']
             and check['native_invocations']==check['native_lean_invocations']==1
             and check['native_bounds']=={'timeout_seconds':20,'cpu_seconds':20,'max_input_bytes':262144,
                                        'max_output_bytes':65536,'max_workspace_bytes':16777216}
             and owned['final_resource_state']['counters']['acquisitions_total']==1
             and owned['final_resource_state']['counters']['releases_total']==1
             and all(check[k] is owned[k] is False for k in AUTHORITY)
             and all(owned[k]==0 for k in ('native_preparation_calls','gradient_evaluations','optimizer_updates',
                                           'fit_calls','autoencoder_fit_calls','test_cases','metadata_hydration_calls',
                                           'source_function_executions','dependency_setup_calls')),
             'owned staged check must preserve exact native bounds/guards/lease and zero prohibited callbacks')
        need(owned['status']=='passed' and owned['root_release_returned'] is True
             and owned['cleanup_errors']==outer['cleanup_errors']==[] and outer['returncode']==0
             and owned['final_resource_state']['active_lease_count']==owned['final_resource_state']['waiting_request_count']==0
             and owned['all_strict_old_and_protected_live_inputs_unchanged'] is True,
             'prior staged module must be owned, closed and drained before import')
        need(check['status']=='passed' and check['native_lean_returncode']==0
             and check['source']['bytes']==selected['source']['bytes']
             and check['source']['sha256']==selected['source']['sha256']
             and [r['theorem'] for r in check['theorem_axiom_output']]==selected['queries'],
             'actual accepted source-bound staged module required')
        compiled=[{k:r[k] for k in ('path','bytes','sha256')} for r in check['compiled_artifacts']]
        need(len(compiled)==1 and all(r['module']!=name for r in new['source_import_modules']),
             'unique new qualified whole module required')
        new['source_import_modules'].append({'module':name,'source':check['augmented_source'],
                                             'compiled':compiled,'package':'locally-qualified'})
        new['local_checked_modules'].append({'module':name,'qualification':row['check_result'],
                                            'environment':check['environment_manifest']})
        new['lean_path']=[str(Path(compiled[0]['path']).parent),*new['lean_path']]
        new['requested_imports'].append(name)
        proof=qualified_module(name,new,row['check_result']);joined.append(proof)
        for r in [row['check_result'],owned_row,outer_row,invocation_row,invocation['specification'],source_gate_row,
                  proof['source'],proof['augmented_source'],proof['retention_manifest'],
                  *proof['compiled'],*proof['retained_chunks']]:
            need(r['path'] not in files or files[r['path']]==r,'qualified dependency body changed')
            exact(r);files[r['path']]=r
    new['files']=[files[p] for p in sorted(files)]
    new['external_file_count']=len(files)
    new['external_file_bytes']=sum(r['bytes'] for r in files.values())
    new['staged_qualified_imports']=joined
    return new,joined



def import_extension(base,imports):
    need(type(imports) is list and len(imports)==10 and imports[:5]==PRIOR_IMPORTS,
         'fixed five parent imports plus exact margins retry dependencies required')
    extras=imports[5:]
    need([r['mode'] for r in extras]==['lean-container-generated-prefix-01','lean-container-evaluation-bridge-01',
        'lean-source-scalar-lift-01','lean-original-prefix-parts-01','lean-source-container-success-01'],
        'exact genuine margins dependency order required; no Success requalification here')
    need(extras[-1]['check_result']==ACCEPTED_CHECK_PINS['lean-source-container-success-01'],
        'only actual accepted Success from original root01 may be reused')
    extended,parent=P7['P6']['P5']['P4']['P3']['import_extension'](base,imports[:5])
    extended,new=_append_imports(extended,extras)
    extended['staged_qualified_imports']=parent+new
    return extended,parent+new
