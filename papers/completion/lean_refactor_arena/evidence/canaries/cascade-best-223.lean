  intros Hup Hinit
  exists (updatedStates σ ks' vs')
  have Hk := UpdateStatesDefined Hup
  have Hlen1 := InitStatesLength Hinit
  have Hlen2 := UpdateStatesLength Hup
  induction Hup generalizing σ''
  case update_none =>
    simp_all
    constructor
    exact updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit)
    simp [InitStatesUpdated Hinit]
    constructor
  case update_some σ x v σ₀ xs vs σ₁ Hup Hups ih =>
    have Hst := updatedStatesInit Hlen1
      (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)
      (InitStatesNodup Hinit)
    refine ⟨rfl, Hst, ?_⟩
    . apply UpdateStates.update_some (σ':=updatedStates σ₀ ks' vs')
      . simp [UpdateStateUpdated Hup, updatedStates]
        rw [← updatedStateComm']
        . have Hdef := UpdateStateDefined' Hup
          simp [isDefined, Option.isSome] at Hdef
          split at Hdef <;> simp_all
          next val heq =>
          apply updatedStateUpdate
          apply InitStatesSomeMonotone heq
          exact Hst
        . rw [List.unzip_zip] <;> simp_all
          have Hnd := InitStatesNotDefined Hinit
          simp [isNotDefined, isDefined] at *
          intros Hin
          simp_all
      . apply (ih Hinit ?_ ?_).2.2
        . simp [isDefined] at * <;> simp_all
        . simp_all
