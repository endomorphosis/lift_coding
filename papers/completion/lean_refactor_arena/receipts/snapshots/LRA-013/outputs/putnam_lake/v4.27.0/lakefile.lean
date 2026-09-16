import Lake
open Lake DSL

package «putnam_lake» where
  moreLeanArgs := #["-DmaxHeartbeats=400000"]
  moreServerArgs := #["-DmaxHeartbeats=400000"]

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @ "v4.27.0"

require aesop from git
  "https://github.com/leanprover-community/aesop.git" @ "v4.27.0"

@[default_target]
lean_lib «Putnam» where
  globs := #[.submodules `Putnam]
