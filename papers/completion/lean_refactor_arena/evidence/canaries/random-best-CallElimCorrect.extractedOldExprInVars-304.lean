  intros Hnorm
  induction post <;>
    simp [Imperative.HasVarsPure.getVars, extractOldExprVars,
          Lambda.LExpr.LExpr.getVars] at * ;
    try simp_all
  case app fn e fn_ih e_ih =>
    unfold extractOldExprVars
    split
    . simp [Lambda.LExpr.LExpr.getVars]
      intros x Hin
      exact Hin
    . next Hfalse =>
      cases Hnorm with
      | app H1 H2 Hn =>
      exfalso
      specialize Hn _
      constructor
      cases Hn
      apply Hfalse
      rfl
    . cases Hnorm with
      | app H1 H2 Hn =>
      apply List.Subset.app
      . apply List.Subset.trans
        apply fn_ih
        exact H1
        intros x Hin
        simp_all
      . apply List.Subset.trans
        apply e_ih
        exact H2
        intros x Hin
        simp_all
  case abs ih =>
    cases Hnorm
    apply ih <;> assumption
  case quant trih eih =>
    cases Hnorm
    apply List.Subset.app
    . apply List.Subset.trans
      apply trih ; assumption
      intros x Hin
      simp_all
    . apply List.Subset.trans
      apply eih <;> assumption
      intros x Hin
      simp_all
  case ite cih tih eih =>
    cases Hnorm
    apply List.Subset.app
    . apply List.Subset.trans
      apply cih ; assumption
      intros x Hin
      simp_all
    apply List.Subset.app
    . apply List.Subset.trans
      apply tih ; assumption
      intros x Hin
      simp_all
    . apply List.Subset.trans
      apply eih <;> assumption
      intros x Hin
      simp_all
  case eq ih1 ih2 =>
    cases Hnorm
    apply List.Subset.app
    . apply List.Subset.trans
      apply ih1 <;> assumption
      intros x Hin
      simp_all
    . apply List.Subset.trans
      apply ih2 <;> assumption
      intros x Hin
      simp_all
