"""Render measured incremental results and retain a numbered evidence snapshot.

Never runs experiments or overwrites the historical final manuscript.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent


def load(relative):
    return json.loads((ROOT / relative).read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--increment", required=True)
    args = parser.parse_args()
    assert args.increment.isdigit()
    snapshot = ROOT / "increments" / args.increment
    snapshot.mkdir(parents=True)
    sources = ["evals/context/results/summary.json", "evals/context/results/rows.json",
               "evals/routing_v2/summary.json", "evals/routing_v2/metering_audit.json",
               "evals/reuse/runs/development-v5/summary.json",
               "evals/reuse/runs/development-v5/cases.json",
               "evals/reuse/runs/development-v5/timing.json",
               "evals/compositional_v2/summary.json"]
    ctx, routing, reuse, native = [load(p) for p in (
        sources[0], sources[2], sources[4], sources[7])]
    # Regenerate routing totals from all terminal cells, preserving zero-call paths.
    cells = [json.loads(p.read_text()) for p in sorted((ROOT / "evals/routing_v2/results").glob("*.json"))
             if not p.name.endswith(".local.json")]
    assert len(cells) == routing["scheduled_cells"] == 8
    for arm in ("baseline", "system"):
        rows = [r for r in cells if r["arm"] == arm]
        assert sum(r["success"] for r in rows) == routing["arms"][arm]["successes"]
        assert sum(r["provider_calls"] for r in rows) == routing["arms"][arm]["provider_calls"]
        assert sum(r["normalized_usage"]["total_tokens"] for r in rows) == routing["arms"][arm]["total_tokens"]
        sources.extend(str(p.relative_to(ROOT)) for p in (ROOT / "evals/routing_v2/results").glob(arm + "-*.json"))
    receipts = list((ROOT / "evals/routing_v2/results/provider").glob("*/result.json"))
    assert len(receipts) == 6
    for p in receipts:
        r = json.loads(p.read_text())
        assert r["status"] == "response" and r["served_model"] == "grok-4.6"
        assert r["usage"]["total_tokens"] == r["normalized_usage"]["total_tokens"]
        sources.extend([str(p.relative_to(ROOT)), str(p.with_name("request.json").relative_to(ROOT))])
    # The paired residual requests are byte-identical canonical envelopes.
    for name in ("clamp_interval", "stable_deduplication"):
        folder = ROOT / "evals/routing_v2/results/provider"
        assert (folder / ("baseline-" + name) / "request.json").read_bytes() == (folder / ("system-" + name) / "request.json").read_bytes()
    assert ctx["total_substituted_windows"] == 0
    assert native["artifact_verification"]["valid"]
    assert reuse["matched_cases"] == reuse["case_count"] == 14
    counts = ctx["message_content_token_totals"]
    a, b = routing["arms"]["baseline"], routing["arms"]["system"]
    reduction = 100 * (1 - b["total_tokens"] / a["total_tokens"])
    text = r"""\section{Incremental system evaluation}
\label{sec:incremental-evaluation}

The following evaluations extend the original architecture questions. They are
development measurements and local qualification, separate from the historical
cold experiment and from any future confirmatory population. Their profiles
and source versions are explicit; they do not yet form one integrated runtime.

\paragraph{Context substitution opportunity.}
We reconstructed all sixteen historical A/B request commitments across eight
unique families and checked the selected public source against its hashes.
All 254 selected windows were protected editable or test source; there were
zero eligible unchanged-dependency files and zero substituted windows.
The guarded substitution adapter therefore retained the raw source. Saved
native packets contained no explicit obligation CIDs and 14,471 unresolved
dependency-edge occurrences. Instruction text was retained, but this cohort
cannot establish explicit obligation preservation or dependency compression.

Using \texttt{tiktoken} 0.12.0 with \texttt{o200k\_base}, exact tokenization of
system/user message content totaled @RAW@ for A, @ADD@ for B, and @SUB@ for
guarded substitution C: increases of @ADDINC@\% and @SUBINC@\% over A.
These counts exclude chat-template overhead and output, and are not Grok
provider usage. A second named encoding gives the same direction.
Eighteen constructed adapter controls separately check expansion and rejection;
they do not qualify a native producer. This result identifies a population
requirement: a compression experiment must include unchanged dependencies that
can actually be replaced under its stated policy.

\paragraph{Checked symbolic closure and live residuals.}
A new development caller invokes the native Python analyzer, bounded CEGIS
repair, visible behavioral checks and native routing. Four constructed tasks
include false success without observation, swallowed backend failure, interval
clamping and stable deduplication. Both arms receive the same source, objective
and public checks; separate Docker execution scores broader behavioral checks.
The first two defects fit the declared deterministic grammar. The remaining two
require the same model residual in both arms. Internal CEGIS marker gates are
not counted as theorem proofs; behavioral checks justify only these bounded
obligations.

\begin{table}[htbp]
\centering
\caption{Constructed four-task routing development comparison. One observation
per task and arm; no population inference.}
\label{tab:routing-development}
\begin{tabular}{lrrr}
\toprule
Arm & Independently passed & Model calls & Total provider tokens \\
\midrule
Model first & @ASUCCESS@/4 & @ACALLS@ & @ATOKENS@ \\
Symbolic first plus residual & @BSUCCESS@/4 & @BCALLS@ & @BTOKENS@ \\
\bottomrule
\end{tabular}
\end{table}

