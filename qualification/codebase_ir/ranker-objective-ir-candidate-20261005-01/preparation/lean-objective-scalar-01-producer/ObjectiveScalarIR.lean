import RealStableFactor
import TypedNumericSlice

set_option backward.isDefEq.respectTransparency false

/-!
UNCOMPILED, UNQUALIFIED SOURCE CANDIDATE.

Generic named scalar syntax is compiled into finite typed slots. Compilation
checks all syntax branches; exact-real evaluation selects only one branch.
Division and log1p have explicit domain errors. This source does not certify
the host AST parser, Python global resolution, binary64/libm behavior, vector
containers, the computed gradient, the complete objective, or a training loop.
-/

namespace RankerObjectiveIR

noncomputable section

inductive SliceError where
  | unsupportedNode (tag : String)
  | unknownName (name : String)
  | divisionByZero
  | logDomain
  deriving DecidableEq

inductive SourceScalar where
  | num (q : ℚ)
  | var (name : String)
  | neg (value : SourceScalar)
  | abs (value : SourceScalar)
  | add (left right : SourceScalar)
  | sub (left right : SourceScalar)
  | mul (left right : SourceScalar)
  | div (left right : SourceScalar)
  | max (left right : SourceScalar)
  | exp (value : SourceScalar)
  | log1p (value : SourceScalar)
  | ifNonneg (condition thenBranch elseBranch : SourceScalar)
  | unsupported (tag : String)
  deriving DecidableEq

inductive ScalarIR (slots : ℕ) where
  | num (q : ℚ)
  | var (slot : Fin slots)
  | neg (value : ScalarIR slots)
  | abs (value : ScalarIR slots)
  | add (left right : ScalarIR slots)
  | sub (left right : ScalarIR slots)
  | mul (left right : ScalarIR slots)
  | div (left right : ScalarIR slots)
  | max (left right : ScalarIR slots)
  | exp (value : ScalarIR slots)
  | log1p (value : ScalarIR slots)
  | ifNonneg (condition thenBranch elseBranch : ScalarIR slots)
  deriving DecidableEq

def mapOne {α β : Type} (f : α → β) : Except SliceError α → Except SliceError β
  | .ok a => .ok (f a)
  | .error e => .error e

def mapTwo {α β γ : Type} (f : α → β → γ) :
    Except SliceError α → Except SliceError β → Except SliceError γ
  | .ok a, .ok b => .ok (f a b)
  | .error e, _ => .error e
  | .ok _, .error e => .error e

def mapThree {α β γ δ : Type} (f : α → β → γ → δ) :
    Except SliceError α → Except SliceError β → Except SliceError γ → Except SliceError δ
  | .ok a, .ok b, .ok c => .ok (f a b c)
  | .error e, _, _ => .error e
  | .ok _, .error e, _ => .error e
  | .ok _, .ok _, .error e => .error e

def applyOne {α β : Type} (f : α → Except SliceError β) :
    Except SliceError α → Except SliceError β
  | .ok a => f a
  | .error e => .error e

def applyTwo {α β γ : Type} (f : α → β → Except SliceError γ) :
    Except SliceError α → Except SliceError β → Except SliceError γ
  | .ok a, .ok b => f a b
  | .error e, _ => .error e
  | .ok _, .error e => .error e

def exactDivision (a b : ℝ) : Except SliceError ℝ :=
  if b = 0 then .error .divisionByZero else .ok (a / b)

def exactLog1p (a : ℝ) : Except SliceError ℝ :=
  if 0 < 1 + a then .ok (Real.log (1 + a)) else .error .logDomain

