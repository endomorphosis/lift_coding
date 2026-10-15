"""Fresh source-model batches; unexecuted until source and tooling gates.

The parent stays immutable. Two selected new modes admit only the fixed five
language imports plus the genuine generated prefix, then genuine scalar lift
for the parts stage. No target, prover, training or metadata callback here.
"""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
WORKSPACE=ROOT.parents[2]
Q5=ROOT.with_name('ranker-objective-ir-candidate-20261005-01')
P3_PIN={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01/language_file_helpers_01.py', 'bytes': 23954, 'sha256': '02f2acef24a0ed3f36fd31429e94de418c5f1e43bb6db77c8f23c38e400c4483'}
P3_TOOLING_GATE={'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-tooling-source-review-20261006-01/review-receipt-01.json', 'bytes': 53604, 'sha256': '33c9ba605e61ebf103d576154f7a6d41cb984caf1c25857130b18f7b1a62f290'}
PRIOR_REQUEST={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01/preparation/lean-container-evaluation-bridge-01-request.json', 'bytes': 777632, 'sha256': 'c436de8196fa522c79f81a473b0321af5afc6f107e7bb1a94736b425dadb9181'}
PRIOR_SEAL={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01/file-only-seal-01.json', 'bytes': 18926, 'sha256': '299db7957707fd44662a7c8f9de1fd0469bfe8d51240a567bd623f6538c89105'}
P3_REVIEW={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01/qualified-review-01.json', 'bytes': 16036, 'sha256': 'f2af908fa47b2b9da6c8f50a82b4949e42d3826ccf5a9fbbb0e7584c9d01a2cc'}
MODULES={'lean-original-prefix-parts-01': {'direct_imports': ['ObjectiveSourceScalarLift'], 'module': 'ObjectiveOriginalPrefixParts', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01', 'lean-source-scalar-lift-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-qualification-20261006-01', 'queries': ['RankerObjectiveOriginalPrefixParts.emitted_prefix_decomposition', 'RankerObjectiveOriginalPrefixParts.emitted_loss_body_scalar_injection', 'RankerObjectiveOriginalPrefixParts.emitted_factor_body_scalar_injection', 'RankerObjectiveOriginalPrefixParts.emitted_loss_body_success', 'RankerObjectiveOriginalPrefixParts.emitted_factor_body_success'], 'source': {'bytes': 8913, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-candidate-20261006-02/math/ObjectiveOriginalPrefixParts.lean', 'sha256': 'a8921ca1035c71f5aa22066777084f27a85dc5f71e8200469f7c9e61b322cf08'}}, 'lean-source-scalar-lift-01': {'direct_imports': ['ObjectiveContainerPrefixGenerated'], 'module': 'ObjectiveSourceScalarLift', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-qualification-20261006-01', 'queries': ['RankerObjectiveSourceScalarLift.eval_lift_scalar_source', 'RankerObjectiveSourceScalarLift.named_stable_loss_success', 'RankerObjectiveSourceScalarLift.named_stable_factor_success'], 'source': {'bytes': 5719, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-candidate-20261006-02/math/ObjectiveSourceScalarLift.lean', 'sha256': '3b475501abcee0f087d3c21ba3365bca31479f860bafec19505ac63341c065fe'}}}
DEPENDENCY_MODULES={'lean-container-generated-prefix-01': {'direct_imports': ['ObjectiveContainerPreservation'], 'module': 'ObjectiveContainerPrefixGenerated', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01', 'queries': ['GeneratedOriginalObjectiveContainerPrefix.emitted_prefix_compiles', 'GeneratedOriginalObjectiveContainerPrefix.emitted_prefix_preserves'], 'source': {'bytes': 8046, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/ObjectiveContainerPrefixGenerated.lean', 'sha256': '31bc24c08296302aa15c8067df2cae7e7aa9f3d3b28b63145d661f82f1d3ccbb'}}, 'lean-source-scalar-lift-01': {'direct_imports': ['ObjectiveContainerPrefixGenerated'], 'module': 'ObjectiveSourceScalarLift', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-qualification-20261006-01', 'queries': ['RankerObjectiveSourceScalarLift.eval_lift_scalar_source', 'RankerObjectiveSourceScalarLift.named_stable_loss_success', 'RankerObjectiveSourceScalarLift.named_stable_factor_success'], 'source': {'bytes': 5719, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-candidate-20261006-02/math/ObjectiveSourceScalarLift.lean', 'sha256': '3b475501abcee0f087d3c21ba3365bca31479f860bafec19505ac63341c065fe'}}}
GEN_CHECK={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01/evidence/lean-container-generated-prefix-01/check-result.json', 'bytes': 16026, 'sha256': '2194c2152ffaaffb94099dd1a4306c1c08fec22fce1077caef22196ee8441c3e'}
CORE_PINS={'candidate-interface.json': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-candidate-20261006-02/candidate-interface.json', 'bytes': 5077, 'sha256': '9308b26a6131d9696267d87283b233c927496ee248f0a34324dc79951027c73b'}, 'math/ObjectiveOriginalPrefixParts.lean': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-candidate-20261006-02/math/ObjectiveOriginalPrefixParts.lean', 'bytes': 8913, 'sha256': 'a8921ca1035c71f5aa22066777084f27a85dc5f71e8200469f7c9e61b322cf08'}, 'math/ObjectiveSourceScalarLift.lean': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-candidate-20261006-02/math/ObjectiveSourceScalarLift.lean', 'bytes': 5719, 'sha256': '3b475501abcee0f087d3c21ba3365bca31479f860bafec19505ac63341c065fe'}, 'obligations.json': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-candidate-20261006-02/obligations.json', 'bytes': 2519, 'sha256': '3739ba926574711a3c6657db7c087af6f34ce9030b480f553d6856fc70a4fc08'}}
CONTEXT_PINS=[{'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-input-review-20261006-01/evaluation-bridge-review-receipt-01.json', 'bytes': 2268, 'sha256': '06d5f2a055a905e31b2279390546b0310fc4af103fd75c2335fedd790a56113b'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-input-review-20261006-01/generated-prefix-review-receipt-01.json', 'bytes': 2264, 'sha256': '4e65a345d21778363b44a083f1de761d81bbceb74861c93c83dcf1c7222683b2'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-candidate-20261006-01/candidate-interface.json', 'bytes': 4007, 'sha256': 'eb847bcc0da81014dd1a844e07b5efed3b6fc54620bb5c0612b6710a7f73f10f'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-candidate-20261006-01/math/ObjectiveOriginalPrefixParts.lean', 'bytes': 10237, 'sha256': '4dc3101b6fc1d9687651959051fa8e5d4010f05f1fe61a25c24598280b8ddd85'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-candidate-20261006-01/math/ObjectiveSourceScalarLift.lean', 'bytes': 5719, 'sha256': '3b475501abcee0f087d3c21ba3365bca31479f860bafec19505ac63341c065fe'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-candidate-20261006-01/obligations.json', 'bytes': 2226, 'sha256': '0deefe6e6848dc9f621876a4a1a53e49ad2da84464494695057970b4ed136c39'}, {'bytes': 41803, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-evaluation-plan-20261006-01/plan-01.json', 'sha256': '3028651403bc7b89ce63ebd32ea43bc6170251dbd095974f44a0ec4069a4c561'}, {'bytes': 43203, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-evaluation-plan-20261006-01/plan-02.json', 'sha256': '6de56ede6ea3420ebdb87ed45911c1437c757167c3e7dfc488ad8b95f2b62bb4'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-evaluation-plan-20261006-01/plan-03.json', 'bytes': 48270, 'sha256': '4a4d8d9c54ff4644f6b2912f65fefdb8c58e746e293959789a2c267953c0a054'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-source-model-plan-readback-20261006-01/readback-01.json', 'bytes': 13323, 'sha256': 'e858ec44bd9feb76c215821c0f1ad385945d7f741c4725b0bd92e43c6bf236a1'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-source-model-qualification-blueprint-20261006-01/blueprint-01.json', 'bytes': 8273, 'sha256': '594bd6bf2786e455e199bfe95b02ff2d8bf13e853390eb547453d2b212112106'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-qualification-20261006-01/module-map-01.json', 'bytes': 1978, 'sha256': '058aa304792b9897124dfd78411834d23ddd71bd3e0906a97dc3948463b065df'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-qualification-20261006-01/module-map-authoring-contract-01.json', 'bytes': 2350, 'sha256': '7048b0016b196def0666f78c030b7905a66880fe1676722fec1e264b0068041b'}, {'bytes': 16391, 'path': '/home/barberb/lift_coding/artifacts/codebase_ir_terminal_bench/terminal-codebase-ir-intent-corpus-head-20261004-01/source/benchmarks/agent_supervisor/container_coding/terminal_codebase_intent_ranker_training.py', 'sha256': '3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a'}, {'bytes': 25170, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-source-plan-20261005-01/source-bindings.json', 'sha256': 'd6cb9f35169351848198d3919a7e794cee89429b07a2879ea680cb8511bfa8b8'}, {'bytes': 13910, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-host-result-20261005-01/objective-prefix-draft.json', 'sha256': '4a7067a4797891740734fa7eae9ad46c02bc3410a4d4fff73ba43445a5a4ae17'}, {'bytes': 14989, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-emitter-candidate-20261006-01/source-v1/objective_container_emitter.py', 'sha256': 'f6a97381502153a336c076093a59504945b8797283ddaa2830826c6d04000a32'}, {'bytes': 7680, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-eval-bridge-candidate-20261006-01/math/ObjectiveContainerEvaluationBridge.lean', 'sha256': 'b39d3c585c5cbbe9da30f932000ce2428d2cc754849e1c9dbd43b6912c3a4587'}, {'bytes': 15602, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-candidate-20261006-02/math/ObjectiveContainerPreservation.lean', 'sha256': 'd2cd7d4fe847942e616328bb4392de027d5f48d678cbe8bc4c060213b7db43c4'}, {'bytes': 11695, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-candidate-20261006-02/math/ObjectiveContainerSemantics.lean', 'sha256': '23bf7349c698832ad088adc68b41913a88affafff235008b38ef6688079b5ec8'}, {'bytes': 11167, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01/qualified-review-01.json', 'sha256': '590163443db860ac03bc2d3fde0f07ac44626e8b6e7cc57a3d6c770c4da87f00'}, {'bytes': 36092, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/qualified-review-01.json', 'sha256': '2c98df30a37fecffff99340d447dcf548c6c244a53223cbed39c914bb0e9238c'}, {'bytes': 22341, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-convergence-20261005-01/qualified-review-01.json', 'sha256': 'eebf40b5de2822faef1293a62578da208b582131e44c8a1f3e0d060071b6d0e7'}, {'bytes': 22527, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01/evidence/lean-objective-scalar-01/check-result.json', 'sha256': '57ac502ebc37df08ae73b7fec69280b2dcb1a2453895ab573869d826d613bd5e'}, {'bytes': 13094, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01/preparation/lean-objective-scalar-01-producer/ObjectiveScalarIR.lean', 'sha256': 'ae4d1ebec782c2395cc9d2585f40296988fc2ec10cfdab3f946258251c527d71'}, {'bytes': 1881720, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01/evidence/lean-objective-scalar-01/lean/ObjectiveScalarIR.olean', 'sha256': '4e8a30cb3830ee6f1c689d827db695ebad8555bf1c6ac624fd320f3c6c80f134'}, {'bytes': 13074, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01/evidence/lean-objective-generated-01/check-result.json', 'sha256': '4bcc8424739067b6e31382f594bd0c17e7e3e800d117bd08b2e38de302177041'}, {'bytes': 4315, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01/preparation/lean-objective-generated-01-producer/GeneratedObjectiveScalarLeaves.lean', 'sha256': 'c6ba9dbc3a9ed056d04d004692180efd76db4e8d379681d7c8ff2edb1da8e919'}, {'bytes': 73712, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01/evidence/lean-objective-generated-01/lean/GeneratedObjectiveScalarLeaves.olean', 'sha256': '867a5617be43f395e05ef1cec1c5027b298f800c0969b625dabc0f2f74224f9a'}, {'bytes': 9684, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/evidence/lean-softplus-02/check-result.json', 'sha256': 'd35a196c44aa8103e93e30bb3cc0de4ee410174648ac3903b7a8185f5636e0dd'}, {'bytes': 4839, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/preparation/lean-softplus-02-producer/ScalarSoftplus.lean', 'sha256': 'e32f5a68f4365fa60a2321a0cb7f6076e998c7841547255f90124a4875a36379'}, {'bytes': 183736, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/evidence/lean-softplus-02/lean/ScalarSoftplus.olean', 'sha256': 'f82e427e3760daaf433894b1e3c14db9efad025f795d2602ac7b95bca0018c58'}, {'bytes': 9601, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/evidence/lean-directional-02/check-result.json', 'sha256': '2c2f7f8c3abef38cd540eb2a2ab07a34943c5bc73a19e67e7da8797055fddd66'}, {'bytes': 7672, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/preparation/lean-directional-02-producer/DirectionalObjective.lean', 'sha256': '94720052863a636db021de6f22eb903df0b4d0c6ead334bd853191920e0cfc6c'}, {'bytes': 199832, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/evidence/lean-directional-02/lean/DirectionalObjective.olean', 'sha256': '56e8b30f864fdfe1d6c8efecc24edab80bb2ce68ff3c172414de0330f2fb9218'}, {'bytes': 8657, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/evidence/lean-gradient-01/check-result.json', 'sha256': '315826ae63c23849542259cd613f70f7f2fa2a0e0b57a57a629880bf9ece1920'}, {'bytes': 3402, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/preparation/lean-gradient-01-producer/RealGradient.lean', 'sha256': '9ece52690c173349ba2cfbb345c1f5d4169365da55fc6f527fa16f41c8d9bdc7'}, {'bytes': 120984, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/evidence/lean-gradient-01/lean/RealGradient.olean', 'sha256': '38c589dcd8587e0d781ae6993fbbba02c8c60ed0d9304d06362732b6e21d4029'}, {'bytes': 9253, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-convergence-20261005-01/evidence/lean-stable-factor-01/check-result.json', 'sha256': '25adf30103c3d7455df5c7fff9eedf6b9e4ceb1fbd5263e919247ed18588e0f5'}, {'bytes': 1767, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-convergence-20261005-01/preparation/lean-stable-factor-01-producer/RealStableFactor.lean', 'sha256': 'b0a6750c1264fa4024b1f033305e60979d45775eb31fc182914b7d3caf74154d'}, {'bytes': 82952, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-convergence-20261005-01/evidence/lean-stable-factor-01/lean/RealStableFactor.olean', 'sha256': 'b1f3128c80daf4015fe1f2f5e61647f50d047f755d908a07df5e5581f1410477'}, {'bytes': 9638, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/evidence/lean-original-profile-02/check-result.json', 'sha256': 'd2d8e94548fb71b2f09f39770c856c2ce2ef17fa769000d875ac6b5b67e806ec'}, {'bytes': 6088, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/preparation/lean-original-profile-02-producer/OriginalRealProfile.lean', 'sha256': '52eecc62595596545013a7ec4f2cfc70e4b4c2b9f1607ff5db7237b46be3d196'}, {'bytes': 90680, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/evidence/lean-original-profile-02/lean/OriginalRealProfile.olean', 'sha256': 'bb4cb92353477546673f3cbca4029c654a4e358bd2994e29182982488249aa54'}, {'bytes': 8924, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/evidence/lean-original-descent-01/check-result.json', 'sha256': '658b3650b7ece388ee2df2fb1ced2a90ccfffb33170018be66e0581ab70d3629'}, {'bytes': 1469, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/preparation/lean-original-descent-01-producer/OriginalRealDescent.lean', 'sha256': '0acf2608c7d7cb5f3628a30f39f0f9a0c0990a29d831ec9266e970c6d1766526'}, {'bytes': 30480, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01/evidence/lean-original-descent-01/lean/OriginalRealDescent.olean', 'sha256': '437f4a0cd82654ec970888a0fefc20d54b60202f3be5f5f95b35a9de18770618'}, {'bytes': 10623, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-convergence-20261005-01/evidence/lean-original-convergence-02/check-result.json', 'sha256': 'c26b9781daa03872d6ec6b42111822357a9f43ee703b06f30e8910b6731f5dd1'}, {'bytes': 4827, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-convergence-20261005-01/preparation/lean-original-convergence-02-producer/OriginalRealConvergenceV2.lean', 'sha256': 'c423d7114996e9f6d1785684b291ca09fde589ae8006d846cdbcd6feb8405469'}, {'bytes': 78128, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-convergence-20261005-01/evidence/lean-original-convergence-02/lean/OriginalRealConvergenceV2.olean', 'sha256': 'c6a5bc6bcfa5cbe04f543eeafe6c8abaa6541a230602dfad89354493c287c2aa'}, {'bytes': 19104, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-semantics-20261005-01/evidence/lean-typed-scalar-02/check-result.json', 'sha256': '1e11d2917e3087dc2e231bdf6b329416518eb74542d6e83074d000ee7f8a0e23'}, {'bytes': 11197, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-semantics-20261005-01/preparation/lean-typed-scalar-02-producer/TypedNumericSlice.lean', 'sha256': 'bd65d5d0c5ba08dfe4523db151ac5e6075d5abb2f54b26e8007b0926b82f335d'}, {'bytes': 939920, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-semantics-20261005-01/evidence/lean-typed-scalar-02/lean/TypedNumericSlice.olean', 'sha256': 'd666b11adfa7d878e2745c2ebdec1c7caf523bd82e0d7a702e99741376209465'}, {'bytes': 8046, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/ObjectiveContainerPrefixGenerated.lean', 'sha256': '31bc24c08296302aa15c8067df2cae7e7aa9f3d3b28b63145d661f82f1d3ccbb'}, {'bytes': 6209, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/ObjectiveOriginalPrefix.lean', 'sha256': 'd096036379e3109bab822cd4565bb522785dbd411b8d2fbb32787c9ab2a1ffda'}, {'bytes': 10097, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/emission-receipt.json', 'sha256': '8f688af528ea08b85b1dde9d7d35f685d1421ee9de3547817221ccc0800e6f7b'}, {'bytes': 9440, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/materialization-receipt.json', 'sha256': '3620933baacb645abcc1055cf2369a38031fb02f958ec6d2cc3c6913783b3fe7'}, {'bytes': 1952, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/file-only-seal-01.json', 'sha256': '3d58dbad41bae68799869d8416dcb8a96d3511cee20c88d41acd132d51451981'}, {'bytes': 10974, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/qualified-review-01.json', 'sha256': '37df4b286e44246faf1f45cbdb07edf167b7d5d120b4b162ce0ea4bf588af39a'}, {'bytes': 31541, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/file-only-seal-01.json', 'sha256': 'f928432ec1bc0053dcea57e9e90ff578eeefb4d269cd747e54dc8c5ae503b338'}, {'bytes': 6382, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-source-review-20261006-01/evaluation-bridge-review-receipt-01.json', 'sha256': '54c1e8d7843768b50d7d440ab7626526335fa699ee2099cd6c50be8635a2f223'}]
PRIOR_IMPORTS=[{'check_result': {'bytes': 14071, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-source-01/check-result.json', 'sha256': 'ca7ed3da92fbae947f595bfde1a8eb1025bc9758ebdd58eaf11210b2d125c0bf'}, 'mode': 'lean-container-source-01'}, {'check_result': {'bytes': 15524, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-typed-01/check-result.json', 'sha256': 'cfb690034025ad99470dad89ab537952955ddb4b14b1ed3675bf8181dfcfad63'}, 'mode': 'lean-container-typed-01'}, {'check_result': {'bytes': 13707, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-semantics-01/check-result.json', 'sha256': '8650075e9f209aa2d61d284d043b51200a866611703ad40739ce29af3f05d62b'}, 'mode': 'lean-container-semantics-01'}, {'check_result': {'bytes': 12509, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-compiler-01/check-result.json', 'sha256': '43276551bd5488e8575cd07a810c5156f6178d75b4924a0bcf677906d2e520df'}, 'mode': 'lean-container-compiler-01'}, {'check_result': {'bytes': 24686, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-preservation-01/check-result.json', 'sha256': '803036eae98f65a373574b00b3434edcdbcf43847be65e7c7e799e0c99dee0b8'}, 'mode': 'lean-container-preservation-01'}]
SOURCE_GATE={'path': '/home/barberb/lift_coding/maintenance/ranker-objective-source-model-source-review-20261006-01/review-receipt-01.json', 'bytes': 11768, 'sha256': '304fc21c62b083853819c3dc0e02e0fe49c453d02c503cb9da3e957e93ed6563'}
STRICT_GUARD_COUNT=3027
NATIVE_LIMITS={'wall_seconds': 20, 'cpu_seconds': 20, 'output_bytes': 65536, 'workspace_bytes': 16777216}
ROOT_LEASE={'cpu_slots': 1, 'memory_mb': 2048, 'child_process_slots': 4}
PRESSURE={'memory_percent': 2.0, 'cpu_percent': 50.0, 'io_percent': 10.0}
AUTHORITY={k:False for k in ('proof_authority','execution_authority','completion_authority','planner_activation')}


def _parent():
    p=Path(P3_PIN['path'])
    if p.resolve(strict=True)!=p or p.is_symlink():raise ValueError('canonical reviewed parent required')
    with p.open('rb') as stream:raw=stream.read(P3_PIN['bytes']+1)
    if len(raw)!=P3_PIN['bytes'] or hashlib.sha256(raw).hexdigest()!=P3_PIN['sha256']:
        raise ValueError('immutable reviewed parent differs')
    ns={'__file__':str(p),'__name__':'held_source_model_parent_file_helpers'}
    exec(compile(raw,str(p),'exec'),ns)
    ns['exact'](P3_PIN);gate=ns['document'](P3_TOOLING_GATE)
    ns['need'](gate['status']=='passed_source_only' and gate['findings']==[]
        and P3_PIN in gate['reviewed_sources'] and gate['reviewed_modules']==ns['MODULES']
        and all(gate[k] is False for k in AUTHORITY),'exact reviewed parent source and tooling required')
    return ns

P3=_parent()
need,pin,exact,fixed,parse,document,write,read_pin,verify_held=(P3[k] for k in
    ('need','pin','exact','fixed','parse','document','write','read_pin','verify_held'))
BASE_PROFILE=P3['BASE_PROFILE']

def module(mode):
    need(type(mode) is str and mode in MODULES,'only two selected frozen source-model modes admitted')
    return MODULES[mode]

def dependency_module(mode):
    need(type(mode) is str and mode in DEPENDENCY_MODULES,'only fixed generated and scalar dependencies admitted')
    return DEPENDENCY_MODULES[mode]

def source_gate(mode):
    selected=module(mode)
    need(bool(SOURCE_GATE) and STRICT_GUARD_COUNT>2945,'actual source gate and exact denominator not frozen')
    gate=document(SOURCE_GATE)
    need(gate['status']=='passed_source_only' and gate['findings']==[]
        and gate['candidate_pins']==CORE_PINS and gate['reviewed_modules']==MODULES
        and gate['candidate_compiled'] is False and gate['actual_new_qualified_queries']==0
        and all(gate[k] is False for k in AUTHORITY),'exact four-file independent source-model gate required')
    for row in CORE_PINS.values():exact(row)
    need(selected['source'] in CORE_PINS.values(),'selected source absent from candidate source gate')
    return gate

def seal_census(row):
    return P3['seal_census'](row)

def complete_guard_union():
    parent_rows,unused=P3['complete_guard_union']()
    need(len(parent_rows)==P3['STRICT_GUARD_COUNT']==2945,'exact complete parent cohort required')
    inherited=document(PRIOR_REQUEST);P3['validate_guard_union'](inherited)
    seal=seal_census(PRIOR_SEAL);review=document(P3_REVIEW)
    need(seal['regular_file_count']==64 and seal['regular_file_bytes']==23928138
        and seal['qualified_native_checks']==2 and seal['qualified_theorem_queries']==11
        and seal['review']==P3_REVIEW and review['status']=='passed_native_scoped'
        and review['new_qualified_queries']==11 and review['total_language_and_prefix_qualified_queries']==21
        and review['actual_emitted_prefix_compiler_acceptance_proved'] is True
        and review['actual_emitted_prefix_exact_Real_preservation_proved'] is True
        and review['qualified_parent_imports']==PRIOR_IMPORTS
        and next(r for r in review['qualified_new_imports'] if r['mode']=='lean-container-generated-prefix-01')['check_result']==GEN_CHECK
        and all(seal[k] is review[k] is False for k in AUTHORITY),
        'genuine accepted generated prefix and complete sealed parent populations required')
    need(bool(SOURCE_GATE),'actual source-model gate not frozen')
    rows={r['path']:r for r in parent_rows}
    additions=[*seal['files'],PRIOR_SEAL,P3_PIN,P3_TOOLING_GATE,PRIOR_REQUEST,P3_REVIEW,
        *CONTEXT_PINS,*CORE_PINS.values(),SOURCE_GATE]
    for row in additions:
        need(row['path'] not in rows or rows[row['path']]==row,'overlapping guarded body differs')
        exact(row);rows[row['path']]=row
    need(len(rows)==STRICT_GUARD_COUNT,'exact additive source-model guard denominator differs')
    return [rows[p] for p in sorted(rows)],inherited

def validate_guard_union(request):
    rows,inherited=complete_guard_union()
    need(request['strict_old_inputs']==rows and request['strict_guard_count']==STRICT_GUARD_COUNT
        and request['protected_live_sources']==inherited['protected_live_sources']
        and request['original_checkout_guards']==inherited['original_checkout_guards']
        and request['prior_language_context_request']==PRIOR_REQUEST
        and request['prior_language_context_seal']==PRIOR_SEAL,'exact sealed parent and source-model guard join required')

def qualified_module(name,profile,check_row=None):
    return P3['qualified_module'](name,profile,check_row)

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
        need(stage_root in (ROOT,ROOT.with_name('ranker-objective-container-prefix-qualification-20261006-01')),
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

def import_extension(base,imports):
    need(type(imports) is list and len(imports) in (6,7) and imports[:5]==PRIOR_IMPORTS,
         'fixed five parent imports plus finite dependency prefix required')
    extras=imports[5:]
    need([r['mode'] for r in extras]==['lean-container-generated-prefix-01']+
        (['lean-source-scalar-lift-01'] if len(extras)==2 else [])
        and extras[0]['check_result']==GEN_CHECK,'exact genuine generated/scalar dependency order required')
    extended,parent=P3['import_extension'](base,imports[:5])
    extended,new=_append_imports(extended,extras)
    extended["staged_qualified_imports"]=parent+new
    return extended,parent+new
