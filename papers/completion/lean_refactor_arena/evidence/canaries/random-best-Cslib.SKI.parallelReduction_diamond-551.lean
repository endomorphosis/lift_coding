  intro a a₁ a₂ h₁ h₂
  cases h₁
  case refl => exact ⟨a₂, h₂, .refl a₂⟩
  case par a a' b b' ha' hb' =>
    cases h₂
    case refl =>
      use a' ⬝ b'
      exact ⟨.refl (a' ⬝ b'), .par ha' hb'⟩
    case par a'' b'' ha'' hb'' =>
      let ⟨a₃, ha⟩ := parallelReduction_diamond ha' ha''
      let ⟨b₃, hb⟩ := parallelReduction_diamond hb' hb''
      use a₃ ⬝ b₃
      exact ⟨.par ha.1 hb.1, .par ha.2 hb.2⟩
    case red_I =>
      rw [I_irreducible a' ha']
      use b', .red_I b'
    case red_K =>
      let ⟨a₂', ha₂'⟩ := Ka_irreducible a₂ a' ha'
      rw [ha₂'.2]
      use a₂'
      exact ⟨.red_K a₂' b', ha₂'.1⟩
    case red_S a c =>
      let ⟨a'', c', h⟩ := Sab_irreducible a c a' ha'
      rw [h.2.2]
      use a'' ⬝ b' ⬝ (c' ⬝ b'), .red_S a'' c' b'
      apply ParallelReduction.par <;>
        apply ParallelReduction.par <;>
        grind
  case red_I =>
    cases h₂
    case refl => use a₁; exact ⟨.refl a₁, .red_I a₁⟩
    case par c a₁' hc ha =>
      rw [I_irreducible c hc]
      use a₁'
      exact ⟨ha, .red_I a₁'⟩
    case red_I => use a₁; exact ⟨.refl a₁, .refl a₁⟩
  case red_K c =>
    cases h₂
    case refl => use a₁; exact ⟨.refl a₁, .red_K a₁ c⟩
    case par a' c' ha hc =>
      let ⟨a₁', h'⟩ := Ka_irreducible a₁ a' ha
      rw [h'.2]
      use a₁'
      exact ⟨h'.1, .red_K a₁' c'⟩
    case red_K =>
      use a₁; exact ⟨.refl a₁, .refl a₁⟩
  case red_S a b c =>
    cases h₂
    case refl =>
      use a ⬝ c ⬝ (b ⬝ c)
      exact ⟨.refl _, .red_S ..⟩
    case par d c' hd hc =>
      let ⟨a', b', h⟩ := Sab_irreducible a b d hd
      rw [h.2.2]
      use a' ⬝ c' ⬝ (b' ⬝ c')
      constructor
      · apply ParallelReduction.par
        · exact .par h.left hc
        · exact .par h.2.1 hc
      · exact .red_S ..
    case red_S => exact ⟨a ⬝ c ⬝ (b ⬝ c), .refl _, .refl _,⟩