/-- Compile every syntactic child, including both conditional branches. -/
def compileScalar {slots : ℕ} (scope : String → Option (Fin slots)) :
    SourceScalar → Except SliceError (ScalarIR slots)
  | .num q => .ok (.num q)
  | .var name => match scope name with
      | some slot => .ok (.var slot)
      | none => .error (.unknownName name)
  | .neg a => mapOne ScalarIR.neg (compileScalar scope a)
  | .abs a => mapOne ScalarIR.abs (compileScalar scope a)
  | .add a b => mapTwo ScalarIR.add (compileScalar scope a) (compileScalar scope b)
  | .sub a b => mapTwo ScalarIR.sub (compileScalar scope a) (compileScalar scope b)
  | .mul a b => mapTwo ScalarIR.mul (compileScalar scope a) (compileScalar scope b)
  | .div a b => mapTwo ScalarIR.div (compileScalar scope a) (compileScalar scope b)
  | .max a b => mapTwo ScalarIR.max (compileScalar scope a) (compileScalar scope b)
  | .exp a => mapOne ScalarIR.exp (compileScalar scope a)
  | .log1p a => mapOne ScalarIR.log1p (compileScalar scope a)
  | .ifNonneg c t e => mapThree ScalarIR.ifNonneg
      (compileScalar scope c) (compileScalar scope t) (compileScalar scope e)
  | .unsupported tag => .error (.unsupportedNode tag)

def evalExact {slots : ℕ} : ScalarIR slots → (Fin slots → ℝ) → Except SliceError ℝ
  | .num q, _ => .ok (q : ℝ)
  | .var slot, environment => .ok (environment slot)
  | .neg a, environment => mapOne (fun x => -x) (evalExact a environment)
  | .abs a, environment => mapOne (fun x => |x|) (evalExact a environment)
  | .add a b, environment => mapTwo (· + ·) (evalExact a environment) (evalExact b environment)
  | .sub a b, environment => mapTwo (· - ·) (evalExact a environment) (evalExact b environment)
  | .mul a b, environment => mapTwo (· * ·) (evalExact a environment) (evalExact b environment)
  | .div a b, environment => applyTwo exactDivision (evalExact a environment) (evalExact b environment)
  | .max a b, environment => mapTwo max (evalExact a environment) (evalExact b environment)
  | .exp a, environment => mapOne Real.exp (evalExact a environment)
  | .log1p a, environment => applyOne exactLog1p (evalExact a environment)
  | .ifNonneg c t e, environment => applyOne
      (fun value => if 0 ≤ value then evalExact t environment else evalExact e environment)
      (evalExact c environment)

def evalSourceExact (environment : String → Except SliceError ℝ) :
    SourceScalar → Except SliceError ℝ
  | .num q => .ok (q : ℝ)
  | .var name => environment name
  | .neg a => mapOne (fun x => -x) (evalSourceExact environment a)
  | .abs a => mapOne (fun x => |x|) (evalSourceExact environment a)
  | .add a b => mapTwo (· + ·) (evalSourceExact environment a) (evalSourceExact environment b)
  | .sub a b => mapTwo (· - ·) (evalSourceExact environment a) (evalSourceExact environment b)
  | .mul a b => mapTwo (· * ·) (evalSourceExact environment a) (evalSourceExact environment b)
  | .div a b => applyTwo exactDivision (evalSourceExact environment a) (evalSourceExact environment b)
  | .max a b => mapTwo max (evalSourceExact environment a) (evalSourceExact environment b)
  | .exp a => mapOne Real.exp (evalSourceExact environment a)
  | .log1p a => applyOne exactLog1p (evalSourceExact environment a)
  | .ifNonneg c t e => applyOne
      (fun value => if 0 ≤ value then evalSourceExact environment t else evalSourceExact environment e)
      (evalSourceExact environment c)
  | .unsupported tag => .error (.unsupportedNode tag)

def namesFromScope {slots : ℕ} (scope : String → Option (Fin slots))
    (environment : Fin slots → ℝ) (name : String) : Except SliceError ℝ :=
  match scope name with
  | some slot => .ok (environment slot)
  | none => .error (.unknownName name)

