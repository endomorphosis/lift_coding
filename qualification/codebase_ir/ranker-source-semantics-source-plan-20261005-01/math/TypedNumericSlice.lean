import OriginalRealDescent
import Mathlib.Algebra.BigOperators.Fin

set_option backward.isDefEq.respectTransparency false

/-!
UNCOMPILED SOURCE-ONLY CANDIDATE.

This module gives a small kernel-side compiler from a named arithmetic syntax
to scalar expressions with typed slots, and list semantics for two pure numeric
slices. Source literals are supplied by a separately reviewed host AST reader.
The host parser/source-hash/literal-emission binding is still a trust frontier.
The exact-real backend interprets math.fsum as an ordered real addition fold;
it does not model CPython Float, fsum, libm, exceptions or full source execution.
No source objective/gradient, preparation or training-loop theorem is asserted.
-/

namespace RankerSourceSemantics

noncomputable section

open scoped BigOperators

/-- Generic arithmetic source syntax. Every unrecognized node is explicit. -/
inductive SourceScalar where
  | num (q : ℚ)
  | var (name : String)
  | add (left right : SourceScalar)
  | sub (left right : SourceScalar)
  | mul (left right : SourceScalar)
  | unsupported (tag : String)
  deriving DecidableEq

/-- A slot cannot refer beyond the finite, typed scalar environment. -/
inductive ScalarIR (slots : ℕ) where
  | num (q : ℚ)
  | var (slot : Fin slots)
  | add (left right : ScalarIR slots)
  | sub (left right : ScalarIR slots)
  | mul (left right : ScalarIR slots)
  deriving DecidableEq

def combine {α β γ : Type} (f : α → β → γ) : Option α → Option β → Option γ
  | some a, some b => some (f a b)
  | _, _ => none

/-- Compilation preserves operator structure and refuses unknown variables. -/
def compile {slots : ℕ} (scope : String → Option (Fin slots)) :
    SourceScalar → Option (ScalarIR slots)
  | .num q => some (.num q)
  | .var name => (scope name).map ScalarIR.var
  | .add a b => combine ScalarIR.add (compile scope a) (compile scope b)
  | .sub a b => combine ScalarIR.sub (compile scope a) (compile scope b)
  | .mul a b => combine ScalarIR.mul (compile scope a) (compile scope b)
  | .unsupported _ => none

/-- Exact-real denotation follows the arithmetic tree without reassociation. -/
def eval {slots : ℕ} : ScalarIR slots → (Fin slots → ℝ) → ℝ
  | .num q, _ => (q : ℝ)
  | .var slot, environment => environment slot
  | .add a b, environment => eval a environment + eval b environment
  | .sub a b, environment => eval a environment - eval b environment
  | .mul a b, environment => eval a environment * eval b environment

/-- Partial source denotation: a refused syntax has no real result. -/
def evalSource (environment : String → Option ℝ) : SourceScalar → Option ℝ
  | .num q => some (q : ℝ)
  | .var name => environment name
  | .add a b => combine (· + ·) (evalSource environment a) (evalSource environment b)
  | .sub a b => combine (· - ·) (evalSource environment a) (evalSource environment b)
  | .mul a b => combine (· * ·) (evalSource environment a) (evalSource environment b)
  | .unsupported _ => none

/-- Preservation for every supported syntax, not only the desired two trees. -/
theorem compile_eval_commutes {slots : ℕ}
    (scope : String → Option (Fin slots)) (environment : Fin slots → ℝ)
    (source : SourceScalar) :
    (compile scope source).map (fun program => eval program environment) =
      evalSource (fun name => (scope name).map environment) source := by
  induction source with
  | num q => rfl
  | var name =>
    simp only [compile, evalSource]
    cases scope name <;> rfl
  | add a b ha hb =>
    simp only [compile, evalSource]
    rw [← ha, ← hb]
    cases compile scope a <;> cases compile scope b <;> rfl
  | sub a b ha hb =>
    simp only [compile, evalSource]
    rw [← ha, ← hb]
    cases compile scope a <;> cases compile scope b <;> rfl
  | mul a b ha hb =>
    simp only [compile, evalSource]
    rw [← ha, ← hb]
    cases compile scope a <;> cases compile scope b <;> rfl
  | unsupported tag => rfl