All six Grok 4.6 requests returned usage, under the same low-effort profile,
2,048-token requested output ceiling and 240-second deadline, without retries.
The observed reduction is @REDUCTION@\% on this suite. Eliminating two requests
accounts for 2,282 baseline tokens; response variation on the residual tasks
accounts for the remaining 153-token net difference. Provider cache state was
not controlled. There were no auxiliary workflow model calls or model-assisted
setup in this caller; experiment authoring and implementation effort are outside
that runtime denominator. The initial expired-credential attempt dispatched
zero requests and remains a separate development record. General repository
performance and full-system setup amortization remain unmeasured.

\paragraph{Lifecycle-preserving test reuse.}
A proposed local evaluation adapter uses native cache admission and Ed25519
runner attestations issued only after actual passing setup/call/teardown.
Its explicitly enrolled pure workload and immutable fixture profile support
valid call-phase reuse while setup and teardown still execute. Fourteen
prespecified cases cover unchanged work, source/test/fixture/configuration/
environment mutations, missing or tampered evidence, revocation, unsupported
fixture values and lifecycle failure. All fourteen match separate cold-process
outcomes. Reuse followed by failing teardown correctly fails the whole item;
the result is not zero-error evidence for arbitrary pytest programs.

Five alternating warm/cold timing pairs omit all five warm test-body executions
while retaining five setups and teardowns in each arm. Total host wall time was
@COLD@ seconds cold and @WARM@ seconds warm, excluding the separately recorded
prime and issuance costs. This small descriptive difference does not establish
a reliable net speedup or token savings. The default production plugin probe
executed the body in both write and read/write modes and produced no positive
reuse. Thus the result qualifies the proposed bounded adapter, not deployment
of the native default reuse path. Earlier failed development invocations and
the historical false-reuse observation remain retained.

\paragraph{Native compositional reasoning.}
An existing original-source vertical slice was run with its compatible nested
datasets tree. A baseline component contract discharged, an injected fault was
refuted, and repair restored discharge. Localization produced an UNSAT core and
a cvc5 interpolant separately checked by Z3; the final artifact was verified by
semantic rescanning, composition redischarge and test replay. Selected and full
tests passed. Host elapsed time was @NATIVETIME@ seconds. This is one existing
constructed fixture with a prescribed fault and expected repair, not a held-out
synthesis experiment. Internal benchmark estimates are not counted as measured
token or compute savings. An earlier source profile failed to import the
required composition module and is preserved separately. Solver validation
does not imply kernel reconstruction or all-language correctness.

\paragraph{Remaining system questions.}
These increments establish local mechanisms and expose limitations. They leave
open matched context-substitution efficacy, persistent multi-task quality/cost,
procedure and world-memory utility, production reuse, governed publication,
native proof profiles, and an integrated held-out comparison with complete
startup, fallback, failed-attempt and recovery accounting.
"""
    values = {
        "RAW": f"{counts['A_raw']['o200k_base']:,}", "ADD": f"{counts['B_additive']['o200k_base']:,}",
        "SUB": f"{counts['C_substitution']['o200k_base']:,}",
        "ADDINC": f"{-100 * ctx['reductions_relative_to_A']['B_additive']['o200k_base']:.2f}",
        "SUBINC": f"{-100 * ctx['reductions_relative_to_A']['C_substitution']['o200k_base']:.2f}",
        "ASUCCESS": a["successes"], "BSUCCESS": b["successes"], "ACALLS": a["provider_calls"],
        "BCALLS": b["provider_calls"], "ATOKENS": f"{a['total_tokens']:,}", "BTOKENS": f"{b['total_tokens']:,}",
        "REDUCTION": f"{reduction:.2f}", "COLD": f"{reuse['cold_wall_total_seconds']:.3f}",
        "WARM": f"{reuse['warm_wall_total_seconds']:.3f}", "NATIVETIME": f"{native['host_elapsed_seconds']:.3f}"}
    for key, value in values.items():
        text = text.replace("@" + key + "@", str(value))
    assert "@" not in text
    generated = ROOT / "manuscript/fragments/incremental_results.tex"
    generated.write_text(text)
    shutil.copyfile(generated, snapshot / "incremental_results.tex")
    sources.extend([str(generated.relative_to(ROOT)), "update_manuscript.py"])
    manifest = {}
    for source in sorted(set(sources)):
        p = ROOT / source
        manifest[source] = hashlib.sha256(p.read_bytes()).hexdigest()
    (snapshot / "evidence_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (snapshot / "checks.json").write_text(json.dumps({"routing_totals_recomputed": True,
        "all_six_live_usage_receipts_checked": True, "paired_residual_requests_identical": True,
        "historical_cells_relabelled": False, "whole_goal_complete": False}, indent=2) + "\n")
    print(f"Generated working manuscript increment {args.increment}; full research objective remains open.")


if __name__ == "__main__":
    main()
