import Init

namespace DecoderKernel
set_option autoImplicit false
set_option maxRecDepth 65536
set_option maxHeartbeats 4000000

abbrev Scalars := List Nat
structure Request where
  id : Scalars
  prompt : Nat
  generated : Nat
  deriving DecidableEq, BEq, ReflBEq, LawfulBEq
structure Shape where
  seq : Nat
  heads : Nat
  hidden : Nat
  deriving DecidableEq, BEq, ReflBEq, LawfulBEq
structure Row where
  id : Scalars
  batch : Scalars
  shape : Shape
  deriving DecidableEq, BEq, ReflBEq, LawfulBEq

inductive Value where
  | str : Scalars → Value
  | nat : Nat → Value
  | obj : List (Scalars × Value) → Value

def maxNatural : Nat := 1000000000000000000
def scalarValid (n : Nat) : Bool :=
  decide (n ≤ 1114111 ∧ ¬ (55296 ≤ n ∧ n ≤ 57343))
def continuation (n : Nat) : Bool := decide (128 ≤ n ∧ n ≤ 191)

def utf8Scalar (raw : List Nat) : Option (Nat × List Nat) := do
  match raw with
  | [] => none
  | a :: rest =>
    if a < 128 then some (a, rest)
    else if 194 ≤ a && a ≤ 223 then
      match rest with
      | b :: tail => if continuation b then some ((a - 192) * 64 + b - 128, tail) else none
      | _ => none
    else if 224 ≤ a && a ≤ 239 then
      match rest with
      | b :: c :: tail =>
        let n := (a - 224) * 4096 + (b - 128) * 64 + c - 128
        if continuation b && continuation c && 2048 ≤ n && scalarValid n then some (n, tail) else none
      | _ => none
    else if 240 ≤ a && a ≤ 244 then
      match rest with
      | b :: c :: d :: tail =>
        let n := (a - 240) * 262144 + (b - 128) * 4096 + (c - 128) * 64 + d - 128
        if continuation b && continuation c && continuation d && 65536 ≤ n && scalarValid n then some (n, tail) else none
      | _ => none
    else none

def hexDigit (b : Nat) : Option Nat :=
  if 48 ≤ b && b ≤ 57 then some (b - 48)
  else if 65 ≤ b && b ≤ 70 then some (b - 55)
  else if 97 ≤ b && b ≤ 102 then some (b - 87)
  else none

def hex4 (raw : List Nat) : Option (Nat × List Nat) := do
  match raw with
  | a :: b :: c :: d :: tail =>
    let aa ← hexDigit a
    let bb ← hexDigit b
    let cc ← hexDigit c
    let dd ← hexDigit d
    some (aa * 4096 + bb * 256 + cc * 16 + dd, tail)
  | _ => none

def escapeScalar (raw : List Nat) : Option (Nat × List Nat) := do
  match raw with
  | 34 :: tail => some (34, tail)
  | 92 :: tail => some (92, tail)
  | 47 :: tail => some (47, tail)
  | 98 :: tail => some (8, tail)
  | 102 :: tail => some (12, tail)
  | 110 :: tail => some (10, tail)
  | 114 :: tail => some (13, tail)
  | 116 :: tail => some (9, tail)
  | 117 :: tail =>
    let (n, tail) ← hex4 tail
    if 55296 ≤ n && n ≤ 56319 then
      match tail with
      | 92 :: 117 :: tail =>
        let (low, tail) ← hex4 tail
        if 56320 ≤ low && low ≤ 57343 then
          some (65536 + (n - 55296) * 1024 + low - 56320, tail)
        else none
      | _ => none
    else if scalarValid n then some (n, tail) else none
  | _ => none

def parseString : Nat → List Nat → Scalars → Option (Scalars × List Nat)
  | 0, _, _ => none
  | _ + 1, [], _ => none
  | fuel + 1, b :: tail, acc => do
    if b == 34 then some (acc.reverse, tail)
    else if b == 92 then
      let (n, tail) ← escapeScalar tail
      if n == 0 then none else parseString fuel tail (n :: acc)
    else
      let (n, tail) ← utf8Scalar (b :: tail)
      if n < 32 then none else parseString fuel tail (n :: acc)

