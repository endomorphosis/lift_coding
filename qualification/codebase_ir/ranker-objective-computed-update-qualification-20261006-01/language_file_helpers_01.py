"""Source-only finite computed-update/iteration qualifier, initially refusing.

Genuine Tail29 and modern relay7 parents have complete sealed closures. The two
exact modes select four update queries then five finite adapter/iteration queries.
The iteration requires a genuinely closed update result before source admission;
no future result or original Python loop/Float/convergence is assumed. Independent
source/tooling pins and the denominator must be frozen before root execution.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
WORKSPACE=ROOT.parents[2]
Q5=ROOT.with_name('ranker-objective-ir-candidate-20261005-01')
PR_PIN={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-qualification-20261006-01/language_file_helpers_01.py', 'bytes': 10862, 'sha256': '2c24357d995ab9144e730b78fea81f4b0d1cdefb1649c8a69300e060e01dac39'}
PR_TOOLING_GATE={'path': '/home/barberb/lift_coding/maintenance/ranker-source-update-owned-relay-tooling-source-review-20261006-01/review-receipt-01.json', 'bytes': 10780, 'sha256': '7ff6ca3698637c4c855e9db86a9d24427b3c761c1409ca2a3f715e532f34eaad'}
PRIOR_REQUEST={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01/preparation/lean-original-prefix-model-projection-01-request.json', 'bytes': 890649, 'sha256': '42c695c7bee8c090166b3e88dc8e25059c8399261d6e2c23e468b02b8c31e92f'}
PRIOR_SEAL={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01/file-only-seal-01.json', 'bytes': 42244, 'sha256': 'bbeabfe60c5eb5ed708fb684f5ad249bf8a2b5c6c9914e2aec7bf18414a02c8b'}
RELAY_REQUEST={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-qualification-20261006-01/preparation/lean-generated-numeric-slices-relay-01-request.json', 'bytes': 888224, 'sha256': '3e5a211f30d9300641506785badb88c2d09436ae98d537bbc7fa44d1d2391050'}
CLOSED_PARENT_SCOPES=[{'seal': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01/file-only-seal-01.json', 'bytes': 42244, 'sha256': 'bbeabfe60c5eb5ed708fb684f5ad249bf8a2b5c6c9914e2aec7bf18414a02c8b'}, 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01', 'regular_file_count': 128, 'regular_file_bytes': 58026192, 'qualified_theorem_queries': 29, 'review': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01/qualified-review-01.json', 'bytes': 12308, 'sha256': 'f0cc293cecad16fa3617c3e61b6587b86a3f6b1c6bedc7b374076a6874ae5567'}}, {'seal': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-candidate-20261006-03/file-only-seal-01.json', 'bytes': 2730, 'sha256': 'd4c53c2f35cdcfb73c3683e415e04ba1bd058dd6f9d36ffbf4d44d27b72bd8bf'}, 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-candidate-20261006-03', 'regular_file_count': 7, 'regular_file_bytes': 50987, 'qualified_theorem_queries': 29}, {'seal': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-qualification-20261006-01/file-only-seal-01.json', 'bytes': 9713, 'sha256': 'b9338e85776ee72cdbaa2224dae25de0fae0daed3710ca177cc244bdaf38cc28'}, 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-qualification-20261006-01', 'regular_file_count': 28, 'regular_file_bytes': 11194975, 'qualified_theorem_queries': 7, 'review': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-qualification-20261006-01/qualified-review-01.json', 'bytes': 2306, 'sha256': '8f9ab7a416ac01447fb15d0c1378cf4449418e8eaf7df445e932e1dc7bff632c'}}, {'seal': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-candidate-20261006-01/file-only-seal-01.json', 'bytes': 1526, 'sha256': 'cc49c2a2ab8309f4588860755f6f344624e2b2a16eef170ce8dad8f1a03086e8'}, 'scope_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-candidate-20261006-01', 'regular_file_count': 3, 'regular_file_bytes': 14657, 'qualified_theorem_queries': 7}]
MODULES={'lean-original-computed-finite-iteration-01': {'direct_imports': ['OriginalComputedSourceUpdate', 'ObjectiveContainerEvaluationBridge', 'RealGapContraction'], 'module': 'OriginalComputedFiniteIteration', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01', 'lean-container-evaluation-bridge-01', 'lean-source-scalar-lift-01', 'lean-original-prefix-parts-01', 'lean-source-container-success-01', 'lean-original-prefix-margins-01', 'lean-original-prefix-loss-regularizer-01', 'lean-original-prefix-factors-01', 'lean-original-prefix-gradient-01', 'lean-original-prefix-record-01', 'lean-original-prefix-model-projection-01', 'lean-generated-numeric-slices-relay-01', 'lean-original-computed-source-update-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-finite-source-iteration-qualification-20261006-01', 'queries': ['RankerObjectiveOriginalComputedFiniteIteration.checked_vector_ofFn_success', 'RankerObjectiveOriginalComputedFiniteIteration.checked_vector_refuses_wrong_length', 'RankerObjectiveOriginalComputedFiniteIteration.actual_computed_vector_update_eq', 'RankerObjectiveOriginalComputedFiniteIteration.source_iterate_eq_model', 'RankerObjectiveOriginalComputedFiniteIteration.source_iterate_finite_gap_bound'], 'source': {'bytes': 5468, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-finite-source-iteration-candidate-20261006-01/math/OriginalComputedFiniteIteration.lean', 'sha256': 'c5de75f08c00c4c3d4cabbce1df601795f56b04fcb1213a7ab86262380e633f8'}}, 'lean-original-computed-source-update-01': {'direct_imports': ['OriginalPrefixModelProjection', 'GeneratedNumericSlices'], 'module': 'OriginalComputedSourceUpdate', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01', 'lean-container-evaluation-bridge-01', 'lean-source-scalar-lift-01', 'lean-original-prefix-parts-01', 'lean-source-container-success-01', 'lean-original-prefix-margins-01', 'lean-original-prefix-loss-regularizer-01', 'lean-original-prefix-factors-01', 'lean-original-prefix-gradient-01', 'lean-original-prefix-record-01', 'lean-original-prefix-model-projection-01', 'lean-generated-numeric-slices-relay-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-computed-update-qualification-20261006-01', 'queries': ['RankerObjectiveOriginalComputedSourceUpdate.actual_computed_update_with_compilation_eq', 'RankerObjectiveOriginalComputedSourceUpdate.actual_computed_update_eq', 'RankerObjectiveOriginalComputedSourceUpdate.actual_computed_update_success_length', 'RankerObjectiveOriginalComputedSourceUpdate.actual_computed_update_has_safe_descent'], 'source': {'bytes': 5193, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-computed-update-candidate-20261006-01/math/OriginalComputedSourceUpdate.lean', 'sha256': 'f20c16c6b4de708cba347581e5f44e8dee80e00bd65839b5dac8bcc45f473287'}}}
MODE_ORDER=['lean-original-computed-source-update-01', 'lean-original-computed-finite-iteration-01']
DEPENDENCY_MODULES={'lean-container-generated-prefix-01': {'direct_imports': ['ObjectiveContainerPreservation'], 'module': 'ObjectiveContainerPrefixGenerated', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01', 'queries': ['GeneratedOriginalObjectiveContainerPrefix.emitted_prefix_compiles', 'GeneratedOriginalObjectiveContainerPrefix.emitted_prefix_preserves'], 'source': {'bytes': 8046, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01/ObjectiveContainerPrefixGenerated.lean', 'sha256': '31bc24c08296302aa15c8067df2cae7e7aa9f3d3b28b63145d661f82f1d3ccbb'}}, 'lean-container-evaluation-bridge-01': {'direct_imports': ['ObjectiveContainerPreservation'], 'module': 'ObjectiveContainerEvaluationBridge', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01', 'queries': ['RankerObjectiveContainerEvaluationBridge.vectorOfList_ofFn', 'RankerObjectiveContainerEvaluationBridge.mapToVector_ofFn_success', 'RankerObjectiveContainerEvaluationBridge.zipMapExact_eq_mapExact_zipWith', 'RankerObjectiveContainerEvaluationBridge.zipWith_ofFn_min', 'RankerObjectiveContainerEvaluationBridge.zipMapExact_ofFn_min_success', 'RankerObjectiveContainerEvaluationBridge.zipToVector_ofFn_min_success', 'RankerObjectiveContainerEvaluationBridge.orderedFsum_ofFn_eq_sum', 'RankerObjectiveContainerEvaluationBridge.orderedFsum_map_success', 'RankerObjectiveContainerEvaluationBridge.orderedFsum_zip_success'], 'source': {'bytes': 7680, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-eval-bridge-candidate-20261006-01/math/ObjectiveContainerEvaluationBridge.lean', 'sha256': 'b39d3c585c5cbbe9da30f932000ce2428d2cc754849e1c9dbd43b6912c3a4587'}}, 'lean-original-prefix-parts-01': {'direct_imports': ['ObjectiveSourceScalarLift'], 'module': 'ObjectiveOriginalPrefixParts', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01', 'lean-source-scalar-lift-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-qualification-20261006-02', 'queries': ['RankerObjectiveOriginalPrefixParts.emitted_prefix_decomposition', 'RankerObjectiveOriginalPrefixParts.emitted_loss_body_scalar_injection', 'RankerObjectiveOriginalPrefixParts.emitted_factor_body_scalar_injection', 'RankerObjectiveOriginalPrefixParts.emitted_loss_body_success', 'RankerObjectiveOriginalPrefixParts.emitted_factor_body_success'], 'source': {'bytes': 8913, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-candidate-20261006-03/math/ObjectiveOriginalPrefixParts.lean', 'sha256': 'a8921ca1035c71f5aa22066777084f27a85dc5f71e8200469f7c9e61b322cf08'}}, 'lean-source-scalar-lift-01': {'direct_imports': ['ObjectiveContainerPrefixGenerated'], 'module': 'ObjectiveSourceScalarLift', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-qualification-20261006-02', 'queries': ['RankerObjectiveSourceScalarLift.eval_lift_scalar_source', 'RankerObjectiveSourceScalarLift.named_stable_loss_success', 'RankerObjectiveSourceScalarLift.named_stable_factor_success'], 'source': {'bytes': 5735, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-candidate-20261006-03/math/ObjectiveSourceScalarLift.lean', 'sha256': '0ecadf24c5e8d23f4904da8fbd4260b8b0488d90fae9643d6dc8bfab14dae89e'}}, 'lean-source-container-success-01': {'direct_imports': ['ObjectiveContainerEvaluationBridge'], 'module': 'ObjectiveSourceContainerSuccess', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-evaluation-bridge-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-qualification-20261006-01', 'queries': ['RankerObjectiveSourceContainerSuccess.eval_source_mapRows_success', 'RankerObjectiveSourceContainerSuccess.eval_source_mapVector_success', 'RankerObjectiveSourceContainerSuccess.eval_source_zipMap_min_success', 'RankerObjectiveSourceContainerSuccess.eval_source_zipRowsMap_min_success', 'RankerObjectiveSourceContainerSuccess.eval_source_rangeMap_success', 'RankerObjectiveSourceContainerSuccess.eval_source_fsum_success', 'RankerObjectiveSourceContainerSuccess.eval_source_lengthVector_success', 'RankerObjectiveSourceContainerSuccess.eval_source_lengthMatrix_success', 'RankerObjectiveSourceContainerSuccess.eval_source_indexVector_success', 'RankerObjectiveSourceContainerSuccess.eval_source_natToScalar_success'], 'source': {'bytes': 8191, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-candidate-20261006-01/math/ObjectiveSourceContainerSuccess.lean', 'sha256': '860982d7e67954d782d776915f5d06bb0fe51de0c03763c10e23c524a750f7a2'}}, 'lean-original-prefix-margins-01': {'direct_imports': ['ObjectiveSourceContainerSuccess', 'ObjectiveOriginalPrefixParts'], 'module': 'OriginalPrefixMarginsEvaluation', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01', 'lean-container-evaluation-bridge-01', 'lean-source-scalar-lift-01', 'lean-original-prefix-parts-01', 'lean-source-container-success-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-qualification-20261006-05', 'queries': ['RankerObjectiveOriginalMarginsEvaluation.actual_margins_source_decomposition', 'RankerObjectiveOriginalMarginsEvaluation.actual_data_source_scalar_body_join', 'RankerObjectiveOriginalMarginsEvaluation.actual_factors_source_scalar_body_join', 'RankerObjectiveOriginalMarginsEvaluation.dot_source_success', 'RankerObjectiveOriginalMarginsEvaluation.margins_source_success', 'RankerObjectiveOriginalMarginsEvaluation.actual_weights_binding', 'RankerObjectiveOriginalMarginsEvaluation.actual_differences_binding', 'RankerObjectiveOriginalMarginsEvaluation.actual_margins_eval_success'], 'source': {'bytes': 8689, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-candidate-20261006-06/math/OriginalPrefixMarginsEvaluation.lean', 'sha256': '49f1b93418d59895a0e76f764b33703ef0a4e7eaacc480793041b1a65ac54c82'}}, 'lean-original-prefix-loss-regularizer-01': {'direct_imports': ['OriginalPrefixMarginsEvaluation'], 'module': 'OriginalPrefixLossRegularizerEvaluation', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01', 'lean-container-evaluation-bridge-01', 'lean-source-scalar-lift-01', 'lean-original-prefix-parts-01', 'lean-source-container-success-01', 'lean-original-prefix-margins-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01', 'queries': ['RankerObjectiveOriginalLossRegularizerEvaluation.data_source_success', 'RankerObjectiveOriginalLossRegularizerEvaluation.actual_regularizer_source_decomposition', 'RankerObjectiveOriginalLossRegularizerEvaluation.regularizer_source_success', 'RankerObjectiveOriginalLossRegularizerEvaluation.after_margins_margins_binding', 'RankerObjectiveOriginalLossRegularizerEvaluation.after_margins_weights_binding', 'RankerObjectiveOriginalLossRegularizerEvaluation.after_data_weights_binding', 'RankerObjectiveOriginalLossRegularizerEvaluation.after_data_margins_binding', 'RankerObjectiveOriginalLossRegularizerEvaluation.after_regularizer_margins_binding', 'RankerObjectiveOriginalLossRegularizerEvaluation.actual_data_eval_success', 'RankerObjectiveOriginalLossRegularizerEvaluation.actual_regularizer_eval_success'], 'source': {'bytes': 9623, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-candidate-20261006-03/math/OriginalPrefixLossRegularizerEvaluation.lean', 'sha256': '8c182dc85278ee1d6b2e2be2f11e14597b29af10cb12614dfc730aeaa7d5ffca'}}, 'lean-original-prefix-factors-01': {'direct_imports': ['OriginalPrefixLossRegularizerEvaluation'], 'module': 'OriginalPrefixFactorsEvaluation', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01', 'lean-container-evaluation-bridge-01', 'lean-source-scalar-lift-01', 'lean-original-prefix-parts-01', 'lean-source-container-success-01', 'lean-original-prefix-margins-01', 'lean-original-prefix-loss-regularizer-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01', 'queries': ['RankerObjectiveOriginalFactorsEvaluation.factors_source_success', 'RankerObjectiveOriginalFactorsEvaluation.after_factors_factors_binding', 'RankerObjectiveOriginalFactorsEvaluation.actual_factors_eval_success'], 'source': {'bytes': 3272, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-candidate-20261006-03/math/OriginalPrefixFactorsEvaluation.lean', 'sha256': '9ffe9f4bbc0729c20f6b3568ed6298a8df3f2a8be806ab5b71a3c701c9f6c242'}}, 'lean-original-prefix-gradient-01': {'direct_imports': ['OriginalPrefixFactorsEvaluation'], 'module': 'OriginalPrefixGradientEvaluation', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01', 'lean-container-evaluation-bridge-01', 'lean-source-scalar-lift-01', 'lean-original-prefix-parts-01', 'lean-source-container-success-01', 'lean-original-prefix-margins-01', 'lean-original-prefix-loss-regularizer-01', 'lean-original-prefix-factors-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01', 'queries': ['RankerObjectiveOriginalGradientEvaluation.actual_gradient_source_decomposition', 'RankerObjectiveOriginalGradientEvaluation.summed_rows_source_success', 'RankerObjectiveOriginalGradientEvaluation.gradient_coordinate_source_success', 'RankerObjectiveOriginalGradientEvaluation.gradient_source_success', 'RankerObjectiveOriginalGradientEvaluation.after_factors_weights_binding', 'RankerObjectiveOriginalGradientEvaluation.after_factors_differences_binding', 'RankerObjectiveOriginalGradientEvaluation.actual_gradient_eval_success'], 'source': {'bytes': 13650, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-candidate-20261006-03/math/OriginalPrefixGradientEvaluation.lean', 'sha256': '3b2e15d58e0e82a6305f8106a0f484c5576719873b1fc0f972ad10582ec45798'}}, 'lean-original-prefix-record-01': {'direct_imports': ['OriginalPrefixGradientEvaluation'], 'module': 'OriginalPrefixRecordEvaluation', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01', 'lean-container-evaluation-bridge-01', 'lean-source-scalar-lift-01', 'lean-original-prefix-parts-01', 'lean-source-container-success-01', 'lean-original-prefix-margins-01', 'lean-original-prefix-loss-regularizer-01', 'lean-original-prefix-factors-01', 'lean-original-prefix-gradient-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01', 'queries': ['RankerObjectiveOriginalRecordEvaluation.actual_prefix_suffix_decomposition', 'RankerObjectiveOriginalRecordEvaluation.eval_source_let_success', 'RankerObjectiveOriginalRecordEvaluation.actual_record_fields_eval_success', 'RankerObjectiveOriginalRecordEvaluation.actual_prefix_eval_success'], 'source': {'bytes': 7929, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-candidate-20261006-03/math/OriginalPrefixRecordEvaluation.lean', 'sha256': 'fbc3d5a8e80e21f15d3ab062d386621ae71698ea0f830aee9cdaa508671f9b5a'}}, 'lean-original-prefix-model-projection-01': {'direct_imports': ['OriginalPrefixRecordEvaluation'], 'module': 'OriginalPrefixModelProjection', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01', 'lean-container-evaluation-bridge-01', 'lean-source-scalar-lift-01', 'lean-original-prefix-parts-01', 'lean-source-container-success-01', 'lean-original-prefix-margins-01', 'lean-original-prefix-loss-regularizer-01', 'lean-original-prefix-factors-01', 'lean-original-prefix-gradient-01', 'lean-original-prefix-record-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01', 'queries': ['RankerObjectiveOriginalModelProjection.source_L2_eq_originalRealMu', 'RankerObjectiveOriginalModelProjection.exact_numeric_objective_eq_model', 'RankerObjectiveOriginalModelProjection.exact_computed_gradient_eq_model', 'RankerObjectiveOriginalModelProjection.actual_numeric_objective_projection_eq', 'RankerObjectiveOriginalModelProjection.actual_computed_gradient_projection_eq'], 'source': {'bytes': 5170, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-candidate-20261006-03/math/OriginalPrefixModelProjection.lean', 'sha256': 'bb11d4d91d3d613ba5e373f7702be26c270d5d7f2aabec50b77629966befafd6'}}, 'lean-generated-numeric-slices-relay-01': {'direct_imports': ['TypedNumericSlice'], 'module': 'GeneratedNumericSlices', 'prior_modes': [], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-qualification-20261006-01', 'queries': ['RankerSourceSemanticsGenerated.emitted_dot_compiles', 'RankerSourceSemanticsGenerated.emitted_update_compiles', 'RankerSourceSemanticsGenerated.emitted_dot_compiler_commutes', 'RankerSourceSemanticsGenerated.emitted_update_compiler_commutes', 'RankerSourceSemanticsGenerated.emitted_dot_projection', 'RankerSourceSemanticsGenerated.emitted_update_projection', 'RankerSourceSemanticsGenerated.emitted_originalRealStep_join'], 'source': {'bytes': 3129, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-candidate-20261006-01/math/GeneratedNumericSlices.lean', 'sha256': '841cc68dd9ef75e76398804ca5c0f2e33cef100611f2c3755c26ee24c9491297'}}, 'lean-original-computed-source-update-01': {'direct_imports': ['OriginalPrefixModelProjection', 'GeneratedNumericSlices'], 'module': 'OriginalComputedSourceUpdate', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01', 'lean-container-semantics-01', 'lean-container-compiler-01', 'lean-container-preservation-01', 'lean-container-generated-prefix-01', 'lean-container-evaluation-bridge-01', 'lean-source-scalar-lift-01', 'lean-original-prefix-parts-01', 'lean-source-container-success-01', 'lean-original-prefix-margins-01', 'lean-original-prefix-loss-regularizer-01', 'lean-original-prefix-factors-01', 'lean-original-prefix-gradient-01', 'lean-original-prefix-record-01', 'lean-original-prefix-model-projection-01', 'lean-generated-numeric-slices-relay-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-computed-update-qualification-20261006-01', 'queries': ['RankerObjectiveOriginalComputedSourceUpdate.actual_computed_update_with_compilation_eq', 'RankerObjectiveOriginalComputedSourceUpdate.actual_computed_update_eq', 'RankerObjectiveOriginalComputedSourceUpdate.actual_computed_update_success_length', 'RankerObjectiveOriginalComputedSourceUpdate.actual_computed_update_has_safe_descent'], 'source': {'bytes': 5193, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-computed-update-candidate-20261006-01/math/OriginalComputedSourceUpdate.lean', 'sha256': 'f20c16c6b4de708cba347581e5f44e8dee80e00bd65839b5dac8bcc45f473287'}}}
DEPENDENCY_SOURCE_GATES={'lean-container-generated-prefix-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-source-review-20261006-01/review-receipt-01.json', 'bytes': 53525, 'sha256': 'e2bd9c412ca4545a68a85ebe33560522ce53ce7932f9c7f840bca1137f0ae7a6'}, 'lean-container-evaluation-bridge-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-prefix-source-review-20261006-01/review-receipt-01.json', 'bytes': 53525, 'sha256': 'e2bd9c412ca4545a68a85ebe33560522ce53ce7932f9c7f840bca1137f0ae7a6'}, 'lean-original-prefix-parts-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-source-model-source-review-20261006-01/review-receipt-02.json', 'bytes': 26037, 'sha256': 'd2f8de49eee73c2b00615501a855b206a46ec80b3fd318ed47efa81b51fa72c8'}, 'lean-source-scalar-lift-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-source-model-source-review-20261006-01/review-receipt-02.json', 'bytes': 26037, 'sha256': 'd2f8de49eee73c2b00615501a855b206a46ec80b3fd318ed47efa81b51fa72c8'}, 'lean-source-container-success-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-evaluation-source-review-20261006-01/review-receipt-01.json', 'bytes': 16600, 'sha256': '56d36c189a4ac0e7c93119b21363a78bb3ace9fe59a169da166e4f43c59a8fb5'}, 'lean-original-prefix-margins-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-evaluation-source-review-20261006-01/review-receipt-05.json', 'bytes': 27694, 'sha256': 'aa11be3fe43f2561cdf4cc00c6a2cfa38dd8b87b69cbd9cbd003a83242315dfc'}, 'lean-original-prefix-loss-regularizer-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-tail-evaluation-source-review-20261006-01/review-receipt-01.json', 'bytes': 46098, 'sha256': '128bc8a8ddcafef02867083542ec6a83c58ad1ae3e73d8ef76e8b7830eb38c6c'}, 'lean-original-prefix-factors-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-tail-evaluation-source-review-20261006-01/review-receipt-01.json', 'bytes': 46098, 'sha256': '128bc8a8ddcafef02867083542ec6a83c58ad1ae3e73d8ef76e8b7830eb38c6c'}, 'lean-original-prefix-gradient-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-tail-evaluation-source-review-20261006-01/review-receipt-01.json', 'bytes': 46098, 'sha256': '128bc8a8ddcafef02867083542ec6a83c58ad1ae3e73d8ef76e8b7830eb38c6c'}, 'lean-original-prefix-record-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-tail-evaluation-source-review-20261006-01/review-receipt-01.json', 'bytes': 46098, 'sha256': '128bc8a8ddcafef02867083542ec6a83c58ad1ae3e73d8ef76e8b7830eb38c6c'}, 'lean-original-prefix-model-projection-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-tail-evaluation-source-review-20261006-01/review-receipt-01.json', 'bytes': 46098, 'sha256': '128bc8a8ddcafef02867083542ec6a83c58ad1ae3e73d8ef76e8b7830eb38c6c'}, 'lean-generated-numeric-slices-relay-01': {'path': '/home/barberb/lift_coding/maintenance/ranker-source-update-owned-relay-source-review-20261006-01/review-receipt-01.json', 'bytes': 18984, 'sha256': '57f85f42ccd470e30a007442ad56baecaa121edfbbe6765058a4680cf9e808e7'}}
ACCEPTED_CHECK_PINS={'lean-container-generated-prefix-01': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01/evidence/lean-container-generated-prefix-01/check-result.json', 'bytes': 16026, 'sha256': '2194c2152ffaaffb94099dd1a4306c1c08fec22fce1077caef22196ee8441c3e'}, 'lean-container-evaluation-bridge-01': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-prefix-qualification-20261006-01/evidence/lean-container-evaluation-bridge-01/check-result.json', 'bytes': 15476, 'sha256': 'e90c43fb19b44daf5d2e9d5fee9506204c43154a7d21e59a7f739767de0184ed'}, 'lean-original-prefix-parts-01': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-qualification-20261006-02/evidence/lean-original-prefix-parts-01/check-result.json', 'bytes': 13909, 'sha256': '396f30b42dab78ebc88229e0bdef551779ad43a6b1f41f94558043be766e4ae0'}, 'lean-source-scalar-lift-01': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-source-model-qualification-20261006-02/evidence/lean-source-scalar-lift-01/check-result.json', 'bytes': 14701, 'sha256': '87ffaddd1a02986f5c0f116233d56caa8edb983244461f437454db1dbb1fdc14'}, 'lean-source-container-success-01': {'bytes': 15589, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-qualification-20261006-01/evidence/lean-source-container-success-01/check-result.json', 'sha256': '27e9598373b6831812abe235b5a806f5183b1b68876e3e1d93c9695eea3444cc'}, 'lean-original-prefix-margins-01': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-evaluation-qualification-20261006-05/evidence/lean-original-prefix-margins-01/check-result.json', 'bytes': 15670, 'sha256': 'b9363dd6d3471b729edacd79aaca7c61f245bc9526d2197f90d50af380d64621'}, 'lean-original-prefix-loss-regularizer-01': {'bytes': 16808, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01/evidence/lean-original-prefix-loss-regularizer-01/check-result.json', 'sha256': '63ca409a680346749b690cd68d39b6af989934f72f89f4fd73748fddee3e87e9'}, 'lean-original-prefix-factors-01': {'bytes': 13136, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01/evidence/lean-original-prefix-factors-01/check-result.json', 'sha256': '7611a30638a94a2fde29370de5c023a56a7e87f0c0be8f7cd35d72df03c5fa3f'}, 'lean-original-prefix-gradient-01': {'bytes': 16385, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01/evidence/lean-original-prefix-gradient-01/check-result.json', 'sha256': 'fe785641040df30f44f735d5d3c762435b20c1f90130bfa225b07781daaad04d'}, 'lean-original-prefix-record-01': {'bytes': 14354, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01/evidence/lean-original-prefix-record-01/check-result.json', 'sha256': '011d988f6105b96a776c6d350a58677511006b3cf19944105709a68ca9319258'}, 'lean-original-prefix-model-projection-01': {'bytes': 15994, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-tail-evaluation-qualification-20261006-01/evidence/lean-original-prefix-model-projection-01/check-result.json', 'sha256': '28bac4dd0aef6dcee6f2bafe46f77b46420631697224600b653369df16b2bddf'}, 'lean-generated-numeric-slices-relay-01': {'bytes': 12427, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-update-owned-relay-qualification-20261006-01/evidence/lean-generated-numeric-slices-relay-01/check-result.json', 'sha256': '250a8232ea550d373ed7595d93364f2a75db195be8225d218356b19f0c30735a'}}
CORE_PINS={'iteration/candidate-interface.json': {'bytes': 11318, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-finite-source-iteration-candidate-20261006-01/candidate-interface.json', 'sha256': '108733e22d56ee1241e29ec48260e3c9da3fcb9b5563cfd32b351b7744bcbd1b'}, 'iteration/math/OriginalComputedFiniteIteration.lean': {'bytes': 5468, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-finite-source-iteration-candidate-20261006-01/math/OriginalComputedFiniteIteration.lean', 'sha256': 'c5de75f08c00c4c3d4cabbce1df601795f56b04fcb1213a7ab86262380e633f8'}, 'iteration/obligations.json': {'bytes': 2302, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-finite-source-iteration-candidate-20261006-01/obligations.json', 'sha256': 'efdabe7d826d4d04ccb808a07de383b423e2d1044e21b3b15e2993d06f60291c'}, 'update/candidate-interface.json': {'bytes': 10345, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-computed-update-candidate-20261006-01/candidate-interface.json', 'sha256': 'fa11c560dde3a6536f9ca47c99b2b63faeca3f49f15815d7bafcdb1494dc756d'}, 'update/math/OriginalComputedSourceUpdate.lean': {'bytes': 5193, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-computed-update-candidate-20261006-01/math/OriginalComputedSourceUpdate.lean', 'sha256': 'f20c16c6b4de708cba347581e5f44e8dee80e00bd65839b5dac8bcc45f473287'}, 'update/obligations.json': {'bytes': 2295, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-computed-update-candidate-20261006-01/obligations.json', 'sha256': 'fa1bb0a973a3bbbe7faba7ff337ce4ac0f087706d68a93c065e170590c787695'}}
CONTEXT_PINS=[{'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-computed-update-qualification-20261006-01/module-map-01.json', 'bytes': 3660, 'sha256': '74a3009227287475df31c08ebdd3def1636d53c55c7960a07adde69011e2f1ba'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-finite-source-iteration-qualification-20261006-01/module-map-01.json', 'bytes': 3660, 'sha256': '74a3009227287475df31c08ebdd3def1636d53c55c7960a07adde69011e2f1ba'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-computed-update-qualification-20261006-01/candidate-pins-01.json', 'bytes': 1814, 'sha256': '0dcaedca036b93e1f9f24e70f3a625939463bc4bf32d2ef10f7f2331abdd8a93'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-source-update-owned-relay-input-review-20261006-01/lean-generated-numeric-slices-relay-01-completed-readback-01.json', 'bytes': 4064, 'sha256': '31ed25a78e1c8c99f32639a9f9d064facf8ab9685f7dca592869365230e74318'}, {'bytes': 4892, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-tail-evaluation-input-review-20261006-01/lean-original-prefix-loss-regularizer-01-completed-readback-01.json', 'sha256': 'b1e1efc599332ecba2fe69bb1725f4a9ae00fb2f20e0d4cda5a4442080dbb8d6'}, {'bytes': 3829, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-tail-evaluation-input-review-20261006-01/lean-original-prefix-factors-01-completed-readback-01.json', 'sha256': '27ec7c95436a881ae356d289ce4ea4608e96da7936d1b7399d9654c1068f5190'}, {'bytes': 4865, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-tail-evaluation-input-review-20261006-01/lean-original-prefix-gradient-01-completed-readback-01.json', 'sha256': '82d8a23e27fc759e17189bb3568e04496c10bc927a3eaee278f348e9ec4fbc81'}, {'bytes': 4248, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-tail-evaluation-input-review-20261006-01/lean-original-prefix-record-01-completed-readback-01.json', 'sha256': 'd4409ab7a2700072e70fbcebc3891e11e26b6d418ead53c1ce38e9688bd47188'}, {'bytes': 5139, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-tail-evaluation-input-review-20261006-01/lean-original-prefix-model-projection-01-completed-readback-01.json', 'sha256': '4ef93f82220a5926bf2b052cedced0c880e239ef33d3827d26fe17f4f3ace351'}]
PRIOR_IMPORTS=[{'check_result': {'bytes': 14071, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-source-01/check-result.json', 'sha256': 'ca7ed3da92fbae947f595bfde1a8eb1025bc9758ebdd58eaf11210b2d125c0bf'}, 'mode': 'lean-container-source-01'}, {'check_result': {'bytes': 15524, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-typed-01/check-result.json', 'sha256': 'cfb690034025ad99470dad89ab537952955ddb4b14b1ed3675bf8181dfcfad63'}, 'mode': 'lean-container-typed-01'}, {'check_result': {'bytes': 13707, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-semantics-01/check-result.json', 'sha256': '8650075e9f209aa2d61d284d043b51200a866611703ad40739ce29af3f05d62b'}, 'mode': 'lean-container-semantics-01'}, {'check_result': {'bytes': 12509, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-compiler-01/check-result.json', 'sha256': '43276551bd5488e8575cd07a810c5156f6178d75b4924a0bcf677906d2e520df'}, 'mode': 'lean-container-compiler-01'}, {'check_result': {'bytes': 24686, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-preservation-01/check-result.json', 'sha256': '803036eae98f65a373574b00b3434edcdbcf43847be65e7c7e799e0c99dee0b8'}, 'mode': 'lean-container-preservation-01'}]
SOURCE_GATE={'path': '/home/barberb/lift_coding/maintenance/ranker-objective-computed-update-iteration-source-review-20261006-01/review-receipt-01.json', 'bytes': 26355, 'sha256': '5dda9a0e1087ef077c2cdc59a2bde6b09731de13aefc14f454ba7576c75989b7'}
STRICT_GUARD_COUNT=3540
BASE_IMPORT_NAMES=['ObjectiveScalarIR', 'RealStableFactor', 'TypedNumericSlice', 'ObjectiveContainerCore', 'ObjectivePrefixIR', 'RealGapContraction']
NATIVE_LIMITS={'wall_seconds': 20, 'cpu_seconds': 20, 'output_bytes': 65536, 'workspace_bytes': 16777216}
ROOT_LEASE={'cpu_slots': 1, 'memory_mb': 2048, 'child_process_slots': 4}
PRESSURE={'memory_percent': 2.0, 'cpu_percent': 50.0, 'io_percent': 10.0}
AUTHORITY={k:False for k in ('proof_authority','execution_authority','completion_authority','planner_activation')}


def _parent():
    p=Path(PR_PIN['path'])
    if p.resolve(strict=True)!=p or p.is_symlink():raise ValueError('canonical reviewed relay parent required')
    with p.open('rb') as stream:raw=stream.read(PR_PIN['bytes']+1)
    if len(raw)!=PR_PIN['bytes'] or hashlib.sha256(raw).hexdigest()!=PR_PIN['sha256']:
        raise ValueError('immutable reviewed relay parent differs')
    ns={'__file__':str(p),'__name__':'held_computed_update_relay_parent_file_helpers'}
    exec(compile(raw,str(p),'exec'),ns)
    ns['exact'](PR_PIN);gate=ns['document'](PR_TOOLING_GATE)
    ns['need'](gate['status']=='passed_source_only' and gate['findings']==[]
        and PR_PIN in gate['reviewed_sources'] and gate['reviewed_modules']==ns['MODULES']
        and all(gate[k] is False for k in AUTHORITY),'exact reviewed relay source and tooling required')
    return ns

PR=_parent()
PT=PR['PT']
need,pin,exact,fixed,parse,document,write,read_pin,verify_held=(PR[k] for k in
    ('need','pin','exact','fixed','parse','document','write','read_pin','verify_held'))
BASE_PROFILE=PR['BASE_PROFILE']


def module(mode):
    need(type(mode) is str and mode in MODULES,'only exact computed-update and finite-iteration modes admitted')
    return MODULES[mode]


def dependency_module(mode):
    need(type(mode) is str and mode in DEPENDENCY_MODULES,'only finite genuine parents and computed-update dependency admitted')
    return DEPENDENCY_MODULES[mode]


def accepted_update_before_iteration():
    selected=MODULES['lean-original-computed-source-update-01']
    path=Path(selected['qualification_root'])/'evidence'/'lean-original-computed-source-update-01'/'check-result.json'
    check=document(pin(path))
    need(check['status']=='passed' and check['native_lean_returncode']==0
        and check['native_invocations']==check['native_lean_invocations']==1
        and check['source']['bytes']==selected['source']['bytes']
        and check['source']['sha256']==selected['source']['sha256']
        and [r['theorem'] for r in check['theorem_axiom_output']]==selected['queries']
        and len(check['compiled_artifacts'])==1 and all(check[k] is False for k in AUTHORITY),
        'actual source-bound four-query update acceptance required before iteration; no prospective or failed module admitted')
    return check


def source_gate(mode):
    selected=module(mode)
    need(bool(SOURCE_GATE) and STRICT_GUARD_COUNT>3370,'actual six-file combined source gate and exact denominator not frozen')
    gate=document(SOURCE_GATE)
    need(gate['status']=='passed_source_only' and gate['findings']==[]
        and gate['candidate_pins']==CORE_PINS and gate['reviewed_modules']==MODULES
        and gate['candidate_compiled'] is False and gate['actual_new_qualified_queries']==0
        and all(gate[k] is False for k in AUTHORITY),'exact six-file two-mode independent source gate required')
    for row in CORE_PINS.values():exact(row)
    need(selected['source'] in CORE_PINS.values(),'selected source absent from combined independent gate')
    if mode=='lean-original-computed-finite-iteration-01':accepted_update_before_iteration()
    return gate


def seal_census(row):
    return PT['seal_census'](row)


def complete_guard_union():
    need(bool(SOURCE_GATE) and STRICT_GUARD_COUNT>3370,'actual combined source gate and exact denominator not frozen')
    # The relay parent recomputes3370, including one fresh3359 tail traversal.
    # Reuse only those freshly computed rows in this read phase; reproduce all
    # six relay-validator comparisons and the common fresh tail-request joins.
    # No body cache survives any preparation/audit/pre/post-native boundary.
    parent_rows,fresh_tail_inherited=PR['complete_guard_union']()
    need(len(parent_rows)==PR['STRICT_GUARD_COUNT']==3370,'exact complete reviewed relay cohort required')
    relay_request=document(RELAY_REQUEST)
    need(relay_request['strict_old_inputs']==parent_rows
        and relay_request['strict_guard_count']==PR['STRICT_GUARD_COUNT']
        and relay_request['protected_live_sources']==fresh_tail_inherited['protected_live_sources']
        and relay_request['original_checkout_guards']==fresh_tail_inherited['original_checkout_guards']
        and relay_request['prior_language_context_request']==PR['PRIOR_REQUEST']
        and relay_request['prior_language_context_seal']==PR['PRIOR_SEAL']
        and all(relay_request[k] is False for k in AUTHORITY),
        'exact six relay-validator comparisons from freshly recomputed complete cohort required')
    inherited=document(PRIOR_REQUEST)
    need(inherited['strict_old_inputs']==fresh_tail_inherited['strict_old_inputs']
        and inherited['strict_guard_count']==fresh_tail_inherited['strict_guard_count']==PT['STRICT_GUARD_COUNT']==3359
        and inherited['protected_live_sources']==fresh_tail_inherited['protected_live_sources']
        and inherited['original_checkout_guards']==fresh_tail_inherited['original_checkout_guards']
        and inherited['prior_language_context_request']==PT['PRIOR_REQUEST']
        and inherited['prior_language_context_seal']==PT['PRIOR_SEAL']
        and all(inherited[k] is False for k in AUTHORITY),
        'actual sealed TailModel request joins exactly the freshly validated common3359 cohort')
    rows={r['path']:r for r in parent_rows}
    additions=[PR_PIN,PR_TOOLING_GATE,PRIOR_REQUEST,RELAY_REQUEST,*CONTEXT_PINS,*CORE_PINS.values(),SOURCE_GATE]
    for scope in CLOSED_PARENT_SCOPES:
        seal=seal_census(scope['seal'])
        need(all(seal[k]==scope[k] for k in ('scope_root','regular_file_count','regular_file_bytes','qualified_theorem_queries'))
            and all(seal[k] is False for k in AUTHORITY),'complete genuine sealed parent population required')
        additions.extend([*seal['files'],scope['seal']])
        if 'review' in scope:
            review=document(scope['review']);need(seal['review']==scope['review'] and all(review[k] is False for k in AUTHORITY),
                'exact sealed genuine parent review required')
            if 'prefix-tail-evaluation-qualification' in scope['scope_root']:
                need(review['status']=='passed_scoped_exact_real_objective_and_computed_gradient'
                    and review['strict_guard_count']==3359 and review['qualified_native_checks']==5
                    and review['qualified_theorem_queries']==29 and review['total_primary_scoped_accepted_queries']==76
                    and review['actual_numeric_objective_and_computed_gradient_model_equivalence_proved'] is True
                    and review['two_actual_standard_axiom_reports_per_query'] is True
                    and {r['mode']:r['check_result'] for r in review['completed_modes']}==
                        {m:ACCEPTED_CHECK_PINS[m] for m in PT['MODE_ORDER']},
                    'actual five-stage source-bound29-query numeric prefix model parent required')
            else:
                need(review['status']=='passed_scoped_owned_relay' and review['strict_guard_count']==3370
                    and review['qualified_native_checks']==1 and review['qualified_theorem_queries']==7
                    and review['modern_owned_relay_admitted'] is True and review['new_mathematical_statements']==0
                    and review['historical_transitive_one_report_support_preserved'] is True
                    and review['check_result']==ACCEPTED_CHECK_PINS['lean-generated-numeric-slices-relay-01'],
                    'actual modern-owned exact-copy relay7 parent required; historical policy unchanged')
    for row in additions:
        need(row['path'] not in rows or rows[row['path']]==row,'overlapping guarded body differs')
        exact(row);rows[row['path']]=row
    need(len(rows)==STRICT_GUARD_COUNT,'exact combined additive guard denominator differs')
    return [rows[p] for p in sorted(rows)],inherited


def validate_guard_union(request):
    rows,inherited=complete_guard_union()
    need(request['strict_old_inputs']==rows and request['strict_guard_count']==STRICT_GUARD_COUNT
        and request['protected_live_sources']==inherited['protected_live_sources']
        and request['original_checkout_guards']==inherited['original_checkout_guards']
        and request['prior_language_context_request']==PRIOR_REQUEST
        and request['prior_language_context_seal']==PRIOR_SEAL,'exact full Tail/Relay closure and combined source population required')


def qualified_module(name,profile,check_row=None):
    return PT['qualified_module'](name,profile,check_row)

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
        need(stage_root in (ROOT,ROOT.with_name('ranker-objective-prefix-evaluation-qualification-20261006-01'),
                            ROOT.with_name('ranker-objective-prefix-evaluation-qualification-20261006-05'),
                            ROOT.with_name('ranker-objective-container-prefix-qualification-20261006-01'),
                            ROOT.with_name('ranker-objective-source-model-qualification-20261006-02'),
                            ROOT.with_name('ranker-objective-prefix-tail-evaluation-qualification-20261006-01'),
                            ROOT.with_name('ranker-source-update-owned-relay-qualification-20261006-01'),
                            ROOT.with_name('ranker-objective-computed-update-qualification-20261006-01')),
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
        source_gate_row=(SOURCE_GATE if row['mode']=='lean-original-computed-source-update-01' else DEPENDENCY_SOURCE_GATES[row['mode']]);gate=document(source_gate_row)
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
    need(type(imports) is list and len(imports) in (17,18) and imports[:5]==PRIOR_IMPORTS,
         'fixed five plus all genuine Tail/Relay parents and optional actual computed update required')
    modes=[r['mode'] for r in imports]
    need(modes in [MODULES[m]['prior_modes'] for m in MODE_ORDER],
        'only exact declared17/18 parent prefixes admitted')
    if len(imports)==18:accepted_update_before_iteration()
    extended,parent=PT['P9']['P8']['P7']['P6']['P5']['P4']['P3']['import_extension'](base,imports[:5])
    extended,new=_append_imports(extended,imports[5:])
    extended['staged_qualified_imports']=parent+new
    return extended,parent+new