theorem compile_sound {slots : ℕ}
    (scope : String → Option (Fin slots)) (environment : Fin slots → ℝ)
    (source : SourceScalar) (program : ScalarIR slots)
    (accepted : compile scope source = some program) :
    evalSource (fun name => (scope name).map environment) source =
      some (eval program environment) := by
  simpa only [accepted, Option.map_some] using
    (compile_eval_commutes scope environment source).symm

theorem compile_refuses_unsupported {slots : ℕ}
    (scope : String → Option (Fin slots)) (tag : String) :
    compile scope (.unsupported tag) = none := rfl

theorem compile_refuses_unknown_name {slots : ℕ}
    (scope : String → Option (Fin slots)) (name : String)
    (unknown : scope name = none) :
    compile scope (.var name) = none := by
  simp only [compile, unknown, Option.map_none]

def dotScope (name : String) : Option (Fin 2) :=
  if name = "x" then some 0 else if name = "y" then some 1 else none

def updateScope (name : String) : Option (Fin 3) :=
  if name = "w" then some 0 else if name = "g" then some 1
  else if name = "step" then some 2 else none

/-- These are renderer interface examples. Actual AST-derived literals must be
emitted separately and must prove the same structural compilation equations. -/
def dotSourceBody : SourceScalar := .mul (.var "x") (.var "y")

def updateSourceBody : SourceScalar :=
  .sub (.var "w") (.mul (.var "step") (.var "g"))

def compiledDotBody : ScalarIR 2 := .mul (.var 0) (.var 1)

def compiledUpdateBody : ScalarIR 3 :=
  .sub (.var 0) (.mul (.var 2) (.var 1))

theorem compiled_dot_body : compile dotScope dotSourceBody = some compiledDotBody := by
  rfl

theorem compiled_update_body :
    compile updateScope updateSourceBody = some compiledUpdateBody := by
  rfl

def pairEnvironment (x y : ℝ) (slot : Fin 2) : ℝ := if slot = 0 then x else y

def updateEnvironment (w g step : ℝ) (slot : Fin 3) : ℝ :=
  if slot = 0 then w else if slot = 1 then g else step

/-- Explicit left-to-right exact-real backend chosen for the fsum call. -/
def orderedFsum (values : List ℝ) : ℝ := values.foldl (· + ·) 0

theorem orderedFsum_eq_sum (values : List ℝ) : orderedFsum values = values.sum := by
  simpa only [orderedFsum] using (List.sum_eq_foldl (xs := values)).symm

/-- Generic zipped-body semantics; unequal lists stop at their shorter length. -/
def zipBody (body : ScalarIR 2) (left right : List ℝ) : List ℝ :=
  List.zipWith (fun x y => eval body (pairEnvironment x y)) left right

def zipBodyWithScalar (body : ScalarIR 3) (parameter : ℝ)
    (left right : List ℝ) : List ℝ :=
  List.zipWith (fun w g => eval body (updateEnvironment w g parameter)) left right

theorem zipBody_length (body : ScalarIR 2) (left right : List ℝ) :
    (zipBody body left right).length = min left.length right.length := by
  exact List.length_zipWith

theorem zipBodyWithScalar_length (body : ScalarIR 3) (parameter : ℝ)
    (left right : List ℝ) :
    (zipBodyWithScalar body parameter left right).length = min left.length right.length := by
  exact List.length_zipWith

def dotSlice (body : ScalarIR 2) (left right : List ℝ) : ℝ :=
  orderedFsum (zipBody body left right)

def updateSlice (body : ScalarIR 3) (step : ℝ) (weights gradient : List ℝ) : List ℝ :=
  zipBodyWithScalar body step weights gradient

/-- The body remains compiled syntax; its execution is generic list semantics. -/
def runDotSource (source : SourceScalar) (left right : List ℝ) : Option ℝ :=
  (compile dotScope source).map (fun body => dotSlice body left right)

def runUpdateSource (source : SourceScalar) (step : ℝ)
    (weights gradient : List ℝ) : Option (List ℝ) :=
  (compile updateScope source).map (fun body => updateSlice body step weights gradient)

