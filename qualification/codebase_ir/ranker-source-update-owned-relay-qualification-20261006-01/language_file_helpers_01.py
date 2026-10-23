"""Unexecuted source-only modern owned relay for exact GeneratedNumericSlices.

Only the seven original queries and exact existing TypedNumericSlice baseline
are selected. The current frozen tail helper supplies guarded file context only;
no tail dependency or whole mutable-tail closure is admitted. Historical owned
records remain historical. Source/tooling gates and exact count must be frozen
before root alone may prepare/run the unchanged bounded native callback.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
WORKSPACE=ROOT.parents[2]
Q5=ROOT.with_name('ranker-objective-ir-candidate-20261005-01')
PT_PIN={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01/language_file_helpers_01.py', 'bytes': 52384, 'sha256': 'a14e76af86820a00915547e911c08172c916cfc39b13571267bc618e7dd64389'}
PT_TOOLING_GATE={'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-tail-evaluation-tooling-source-review-20261006-01/review-receipt-01.json', 'bytes': 29597, 'sha256': '9026526bfa095e012671f822e79d3f46c6fa025c083b9a78f84d6731b5899e5f'}
PRIOR_REQUEST={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01/preparation/lean-original-prefix-loss-regularizer-01-request.json', 'bytes': 889712, 'sha256': 'abd732fb5944cf00660b284e49ae2548ef10eba1ba6adbf528a8ad9fa3badfc5'}
PRIOR_SEAL={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-qualification-20261006-05/file-only-seal-01.json', 'bytes': 9994, 'sha256': '782c5a439b8e88054835697d2a7c53af104f3bb309a199110d621779e6b50ffd'}
MODULES={'lean-generated-numeric-slices-relay-01': {'direct_imports': ['TypedNumericSlice'], 'module': 'GeneratedNumericSlices', 'prior_modes': [], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-qualification-20261006-01', 'queries': ['RankerSourceSemanticsGenerated.emitted_dot_compiles', 'RankerSourceSemanticsGenerated.emitted_update_compiles', 'RankerSourceSemanticsGenerated.emitted_dot_compiler_commutes', 'RankerSourceSemanticsGenerated.emitted_update_compiler_commutes', 'RankerSourceSemanticsGenerated.emitted_dot_projection', 'RankerSourceSemanticsGenerated.emitted_update_projection', 'RankerSourceSemanticsGenerated.emitted_originalRealStep_join'], 'source': {'bytes': 3129, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-candidate-20261006-01/math/GeneratedNumericSlices.lean', 'sha256': '841cc68dd9ef75e76398804ca5c0f2e33cef100611f2c3755c26ee24c9491297'}}}
MODE_ORDER=['lean-generated-numeric-slices-relay-01']
CORE_PINS={'candidate-interface.json': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-candidate-20261006-01/candidate-interface.json', 'bytes': 9122, 'sha256': '3e955a8fefca1a5a38cfee206bedef0350a7266e98e8214c5d611350332201dc'}, 'math/GeneratedNumericSlices.lean': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-candidate-20261006-01/math/GeneratedNumericSlices.lean', 'bytes': 3129, 'sha256': '841cc68dd9ef75e76398804ca5c0f2e33cef100611f2c3755c26ee24c9491297'}, 'obligations.json': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-candidate-20261006-01/obligations.json', 'bytes': 2406, 'sha256': '4955373e27fb9b5e180aa51967b0cf9b28fd69b4b75687b060b80ddb919cca17'}}
CONTEXT_PINS=[{'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01/prepare_language_batch_01.py', 'bytes': 9539, 'sha256': '7ef405bcd16d0f4176521e9de1b8e11d422f2efcfb4c88d06aebede0d8c72d43'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01/run_language_batch_01.py', 'bytes': 28089, 'sha256': '49e78908d41f0afd4fce6024849145800ba0d0e045ebd5474efe85d13a39c9a2'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-qualification-20261006-01/module-map-01.json', 'bytes': 1087, 'sha256': '6064791d26c46d400fcd1f6ddd362f053b8f05a30a4b2e383a2710c9c41a17f8'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-update-iteration-dependency-readback-20261006-01/readback-01.json', 'bytes': 20053, 'sha256': 'ea10c9f43241168c4dc1cd1abc28f1eccc75345e255ded5334b7d4f73478f1be'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-semantics-20261005-01/preparation/lean-generated-slices-01-producer/GeneratedNumericSlices.lean', 'bytes': 3129, 'sha256': '841cc68dd9ef75e76398804ca5c0f2e33cef100611f2c3755c26ee24c9491297'}]
SOURCE_GATE={'path': '/home/barberb/lift_coding/maintenance/ranker-source-update-owned-relay-source-review-20261006-01/review-receipt-01.json', 'bytes': 18984, 'sha256': '57f85f42ccd470e30a007442ad56baecaa121edfbbe6765058a4680cf9e808e7'}
STRICT_GUARD_COUNT=3370
BASE_IMPORT_NAMES=['TypedNumericSlice']
NATIVE_LIMITS={'wall_seconds': 20, 'cpu_seconds': 20, 'output_bytes': 65536, 'workspace_bytes': 16777216}
ROOT_LEASE={'cpu_slots': 1, 'memory_mb': 2048, 'child_process_slots': 4}
PRESSURE={'memory_percent': 2.0, 'cpu_percent': 50.0, 'io_percent': 10.0}
AUTHORITY={k:False for k in ('proof_authority','execution_authority','completion_authority','planner_activation')}


def _parent():
    p=Path(PT_PIN['path'])
    if p.resolve(strict=True)!=p or p.is_symlink():raise ValueError('canonical reviewed guard-context parent required')
    with p.open('rb') as stream:raw=stream.read(PT_PIN['bytes']+1)
    if len(raw)!=PT_PIN['bytes'] or hashlib.sha256(raw).hexdigest()!=PT_PIN['sha256']:
        raise ValueError('immutable reviewed guard-context parent differs')
    ns={'__file__':str(p),'__name__':'held_generated_relay_guard_context_file_helpers'}
    exec(compile(raw,str(p),'exec'),ns)
    ns['exact'](PT_PIN);gate=ns['document'](PT_TOOLING_GATE)
    ns['need'](gate['status']=='passed_source_only' and gate['findings']==[]
        and PT_PIN in gate['reviewed_sources'] and gate['reviewed_modules']==ns['MODULES']
        and all(gate[k] is False for k in AUTHORITY),'exact reviewed guard-context source and tooling required')
    return ns

PT=_parent()
need,pin,exact,fixed,parse,document,write,read_pin,verify_held=(PT[k] for k in
    ('need','pin','exact','fixed','parse','document','write','read_pin','verify_held'))
BASE_PROFILE=PT['BASE_PROFILE']


def module(mode):
    need(type(mode) is str and mode in MODULES,'only exact GeneratedNumericSlices relay mode admitted')
    return MODULES[mode]


def source_gate(mode):
    selected=module(mode)
    need(bool(SOURCE_GATE) and STRICT_GUARD_COUNT>3359,'actual three-file relay source gate and exact denominator not frozen')
    gate=document(SOURCE_GATE)
    need(gate['status']=='passed_source_only' and gate['findings']==[]
        and gate['candidate_pins']==CORE_PINS and gate['reviewed_modules']==MODULES
        and gate['candidate_compiled'] is False and gate['actual_new_qualified_queries']==0
        and all(gate[k] is False for k in AUTHORITY),'exact three-file one-mode independent relay source gate required')
    for row in CORE_PINS.values():exact(row)
    need(selected['source'] in CORE_PINS.values(),'selected relay source absent from independent gate')
    original=CONTEXT_PINS[-1]
    need(exact(selected['source'],True)==exact(original,True),
        'fresh relay must be byte-identical to exact historical source; no copied evidence is modern acceptance')
    return gate


def complete_guard_union():
    need(bool(SOURCE_GATE) and STRICT_GUARD_COUNT>3359,'actual relay source gate and exact denominator not frozen')
    # One complete fresh guard-context traversal in this read phase. Reproduce
    # all six independently pinned parent-validator comparisons; retain no body
    # hashes across preparation/audit/native mutation boundaries. The completed
    # Loss request is file context, not a semantic import or tail-scope seal.
    parent_rows,parent_inherited=PT['complete_guard_union']()
    need(len(parent_rows)==PT['STRICT_GUARD_COUNT']==3359,'exact complete reviewed guard-context cohort required')
    inherited=document(PRIOR_REQUEST)
    need(inherited['strict_old_inputs']==parent_rows
        and inherited['strict_guard_count']==PT['STRICT_GUARD_COUNT']
        and inherited['protected_live_sources']==parent_inherited['protected_live_sources']
        and inherited['original_checkout_guards']==parent_inherited['original_checkout_guards']
        and inherited['prior_language_context_request']==PT['PRIOR_REQUEST']
        and inherited['prior_language_context_seal']==PT['PRIOR_SEAL']==PRIOR_SEAL
        and all(inherited[k] is False for k in AUTHORITY),
        'exact six parent-validator joins from freshly recomputed whole context cohort required')
    rows={r['path']:r for r in parent_rows}
    additions=[PT_PIN,PT_TOOLING_GATE,PRIOR_REQUEST,*CONTEXT_PINS,*CORE_PINS.values(),SOURCE_GATE]
    for row in additions:
        need(row['path'] not in rows or rows[row['path']]==row,'overlapping guarded body differs')
        exact(row);rows[row['path']]=row
    need(len(rows)==STRICT_GUARD_COUNT,'exact relay additive guard denominator differs')
    return [rows[p] for p in sorted(rows)],inherited


def validate_guard_union(request):
    rows,inherited=complete_guard_union()
    need(request['strict_old_inputs']==rows and request['strict_guard_count']==STRICT_GUARD_COUNT
        and request['protected_live_sources']==inherited['protected_live_sources']
        and request['original_checkout_guards']==inherited['original_checkout_guards']
        and request['prior_language_context_request']==PRIOR_REQUEST
        and request['prior_language_context_seal']==PRIOR_SEAL,'exact guard-only ancestry and relay population required')


def qualified_module(name,profile,check_row=None):
    need(name in BASE_IMPORT_NAMES and check_row is None,'only genuine existing TypedNumericSlice base import admitted')
    return PT['qualified_module'](name,profile,check_row)


def import_extension(base,imports):
    need(type(imports) is list and imports==[],
         'relay has no staged imports; no tail/language/historical GeneratedNumericSlices import admitted')
    need(base==document(BASE_PROFILE) and len(base['files'])==base['external_file_count']==20184
        and all(r['module']!='GeneratedNumericSlices' for r in base['source_import_modules'])
        and all(r['module']!='GeneratedNumericSlices' for r in base['local_checked_modules']),
        'exact original baseline with no historical GeneratedNumericSlices alias required')
    extended=dict(base);extended['staged_qualified_imports']=[]
    return extended,[]
