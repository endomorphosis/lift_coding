-- UNQUALIFIED SOURCE-ONLY CANDIDATE; no native run has occurred.
-- Source SHA256 3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a
-- _objective AST SHA256 129da31ae6856167478c7f030a059d0f477b8362bb8fa478221eac7bac6031c2
-- Stable loss AST SHA256 b71027e5d37d1a5b5b574a4b880a0857f0885dbc19c81dff3e652f8f7c76287e
-- Stable factor AST SHA256 a5f60c17cb8efc0869ec1ac4001c04c1b43f67d7d38bc025cbb87061247d70aa
-- Exact-real scalar projection only; Python/Float/full objective/gradient/training remain open.
import ObjectiveScalarIR

namespace RankerObjectiveIRGenerated
noncomputable section
open RankerObjectiveIR

def emittedStableLossSource : SourceScalar := (.add (.max (.num (0 : Rat)) (.neg (.var "z"))) (.log1p (.exp (.neg (.abs (.var "z"))))))
def emittedStableFactorSource : SourceScalar := (.ifNonneg (.var "z") (.div (.exp (.neg (.var "z"))) (.add (.num (1 : Rat)) (.exp (.neg (.var "z"))))) (.div (.num (1 : Rat)) (.add (.num (1 : Rat)) (.exp (.var "z")))))
def emittedSourceL2 : SourceScalar := (.num ((5764607523034235 : Rat) / 576460752303423488))
def emittedScalarScope (name : String) : Option (Fin 1) :=
  if name = "z" then some 0 else none

theorem emitted_compile_scalar_sound {slots : Nat}
    (scope : String → Option (Fin slots)) (environment : Fin slots → Real)
    (source : SourceScalar) (program : ScalarIR slots)
    (accepted : compileScalar scope source = .ok program) :
    evalSourceExact (namesFromScope scope environment) source = evalExact program environment := by
  exact RankerObjectiveIR.compile_scalar_sound
    (scope := scope) (environment := environment) (source := source)
    (program := program) (accepted := accepted)

theorem emitted_compile_refuses_unsupported {slots : Nat}
    (scope : String → Option (Fin slots)) (tag : String) :
    compileScalar scope (.unsupported tag) = .error (.unsupportedNode tag) := by
  rfl

theorem emitted_compile_refuses_unknown_name {slots : Nat}
    (scope : String → Option (Fin slots)) (name : String) (missing : scope name = none) :
    compileScalar scope (.var name) = .error (.unknownName name) := by
  simp only [compileScalar, missing]

theorem emitted_stableLoss_compiles :
    compileScalar emittedScalarScope emittedStableLossSource = .ok stableLossBody := by
  rfl

theorem emitted_stableFactor_compiles :
    compileScalar emittedScalarScope emittedStableFactorSource = .ok stableFactorBody := by
  rfl

theorem emitted_stableLoss_eval_success (z : Real) :
    evalSourceExact (namesFromScope emittedScalarScope (scalarEnvironment z))
      emittedStableLossSource = .ok (RankerRealCurvature.realStablePairLoss z) := by
  rw [emitted_compile_scalar_sound emittedScalarScope (scalarEnvironment z)
    emittedStableLossSource stableLossBody emitted_stableLoss_compiles]
  exact RankerObjectiveIR.stableLoss_eval_success z

theorem emitted_stableFactor_eval_success (z : Real) :
    evalSourceExact (namesFromScope emittedScalarScope (scalarEnvironment z))
      emittedStableFactorSource = .ok (RankerRealCurvature.realStableLogisticP z) := by
  rw [emitted_compile_scalar_sound emittedScalarScope (scalarEnvironment z)
    emittedStableFactorSource stableFactorBody emitted_stableFactor_compiles]
  exact RankerObjectiveIR.stableFactor_eval_success z

theorem emitted_stableLoss_eq_pairLoss (z : Real) :
    evalSourceExact (namesFromScope emittedScalarScope (scalarEnvironment z))
      emittedStableLossSource = .ok (RankerRealCurvature.realPairLoss z) := by
  rw [emitted_stableLoss_eval_success, RankerRealCurvature.realStablePairLoss_eq]

theorem emitted_stableFactor_eq_logisticP (z : Real) :
    evalSourceExact (namesFromScope emittedScalarScope (scalarEnvironment z))
      emittedStableFactorSource = .ok (RankerRealCurvature.realLogisticP z) := by
  rw [emitted_stableFactor_eval_success, RankerRealCurvature.realStableLogisticP_eq]

#print axioms emitted_compile_scalar_sound
#print axioms emitted_compile_refuses_unsupported
#print axioms emitted_compile_refuses_unknown_name
#print axioms emitted_stableLoss_compiles
#print axioms emitted_stableFactor_compiles
#print axioms emitted_stableLoss_eval_success
#print axioms emitted_stableFactor_eval_success
#print axioms emitted_stableLoss_eq_pairLoss
#print axioms emitted_stableFactor_eq_logisticP

end
end RankerObjectiveIRGenerated

#print axioms _root_.RankerObjectiveIRGenerated.emitted_compile_scalar_sound
#print axioms _root_.RankerObjectiveIRGenerated.emitted_compile_refuses_unsupported
#print axioms _root_.RankerObjectiveIRGenerated.emitted_compile_refuses_unknown_name
#print axioms _root_.RankerObjectiveIRGenerated.emitted_stableLoss_compiles
#print axioms _root_.RankerObjectiveIRGenerated.emitted_stableFactor_compiles
#print axioms _root_.RankerObjectiveIRGenerated.emitted_stableLoss_eval_success
#print axioms _root_.RankerObjectiveIRGenerated.emitted_stableFactor_eval_success
#print axioms _root_.RankerObjectiveIRGenerated.emitted_stableLoss_eq_pairLoss
#print axioms _root_.RankerObjectiveIRGenerated.emitted_stableFactor_eq_logisticP
