set_option maxHeartbeats 200000

theorem dependent_countermodel : ¬ (∀ (α : Type) (x y : α), x = y) := by
  intro h
  have h1 : false = true := h Bool false true
  cases h1

#print axioms dependent_countermodel

theorem higher_order_countermodel : ¬ (∀ (p : (Nat → Nat) → Prop) (f g : Nat → Nat), p f → p g) := by
  intro h
  have h1 : (1 : Nat) = 0 := h (fun f => f 0 = 0) (fun _ => 0) (fun _ => 1) rfl
  cases h1

#print axioms higher_order_countermodel
