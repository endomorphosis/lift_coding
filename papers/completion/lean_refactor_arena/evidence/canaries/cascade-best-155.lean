  intros Hup Hinit
  exists updatedStates σ ks' vs'
  have := UpdateStatesDefined Hup
  have Hlen1 := InitStatesLength Hinit
  have Hlen2 := UpdateStatesLength Hup
  induction Hup
  ·
    simp_all
    constructor
    exact updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) $ InitStatesNodup Hinit
    simp [InitStatesUpdated Hinit]
    constructor
  ·
    rename_i Hup Hups ih
    have := InitStatesNotDefined Hinit
    have Hst := updatedStatesInit Hlen1
      (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' this Hups) Hup)
      $ InitStatesNodup Hinit
    constructor
    rfl
    constructor
    assumption
    . refine .update_some ?_ (ih Hinit (by simp_all [isDefined]) $ by simp_all).2.2
      . simp [UpdateStateUpdated Hup, updatedStates]
        rw [← updatedStateComm']
        . have := UpdateStateDefined' Hup
          simp_all [isDefined, Option.isSome]
          split at this
          all_goals simp_all
          exact updatedStateUpdate $ InitStatesSomeMonotone ‹_› Hst
        . intros Hin
          simp_all [List.unzip_zip, isNotDefined, isDefined]