private theorem mapOne_accepted {α β : Type} (f : α → β)
    (input : Except SliceError α) (output : β) (accepted : mapOne f input = .ok output) :
    ∃ value, input = .ok value ∧ output = f value := by
  cases input with
  | error e => simp [mapOne] at accepted
  | ok value => exact ⟨value, rfl, (Except.ok.inj accepted).symm⟩

private theorem mapTwo_accepted {α β γ : Type} (f : α → β → γ)
    (left : Except SliceError α) (right : Except SliceError β) (output : γ)
    (accepted : mapTwo f left right = .ok output) :
    ∃ a b, left = .ok a ∧ right = .ok b ∧ output = f a b := by
  cases left with
  | error e => simp [mapTwo] at accepted
  | ok a =>
    cases right with
    | error e => simp [mapTwo] at accepted
    | ok b => exact ⟨a, b, rfl, rfl, (Except.ok.inj accepted).symm⟩

private theorem mapThree_accepted {α β γ δ : Type} (f : α → β → γ → δ)
    (first : Except SliceError α) (second : Except SliceError β) (third : Except SliceError γ)
    (output : δ) (accepted : mapThree f first second third = .ok output) :
    ∃ a b c, first = .ok a ∧ second = .ok b ∧ third = .ok c ∧ output = f a b c := by
  cases first with
  | error e => simp [mapThree] at accepted
  | ok a =>
    cases second with
    | error e => simp [mapThree] at accepted
    | ok b =>
      cases third with
      | error e => simp [mapThree] at accepted
      | ok c => exact ⟨a, b, c, rfl, rfl, rfl, (Except.ok.inj accepted).symm⟩

/-- Soundness is restricted to accepted programs. No blanket commuting law
equates compilation refusal with the value of an unselected source branch. -/
theorem compile_scalar_sound {slots : ℕ}
    (scope : String → Option (Fin slots)) (environment : Fin slots → ℝ)
    (source : SourceScalar) (program : ScalarIR slots)
    (accepted : compileScalar scope source = .ok program) :
    evalSourceExact (namesFromScope scope environment) source = evalExact program environment := by
  induction source generalizing program with
  | num q =>
    have h : program = .num q := (Except.ok.inj accepted).symm
    subst program
    rfl
  | var name =>
    cases hscope : scope name with
    | none => simp [compileScalar, hscope] at accepted
    | some slot =>
      have h : program = .var slot := by simpa [compileScalar, hscope] using accepted.symm
      subst program
      simp only [evalSourceExact, namesFromScope, hscope, evalExact]
  | neg a ha =>
    rcases mapOne_accepted _ _ _ accepted with ⟨pa, hpa, rfl⟩
    simp only [evalSourceExact, evalExact]
    rw [ha pa hpa]
  | abs a ha =>
    rcases mapOne_accepted _ _ _ accepted with ⟨pa, hpa, rfl⟩
    simp only [evalSourceExact, evalExact]
    rw [ha pa hpa]
  | add a b ha hb =>
    rcases mapTwo_accepted _ _ _ _ accepted with ⟨pa, pb, hpa, hpb, rfl⟩
    simp only [evalSourceExact, evalExact]
    rw [ha pa hpa, hb pb hpb]
  | sub a b ha hb =>
    rcases mapTwo_accepted _ _ _ _ accepted with ⟨pa, pb, hpa, hpb, rfl⟩
    simp only [evalSourceExact, evalExact]
    rw [ha pa hpa, hb pb hpb]
  | mul a b ha hb =>
    rcases mapTwo_accepted _ _ _ _ accepted with ⟨pa, pb, hpa, hpb, rfl⟩
    simp only [evalSourceExact, evalExact]
    rw [ha pa hpa, hb pb hpb]
  | div a b ha hb =>
    rcases mapTwo_accepted _ _ _ _ accepted with ⟨pa, pb, hpa, hpb, rfl⟩
    simp only [evalSourceExact, evalExact]
    rw [ha pa hpa, hb pb hpb]
  | max a b ha hb =>
    rcases mapTwo_accepted _ _ _ _ accepted with ⟨pa, pb, hpa, hpb, rfl⟩
    simp only [evalSourceExact, evalExact]
    rw [ha pa hpa, hb pb hpb]
  | exp a ha =>
    rcases mapOne_accepted _ _ _ accepted with ⟨pa, hpa, rfl⟩
    simp only [evalSourceExact, evalExact]
    rw [ha pa hpa]
  | log1p a ha =>
    rcases mapOne_accepted _ _ _ accepted with ⟨pa, hpa, rfl⟩
    simp only [evalSourceExact, evalExact]
    rw [ha pa hpa]
  | ifNonneg c t e hc ht he =>
    rcases mapThree_accepted _ _ _ _ _ accepted with ⟨pc, pt, pe, hpc, hpt, hpe, rfl⟩
    simp only [evalSourceExact, evalExact]
    rw [hc pc hpc, ht pt hpt, he pe hpe]
  | unsupported tag => simp [compileScalar] at accepted

