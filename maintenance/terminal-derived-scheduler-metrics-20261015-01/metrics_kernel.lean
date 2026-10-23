namespace DecoderKernel
set_option autoImplicit false

-- A decimal-rational mathematical projection of the retained source profile.
-- These definitions do not model Python binary64 rounding or source execution.
def scalarLE : Scalars → Scalars → Bool
  | [], _ => true
  | _ :: _, [] => false
  | a :: aa, b :: bb => if a < b then true else if b < a then false else scalarLE aa bb

def metricInsert {α : Type} (le : α → α → Bool) (x : α) : List α → List α
  | [] => [x]
  | y :: ys => if le x y then x :: y :: ys else y :: metricInsert le x ys
def metricSort {α : Type} (le : α → α → Bool) : List α → List α
  | [] => []
  | x :: xs => metricInsert le x (metricSort le xs)

def sumNats (xs : List Nat) : Nat := xs.foldl (· + ·) 0
def maxNats (xs : List Nat) : Nat := xs.foldl max 0
def sumSquares (a n : Nat) : Nat :=
  n * (a * a) + a * n * (n - 1) + (n * (n - 1) * (2 * n - 1)) / 6
def sumLinear (a n : Nat) : Nat := n * a + (n * (n - 1)) / 2
def prefillCost (s : Nat) : Nat := 2 * s * s + 4096 * s
def prefillLatencyUnits (s : Nat) : Nat := 5 * s * s + 15360 * s
def decodeCost (s g : Nat) : Nat := sumSquares s g + 2048 * sumLinear s g
def decodeLatencyUnits (s g : Nat) : Nat := 3 * sumSquares s g + 6144 * sumLinear s g

structure MetricBatch where
  id : Scalars
  shape : Shape
  cost : Nat
  padding : Nat
  real : Nat
  latencyUnits : List Nat
  deriving DecidableEq

def lastShape (rows : List Row) (bid : Scalars) : Shape :=
  rows.foldl (fun shape row => if row.batch == bid then row.shape else shape)
    { seq := 0, heads := 32, hidden := 4096 }

def batchFromRequests (bid : Scalars) (shape : Shape) (requests : List Request) : MetricBatch :=
  let s := maxNats (requests.map (fun request => ceil64 request.prompt))
  let g := maxNats (requests.map Request.generated)
  { id := bid, shape := shape,
    cost := sumNats (requests.map (fun request => prefillCost (ceil64 request.prompt))) +
      requests.length * decodeCost s g,
    padding := sumNats (requests.map (fun request => ceil64 request.prompt - request.prompt)) +
      sumNats (requests.map (fun request => g - request.generated)),
    real := sumNats (requests.map (fun request => request.prompt + request.generated)),
    latencyUnits := requests.map (fun request =>
      prefillLatencyUnits (ceil64 request.prompt) + decodeLatencyUnits s g + 20000) }

def metricBatches (requests : List Request) (rows : List Row) : Option (List MetricBatch) :=
  (metricSort scalarLE ((rows.map Row.batch).eraseDups)).mapM (fun bid => do
    let selected := rows.filter (fun row => row.batch == bid)
    let rs ← selected.mapM (fun row => requests.find? (fun request => request.id == row.id))
    some (batchFromRequests bid (lastShape rows bid) rs))

def compileCost (shape : Shape) : Nat :=
  if shape.seq = 0 then 0 else 500 * shape.seq * shape.seq + 8192 * shape.seq

def chargeCompilation (batches : List MetricBatch) : List MetricBatch :=
  (batches.foldl (fun (state : List Shape × List MetricBatch) batch =>
    let already := state.1.contains batch.shape
    let charged := if already then batch else
      { batch with latencyUnits := match batch.latencyUnits with
        | [] => []
        | x :: xs => (x + 3750000) :: xs }
    (batch.shape :: state.1, state.2 ++ [charged])) ([], [])).2

def p95Units (latencies : List Nat) : Nat :=
  let sorted := metricSort (fun a b => decide (a ≤ b)) latencies
  let index := min (latencies.length - 1) (((19 * latencies.length + 19) / 20) - 1)
  sorted[index]?.getD 0

def metricProfile (requests : List Request) (rows : List Row) : Bool :=
  decide (requests.length ≤ 256 ∧ rows.length ≤ 256) &&
  requests.all (fun request => decide (request.prompt ≤ 4096 ∧ request.generated ≤ 1024)) &&
  rows.all (fun row => decide (row.shape.seq ≤ 8192))

def derivedMetrics (requests : List Request) (rows : List Row) : Option Metrics := do
  if !metricProfile requests rows then none else do
    let raw ← metricBatches requests rows
    let charged := chargeCompilation raw
    let shapes := (raw.map MetricBatch.shape).eraseDups
    let cost := sumNats (raw.map MetricBatch.cost) +
      sumNats (shapes.map compileCost) + 10000000 * raw.length
    let padding := sumNats (raw.map MetricBatch.padding)
    let real := max 1 (sumNats (raw.map MetricBatch.real))
    let latencies := charged.flatMap MetricBatch.latencyUnits
    let sequential := sumNats (charged.map (fun batch => maxNats batch.latencyUnits))
    some {
      cost := { numerator := cost, denominator := 1 },
      padding := { numerator := padding, denominator := real },
      latency := { numerator := p95Units latencies, denominator := 2500 },
      sequential := { numerator := sequential, denominator := 2500 } }

def derivedModelAccept (a b : Bucket) : Option Bool := do
  let ma ← derivedMetrics a.requests a.rows
  let mb ← derivedMetrics b.requests b.rows
  some (modelAccept { a with metrics := ma } { b with metrics := mb })

theorem derivedModelAccept_of_metrics (a b : Bucket) (ma mb : Metrics)
    (ha : derivedMetrics a.requests a.rows = some ma)
    (hb : derivedMetrics b.requests b.rows = some mb) :
    derivedModelAccept a b = some (modelAccept { a with metrics := ma } { b with metrics := mb }) := by
  simp only [derivedModelAccept, ha, hb, Option.bind_eq_bind, Option.bind_some]

def decodedDerivedModelAccept (a b : Bucket) (ra pa rb pb : List Nat) : Option Bool := do
  let requests1 ← decodeRequests ra
  let rows1 ← decodePlans pa
  let requests2 ← decodeRequests rb
  let rows2 ← decodePlans pb
  derivedModelAccept { a with requests := requests1, rows := rows1 }
    { b with requests := requests2, rows := rows2 }

theorem decodedDerivedModelAccept_of_decodes (a b : Bucket) (ra pa rb pb : List Nat)
    (hra : decodeRequests ra = some a.requests) (hpa : decodePlans pa = some a.rows)
    (hrb : decodeRequests rb = some b.requests) (hpb : decodePlans pb = some b.rows) :
    decodedDerivedModelAccept a b ra pa rb pb = derivedModelAccept a b := by
  simp only [decodedDerivedModelAccept, hra, hpa, hrb, hpb,
    Option.bind_eq_bind, Option.bind_some]

def fractionEquivalent (a b : Fraction) : Bool :=
  decide (0 < a.denominator ∧ 0 < b.denominator ∧
    a.numerator * b.denominator = b.numerator * a.denominator)
def metricsEquivalent (a b : Metrics) : Bool :=
  fractionEquivalent a.cost b.cost && fractionEquivalent a.padding b.padding &&
  fractionEquivalent a.latency b.latency && fractionEquivalent a.sequential b.sequential
def metricsMatch (actual : Option Metrics) (expected : Metrics) : Bool :=
  match actual with
  | none => false
  | some value => metricsEquivalent value expected

end DecoderKernel
