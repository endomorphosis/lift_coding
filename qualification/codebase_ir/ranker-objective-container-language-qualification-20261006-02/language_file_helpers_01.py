"""Reviewed-file helpers for sequential, exact container-language batches.

The immutable prior helpers remain separate. New source modules are selected
only from the frozen finite module map. Imports must have genuine native
complete-object/ordered-chunk qualification. No project or prover executes.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
WORKSPACE=ROOT.parents[2]
Q5=ROOT.with_name('ranker-objective-ir-candidate-20261005-01')
PRIOR=ROOT.with_name('ranker-objective-prefix-projections-candidate-20261006-02')
CANDIDATE=ROOT.with_name('ranker-objective-container-language-candidate-20261006-02')
PRIOR_HELPER={'path':str(PRIOR/'prefix_file_helpers_01.py'),'bytes':22214,
 'sha256':'40ed16e8f7bb3d7c7db1a7b6c2de9660d50db073c9ce318614d61e3be84451e0'}
PRIOR_REQUEST={'path':str(PRIOR/'preparation/request-v1.json'),'bytes':694192,
 'sha256':'59f6642f673041395ac089ed0743a85547286723cc894876601bce1b20d9c151'}
BASE_PROFILE={'path':str(PRIOR/'preparation/lean-objective-prefix-projections-02-producer/environment-manifest.json'),
 'bytes':10016048,'sha256':'b3071501a40a55cb1dc6ec547f2573090d382403e1887ef9f8db4ad74c244350'}
PRIOR_SEAL={'path':str(PRIOR/'file-only-seal-01.json'),'bytes':9357,
 'sha256':'6530ef110b00bc8d3c8baacdcfcaf204cc90c3d66b1c72c9cbc9dc2896626247'}
PROGRESS={'path':str(WORKSPACE/'maintenance/ranker-objective-prefix-kernel-progress-20261006-01/closed.json'),
 'bytes':3307,'sha256':'273894c74fe3ef9c062aac14c89b40d0ab7a2e147bac4d518db69d62345cd5a1'}
READBACK={'path':str(WORKSPACE/'maintenance/ranker-objective-prefix-kernel-progress-20261006-01/readback-01.json'),
 'bytes':9237,'sha256':'607f5283a2ed722b4cc99fb4613b9ab4ac05ab9451a899b0b8b0f2531b5545a9'}
MODULES={'lean-container-compiler-01': {'direct_imports': ['ObjectiveContainerSemantics'], 'module': 'ObjectiveContainerCompiler', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02', 'queries': ['RankerObjectiveContainerLanguage.compile_duplicate_context_refuses'], 'source': {'bytes': 5089, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-candidate-20261006-02/math/ObjectiveContainerCompiler.lean', 'sha256': '60fc820c383225ccb4be4eabdf3b944097478f37092c42c413f069981537bc91'}}, 'lean-container-preservation-01': {'direct_imports': ['ObjectiveContainerCompiler'], 'module': 'ObjectiveContainerPreservation', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02', 'queries': ['RankerObjectiveContainerLanguage.compile_expr_sound', 'RankerObjectiveContainerLanguage.compile_prefix_sound', 'RankerObjectiveContainerLanguage.if_nonneg_selected_branch_only'], 'source': {'bytes': 15602, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-candidate-20261006-02/math/ObjectiveContainerPreservation.lean', 'sha256': 'd2cd7d4fe847942e616328bb4392de027d5f48d678cbe8bc4c060213b7db43c4'}}, 'lean-container-semantics-01': {'direct_imports': ['ObjectiveContainerTyped'], 'module': 'ObjectiveContainerSemantics', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02', 'queries': ['RankerObjectiveContainerLanguage.map_to_vector_error', 'RankerObjectiveContainerLanguage.zip_to_vector_error', 'RankerObjectiveContainerLanguage.ordered_map_first_error', 'RankerObjectiveContainerLanguage.ordered_zip_first_error'], 'source': {'bytes': 11695, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-candidate-20261006-02/math/ObjectiveContainerSemantics.lean', 'sha256': '23bf7349c698832ad088adc68b41913a88affafff235008b38ef6688079b5ec8'}}, 'lean-container-source-01': {'direct_imports': ['ObjectivePrefixIR'], 'module': 'ObjectiveContainerSource', 'prior_modes': [], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01', 'queries': ['RankerObjectiveContainerLanguage.source_zip_left_index_bound'], 'source': {'bytes': 3060, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-candidate-20261006-02/math/ObjectiveContainerSource.lean', 'sha256': 'fc01f1d99e348e79f9cc9fdaf35cbbdb29d0c0963e88b4b984fde469e2eee410'}}, 'lean-container-typed-01': {'direct_imports': ['ObjectiveContainerSource'], 'module': 'ObjectiveContainerTyped', 'prior_modes': ['lean-container-source-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01', 'queries': ['RankerObjectiveContainerLanguage.typed_zip_right_index_bound'], 'source': {'bytes': 3583, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-candidate-20261006-02/math/ObjectiveContainerTyped.lean', 'sha256': 'bdb3140f15e51c5f52c37f2326ef7dcb2ebbdf372720915202eb13c1701cda67'}}}
CORE_PINS={'candidate-interface.json': (6570, 'a8bf03e869555953addb75db18ed1f62e39a2892bee0e86bf2ed30b8631a6015'), 'math/ObjectiveContainerCompiler.lean': (5089, '60fc820c383225ccb4be4eabdf3b944097478f37092c42c413f069981537bc91'), 'math/ObjectiveContainerPreservation.lean': (15602, 'd2cd7d4fe847942e616328bb4392de027d5f48d678cbe8bc4c060213b7db43c4'), 'math/ObjectiveContainerSemantics.lean': (11695, '23bf7349c698832ad088adc68b41913a88affafff235008b38ef6688079b5ec8'), 'math/ObjectiveContainerSource.lean': (3060, 'fc01f1d99e348e79f9cc9fdaf35cbbdb29d0c0963e88b4b984fde469e2eee410'), 'math/ObjectiveContainerTyped.lean': (3583, 'bdb3140f15e51c5f52c37f2326ef7dcb2ebbdf372720915202eb13c1701cda67'), 'obligations.json': (5154, 'ae734b0d38eb74ad49295e6fd04c4875c881f63ed9d89ca77bec4087717a9d83')}
SOURCE_GATE={'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-source-review-20261006-01/review-receipt-02.json', 'bytes': 14517, 'sha256': 'd3a869e27ab6ee61d2adca560fc5e802f775cc508bfe6e3f974a7ac504ade09c'}
STRICT_GUARD_COUNT=2806
CONTEXT_GATES=({'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-projections-source-review-20261006-02/review-receipt.json', 'bytes': 2607, 'sha256': 'c0f677ed760ec27cd5b9277d7e1e3b3f15fdaf8248160100783d618c42de6e0d'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-projections-tooling-source-review-20261006-02/review-receipt.json', 'bytes': 1905, 'sha256': '8237dd7fde3a7ee2c545f199ac290114923383c6cebca65185b2505de67e38c6'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-projections-input-review-20261006-02/review-receipt.json', 'bytes': 1588, 'sha256': 'dd73dc2dcd544a322f4fc5dcce683d46f742b82615707ffc0173f7230be9875b'})
PRESERVED_SEALS=[{'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/file-only-seal-01.json', 'bytes': 26120, 'sha256': '9fb696dbc61c09834f552b1e21d38bb599f402fc5c652e7e2e937d361f09bfd0'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-candidate-20261006-01/source-file-only-seal-01.json', 'bytes': 2278, 'sha256': '987d5e3b99eb1bbbe20e9ecc0e6b3c84714f8c6dc781a1721890efcaeebd4fec'}]
ADDITIVE_CONTEXT_PINS=[{'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-emitter-controls-20261006-01/control-plan-01.json', 'bytes': 3934, 'sha256': '1469cfdc4a61428ff72ab7945c6e348f2715845b0e8a90419f3061d0d5588770'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-emitter-controls-20261006-01/control-plan-02.json', 'bytes': 3938, 'sha256': '15167672f23666f121bc64335991cf80ad0f1dfc53b4b6c4427abfa5be2cc9fb'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-emitter-controls-20261006-01/run-01/closed.json', 'bytes': 3904, 'sha256': '8d57cc87ffb9105481022a97b5d52f71432bc48067a571131e1d49b45f0681e9'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-emitter-controls-20261006-01/run-01/held-source/objective_container_emitter.py', 'bytes': 14989, 'sha256': 'f6a97381502153a336c076093a59504945b8797283ddaa2830826c6d04000a32'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-emitter-controls-20261006-01/run-01/held-source/test_objective_container_emitter.py', 'bytes': 17651, 'sha256': 'a0a679abd18744428be3eaddccf4397fb93496d90f1d53ef86b623e4808ba4ec'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-emitter-controls-20261006-01/run-01/junit.xml', 'bytes': 3127, 'sha256': 'bfd47dbadb567b5622b61d29eb35998b35e445cadfb614275060af25311c65a4'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-emitter-controls-20261006-01/run-01/pytest-stdout.log', 'bytes': 99, 'sha256': '7ae6e16967f343d0d2aeed41ceb38e89b8a4306845da0b35c7579a33d3b5c7a8'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-emitter-controls-20261006-01/run_controls_01.py', 'bytes': 15133, 'sha256': '26a8538b85cd49e727e1cb6379e06e32f5c4ac6632f7207df14b5ee401a28e63'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-emitter-controls-20261006-01/run_controls_02.py', 'bytes': 15151, 'sha256': '5559cc477c0d87ab5284c6a631b037863ef2f1b2914a299dfad4072be4722d24'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-emitter-controls-source-review-20261006-01/review-receipt-02.json', 'bytes': 10401, 'sha256': 'a78c87cb82b4976fac1b235d7800f6a1824f72d95dd8dc1c290feb7bf3c920f9'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-emitter-controls-source-review-20261006-01/review-receipt.json', 'bytes': 9290, 'sha256': 'd28915007bf78fd936da8f83a5cfd00a17dbffe64562caa2fba4a12f4ba90f75'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-input-review-20261006-01/semantics-review-receipt-01.json', 'bytes': 1586, 'sha256': 'aa0ada85159cfd48c77daeb5cd5978c118065045831153cabd7bee4802837101'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-input-review-20261006-01/source-review-receipt-01.json', 'bytes': 1540, 'sha256': '147b398282a6e63de74e285101054a96ca64b664f22a4e51c93a6340ef93aaf1'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-input-review-20261006-01/typed-review-receipt-01.json', 'bytes': 1561, 'sha256': '31a6add27e93423f5614bda21348bf4908921dbd9f124fccbc418d579506f8e4'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-source-review-20261006-01/emitter-review-receipt-01.json', 'bytes': 9009, 'sha256': 'ffbdef68b60beed2599c22f95ad0f81696d380f16505668c3a964788ee616a52'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-source-review-20261006-01/review-receipt-01.json', 'bytes': 13034, 'sha256': '6704fc5676a6ebe5ff1abddc58acfa06d91168a5d59a26faa181ed116bafcb94'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-source-review-20261006-01/review-receipt-02.json', 'bytes': 14517, 'sha256': 'd3a869e27ab6ee61d2adca560fc5e802f775cc508bfe6e3f974a7ac504ade09c'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-source-review-20261006-01/tooling-cross-review-receipt-01.json', 'bytes': 5401, 'sha256': 'da9f17016f311b34dc8fdb0ad10f68198fa453e873d6e0a4b15fa197b5f9effd'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-tooling-source-review-20261006-01/review-receipt-01.json', 'bytes': 10232, 'sha256': 'c6ee526277c735c2f9fa4df3c77c2a58ae2396864f4921edefad2bcbd47fb383'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-emitter-candidate-20261006-01/candidate-interface.json', 'bytes': 7928, 'sha256': 'afa83f7e6904db8c998402f7a0aca5a04400a7597987d06a3fd0f4009376ca0e'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-emitter-candidate-20261006-01/source-model-obligations-01.json', 'bytes': 9731, 'sha256': '0963b63d0679909784b79548c3288d0f7b4508342d51d1baae9daaa9a335d3ad'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-emitter-candidate-20261006-01/source-v1/objective_container_emitter.py', 'bytes': 14989, 'sha256': 'f6a97381502153a336c076093a59504945b8797283ddaa2830826c6d04000a32'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-emitter-candidate-20261006-01/source-v1/test_objective_container_emitter.py', 'bytes': 17651, 'sha256': 'a0a679abd18744428be3eaddccf4397fb93496d90f1d53ef86b623e4808ba4ec'}]

NATIVE_LIMITS={'wall_seconds':20,'cpu_seconds':20,'output_bytes':65536,'workspace_bytes':16777216}
ROOT_LEASE={'cpu_slots':1,'memory_mb':2048,'child_process_slots':4}
PRESSURE={'memory_percent':2.0,'cpu_percent':50.0,'io_percent':10.0}
AUTHORITY={k:False for k in ('proof_authority','execution_authority','completion_authority','planner_activation')}


def _prior():
    p=Path(PRIOR_HELPER['path'])
    if p.resolve(strict=True)!=p or p.is_symlink():raise ValueError('canonical immutable prior file helper required')
    with p.open('rb') as stream:raw=stream.read(PRIOR_HELPER['bytes']+1)
    if len(raw)!=PRIOR_HELPER['bytes'] or hashlib.sha256(raw).hexdigest()!=PRIOR_HELPER['sha256']:
        raise ValueError('immutable prior file helper differs')
    ns={'__file__':str(p),'__name__':'held_prior_container_language_file_helpers'}
    exec(compile(raw,str(p),'exec'),ns)
    ns['exact'](PRIOR_HELPER)
    return ns


P=_prior()
need,pin,exact,fixed,parse,document,write,read_pin,verify_held=(P[k] for k in
 ('need','pin','exact','fixed','parse','document','write','read_pin','verify_held'))


def module(mode):
    need(type(mode) is str and mode in MODULES,'exact frozen module mode required')
    return MODULES[mode]


def source_gate(mode):
    selected=module(mode)
    gate=document(SOURCE_GATE)
    wanted={name:{'path':str(CANDIDATE/name),'bytes':pair[0],'sha256':pair[1]} for name,pair in CORE_PINS.items()}
    need(gate['status']=='passed_source_only' and gate['findings']==[] and gate['candidate_pins']==wanted
         and gate['reviewed_modules']==MODULES and gate['candidate_compiled'] is False
         and gate['actual_new_qualified_queries']==0 and all(gate[k] is False for k in AUTHORITY),
         'exact unqualified whole candidate independent source review required')
    for row in wanted.values():exact(row)
    need(selected['source'] in wanted.values(),'selected source absent from whole source gate')
    return gate


def descriptors(value):
    if type(value) is dict:
        if set(value)=={'path','bytes','sha256'}:yield value
        else:
            for child in value.values():yield from descriptors(child)
    elif type(value) is list:
        for child in value:yield from descriptors(child)


def seal_census(row):
    seal=document(row)
    root=Path(seal['scope_root'])
    files=seal['files'];paths={r['path'] for r in files}
    need(len(paths)==len(files)==seal['regular_file_count'] and row['path'] not in paths
         and all(Path(p).is_relative_to(root) for p in paths)
         and seal['regular_file_bytes']==sum(r['bytes'] for r in files),'complete confined seal inventory required')
    wire=json.dumps(files,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
    need(hashlib.sha256(wire).hexdigest()==seal['file_inventory_sha256'],'seal inventory digest differs')
    physical=list(root.rglob('*'))
    need(not any(p.is_symlink() for p in physical) and all(p.is_file() or p.is_dir() for p in physical)
         and {str(p) for p in physical if p.is_file()}==paths|{row['path']},'complete quiet physical seal census differs')
    for r in files:exact(r)
    return seal


def complete_guard_union():
    inherited=document(PRIOR_REQUEST)
    P['validate_guard_union'](inherited)
    seal=seal_census(PRIOR_SEAL)
    need(seal['qualified_native_checks']==1 and seal['qualified_theorem_queries']==8,
         'actual prior eight scoped source projections required')
    rows={r['path']:r for r in inherited['strict_old_inputs']}
    additions=[*seal['files'],PRIOR_SEAL,PRIOR_HELPER,PRIOR_REQUEST,BASE_PROFILE,PROGRESS,READBACK,*CONTEXT_GATES]
    for r in (PROGRESS,READBACK):additions+=list(descriptors(document(r)))
    for descriptor in PRESERVED_SEALS:
        preserved=seal_census(descriptor)
        additions += [*preserved['files'],descriptor]
    additions += ADDITIVE_CONTEXT_PINS
    additions += [fixed(CANDIDATE/name,pair)[1] for name,pair in CORE_PINS.items()]
    for r in additions:
        need(r['path'] not in rows or rows[r['path']]==r,'overlapping guard descriptor differs')
        exact(r);rows[r['path']]=r
    need(len(rows)==STRICT_GUARD_COUNT,'exact additive historical/source guard denominator differs')
    return [rows[p] for p in sorted(rows)],inherited


def validate_guard_union(request):
    rows,inherited=complete_guard_union()
    need(request['strict_old_inputs']==rows and request['protected_live_sources']==inherited['protected_live_sources']
         and request['original_checkout_guards']==inherited['original_checkout_guards']
         and request['prior_language_context_request']==PRIOR_REQUEST
         and request['prior_language_context_seal']==PRIOR_SEAL,'exact inherited and sealed guard join required')


def qualified_module(name,profile,check_row=None):
    if check_row is None and name in ('ObjectiveContainerCore','ObjectivePrefixIR'):
        check_row=P['Q6_CHECK' if name=='ObjectiveContainerCore' else 'KERNEL_CHECK']
    if check_row is not None:P['O']['IMPORT_CHECKS'][name]=(Path(check_row['path']),check_row['sha256'])
    return P['qualified_module'](name,profile)


def import_extension(base,imports):
    """Only dependency-prefix modules with whole native objects may be added."""
    need(type(imports) is list and len(imports)<=len(MODULES),'finite declared dependency population required')
    new=dict(base)
    new['source_import_modules']=list(base['source_import_modules'])
    new['local_checked_modules']=list(base['local_checked_modules'])
    new['lean_path']=list(base['lean_path'])
    new['requested_imports']=list(base['requested_imports'])
    files={r['path']:r for r in base['files']};joined=[];seen=set()
    for row in imports:
        need(type(row) is dict and set(row)=={'mode','check_result'} and row['mode'] not in seen,
             'unique closed dependency mode descriptors required')
        seen.add(row['mode']);selected=module(row['mode']);name=selected['module']
        stage_root=Path(selected['qualification_root'])
        need(stage_root in (ROOT,ROOT.with_name('ranker-objective-container-language-qualification-20261006-01')),
             'only independently frozen accepted stage roots are permitted')
        expected=stage_root/'evidence'/row['mode']/'check-result.json'
        need(row['check_result']['path']==str(expected),'exact prior-stage qualified check path required')
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
        for r in [row['check_result'],owned_row,outer_row,invocation_row,invocation['specification'],
                  proof['source'],proof['augmented_source'],proof['retention_manifest'],
                  *proof['compiled'],*proof['retained_chunks']]:
            need(r['path'] not in files or files[r['path']]==r,'qualified dependency body changed')
            exact(r);files[r['path']]=r
    new['files']=[files[p] for p in sorted(files)]
    new['external_file_count']=len(files)
    new['external_file_bytes']=sum(r['bytes'] for r in files.values())
    new['staged_qualified_imports']=joined
    return new,joined