def digit (b : Nat) : Bool := decide (48 ≤ b ∧ b ≤ 57)
def parseDigits : Nat → List Nat → Nat → Option (Nat × List Nat)
  | 0, _, _ => none
  | fuel + 1, raw, acc =>
    match raw with
    | [] => some (acc, [])
    | b :: tail =>
      if digit b then
        let next := acc * 10 + b - 48
        if next ≤ maxNatural then parseDigits fuel tail next else none
      else some (acc, raw)

def parseNatural (raw : List Nat) : Option (Nat × List Nat) :=
  match raw with
  | [] => none
  | 48 :: tail =>
    match tail with
    | b :: _ => if digit b then none else some (0, tail)
    | [] => some (0, [])
  | b :: _ => if 49 ≤ b && b ≤ 57 then parseDigits (raw.length + 1) raw 0 else none

def whitespace (raw : List Nat) : List Nat := raw.dropWhile (fun b => b == 32 || b == 9)

mutual
  def parseValue : Nat → Nat → List Nat → Option (Value × List Nat)
    | 0, _, _ => none
    | fuel + 1, depth, raw => do
      match whitespace raw with
      | [] => none
      | 34 :: tail =>
        let (text, tail) ← parseString (tail.length + 1) tail []
        some (.str text, tail)
      | 123 :: tail =>
        if depth < 8 then parseObject fuel (depth + 1) (whitespace tail) [] else none
      | tail =>
        let (n, tail) ← parseNatural tail
        some (.nat n, tail)

  def parseObject : Nat → Nat → List Nat → List (Scalars × Value) → Option (Value × List Nat)
    | 0, _, _, _ => none
    | fuel + 1, depth, raw, acc => do
      match raw with
      | 125 :: tail => if acc.isEmpty then some (.obj [], tail) else none
      | 34 :: tail =>
        let (key, tail) ← parseString (tail.length + 1) tail []
        if (acc.map Prod.fst).contains key then none else
          match whitespace tail with
          | 58 :: tail =>
            let (value, tail) ← parseValue fuel depth tail
            let fields := (key, value) :: acc
            match whitespace tail with
            | 125 :: tail => some (.obj fields.reverse, tail)
            | 44 :: tail => parseObject fuel depth (whitespace tail) fields
            | _ => none
          | _ => none
      | _ => none
end

def physicalLinesAux : List Nat → List Nat → List (List Nat) → List (List Nat)
  | [], current, acc => if current.isEmpty then acc.reverse else (current.reverse :: acc).reverse
  | b :: tail, current, acc =>
    if b == 10 then physicalLinesAux tail [] ((b :: current).reverse :: acc)
    else physicalLinesAux tail (b :: current) acc

def physicalLines (raw : List Nat) : List (List Nat) := physicalLinesAux raw [] []
def recordBytes (physical : List Nat) : List Nat :=
  match physical.reverse with
  | 10 :: 13 :: tail => tail.reverse
  | 10 :: tail => tail.reverse
  | _ => physical

def parseLine (physical : List Nat) : Option Value := do
  if physical.length > 8192 then none else
    let raw := recordBytes physical
    if raw.contains 13 then none else
      let (value, tail) ← parseValue (raw.length + 1) 0 raw
      if (whitespace tail).isEmpty then some value else none

def field (fields : List (Scalars × Value)) (key : Scalars) : Option Value :=
  (fields.find? (fun pair => pair.1 == key)).map Prod.snd
def exactKeys (fields : List (Scalars × Value)) (keys : List Scalars) : Bool :=
  fields.length == keys.length && keys.all (fun key => (fields.map Prod.fst).contains key)

def scalarBytes (n : Nat) : Nat :=
  if n < 128 then 1 else if n < 2048 then 2 else if n < 65536 then 3 else 4