theorem compile_scalar_refuses_unsupported {slots : ℕ}
    (scope : String → Option (Fin slots)) (tag : String) :
    compileScalar scope (.unsupported tag) = .error (.unsupportedNode tag) := rfl

theorem compile_scalar_refuses_unknown_name {slots : ℕ}
    (scope : String → Option (Fin slots)) (name : String) (unknown : scope name = none) :
    compileScalar scope (.var name) = .error (.unknownName name) := by
  simp only [compileScalar, unknown]

def zScope (name : String) : Option (Fin 1) := if name = "z" then some 0 else none

/-- Generic interface trees. A separate generated module must bind actual
pinned AST literals to these operator structures before source claims. -/
def scalarEnvironment (z : ℝ) : Fin 1 → ℝ := fun _ => z

def stableLossBody : ScalarIR 1 :=
  .add (.max (.num 0) (.neg (.var 0))) (.log1p (.exp (.neg (.abs (.var 0)))))

def stableFactorBody : ScalarIR 1 :=
  .ifNonneg (.var 0)
    (.div (.exp (.neg (.var 0))) (.add (.num 1) (.exp (.neg (.var 0)))))
    (.div (.num 1) (.add (.num 1) (.exp (.var 0))))

theorem stableLoss_eval_success (z : ℝ) :
    evalExact stableLossBody (scalarEnvironment z) = .ok (RankerRealCurvature.realStablePairLoss z) := by
  have hlog : 0 < 1 + Real.exp (-|z|) := by linarith [Real.exp_pos (-|z|)]
  simp [stableLossBody, scalarEnvironment, evalExact, mapOne, mapTwo, applyOne, exactLog1p, hlog,
    RankerRealCurvature.realStablePairLoss]

theorem stableFactor_eval_success (z : ℝ) :
    evalExact stableFactorBody (scalarEnvironment z) = .ok (RankerRealCurvature.realStableLogisticP z) := by
  have hnegative : 1 + Real.exp (-z) ≠ 0 := ne_of_gt (by linarith [Real.exp_pos (-z)])
  have hpositive : 1 + Real.exp z ≠ 0 := ne_of_gt (by linarith [Real.exp_pos z])
  by_cases h : 0 ≤ z <;>
    simp [stableFactorBody, scalarEnvironment, evalExact, mapOne, mapTwo, applyOne, applyTwo, exactDivision,
      hnegative, hpositive, h, RankerRealCurvature.realStableLogisticP]

#print axioms compile_scalar_sound
#print axioms compile_scalar_refuses_unsupported
#print axioms compile_scalar_refuses_unknown_name
#print axioms stableLoss_eval_success
#print axioms stableFactor_eval_success

end

end RankerObjectiveIR
