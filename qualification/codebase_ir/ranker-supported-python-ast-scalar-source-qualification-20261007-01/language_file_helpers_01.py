"""SOURCE-ONLY: standalone scalar Python AST qualification file readers.

No historical helper executes or has its globals patched. Historical inputs
are preserved by an independent reviewed closure replay; actual current and
imported native modules still pass owned admission and whole object checks.
Disabled until all exact source/manifest/gate/module pins are frozen.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT=Path(__file__).resolve().parent
WORKSPACE=ROOT.parents[2]
Q5=ROOT.with_name('ranker-objective-ir-candidate-20261005-01')
HELD={}
FROZEN = {'REPLAY_SOURCE': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-qualification-checkpoint-replay-candidate-20261006-02/checkpoint_replay.py', 'bytes': 16861, 'sha256': 'bddc7677eceb8db478fb32183ba9ef47520f6fb6156c8b525ab5ddd246ffa152'}, 'CHECKPOINT': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-qualification-checkpoint-replay-candidate-20261006-02/history-checkpoint-02.json', 'bytes': 1213138, 'sha256': '6c81310108cc3594a96fcf46070c2eceae2441311f83dfc74a069e90cf02bc99'}, 'REPLAY_GATE': {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-checkpoint-replay-source-review-20261006-02/review-receipt-01.json', 'bytes': 4886, 'sha256': 'ffec7170766fe5ad2026dc2fcb746877878e3f516bc268109d76080b57294160'}, 'MODULE_MAP': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-scalar-source-qualification-20261007-01/module-map-01.json', 'bytes': 1096, 'sha256': 'a8d13cd082baba0ccb0cd6f2eafba01f673a4a9e05a3050a4fc4b3bfdd73d22c'}, 'CANDIDATE_PINS': {'candidate-interface.json': {'bytes': 2186, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-scalar-source-candidate-20261007-01/candidate-interface.json', 'sha256': '75e41bdbee11a91be89eea0d20ea245833c505b664af484864742e406bc8bf73'}, 'math/GeneratedPythonAstScalarSource.lean': {'bytes': 2027, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-scalar-source-candidate-20261007-01/math/GeneratedPythonAstScalarSource.lean', 'sha256': '02ed3582f6a19ee3962b92251dea05bc5ab11451417b831cf2cdd9fbc8749db7'}, 'obligations.json': {'bytes': 715, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-scalar-source-candidate-20261007-01/obligations.json', 'sha256': 'b939281d31f652843df0c7fdcf361c03c43a95cc8520265e89a5486652ec3dc4'}}, 'SOURCE_GATE': {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-scalar-source-math-source-review-20261007-01/review-receipt-01.json', 'bytes': 9242, 'sha256': '012b6cf05d98d20858c6b4af0df21491c3c78aa4348378690e4acda29aa22cd6'}, 'EXTRA_CONTEXT': [{'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-02/candidate-pins-01.json', 'bytes': 844, 'sha256': 'a81ba63d9ba461109bb679ec20e27516a0aa6ef149802cd4d9d8b012c2d7d63e'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-math-source-review-20261006-01/review-receipt-01.json', 'bytes': 8187, 'sha256': '320d464175c620bfb4c517918246b19c71a056248328bbe8980b8dda5e1e4924'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-tooling-source-review-20261006-01/review-receipt-01.json', 'bytes': 14414, 'sha256': 'de639814c184ccc3e492d00db035300fdf8fbcbf305a076abf6b4c4a2d8cde33'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-01/read_completed_01.py', 'bytes': 10087, 'sha256': 'c5e987c8d5971f52bd006811c24a45021ba395a53b4868b3a9eb9ddbde8be77b'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-01/lean-python-ast-subset-01-prepared-audit-01.json', 'bytes': 2205, 'sha256': '6506876039b313af58e77b1f484a705401fb037426dc509e3ac35844857b2300'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-01/lean-python-ast-semantics-01-prepared-audit-01.json', 'bytes': 2217, 'sha256': '001e13b65811b7cef8134fa977567816db2afac8a4b7a44da9ad097d258f0576'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-01/lean-python-ast-lowering-01-prepared-audit-01.json', 'bytes': 2213, 'sha256': 'b3644a7028e0b43a4adadebe914098fa5a620bf40858f3c522cd359fe1114267'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-01/lean-python-ast-preservation-01-prepared-audit-01.json', 'bytes': 2229, 'sha256': 'a371416f6527718e8ddbd8e67772c26275bcf3240ea26b3b84e3e053aeab0030'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-01/lean-python-ast-subset-01-completed-readback-01.json', 'bytes': 7469, 'sha256': 'c249dcd38f3b688614d1810a3036e851a64db0f7c42860a89055685ac89991ad'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-01/lean-python-ast-semantics-01-completed-readback-01.json', 'bytes': 6617, 'sha256': 'c8c52ee20fddfaa77d7d1b1ed89dd0ba579f240f2d1d0251ea72385e90eed90d'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-01/lean-python-ast-lowering-01-completed-readback-01.json', 'bytes': 6579, 'sha256': '1921c4ac3655132e0e4685c109309b5671f3ff76013bc7734726fa10b6b2c9eb'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-01/lean-python-ast-preservation-01-failed-preflight-readback-01.json', 'bytes': 4011, 'sha256': '5e80a45150c6036ac0a8ba99ea06425973d66b38192ce5b9900554c2d48d113a'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-checkpoint-replay-source-review-20261006-01/review-receipt-01.json', 'bytes': 3704, 'sha256': '1f8b7f58545d7c641df08404dbc7ebc1a07b936f80d48647157679c03863c691'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-checkpoint-replay-input-review-20261006-02/replay-readback-01.json', 'bytes': 1782, 'sha256': 'e4b8541138af2838f7fe59da7f8fd6f814de83b199ace9bf7745a5ad9ee01f48'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-replay-controls-readback-review-20261006-01/review-receipt-01.json', 'bytes': 28493, 'sha256': '28ff44621412d7e753add213895aa5057f1753d9c867f58093539c6db242d3a7'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-transport-source-review-20261006-01/review-receipt-01.json', 'bytes': 5581, 'sha256': '4e98ca6d333239feed2b5d2955d7a8c23e25eb933270299256df7a77be4b9661'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-transport-controls-source-review-20261006-02/review-receipt-01.json', 'bytes': 2891, 'sha256': 'cf787d2d98fcc19f88685f49d65132ca3adf4080ee689a912a826e227354e48e'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-transport-controls-source-review-20261006-03/review-receipt-01.json', 'bytes': 3711, 'sha256': 'ba0f796bef0f51077e6a5883cf78a20677a863015689d68e8f16c4e7fb74ab4e'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-03/candidate-pins-01.json', 'bytes': 844, 'sha256': 'afd9878e7853d66324fd64b6f52c56f7af2afa9bc818c770503cfe5f0632b7c6'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-math-source-review-20261006-02/review-receipt-01.json', 'bytes': 6822, 'sha256': '5f7cb7f95a8bb2dee4b9ab24eb88b0a455ede7cfbc48c07e5b3155a8aa6d430f'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-tooling-source-review-20261006-02/review-receipt-01.json', 'bytes': 18086, 'sha256': '11dde47dc19aef2a62f25453b35155cf0159ef0fe0358554d6381bee595632f4'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-02/read_completed_01.py', 'bytes': 10213, 'sha256': 'fa15de403454473a9b5cb29d49afe3eb6c2bb9c5b3eabcb86453ff8d96e0528a'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-02/lean-python-ast-preservation-01-prepared-audit-01.json', 'bytes': 2229, 'sha256': '1eecad0daecdd87d5e9359ce776d33beae41665eb349fb6dafdfdc5272983be6'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-02/lean-python-ast-preservation-01-failed-native-readback-01.json', 'bytes': 2832, 'sha256': '18fd62ab68cc56fed06d501a9c969f77d5dba88e7a3883b87b0e0a146561a12d'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-native-readback-review-20261006-01/review-receipt-01.json', 'bytes': 51765, 'sha256': '22a3b74aea0bb03b0238e81340a69d789eff1ab4ea51e17b72fa27c5ce84fa95'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-native-readback-review-20261006-02/review-receipt-01.json', 'bytes': 15231, 'sha256': '3277725535bf6b7910a0f00f6351a4cbf07bcc632133a4b098239d6374df3ed4'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-04/candidate-pins-01.json', 'bytes': 844, 'sha256': '61ac22ccdf7f4e9907fa5c9d094eb0e40165015ff6b7eec8fe2570ff9906ac23'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-math-source-review-20261006-03/review-receipt-01.json', 'bytes': 7716, 'sha256': 'b124d1db247595119e3cc3dd1ac47e1ea16f17c144d1ec40e81f4bce333f0d7f'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-tooling-source-review-20261006-03/review-receipt-01.json', 'bytes': 19821, 'sha256': 'c070287a6387a80c0b98173a92ed5e7da379e37341295662917b8cccb438ea16'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-03/read_completed_01.py', 'bytes': 10213, 'sha256': 'b78ef51ccfec759e484f6577d607c05fe129170a01a7b633a36f2e9561b6c118'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-03/lean-python-ast-preservation-01-prepared-audit-01.json', 'bytes': 2229, 'sha256': '0d8776fa9b4d9e7c48bbcf44e0841166a0030ac00099cd3a18c032bfe8a5e470'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-03/lean-python-ast-preservation-01-failed-native-readback-01.json', 'bytes': 2832, 'sha256': 'f0db57d903e0b3e8a007f60769725e20cc6938ee1af6ff2293971389cfe2cefd'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-native-readback-review-20261006-03/review-receipt-01.json', 'bytes': 16123, 'sha256': '132df22cf135e4016e9ac59b1a49691099e22e294bbcc7bf03d8412d20ec0c9b'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-math-source-review-20261006-04/review-receipt-01.json', 'bytes': 7820, 'sha256': '9a0be40fc729a9d4333efd4308b1442644f5834f1949fb8a8e8896e208bb76cf'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-tooling-source-review-20261006-04/review-receipt-01.json', 'bytes': 26210, 'sha256': 'e44ab387831dd3531781c8038c401e3cd4321966247c1c5647987457c4952308'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-04/lean-python-ast-preservation-01-prepared-audit-01.json', 'bytes': 2229, 'sha256': 'a5bcfc61c96b6943f04440d6ca4c4537934d9d8ec8649a24ce32844d0b4d0014'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-04/lean-python-ast-preservation-01-failed-native-readback-01.json', 'bytes': 2921, 'sha256': 'cd78dd030adc580d5c59862244c89bf3ad95e70862e4b2430cc43548396ab750'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-input-review-20261006-04/read_completed_01.py', 'bytes': 10213, 'sha256': '56c062528d0295ff2432db0916e9d42233a92c3bbb35dc5b080dcb4d2141b92f'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-native-readback-review-20261006-04/review-receipt-01.json', 'bytes': 16807, 'sha256': '10cce969ec2f01a811b565b9cac42b6a3caec8330e23d70f27ff52890d1dc13a'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-container-extension-design-20261006-01/design-01.json', 'bytes': 44852, 'sha256': '814ccc88c1f87de6cc99467419d1fb0a6eb99bb616763dce386f85c4b7e64b59'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-source-model-progress-20261006-01/progress-08.json', 'bytes': 21336, 'sha256': '3b0e4c04f3002cae14dafb89b43a323d9527e5d695173119a8b050cca17f84cd'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-math-source-review-20261006-05/review-receipt-01.json', 'bytes': 9149, 'sha256': '140ff7de9ed0de338d529920c74eacbd177333760f97ade2c474da63e2667036'}, {'bytes': 9149, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-math-source-review-20261006-05/review-receipt-01.json', 'sha256': '140ff7de9ed0de338d529920c74eacbd177333760f97ade2c474da63e2667036'}, {'bytes': 10298, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-tooling-source-review-20261006-05/review-receipt-01.json', 'sha256': 'a3b3de308d7d69cf7a7f8bfd1023febde8abd4cce871935c9df3d8b19cf88091'}, {'bytes': 25170, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-source-plan-20261005-01/source-bindings.json', 'sha256': 'd6cb9f35169351848198d3919a7e794cee89429b07a2879ea680cb8511bfa8b8'}, {'bytes': 13910, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-host-result-20261005-01/objective-prefix-draft.json', 'sha256': '4a7067a4797891740734fa7eae9ad46c02bc3410a4d4fff73ba43445a5a4ae17'}, {'bytes': 299466, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-scalar-occurrence-fixtures-20261006-01/scalar-source-occurrences-01.json', 'sha256': 'acfd1af4ccf740d9093d0b38468b25453c86f5683caddcc2dce12e067e91297d'}, {'bytes': 3445, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-scalar-occurrence-fixture-review-20261006-01/review-receipt-01.json', 'sha256': 'c5e93dc6f5c256feeb8337b48b03803a2f16ca299a6907f982297755fbb6daa5'}, {'bytes': 3916, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-01/math/PyAstNumericSubset.lean', 'sha256': '11baa458c201926c3a6e02b8ec7ca35213c336a30da199ce0390e3f1d7972faf'}, {'bytes': 15696, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01/evidence/lean-python-ast-subset-01/check-result.json', 'sha256': 'e1ecd6db20451ed9da5364e1a509c3d46ae908b0816e5529a8dde91e80e238fc'}, {'bytes': 43572, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-source-transport-candidate-20261006-01/python_ast_transport.py', 'sha256': 'adb876326a54fde0481b52c838815c1cae65f62e918025e7444bc285a6854c0d'}, {'bytes': 3711, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-transport-controls-source-review-20261006-03/review-receipt-01.json', 'sha256': 'ba0f796bef0f51077e6a5883cf78a20677a863015689d68e8f16c4e7fb74ab4e'}, {'bytes': 12547, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-transport-controls-20261006-03/run-01/closed.json', 'sha256': '12b436ee2403012aa8e133b3ccb0ea7bc7044ef321120f284d1155d3b6b62712'}, {'bytes': 4192, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-transport-controls-20261006-03/file-only-seal-01.json', 'sha256': '27a8884dbebd6c2f7f71d57e37e368b6072684242359d58ded321ba93c4ed726'}, {'bytes': 10390, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-source-transport-candidate-20261006-01/candidate-interface.json', 'sha256': 'edb98ff591ec2b9a3aeb816ebcf32e67006ea8288aa55d4ec1b14a4f80ff5f77'}, {'bytes': 2102, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-source-transport-candidate-20261006-01/file-only-seal-01.json', 'sha256': '364b73d9d697f7c367debb48c4ca18eeacf7037d3cf105473f88206b42d8cfd3'}, {'bytes': 5581, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-transport-source-review-20261006-01/review-receipt-01.json', 'sha256': '4e98ca6d333239feed2b5d2955d7a8c23e25eb933270299256df7a77be4b9661'}, {'bytes': 28493, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-replay-controls-readback-review-20261006-01/review-receipt-01.json', 'sha256': '28ff44621412d7e753add213895aa5057f1753d9c867f58093539c6db242d3a7'}, {'bytes': 6295, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-next-source-bridge-gaps-20261006-03/gaps-01.json', 'sha256': '9bb0d63766c883cf92f3c3299eb375469f7ca1d084cda3312013e72c4dd1df1c'}, {'bytes': 26539, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-source-model-progress-20261006-01/progress-09.json', 'sha256': '73c8162a5a0af76f47a3fad1ac20ec52b6c09b421d7814ba605a7c9f199c77af'}, {'bytes': 1213138, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-qualification-checkpoint-replay-candidate-20261006-02/history-checkpoint-02.json', 'sha256': '6c81310108cc3594a96fcf46070c2eceae2441311f83dfc74a069e90cf02bc99'}, {'bytes': 16861, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-qualification-checkpoint-replay-candidate-20261006-02/checkpoint_replay.py', 'sha256': 'bddc7677eceb8db478fb32183ba9ef47520f6fb6156c8b525ab5ddd246ffa152'}, {'bytes': 4886, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-checkpoint-replay-source-review-20261006-02/review-receipt-01.json', 'sha256': 'ffec7170766fe5ad2026dc2fcb746877878e3f516bc268109d76080b57294160'}, {'bytes': 16391, 'path': '/home/barberb/lift_coding/artifacts/codebase_ir_terminal_bench/terminal-codebase-ir-intent-corpus-head-20261004-01/source/benchmarks/agent_supervisor/container_coding/terminal_codebase_intent_ranker_training.py', 'sha256': '3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-scalar-source-context-review-20261007-01/review-receipt-01.json', 'bytes': 6415, 'sha256': '6648d057365daf36f240d68e2b9d0f8802b17f8af0e5e2fbfede8efef01f2587'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-scalar-source-transport-source-review-20261007-01/review-receipt-01.json', 'bytes': 4660, 'sha256': '0f57cc8e373cce3fa828b0bb07f40a491c4de4aa7d79cf8db52d3d3d6b10edc6'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-scalar-source-transport-source-review-20261007-02/review-receipt-01.json', 'bytes': 9286, 'sha256': '8d26307566cb838d8c9c9f4898bf62eda793eea11e5b3afa64dafbc5561606d3'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-scalar-source-input-review-20261007-02/host-readback-01.json', 'bytes': 1974, 'sha256': 'ecb4787a376580f73c7f1e47c6464ea91096886c91911cd87abf201e42bd530f'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-scalar-source-native-input-review-20261007-02/review-receipt-01.json', 'bytes': 13462, 'sha256': 'fc42c091b086041be66275084a0c708a5bcf2eeeae6f3b3b69d355b715e100af'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-scalar-native-staging-20261007-01/prior-import-context-01.json', 'bytes': 14590, 'sha256': '1bdcd3f6a17e44a8881dd449728a2dc0bf78d3de028b9dd019f045937bc99be1'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-original-scalar-bodies-design-20261007-01/design-01.json', 'bytes': 21572, 'sha256': 'fcd517e40706a14838c47b1029986d9931bb99418bf31f5aa6d6ee7cdf8cfefd'}], 'CONTEXT_SEALS': [{'regular_file_bytes': 2443136, 'regular_file_count': 3, 'schema': 'ranker-checkpoint-replay-failed-file-only-seal@1', 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-qualification-checkpoint-replay-candidate-20261006-01', 'seal': {'bytes': 1836, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-qualification-checkpoint-replay-candidate-20261006-01/file-only-seal-01.json', 'sha256': '0eb2413bc22d4bcdc9aacd46907ff30a4aff5867ceaa186a689a151c32195a31'}}, {'regular_file_bytes': 1229999, 'regular_file_count': 2, 'schema': 'ranker-supported-python-ast-checkpoint-replay-file-only-seal@1', 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-qualification-checkpoint-replay-candidate-20261006-02', 'seal': {'bytes': 1557, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-qualification-checkpoint-replay-candidate-20261006-02/file-only-seal-01.json', 'sha256': '9837ce419808e63477dbe63180f67c62be49bc33b7fe4b3ebf7e698643c98064'}}, {'regular_file_bytes': 49645341, 'regular_file_count': 122, 'schema': 'ranker-supported-python-ast-partial-native-complete-seal@1', 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01', 'seal': {'bytes': 37723, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01/file-only-seal-01.json', 'sha256': 'bb186005c1580312a084fcf0e3c10adb027549c7f4b09caf1014311ebcf0d287'}}, {'regular_file_bytes': 43022, 'regular_file_count': 6, 'schema': 'ranker-supported-python-ast-scalar-source-candidate-file-only-seal@1', 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-01', 'seal': {'bytes': 2559, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-01/file-only-seal-01.json', 'sha256': 'c2eefb33b654296dc1eb7c84fa6f7ecf4cf325ffcd4bf395c52ea6fa14731244'}}, {'regular_file_bytes': 71846, 'regular_file_count': 4, 'schema': 'ranker-supported-python-ast-source-transport-file-only-seal@1', 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-source-transport-candidate-20261006-01', 'seal': {'bytes': 2102, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-source-transport-candidate-20261006-01/file-only-seal-01.json', 'sha256': '364b73d9d697f7c367debb48c4ca18eeacf7037d3cf105473f88206b42d8cfd3'}}, {'regular_file_bytes': 178503, 'regular_file_count': 13, 'schema': 'ranker-supported-python-ast-failed-host-controls-file-only-seal@1', 'scope_root': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-transport-controls-20261006-02', 'seal': {'bytes': 4605, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-transport-controls-20261006-02/file-only-seal-01.json', 'sha256': 'ab011caebfd050b2faade08ef0d4140bb1cdbd25163d014098c3a05e88d3e355'}}, {'regular_file_bytes': 176778, 'regular_file_count': 12, 'schema': 'ranker-supported-python-ast-passed-host-controls-file-only-seal@1', 'scope_root': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-transport-controls-20261006-03', 'seal': {'bytes': 4192, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-transport-controls-20261006-03/file-only-seal-01.json', 'sha256': '27a8884dbebd6c2f7f71d57e37e368b6072684242359d58ded321ba93c4ed726'}}, {'regular_file_bytes': 11552442, 'regular_file_count': 27, 'schema': 'ranker-supported-python-ast-preservation-failed-native-complete-seal@1', 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-02', 'seal': {'bytes': 8971, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-02/file-only-seal-01.json', 'sha256': '5bfb60b21ce105c522a47ab0c48e4ff46a45d3488c2110eee67926744e8da021'}}, {'regular_file_bytes': 23157, 'regular_file_count': 3, 'schema': 'ranker-supported-python-ast-preservation-failed-source-complete-seal@1', 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-02', 'seal': {'bytes': 1732, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-02/file-only-seal-01.json', 'sha256': '4f352f562f75d64b3bff17b9e36a76a6c0205ccc7813268bc433ab7a8cfa795f'}}, {'regular_file_bytes': 11576586, 'regular_file_count': 27, 'schema': 'ranker-supported-python-ast-preservation-failed-native-complete-seal@1', 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-03', 'seal': {'bytes': 8971, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-03/file-only-seal-01.json', 'sha256': 'b403ed94b747069111ba01c6f86f037f35904bbb1f3593d9903f8abad73e5706'}}, {'regular_file_bytes': 24662, 'regular_file_count': 3, 'schema': 'ranker-supported-python-ast-preservation-failed-source-complete-seal@1', 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-03', 'seal': {'bytes': 1732, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-03/file-only-seal-01.json', 'sha256': 'a9ba6f027f23aa2211c67e370f874c3abb0a1bd924817cada0564aac2aa54044'}}, {'regular_file_bytes': 11575281, 'regular_file_count': 27, 'schema': 'ranker-supported-python-ast-preservation-failed-native-seal@1', 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-04', 'seal': {'bytes': 9031, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-04/file-only-seal-01.json', 'sha256': '6c7357f2ee8abff80d4954f808b459143572cb0e1af56b411ba27abb672fe05e'}}, {'regular_file_bytes': 25271, 'regular_file_count': 3, 'schema': 'ranker-supported-python-ast-preservation-failed-candidate-seal@1', 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-04', 'seal': {'bytes': 1810, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-04/file-only-seal-01.json', 'sha256': '7c2406074e4a2946bc948d5b411bff286157e018a1e0c41e27166089c3f73fbd'}}, {'regular_file_bytes': 15086870, 'regular_file_count': 55, 'schema': 'ranker-supported-python-ast-preservation-qualified-native-seal@1', 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-05', 'seal': {'bytes': 17730, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-05/file-only-seal-01.json', 'sha256': 'a99150efbeb5d0e08c53818b741c390103792cfe07996614970702671eee75c5'}}, {'regular_file_bytes': 26251, 'regular_file_count': 3, 'schema': 'ranker-supported-python-ast-preservation-qualified-candidate-seal@1', 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-05', 'seal': {'bytes': 1824, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-05/file-only-seal-01.json', 'sha256': 'aede5b465cb942d9e196636286b3eee341fafbc978e3501c1f73e468dd32ee87'}}, {'seal': {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-scalar-source-transport-20261007-01/file-only-seal-01.json', 'bytes': 1303, 'sha256': '97731b41113c4cc0dc974b9aa2301b2c42ae9495b3e37a809da4c0351437676b'}, 'scope_root': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-scalar-source-transport-20261007-01', 'schema': 'ranker-supported-python-ast-scalar-source-rejected-producer-seal@1', 'regular_file_count': 1, 'regular_file_bytes': 43269}, {'seal': {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-scalar-source-transport-20261007-02/file-only-seal-01.json', 'bytes': 4653, 'sha256': '1cf3dfa5ab317077f17bcf49851ea9c818040cd913b51ef90679987b2fea2d57'}, 'scope_root': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-scalar-source-transport-20261007-02', 'schema': 'ranker-supported-python-ast-scalar-source-owned-producer-seal@1', 'regular_file_count': 13, 'regular_file_bytes': 526951}, {'seal': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-scalar-source-host-result-20261007-02/file-only-seal-01.json', 'bytes': 2492, 'sha256': '84e9006c88597bb7c1fd918277b9345b147563208ca92622c4f29fffb30a85a3'}, 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-scalar-source-host-result-20261007-02', 'schema': 'ranker-supported-python-ast-scalar-source-host-result-seal@1', 'regular_file_count': 5, 'regular_file_bytes': 503980}, {'seal': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-scalar-source-transport-plan-20261007-01/file-only-seal-01.json', 'bytes': 1325, 'sha256': '644720c3d676e3cefa5c5cb24321619a1f2b84afa66ae6186a914a242cca06bd'}, 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-scalar-source-transport-plan-20261007-01', 'schema': 'ranker-supported-python-ast-scalar-source-context-plan-seal@1', 'regular_file_count': 1, 'regular_file_bytes': 17939}], 'STRICT_GUARD_COUNT': 4327}
BASE_PROFILE={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-projections-candidate-20261006-02/preparation/lean-objective-prefix-projections-02-producer/environment-manifest.json', 'bytes': 10016048, 'sha256': 'b3071501a40a55cb1dc6ec547f2573090d382403e1887ef9f8db4ad74c244350'}
PRIOR_REQUEST={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-infinite-evaluator-extension-qualification-20261006-01/preparation/lean-original-source-evaluator-infinite-extension-01-request.json', 'bytes': 979363, 'sha256': '4182b135d81188179950c4f89864ed45321bcec11d5d8bf74e634fd57c6f487a'}
PRIOR_SEAL={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-infinite-evaluator-extension-qualification-20261006-01/file-only-seal-01.json', 'bytes': 11913, 'sha256': 'bfb72c24f578eaef2d961876f62d4c37d92016e3f2374774ffcde2bded64e623'}
BASE_IMPORT_NAMES=['ObjectiveScalarIR', 'RealStableFactor', 'TypedNumericSlice', 'ObjectiveContainerCore', 'ObjectivePrefixIR', 'RealGapContraction']
PRIOR_IMPORTS = [{'check_result': {'bytes': 14071, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-source-01/check-result.json', 'sha256': 'ca7ed3da92fbae947f595bfde1a8eb1025bc9758ebdd58eaf11210b2d125c0bf'}, 'mode': 'lean-container-source-01'}, {'check_result': {'bytes': 15524, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-typed-01/check-result.json', 'sha256': 'cfb690034025ad99470dad89ab537952955ddb4b14b1ed3675bf8181dfcfad63'}, 'mode': 'lean-container-typed-01'}, {'check_result': {'bytes': 13707, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-semantics-01/check-result.json', 'sha256': '8650075e9f209aa2d61d284d043b51200a866611703ad40739ce29af3f05d62b'}, 'mode': 'lean-container-semantics-01'}, {'check_result': {'bytes': 15696, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01/evidence/lean-python-ast-subset-01/check-result.json', 'sha256': 'e1ecd6db20451ed9da5364e1a509c3d46ae908b0816e5529a8dde91e80e238fc'}, 'mode': 'lean-python-ast-subset-01'}, {'check_result': {'bytes': 15178, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01/evidence/lean-python-ast-semantics-01/check-result.json', 'sha256': '38b975f475e7f47b135435745e053aca05a807ffb3ccaeca491ba6a360db94a3'}, 'mode': 'lean-python-ast-semantics-01'}, {'check_result': {'bytes': 15213, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01/evidence/lean-python-ast-lowering-01/check-result.json', 'sha256': 'f1414bd0c4450d9c3a78cee4ac39794b33eb2fd5adb17b868978c19c8e4944af'}, 'mode': 'lean-python-ast-lowering-01'}, {'check_result': {'bytes': 26127, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-05/evidence/lean-python-ast-preservation-01/check-result.json', 'sha256': 'a89575bd9f2c7c9ac981046a5b7f2fd1b1bf946df7acc067dae268c725ca145d'}, 'mode': 'lean-python-ast-preservation-01'}]
DEPENDENCY_MODULES = {'lean-container-semantics-01': {'direct_imports': ['ObjectiveContainerTyped'], 'module': 'ObjectiveContainerSemantics', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02', 'queries': ['RankerObjectiveContainerLanguage.map_to_vector_error', 'RankerObjectiveContainerLanguage.zip_to_vector_error', 'RankerObjectiveContainerLanguage.ordered_map_first_error', 'RankerObjectiveContainerLanguage.ordered_zip_first_error'], 'source': {'bytes': 11695, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-candidate-20261006-02/math/ObjectiveContainerSemantics.lean', 'sha256': '23bf7349c698832ad088adc68b41913a88affafff235008b38ef6688079b5ec8'}}, 'lean-container-source-01': {'direct_imports': ['ObjectivePrefixIR'], 'module': 'ObjectiveContainerSource', 'prior_modes': [], 'queries': ['RankerObjectiveContainerLanguage.source_zip_left_index_bound'], 'source': {'bytes': 3060, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-candidate-20261006-01/math/ObjectiveContainerSource.lean', 'sha256': 'fc01f1d99e348e79f9cc9fdaf35cbbdb29d0c0963e88b4b984fde469e2eee410'}}, 'lean-container-typed-01': {'direct_imports': ['ObjectiveContainerSource'], 'module': 'ObjectiveContainerTyped', 'prior_modes': ['lean-container-source-01'], 'queries': ['RankerObjectiveContainerLanguage.typed_zip_right_index_bound'], 'source': {'bytes': 3583, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-candidate-20261006-01/math/ObjectiveContainerTyped.lean', 'sha256': 'bdb3140f15e51c5f52c37f2326ef7dcb2ebbdf372720915202eb13c1701cda67'}}, 'lean-python-ast-lowering-01': {'direct_imports': ['PyAstNumericSubset', 'ObjectiveContainerSource'], 'module': 'PyAstNumericLowering', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-python-ast-subset-01', 'lean-python-ast-semantics-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01', 'queries': ['RankerSupportedPythonAstReal.unbound_name_refused', 'RankerSupportedPythonAstReal.unsupported_dead_branch_refused'], 'source': {'bytes': 5287, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-01/math/PyAstNumericLowering.lean', 'sha256': '9694b40446f7c8661e183b9d137bf936642940f879227c8373d2a3bdf627b881'}}, 'lean-python-ast-preservation-01': {'direct_imports': ['PyAstNumericSemantics', 'PyAstNumericLowering', 'ObjectiveContainerSemantics'], 'module': 'PyAstNumericPreservation', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-python-ast-subset-01', 'lean-python-ast-semantics-01', 'lean-python-ast-lowering-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-05', 'queries': ['RankerSupportedPythonAstReal.lower_supported_ast_observation_preserved', 'RankerSupportedPythonAstReal.lower_supported_ast_success_observation', 'RankerSupportedPythonAstReal.lower_supported_ast_error_observation'], 'source': {'bytes': 21942, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-05/math/PyAstNumericPreservation.lean', 'sha256': '5c6c65dc530540030fe3edf82be868ede8fd675236078dd0714ddb6bfb159b2a'}}, 'lean-python-ast-semantics-01': {'direct_imports': ['PyAstNumericSubset', 'Mathlib.Analysis.SpecialFunctions.Log.Basic'], 'module': 'PyAstNumericSemantics', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-python-ast-subset-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01', 'queries': ['RankerSupportedPythonAstReal.binary_left_error_precedence', 'RankerSupportedPythonAstReal.constant_true_if_keeps_selected_observation'], 'source': {'bytes': 6314, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-01/math/PyAstNumericSemantics.lean', 'sha256': '3ce628f904f57b800f67b7a739f04e3adf72e0888b1689e23f7cef3e1ac2a2b8'}}, 'lean-python-ast-subset-01': {'direct_imports': ['Mathlib.Data.Rat.Defs'], 'module': 'PyAstNumericSubset', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01', 'queries': ['RankerSupportedPythonAstReal.integer_and_float_syntax_distinct'], 'source': {'bytes': 3916, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-01/math/PyAstNumericSubset.lean', 'sha256': '11baa458c201926c3a6e02b8ec7ca35213c336a30da199ce0390e3f1d7972faf'}}}
DEPENDENCY_ROOTS = {'lean-container-semantics-01': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02', 'lean-container-source-01': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01', 'lean-container-typed-01': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01', 'lean-python-ast-lowering-01': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01', 'lean-python-ast-preservation-01': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-05', 'lean-python-ast-semantics-01': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01', 'lean-python-ast-subset-01': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01'}
DEPENDENCY_SOURCE_GATES = {'lean-container-semantics-01': {'bytes': 14517, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-source-review-20261006-01/review-receipt-02.json', 'sha256': 'd3a869e27ab6ee61d2adca560fc5e802f775cc508bfe6e3f974a7ac504ade09c'}, 'lean-container-source-01': {'bytes': 13034, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-source-review-20261006-01/review-receipt-01.json', 'sha256': '6704fc5676a6ebe5ff1abddc58acfa06d91168a5d59a26faa181ed116bafcb94'}, 'lean-container-typed-01': {'bytes': 13034, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-source-review-20261006-01/review-receipt-01.json', 'sha256': '6704fc5676a6ebe5ff1abddc58acfa06d91168a5d59a26faa181ed116bafcb94'}, 'lean-python-ast-lowering-01': {'bytes': 8187, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-math-source-review-20261006-01/review-receipt-01.json', 'sha256': '320d464175c620bfb4c517918246b19c71a056248328bbe8980b8dda5e1e4924'}, 'lean-python-ast-preservation-01': {'bytes': 9149, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-math-source-review-20261006-05/review-receipt-01.json', 'sha256': '140ff7de9ed0de338d529920c74eacbd177333760f97ade2c474da63e2667036'}, 'lean-python-ast-semantics-01': {'bytes': 8187, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-math-source-review-20261006-01/review-receipt-01.json', 'sha256': '320d464175c620bfb4c517918246b19c71a056248328bbe8980b8dda5e1e4924'}, 'lean-python-ast-subset-01': {'bytes': 8187, 'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-math-source-review-20261006-01/review-receipt-01.json', 'sha256': '320d464175c620bfb4c517918246b19c71a056248328bbe8980b8dda5e1e4924'}}
ACCEPTED_CHECK_PINS = {'lean-container-semantics-01': {'bytes': 13707, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-semantics-01/check-result.json', 'sha256': '8650075e9f209aa2d61d284d043b51200a866611703ad40739ce29af3f05d62b'}, 'lean-container-source-01': {'bytes': 14071, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-source-01/check-result.json', 'sha256': 'ca7ed3da92fbae947f595bfde1a8eb1025bc9758ebdd58eaf11210b2d125c0bf'}, 'lean-container-typed-01': {'bytes': 15524, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-typed-01/check-result.json', 'sha256': 'cfb690034025ad99470dad89ab537952955ddb4b14b1ed3675bf8181dfcfad63'}, 'lean-python-ast-lowering-01': {'bytes': 15213, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01/evidence/lean-python-ast-lowering-01/check-result.json', 'sha256': 'f1414bd0c4450d9c3a78cee4ac39794b33eb2fd5adb17b868978c19c8e4944af'}, 'lean-python-ast-preservation-01': {'bytes': 26127, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-05/evidence/lean-python-ast-preservation-01/check-result.json', 'sha256': 'a89575bd9f2c7c9ac981046a5b7f2fd1b1bf946df7acc067dae268c725ca145d'}, 'lean-python-ast-semantics-01': {'bytes': 15178, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01/evidence/lean-python-ast-semantics-01/check-result.json', 'sha256': '38b975f475e7f47b135435745e053aca05a807ffb3ccaeca491ba6a360db94a3'}, 'lean-python-ast-subset-01': {'bytes': 15696, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01/evidence/lean-python-ast-subset-01/check-result.json', 'sha256': 'e1ecd6db20451ed9da5364e1a509c3d46ae908b0816e5529a8dde91e80e238fc'}}
NATIVE_LIMITS={'wall_seconds': 20, 'cpu_seconds': 20, 'output_bytes': 65536, 'workspace_bytes': 16777216}
ROOT_LEASE={'cpu_slots': 1, 'memory_mb': 2048, 'child_process_slots': 4}
PRESSURE={'memory_percent': 2.0, 'cpu_percent': 50.0, 'io_percent': 10.0}
AUTHORITY={'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False}
MODE_ORDER = ['lean-python-ast-actual-source-01']

def need(value, message):
    if value is not True:
        raise ValueError(message)

def read_pin(path, capture=False):
    path = Path(path).absolute()
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical nonsymlink input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'unaliased regular input required')
        need(not capture or before.st_size <= 32 * 1024**2, 'parsed input exceeds fixed cap')
        blocks, total, digest = [], 0, hashlib.sha256()
        while block := os.read(fd, 1024**2):
            total += len(block)
            need(total <= before.st_size, 'input grew during read')
            digest.update(block)
            if capture:
                blocks.append(block)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda info: tuple(getattr(info, key) for key in fields)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat())
             and path.resolve(strict=True) == path and not path.is_symlink()
             and total == before.st_size, 'input changed during read')
    finally:
        os.close(fd)
    descriptor = {'path': str(path), 'bytes': total, 'sha256': digest.hexdigest()}
    need(str(path) not in HELD or HELD[str(path)] == descriptor, 'held input changed')
    HELD[str(path)] = descriptor
    return b''.join(blocks), descriptor

def pin(path):
    return read_pin(path)[1]

def exact(row, capture=False):
    need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'} and type(row['bytes']) is int and row['bytes'] >= 0
         and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None, 'exact descriptor required')
    raw, actual = read_pin(row['path'], capture)
    need(actual == row, 'same-buffer descriptor differs')
    return raw

def fixed(path, pair, capture=False):
    row = {'path': str(path), 'bytes': pair[0], 'sha256': pair[1]}
    return exact(row, capture), row

def parse(raw):
    def unique(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate JSON field')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)

def document(row):
    return parse(exact(row, True))

def write(path, value):
    path = Path(path)
    with path.open('xb') as stream:
        stream.write((json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    return pin(path)

def verify_held():
    for row in list(HELD.values()):
        exact(row)

def qualified_module(name, base, check_row=None):
    registry_local = next(row for row in base['local_checked_modules'] if row['module'] == name)
    check_pin = registry_local['qualification'] if check_row is None else check_row
    need(check_pin == registry_local['qualification'], 'exact declared qualified check registry required')
    raw = exact(check_pin, True)
    check = parse(raw)
    need(check['status'] == 'passed' and check['matches_expectation'] is True and check['expected_success'] is True
         and check['native_lean_returncode'] == 0 and check['native_invocations'] == 1
         and check['axiom_report_error'] is None and check['post_call_binding_error'] is None,
         'actual accepted native import required')
    queries = check['theorem_axiom_output']
    need(queries and all(row['report_occurrences'] == 2 and set(row['axioms']) <= {'Classical.choice', 'Quot.sound', 'propext'} for row in queries), 'qualified standard axioms required')
    registry = next(row for row in base['source_import_modules'] if row['module'] == name)
    local = next(row for row in base['local_checked_modules'] if row['module'] == name)
    need(local['qualification'] == check_pin and local['environment'] == check['environment_manifest']
         and registry['source'] == check['augmented_source'], 'existing qualified module registry differs')
    objects = []
    for row in check['compiled_artifacts']:
        need(row['complete'] is True, 'complete imported object required')
        descriptor = {key: row[key] for key in ('path', 'bytes', 'sha256')}
        exact(descriptor)
        objects.append(descriptor)
    need(objects == registry['compiled'] and len(objects) == 1 and Path(objects[0]['path']).name == name + '.olean', 'whole ordered import object registry differs')
    for row in (check['source'], check['augmented_source'], check['environment_manifest']):
        exact(row)
    retention = check['retention_manifest']
    need(retention['complete'] is True, 'complete import retention manifest required')
    manifest = document({key: retention[key] for key in ('path', 'bytes', 'sha256')})
    need(manifest == check['retention_manifest_body'] and manifest['schema'] == 'bounded_lean_chunks@1'
         and manifest['status'] == 'complete' and manifest['native_lean_returncode'] == 0,
         'same-buffer actual retained object manifest differs')
    chunks = check['retained_chunk_artifacts']
    need(len(chunks) == len(manifest['chunks']) <= 61 and len(manifest['objects']) == 1, 'complete bounded chunk population required')
    table, held_chunks = {}, {}
    for actual, declared in zip(chunks, manifest['chunks']):
        need(actual['complete'] is True and Path(actual['path']).name == declared['name'] and 0 < actual['bytes'] <= 65536
             and actual['bytes'] == declared['bytes'] and actual['sha256'] == declared['sha256'], 'import chunk descriptor differs')
        descriptor = {key: actual[key] for key in ('path', 'bytes', 'sha256')}
        need(declared['name'] not in table, 'duplicate import chunk name')
        table[declared['name']] = exact(descriptor, True)
        held_chunks[declared['name']] = descriptor
    obj = manifest['objects'][0]
    need(obj['name'] == Path(objects[0]['path']).name and obj['bytes'] == objects[0]['bytes'] and obj['sha256'] == objects[0]['sha256']
         and obj['chunks'] == list(table) and manifest['aggregate_raw_object_bytes'] == obj['bytes'] <= 3997696,
         'complete reconstructed historical object differs')
    joined = hashlib.sha256()
    total = 0
    for chunk in obj['chunks']:
        total += len(table[chunk])
        joined.update(table[chunk])
    need(total == obj['bytes'] and joined.hexdigest() == obj['sha256'], 'historical chunks do not reconstruct whole object')
    return {'module': name, 'qualification': check_pin, 'source': check['source'], 'augmented_source': check['augmented_source'],
            'compiled': objects, 'retention_manifest': {key: retention[key] for key in ('path', 'bytes', 'sha256')},
            'retained_chunks': list(held_chunks.values()), 'historical_complete_object_join_verified': True}

def _append_imports(base,imports):
    """Only dependency-prefix modules with whole native objects may be added."""
    need(type(imports) is list and len(imports)<=len(DEPENDENCY_MODULES)+len(MODE_ORDER),'finite declared dependency population required')
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
        stage_root=Path(DEPENDENCY_ROOTS.get(row['mode'], str(ROOT)))
        need(stage_root in (ROOT, ROOT.with_name('ranker-supported-python-ast-qualification-20261006-01'), ROOT.with_name('ranker-objective-container-language-qualification-20261006-01'),
                            ROOT.with_name('ranker-objective-container-language-qualification-20261006-02'), ROOT.with_name('ranker-supported-python-ast-qualification-20261006-05')),
             'only three historical scalar-target stages or fresh declared AST modes allowed')
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
        source_gate_row=DEPENDENCY_SOURCE_GATES.get(row['mode'], SOURCE_GATE);gate=document(source_gate_row)
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


# A single literal source review freezes these descriptors before any execution.
SOURCE_GATE=FROZEN['SOURCE_GATE']
STRICT_GUARD_COUNT=FROZEN['STRICT_GUARD_COUNT']

def module(mode):
    modules=document(FROZEN['MODULE_MAP'])
    need(type(mode) is str and mode in modules, 'exact frozen AST mode required')
    return modules[mode]

def dependency_module(mode):
    return DEPENDENCY_MODULES[mode] if mode in DEPENDENCY_MODULES else module(mode)

def source_gate(mode):
    selected=module(mode);gate=document(SOURCE_GATE)
    need(gate['status']=='passed_source_only' and gate['findings']==[]
         and gate['candidate_pins']==FROZEN['CANDIDATE_PINS']
         and gate['reviewed_modules']==document(FROZEN['MODULE_MAP'])
         and gate['candidate_compiled'] is False and gate['actual_new_qualified_queries']==0
         and all(gate[key] is False for key in AUTHORITY), 'exact reviewed unqualified scalar AST source gate required')
    for row in FROZEN['CANDIDATE_PINS'].values():exact(row)
    need(selected['source'] in FROZEN['CANDIDATE_PINS'].values(), 'selected AST source absent from gate')
    return gate

def complete_guard_union():
    gate=document(FROZEN['REPLAY_GATE'])
    need(gate['status']=='passed_source_only' and gate['findings']==[]
         and gate['reviewed_sources']==[FROZEN['REPLAY_SOURCE'],FROZEN['CHECKPOINT']]
         and all(gate[key] is False for key in AUTHORITY), 'exact independent checkpoint replay source gate required')
    raw=exact(FROZEN['REPLAY_SOURCE'], True)
    namespace={'__file__':FROZEN['REPLAY_SOURCE']['path'],'__name__':'held_standalone_checkpoint_replay'}
    exec(compile(raw,FROZEN['REPLAY_SOURCE']['path'],'exec'),namespace)
    result=namespace['replay'](FROZEN['CHECKPOINT'])
    need(result['status']=='passed_file_only' and result['historical_helpers_executed']==0
         and result['digest_cache_used'] is False, 'fresh complete historical closure replay required')
    checkpoint=document(FROZEN['CHECKPOINT']);inherited=document(PRIOR_REQUEST)
    rows={row['path']:row for row in checkpoint['closure']}
    for expected in FROZEN['CONTEXT_SEALS']:
        seal_pin=expected['seal'];seal=document(seal_pin);scope=Path(expected['scope_root']);leaves=seal['files']
        need(seal['schema']==expected['schema'] and seal['scope_root']==str(scope)
             and scope.resolve(strict=True)==scope and not scope.is_symlink()
             and Path(seal_pin['path']).parent==scope
             and len(leaves)==seal['regular_file_count']==expected['regular_file_count']
             and len({row['path'] for row in leaves})==len(leaves)
             and seal['regular_file_bytes']==sum(row['bytes'] for row in leaves)==expected['regular_file_bytes']
             and hashlib.sha256(json.dumps(leaves,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()==seal['file_inventory_sha256']
             and seal['seal_self_excluded_from_files'] is True
             and seal['fixture_symlinks']==seal['excluded_dependency_subtrees']==[]
             and all(Path(row['path']).is_relative_to(scope) for row in leaves)
             and all(seal[key] is False for key in AUTHORITY), 'exact frozen recent closure context required')
        physical=list(scope.rglob('*'))
        need(not any(path.is_symlink() for path in physical)
             and all(path.is_file() or path.is_dir() for path in physical)
             and {str(path) for path in physical if path.is_file()}=={row['path'] for row in leaves}|{seal_pin['path']},
             'complete recent context physical census differs')
        for row in [seal_pin,*leaves,seal['review']]:
            need(row['path'] not in rows or rows[row['path']]==row,'recent context overlaps changed body')
            exact(row);rows[row['path']]=row
    additions=[FROZEN['REPLAY_SOURCE'],FROZEN['CHECKPOINT'],FROZEN['REPLAY_GATE'],
               FROZEN['MODULE_MAP'],*FROZEN['CANDIDATE_PINS'].values(),SOURCE_GATE,*FROZEN['EXTRA_CONTEXT']]
    for row in additions:
        need(row['path'] not in rows or rows[row['path']]==row,'overlapping current guarded descriptor differs')
        exact(row);rows[row['path']]=row
    need(len(rows)==STRICT_GUARD_COUNT, 'fixed current closure denominator differs')
    return [rows[path] for path in sorted(rows)],inherited

def validate_guard_union(request):
    rows,inherited=complete_guard_union()
    need(request['strict_old_inputs']==rows and request['strict_guard_count']==STRICT_GUARD_COUNT
         and request['protected_live_sources']==inherited['protected_live_sources']
         and request['original_checkout_guards']==inherited['original_checkout_guards']
         and request['prior_language_context_request']==PRIOR_REQUEST
         and request['prior_language_context_seal']==PRIOR_SEAL, 'complete checkpoint/current source union required')

def import_extension(base, imports):
    need(type(imports) is list and len(imports)==7 and imports==PRIOR_IMPORTS,
         'exact seven actually owned prior scalar-target and AST support modules required')
    return _append_imports(base,imports)