def identifier (v : Value) : Option Scalars :=
  match v with
  | .str s =>
    if s.contains 0 || (s.map scalarBytes).sum > 512 then none else some s
  | _ => none
def natural (v : Value) : Option Nat :=
  match v with
  | .nat n => if n ≤ maxNatural then some n else none
  | _ => none

def requestIDKey : Scalars := [114,101,113,117,101,115,116,95,105,100]
def promptKey : Scalars := [112,114,111,109,112,116,95,108,101,110]
def generatedKey : Scalars := [103,101,110,95,108,101,110]
def batchKey : Scalars := [98,97,116,99,104,95,105,100]
def shapeKey : Scalars := [115,104,97,112,101]
def seqKey : Scalars := [115,101,113,95,97,108,105,103,110]
def headsKey : Scalars := [104,101,97,100,115,95,97,108,105,103,110]
def hiddenKey : Scalars := [104,105,100,100,101,110,95,97,108,105,103,110]

def request (v : Value) : Option Request := do
  match v with
  | .obj fields =>
    if exactKeys fields [requestIDKey, promptKey, generatedKey] then
      let id ← identifier (← field fields requestIDKey)
      let prompt ← natural (← field fields promptKey)
      let generated ← natural (← field fields generatedKey)
      some { id, prompt, generated }
    else none
  | _ => none

def shape (v : Value) : Option Shape := do
  match v with
  | .obj fields =>
    if exactKeys fields [seqKey, headsKey, hiddenKey] then
      let seq ← natural (← field fields seqKey)
      let heads ← natural (← field fields headsKey)
      let hidden ← natural (← field fields hiddenKey)
      some { seq, heads, hidden }
    else none
  | _ => none

def row (v : Value) : Option Row := do
  match v with
  | .obj fields =>
    if exactKeys fields [requestIDKey, batchKey, shapeKey] then
      let id ← identifier (← field fields requestIDKey)
      let batch ← identifier (← field fields batchKey)
      let shape ← shape (← field fields shapeKey)
      some { id, batch, shape }
    else none
  | _ => none

def fileValues (raw : List Nat) : Option (List Value) := do
  if raw.length > 65536 || raw.any (fun b => b > 255 || b == 0) then none else
    let lines := physicalLines raw
    if lines.length > 256 then none else lines.mapM parseLine

def decodeRequests (raw : List Nat) : Option (List Request) := do
  let values ← fileValues raw
  let requests ← values.mapM request
  if decide (requests.map Request.id).Nodup then some requests else none

def decodePlans (raw : List Nat) : Option (List Row) := do
  let values ← fileValues raw
  let rows ← values.mapM row
  if decide (rows.map Row.id).Nodup then some rows else none

theorem decoded_request_ids_unique (raw : List Nat) (rows : List Request)
    (accepted : decodeRequests raw = some rows) : (rows.map Request.id).Nodup := by
  cases hv : fileValues raw with
  | none => simp [decodeRequests, hv] at accepted
  | some values =>
    cases hr : values.mapM request with
    | none => simp [decodeRequests, hv, hr] at accepted
    | some requests =>
      by_cases hn : (requests.map Request.id).Nodup
      · simp [decodeRequests, hv, hr, hn] at accepted
        subst rows
        exact hn
      · simp [decodeRequests, hv, hr, hn] at accepted

theorem decoded_plan_ids_unique (raw : List Nat) (rows : List Row)
    (accepted : decodePlans raw = some rows) : (rows.map Row.id).Nodup := by
  cases hv : fileValues raw with
  | none => simp [decodePlans, hv] at accepted
  | some values =>
    cases hr : values.mapM row with
    | none => simp [decodePlans, hv, hr] at accepted
    | some plans =>
      by_cases hn : (plans.map Row.id).Nodup
      · simp [decodePlans, hv, hr, hn] at accepted
        subst rows
        exact hn
      · simp [decodePlans, hv, hr, hn] at accepted

end DecoderKernel
