-- SOURCE-ONLY CANDIDATE: original raw source SHA256 3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a
-- dot expression AST SHA256 a40bd993387cc9aa7cf6392f126c30d9e7a56f7277ddaf3532553b560366ffe5
-- update assignment AST SHA256 18f6dae8d8b26c08e101018837033db979d20c4bb5b65cb80119a4fd03084c4b
-- update function context AST SHA256 5b87aa5ce21daf1439ed8d51f37557e6aba962130fd4f8732d149cea7ca2ac5a
-- No Python/Float, objective, preparation, or full training equivalence is asserted.
import TypedNumericSlice

namespace RankerSourceSemanticsGenerated
noncomputable section
open RankerSourceSemantics

def emittedDotBody : SourceScalar := (.mul (.var "x") (.var "y"))
def emittedUpdateBody : SourceScalar := (.sub (.var "w") (.mul (.var "step") (.var "g")))

theorem emitted_dot_compiles :
    compile dotScope emittedDotBody = some compiledDotBody := by rfl

theorem emitted_update_compiles :
    compile updateScope emittedUpdateBody = some compiledUpdateBody := by rfl

theorem emitted_dot_compiler_commutes (environment : Fin 2 → ℝ) :
    (compile dotScope emittedDotBody).map (fun body => eval body environment) =
      evalSource (fun name => (dotScope name).map environment) emittedDotBody := by
  exact compile_eval_commutes dotScope environment emittedDotBody

theorem emitted_update_compiler_commutes (environment : Fin 3 → ℝ) :
    (compile updateScope emittedUpdateBody).map (fun body => eval body environment) =
      evalSource (fun name => (updateScope name).map environment) emittedUpdateBody := by
  exact compile_eval_commutes updateScope environment emittedUpdateBody

theorem emitted_dot_projection {m : ℕ} (left right : Fin m → ℝ) :
    runDotSource emittedDotBody (List.ofFn left) (List.ofFn right) =
      some (RankerRealCurvature.dot left right) := by
  exact source_dot_literal_eq emittedDotBody emitted_dot_compiles left right

theorem emitted_update_projection {m : ℕ} (step : ℝ) (weights gradient : Fin m → ℝ) :
    runUpdateSource emittedUpdateBody step (List.ofFn weights) (List.ofFn gradient) =
      some (List.ofFn (fun i => weights i - step * gradient i)) := by
  exact source_update_literal_eq emittedUpdateBody emitted_update_compiles step weights gradient

theorem emitted_originalRealStep_join (weights : Fin 80 → ℝ) :
    runUpdateSource emittedUpdateBody RankerRealCurvature.originalRealEta
      (List.ofFn weights)
      (List.ofFn (RankerRealCurvature.realCoordinateGradient
        RankerRealCurvature.originalRealMu RankerRealCurvature.originalRealDifferences weights)) =
      some (List.ofFn (RankerRealCurvature.realGradientStep
        RankerRealCurvature.originalRealMu RankerRealCurvature.originalRealEta
        RankerRealCurvature.originalRealDifferences weights)) := by
  simpa only [RankerRealCurvature.realGradientStep] using
    emitted_update_projection RankerRealCurvature.originalRealEta weights
      (RankerRealCurvature.realCoordinateGradient RankerRealCurvature.originalRealMu
        RankerRealCurvature.originalRealDifferences weights)

#print axioms emitted_dot_compiles
#print axioms emitted_update_compiles
#print axioms emitted_dot_compiler_commutes
#print axioms emitted_update_compiler_commutes
#print axioms emitted_dot_projection
#print axioms emitted_update_projection
#print axioms emitted_originalRealStep_join

end
end RankerSourceSemanticsGenerated
