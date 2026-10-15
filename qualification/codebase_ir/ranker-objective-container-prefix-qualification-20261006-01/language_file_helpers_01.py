"""Fresh finite q3 helpers; source-only until independent review.

P2 retains its own exact module map and mixed q1/q2 qualification roots. This
helper exposes only the two new finite modes. All readers/import proofs are
from immutable reviewed stdlib definitions; no target model/prover runs here.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
WORKSPACE=ROOT.parents[2]
Q5=ROOT.with_name('ranker-objective-ir-candidate-20261005-01')
P2_PIN={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/language_file_helpers_01.py', 'bytes': 24254, 'sha256': '12ccff684135c86e737213dec2f4f9883a2d02a004dc1964677584eb724006ec'}
P2_TOOLING_GATE={'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-tooling-source-review-20261006-02/review-receipt-01.json', 'bytes': 44759, 'sha256': '6d355386d057766ee190b7869c1cc13e3a2fb0c72a37d2c75e42819071a3036b'}
PRIOR_REQUEST={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/preparation/lean-container-preservation-01-request.json', 'bytes': 739419, 'sha256': 'c45b8eaaca80aa52eedce09b3e3552463088e77759b5f797c8641249edc5d387'}
PRIOR_SEAL={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/file-only-seal-01.json', 'bytes': 31541, 'sha256': 'f928432ec1bc0053dcea57e9e90ff578eeefb4d269cd747e54dc8c5ae503b338'}
P2_SOURCE_SEAL={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-candidate-20261006-02/source-file-only-seal-01.json', 'bytes': 2643, 'sha256': 'c12a6bd3a32f77d28f0a6f897d6843ee07fe394d4158b41db188500c8cac4309'}
HOST_SEAL={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/file-only-seal-01.json', 'bytes': 1952, 'sha256': '3d58dbad41bae68799869d8416dcb8a96d3511cee20c88d41acd132d51451981'}
P2_QUALIFIED_REVIEW={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/qualified-review-01.json', 'bytes': 10974, 'sha256': '37df4b286e44246faf1f45cbdb07edf167b7d5d120b4b162ce0ea4bf588af39a'}
MODULES={'lean-container-evaluation-bridge-01': {'direct_imports': ['ObjectiveContainerPreservation'], 'module': 'ObjectiveContainerEvaluationBridge', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01', 'queries': ['RankerObjectiveContainerEvaluationBridge.vectorOfList_ofFn', 'RankerObjectiveContainerEvaluationBridge.mapToVector_ofFn_success', 'RankerObjectiveContainerEvaluationBridge.zipMapExact_eq_mapExact_zipWith', 'RankerObjectiveContainerEvaluationBridge.zipWith_ofFn_min', 'RankerObjectiveContainerEvaluationBridge.zipMapExact_ofFn_min_success', 'RankerObjectiveContainerEvaluationBridge.zipToVector_ofFn_min_success', 'RankerObjectiveContainerEvaluationBridge.orderedFsum_ofFn_eq_sum', 'RankerObjectiveContainerEvaluationBridge.orderedFsum_map_success', 'RankerObjectiveContainerEvaluationBridge.orderedFsum_zip_success'], 'source': {'bytes': 7680, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-eval-bridge-candidate-20261006-01/math/ObjectiveContainerEvaluationBridge.lean', 'sha256': 'b39d3c585c5cbbe9da30f932000ce2428d2cc754849e1c9dbd43b6912c3a4587'}}, 'lean-container-generated-prefix-01': {'direct_imports': ['ObjectiveContainerPreservation'], 'module': 'ObjectiveContainerPrefixGenerated', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01', 'queries': ['GeneratedOriginalObjectiveContainerPrefix.emitted_prefix_compiles', 'GeneratedOriginalObjectiveContainerPrefix.emitted_prefix_preserves'], 'source': {'bytes': 8046, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/ObjectiveContainerPrefixGenerated.lean', 'sha256': '31bc24c08296302aa15c8067df2cae7e7aa9f3d3b28b63145d661f82f1d3ccbb'}}}
CORE_PINS={'bridge/math': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-eval-bridge-candidate-20261006-01/math/ObjectiveContainerEvaluationBridge.lean', 'bytes': 7680, 'sha256': 'b39d3c585c5cbbe9da30f932000ce2428d2cc754849e1c9dbd43b6912c3a4587'}, 'bridge/interface': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-eval-bridge-candidate-20261006-01/candidate-interface.json', 'bytes': 3497, 'sha256': 'e249f1fea7960bd306a76ed059e6226af7bd65107338efcf6142c8418510b8ff'}, 'bridge/obligations': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-eval-bridge-candidate-20261006-01/obligations.json', 'bytes': 2187, 'sha256': 'd810e7f086fb2677cde583daf839d289beef0e5edaebcacf89abe5ed6385fe9a'}, 'host/original': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/ObjectiveOriginalPrefix.lean', 'bytes': 6209, 'sha256': 'd096036379e3109bab822cd4565bb522785dbd411b8d2fbb32787c9ab2a1ffda'}, 'host/generated': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/ObjectiveContainerPrefixGenerated.lean', 'bytes': 8046, 'sha256': '31bc24c08296302aa15c8067df2cae7e7aa9f3d3b28b63145d661f82f1d3ccbb'}, 'host/emission': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/emission-receipt.json', 'bytes': 10097, 'sha256': '8f688af528ea08b85b1dde9d7d35f685d1421ee9de3547817221ccc0800e6f7b'}, 'host/materialization': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/materialization-receipt.json', 'bytes': 9440, 'sha256': '3620933baacb645abcc1055cf2369a38031fb02f958ec6d2cc3c6913783b3fe7'}}
CONTEXT_PINS=[{'bytes': 16391, 'path': '/home/barberb/lift_coding/artifacts/codebase_ir_terminal_bench/terminal-codebase-ir-intent-corpus-head-20261004-01/source/benchmarks/agent_supervisor/container_coding/terminal_codebase_intent_ranker_training.py', 'sha256': '3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a'}, {'bytes': 3938, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-emitter-controls-20261006-01/control-plan-02.json', 'sha256': '15167672f23666f121bc64335991cf80ad0f1dfc53b4b6c4427abfa5be2cc9fb'}, {'bytes': 3904, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-emitter-controls-20261006-01/run-01/closed.json', 'sha256': '8d57cc87ffb9105481022a97b5d52f71432bc48067a571131e1d49b45f0681e9'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-input-review-20261006-02/audit_prepared_batch_01.py', 'bytes': 2954, 'sha256': 'c75bd0718632b12588de2aba4c5fad18989b2797506e1188120b9271d6116158'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-input-review-20261006-02/audit_prepared_batch_02.py', 'bytes': 3132, 'sha256': 'a0ad47b1944f170bff16d8229e82077c76fb74177737c6f34201cd270b95c218'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-input-review-20261006-02/compiler-review-receipt-01.json', 'bytes': 2240, 'sha256': '1a397f16115ccaae71242cbeb191c9c0ec23191a66a295f33d90ea615da08ba8'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-input-review-20261006-02/preservation-review-receipt-01.json', 'bytes': 2256, 'sha256': 'c04ccbf40fb616a3e37485a03c589a691fec4a540418c42147c42197497e74a4'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-input-review-20261006-02/semantics-review-receipt-01.json', 'bytes': 2244, 'sha256': 'b716b9a933f36eece7090b46b79385f10b2b97fc7a84e1b84bf2bdf739250201'}, {'bytes': 9009, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-source-review-20261006-01/emitter-review-receipt-01.json', 'sha256': 'ffbdef68b60beed2599c22f95ad0f81696d380f16505668c3a964788ee616a52'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-source-review-20261006-01/evaluation-bridge-review-receipt-01.json', 'bytes': 6382, 'sha256': '54c1e8d7843768b50d7d440ab7626526335fa699ee2099cd6c50be8635a2f223'}, {'bytes': 14517, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-source-review-20261006-01/review-receipt-02.json', 'sha256': 'd3a869e27ab6ee61d2adca560fc5e802f775cc508bfe6e3f974a7ac504ade09c'}, {'bytes': 44759, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-tooling-source-review-20261006-02/review-receipt-01.json', 'sha256': '6d355386d057766ee190b7869c1cc13e3a2fb0c72a37d2c75e42819071a3036b'}, {'bytes': 6556, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-materialization-20261006-01/interface-01.json', 'sha256': '79a586b4f314349c93da55cd0eca841b21cbc0e2585846abff1e3fe1ee389141'}, {'bytes': 3367, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-materialization-20261006-01/interface-02.json', 'sha256': 'bc4be207b971b0748aacd854074de1e7fe4ea26078cc582305e25ad0f7e975d8'}, {'bytes': 17458, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-materialization-20261006-01/materialize_01.py', 'sha256': '0a023b11377f804056e6e6bee7bd9f339ed84f9eaeff6d180f8179e7d82475d4'}, {'bytes': 17536, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-materialization-20261006-01/materialize_02.py', 'sha256': '941ed3af87990d08a157c01614750ac02ce95265bbdc9bf4f0fd64ae04984fdf'}, {'bytes': 4444, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-materialization-20261006-01/plan-01.json', 'sha256': '393ed6bec50a0de162a8340395469b057fc4e97e33e4a800ee65b6f15fe8fdae'}, {'bytes': 1837, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-materialization-20261006-01/proof-suffix-01.lean.txt', 'sha256': 'eca0456de2d10fa21507ca3b1150a5943e74daa3e965973265de8d4d75dbd919'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-materialization-20261006-01/third-stage-blueprint-01.json', 'bytes': 12759, 'sha256': '96e12e116deb6237918bfbe1f2d4096933ed2372082ffd4ceae21029484d67a4'}, {'bytes': 9378, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-materialization-source-review-20261006-01/review-receipt-01.json', 'sha256': 'fa529f0a0a7af962c3edcd759a233347150d30541128a4211bd92a3f39edb0c1'}, {'bytes': 14989, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-emitter-candidate-20261006-01/source-v1/objective_container_emitter.py', 'sha256': 'f6a97381502153a336c076093a59504945b8797283ddaa2830826c6d04000a32'}, {'bytes': 14071, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-source-01/check-result.json', 'sha256': 'ca7ed3da92fbae947f595bfde1a8eb1025bc9758ebdd58eaf11210b2d125c0bf'}, {'bytes': 15524, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-typed-01/check-result.json', 'sha256': 'cfb690034025ad99470dad89ab537952955ddb4b14b1ed3675bf8181dfcfad63'}, {'bytes': 12509, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-compiler-01/check-result.json', 'sha256': '43276551bd5488e8575cd07a810c5156f6178d75b4924a0bcf677906d2e520df'}, {'bytes': 24686, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-preservation-01/check-result.json', 'sha256': '803036eae98f65a373574b00b3434edcdbcf43847be65e7c7e799e0c99dee0b8'}, {'bytes': 13707, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-semantics-01/check-result.json', 'sha256': '8650075e9f209aa2d61d284d043b51200a866611703ad40739ce29af3f05d62b'}, {'bytes': 24254, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/language_file_helpers_01.py', 'sha256': '12ccff684135c86e737213dec2f4f9883a2d02a004dc1964677584eb724006ec'}, {'bytes': 739419, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/preparation/lean-container-preservation-01-request.json', 'sha256': 'c45b8eaaca80aa52eedce09b3e3552463088e77759b5f797c8641249edc5d387'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/qualified-review-01.json', 'bytes': 10974, 'sha256': '37df4b286e44246faf1f45cbdb07edf167b7d5d120b4b162ce0ea4bf588af39a'}, {'bytes': 48095, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-candidate-20261005-02/source-v2/objective_prefix_compiler.py', 'sha256': 'd4aec9ef8f239314c48ca2d2e0a70495be6d2df4c79329e338d9a96c26ee196c'}, {'bytes': 8046, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/ObjectiveContainerPrefixGenerated.lean', 'sha256': '31bc24c08296302aa15c8067df2cae7e7aa9f3d3b28b63145d661f82f1d3ccbb'}, {'bytes': 6209, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/ObjectiveOriginalPrefix.lean', 'sha256': 'd096036379e3109bab822cd4565bb522785dbd411b8d2fbb32787c9ab2a1ffda'}, {'bytes': 10097, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/emission-receipt.json', 'sha256': '8f688af528ea08b85b1dde9d7d35f685d1421ee9de3547817221ccc0800e6f7b'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01/module-map-01.json', 'bytes': 2337, 'sha256': '18ec8bef9b05a4d1e5d5c09444c5d2feb80ba3ede1a63cc875cd560474714e7d'}, {'bytes': 25170, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-source-plan-20261005-01/source-bindings.json', 'sha256': 'd6cb9f35169351848198d3919a7e794cee89429b07a2879ea680cb8511bfa8b8'}, {'bytes': 43818, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-decoder-candidate-20261006-01/source-v1/objective_prefix_decoder.py', 'sha256': '4939b0257334dabe239085946c8bc1a5706805df2b39f2f8108ea05ccf965965'}, {'bytes': 2426, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-host-result-20261005-01/materialization-receipt.json', 'sha256': 'e846d7ab984a14e1d279965364360e9e8f72ab1ab0408ddff66cfefe09440430'}, {'bytes': 13910, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-host-result-20261005-01/objective-prefix-draft.json', 'sha256': '4a7067a4797891740734fa7eae9ad46c02bc3410a4d4fff73ba43445a5a4ae17'}, {'bytes': 10016048, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-projections-candidate-20261006-02/preparation/lean-objective-prefix-projections-02-producer/environment-manifest.json', 'sha256': 'b3071501a40a55cb1dc6ec547f2573090d382403e1887ef9f8db4ad74c244350'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01/candidate-role-pins-01.json', 'bytes': 1814, 'sha256': 'cec56b5da6a1caa947a11537ace44cfa3a4564032e1533cc5d0b79565f983e02'}]
PRIOR_IMPORTS=[{'check_result': {'bytes': 14071, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-source-01/check-result.json', 'sha256': 'ca7ed3da92fbae947f595bfde1a8eb1025bc9758ebdd58eaf11210b2d125c0bf'}, 'mode': 'lean-container-source-01'}, {'check_result': {'bytes': 15524, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-typed-01/check-result.json', 'sha256': 'cfb690034025ad99470dad89ab537952955ddb4b14b1ed3675bf8181dfcfad63'}, 'mode': 'lean-container-typed-01'}, {'check_result': {'bytes': 13707, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-semantics-01/check-result.json', 'sha256': '8650075e9f209aa2d61d284d043b51200a866611703ad40739ce29af3f05d62b'}, 'mode': 'lean-container-semantics-01'}, {'check_result': {'bytes': 12509, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-compiler-01/check-result.json', 'sha256': '43276551bd5488e8575cd07a810c5156f6178d75b4924a0bcf677906d2e520df'}, 'mode': 'lean-container-compiler-01'}, {'check_result': {'bytes': 24686, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-preservation-01/check-result.json', 'sha256': '803036eae98f65a373574b00b3434edcdbcf43847be65e7c7e799e0c99dee0b8'}, 'mode': 'lean-container-preservation-01'}]
SOURCE_GATE={'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-source-review-20261006-01/review-receipt-01.json', 'bytes': 53525, 'sha256': 'e2bd9c412ca4545a68a85ebe33560522ce53ce7932f9c7f840bca1137f0ae7a6'}
STRICT_GUARD_COUNT=2945
NATIVE_LIMITS={'wall_seconds':20,'cpu_seconds':20,'output_bytes':65536,'workspace_bytes':16777216}
ROOT_LEASE={'cpu_slots':1,'memory_mb':2048,'child_process_slots':4}
PRESSURE={'memory_percent':2.0,'cpu_percent':50.0,'io_percent':10.0}
AUTHORITY={k:False for k in ('proof_authority','execution_authority','completion_authority','planner_activation')}


def _parent():
    p=Path(P2_PIN['path'])
    if p.resolve(strict=True)!=p or p.is_symlink():raise ValueError('canonical immutable P2 reader required')
    with p.open('rb') as stream:raw=stream.read(P2_PIN['bytes']+1)
    if len(raw)!=P2_PIN['bytes'] or hashlib.sha256(raw).hexdigest()!=P2_PIN['sha256']:
        raise ValueError('exact independently reviewed P2 helper differs')
    ns={'__file__':str(p),'__name__':'held_q3_parent_language_file_readers'}
    exec(compile(raw,str(p),'exec'),ns)
    ns['exact'](P2_PIN)
    gate=ns['document'](P2_TOOLING_GATE)
    ns['need'](gate['status']=='passed_source_only' and gate['findings']==[]
        and P2_PIN in gate['reviewed_sources'] and gate['reviewed_modules']==ns['MODULES']
        and all(gate[k] is False for k in AUTHORITY),'exact P2 source/tooling gate required')
    return ns


P2=_parent()
need,pin,exact,fixed,parse,document,write,read_pin,verify_held=(P2[k] for k in
    ('need','pin','exact','fixed','parse','document','write','read_pin','verify_held'))
BASE_PROFILE=P2['BASE_PROFILE']


def module(mode):
    need(type(mode) is str and mode in MODULES,'only two exact frozen q3 modes admitted')
    return MODULES[mode]


def source_gate(mode):
    selected=module(mode)
    need(bool(SOURCE_GATE) and STRICT_GUARD_COUNT>2806,'actual combined source gate and denominator not frozen')
    gate=document(SOURCE_GATE)
    need(gate['status']=='passed_source_only' and gate['findings']==[]
        and gate['candidate_pins']==CORE_PINS and gate['reviewed_modules']==MODULES
        and gate['candidate_compiled'] is False and gate['actual_new_qualified_queries']==0
        and all(gate[k] is False for k in AUTHORITY),'exact combined two-mode independent source gate required')
    for row in CORE_PINS.values():exact(row)
    need(selected['source'] in CORE_PINS.values(),'selected source absent from reviewed actual whole bodies')
    return gate


def seal_census(row):
    return P2['seal_census'](row)


def complete_guard_union():
    # Recompute P2's entire frozen cohort, rather than copying a caller list.
    parent_rows,unused=P2['complete_guard_union']()
    need(len(parent_rows)==P2['STRICT_GUARD_COUNT']==2806,'exact complete P2 cohort required')
    inherited=document(PRIOR_REQUEST)
    P2['validate_guard_union'](inherited)
    rows={row['path']:row for row in parent_rows}
    qualified=seal_census(PRIOR_SEAL)
    source=seal_census(P2_SOURCE_SEAL)
    host=seal_census(HOST_SEAL)
    review=document(P2_QUALIFIED_REVIEW)
    need(qualified['scope_root']==str(ROOT.with_name('ranker-objective-container-language-qualification-20261006-02'))
        and qualified['regular_file_count']==110 and qualified['regular_file_bytes']==38148950
        and qualified['qualified_native_checks']==3 and qualified['qualified_theorem_queries']==8
        and qualified['review']==P2_QUALIFIED_REVIEW
        and review['status']=='passed_native_scoped' and review['new_qualified_queries']==8
        and review['qualified_query_count_including_reuse']==10
        and review['qualified_staged_imports']==PRIOR_IMPORTS
        and source['regular_file_count']==7 and source['regular_file_bytes']==50753
        and host['regular_file_count']==4 and host['regular_file_bytes']==33792
        and host['qualified_native_checks']==host['qualified_theorem_queries']==0
        and all(qualified[k] is source[k] is host[k] is review[k] is False for k in AUTHORITY),
        'accepted mixed-root parent/source and host-only complete sealed populations required')
    additions=[*qualified['files'],PRIOR_SEAL,*source['files'],P2_SOURCE_SEAL,
        *host['files'],HOST_SEAL,P2_PIN,P2_TOOLING_GATE,PRIOR_REQUEST,P2_QUALIFIED_REVIEW,
        *CONTEXT_PINS,*CORE_PINS.values()]
    need(bool(SOURCE_GATE),'actual q3 source gate not frozen')
    additions.append(SOURCE_GATE)
    for row in additions:
        need(row['path'] not in rows or rows[row['path']]==row,'overlapping whole historical descriptor differs')
        exact(row);rows[row['path']]=row
    need(len(rows)==STRICT_GUARD_COUNT,'exact additive q3 sealed/context/source denominator differs')
    return [rows[p] for p in sorted(rows)],inherited


def validate_guard_union(request):
    rows,inherited=complete_guard_union()
    need(request['strict_old_inputs']==rows and request['strict_guard_count']==STRICT_GUARD_COUNT
        and request['protected_live_sources']==inherited['protected_live_sources']
        and request['original_checkout_guards']==inherited['original_checkout_guards']
        and request['prior_language_context_request']==PRIOR_REQUEST
        and request['prior_language_context_seal']==PRIOR_SEAL,
        'exact complete sealed P2 plus q3 whole source/host cohort required')


def qualified_module(name,profile,check_row=None):
    return P2['qualified_module'](name,profile,check_row)


def import_extension(base,imports):
    # Both new modes import all five accepted parent modules, never each other.
    need(imports==PRIOR_IMPORTS,'only exact five genuine mixed-root parent imports permitted')
    extended,joined=P2['import_extension'](base,imports)
    need([row['module'] for row in joined]==['ObjectiveContainerSource','ObjectiveContainerTyped',
        'ObjectiveContainerSemantics','ObjectiveContainerCompiler','ObjectiveContainerPreservation'],
        'complete parent import module order differs')
    return extended,joined