theorem zipWith_ofFn_same_length {α β γ : Type} {m : ℕ}
    (operation : α → β → γ) (left : Fin m → α) (right : Fin m → β) :
    List.zipWith operation (List.ofFn left) (List.ofFn right) =
      List.ofFn (fun i => operation (left i) (right i)) := by
  induction m generalizing left right with
  | zero => simp
  | succ m ih =>
    rw [List.ofFn_succ, List.ofFn_succ, List.ofFn_succ]
    simp only [List.zipWith_cons_cons]
    congr 1
    exact ih (fun i => left i.succ) (fun i => right i.succ)

/-- Equal-size inputs make zip's truncation harmless; the scalar body was not
replaced by a dot primitive during compilation. -/
theorem supported_dot_eq {m : ℕ} (left right : Fin m → ℝ) :
    dotSlice compiledDotBody (List.ofFn left) (List.ofFn right) =
      RankerRealCurvature.dot left right := by
  change orderedFsum (List.zipWith (fun x y => x * y)
    (List.ofFn left) (List.ofFn right)) = RankerRealCurvature.dot left right
  rw [zipWith_ofFn_same_length, orderedFsum_eq_sum, List.sum_ofFn]
  rfl

theorem source_dot_literal_eq {m : ℕ} (source : SourceScalar)
    (compiled : compile dotScope source = some compiledDotBody)
    (left right : Fin m → ℝ) :
    runDotSource source (List.ofFn left) (List.ofFn right) =
      some (RankerRealCurvature.dot left right) := by
  simp only [runDotSource, compiled, Option.map_some, supported_dot_eq]

theorem supported_update_eq {m : ℕ} (step : ℝ) (weights gradient : Fin m → ℝ) :
    updateSlice compiledUpdateBody step (List.ofFn weights) (List.ofFn gradient) =
      List.ofFn (fun i => weights i - step * gradient i) := by
  change List.zipWith (fun w g => w - step * g)
    (List.ofFn weights) (List.ofFn gradient) =
      List.ofFn (fun i => weights i - step * gradient i)
  exact zipWith_ofFn_same_length _ weights gradient

theorem source_update_literal_eq {m : ℕ} (source : SourceScalar)
    (compiled : compile updateScope source = some compiledUpdateBody)
    (step : ℝ) (weights gradient : Fin m → ℝ) :
    runUpdateSource source step (List.ofFn weights) (List.ofFn gradient) =
      some (List.ofFn (fun i => weights i - step * gradient i)) := by
  simp only [runUpdateSource, compiled, Option.map_some, supported_update_eq]

/-- Conditional composition boundary: the supplied gradient here is the
previously qualified mathematical gradient, not an `_objective` translation. -/
theorem originalRealStep_update_join (weights : Fin 80 → ℝ) :
    updateSlice compiledUpdateBody RankerRealCurvature.originalRealEta
      (List.ofFn weights)
      (List.ofFn (RankerRealCurvature.realCoordinateGradient
        RankerRealCurvature.originalRealMu RankerRealCurvature.originalRealDifferences weights)) =
      List.ofFn (RankerRealCurvature.realGradientStep
        RankerRealCurvature.originalRealMu RankerRealCurvature.originalRealEta
        RankerRealCurvature.originalRealDifferences weights) := by
  simpa only [RankerRealCurvature.realGradientStep] using
    supported_update_eq RankerRealCurvature.originalRealEta weights
      (RankerRealCurvature.realCoordinateGradient RankerRealCurvature.originalRealMu
        RankerRealCurvature.originalRealDifferences weights)

#print axioms compile_eval_commutes
#print axioms compile_sound
#print axioms compile_refuses_unsupported
#print axioms compile_refuses_unknown_name
#print axioms compiled_dot_body
#print axioms compiled_update_body
#print axioms orderedFsum_eq_sum
#print axioms zipBody_length
#print axioms zipBodyWithScalar_length
#print axioms supported_dot_eq
#print axioms source_dot_literal_eq
#print axioms supported_update_eq
#print axioms source_update_literal_eq
#print axioms originalRealStep_update_join

end

end RankerSourceSemantics
