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
               "evals/reuse/runs/development-v6/summary.json",
               "evals/reuse/runs/development-v6/cases.json",
               "evals/reuse/runs/development-v6/timing.json",
               "evals/compositional_v2/summary.json"]
    ctx, routing, reuse, native = [load(p) for p in (
        sources[0], sources[2], sources[4], sources[7])]
    sources.extend(["evals/persistence/summary.json", "evals/context/native_development/results_v1/summary.json"])
    persistence, dependency = load(sources[-2]), load(sources[-1])
    sources.append("evals/context/live_v1/summary.json")
    live_context = load(sources[-1])
    assert live_context["complete"] and live_context["observed_cells"] == 6
    sources.extend(["evals/procedures/summary.json", "evals/procedures/control_summary.json",
                    "evals/native_proof/runs/source-built-v1/summary.json"])
    procedures, procedure_control, native_proof = [load(p) for p in sources[-3:]]
    sources.extend(["evals/scorer_integrity/summary.json", "evals/scorer_integrity/saved_rescore.json",
                    "evals/native_proof/runs/horn-v1/honest_only_summary.json",
                    "evals/publication_baseline/run-v1/summary.json"])
    scorer, rescores, horn, publication = [load(p) for p in sources[-4:]]
    assert scorer["frozen_files_match"] and scorer["saved_records"] == len(rescores) == 14
    assert scorer["categories"]["adversarial"]["old_false_admissions"] == 5
    assert scorer["categories"]["adversarial"]["stronger_false_admissions"] == 0
    assert all(r["stronger_scorer_success"] == r["original_success"] for r in rescores)
    for row in rescores:
        path = ROOT.parents[2] / row["source_record"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["source_record_sha256"]
    assert horn["checks_passed"] and len(horn["positive_rows"]) == 3
    assert not horn["incomplete_investigation"]["custom_executable_run"]
    assert publication["returncode"] == 0 and publication["counts"]["passed"] == 47
    sources.extend(["evals/scorer_integrity/freeze.json", "evals/scorer_integrity/artifact_audit.json",
                    "evals/native_proof/runs/horn-v1/freeze.json",
                    "evals/publication_baseline/run-v1/freeze.json",
                    "evals/publication_baseline/run-v1/loaded_sources.json",
                    "evals/publication_baseline/run-v1/results.xml"])
    for row in horn["positive_rows"]:
        sources.extend(str(Path(row[k]).relative_to(ROOT)) for k in ("proof", "witness", "prove_receipt", "verify_receipt"))
    assert procedure_control["independently_replayed_cells"] == 16
    assert native_proof["positive_proofs"] == 3 and native_proof["ordinary_rejections"] == 8
    assert persistence["observations"]["same_attempt_not_executed_twice"]
    assert dependency["cold_incremental_root_matches"] == dependency["cold_incremental_comparisons"] == 12
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

\paragraph{Native dependency context and bounded projection.}
Three authored multi-module repositories supply six fresh native exact
dependency admissions. Twelve cold/incremental index and semantic-bundle root
comparisons agree; dependency edits invalidate prior capsules and unknown-call
mutations require raw fallback. Full transported native capsules total
@FULLCAPSULES@ serialized context-content
tokens versus @DEPROW@ for raw source. A new restricted projection instead
transports source-bound integer equations. Six separate Z3 equivalence checks
and 252 concrete source executions check that projection; its @EQUATIONS@
tokens are @EQUATIONRED@\% below raw. Plain AST source compaction totals
@ASTTOKENS@ tokens. These are named-encoding offline counts, not provider savings.
The equation profile excludes floats, custom objects, side effects and unsupported
syntax. The compact projection is an evaluated addition; the full native capsule
payload itself is larger than raw source in these examples.

\paragraph{Live context substitution.}
The three dependency-bearing development repositories also support a matched
raw-versus-equation repair pilot. Both arms pass all three separate cold
behavioral checks; all six requests return usage. Provider input totals are
@LIVEINPUTRAW@ raw versus @LIVEINPUTCOMPACT@ compact (@LIVEINPUTRED@\% fewer),
and total usage is @LIVETOTALRAW@ versus @LIVETOTALCOMPACT@ (@LIVETOTALRED@\%
fewer). Both arms use three requests with the same Grok 4.6 low-effort profile
and resource ceilings as the routing pilot. Cached-input totals differ, so
charge differences cannot be attributed solely to compaction. This tests a
restricted, verified representation on trivial constructed repairs; dynamic
source expansion and broader repository quality remain unmeasured. The result
is separate from, and must not be added to, the routing reduction.

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
\texttt{max\_tokens=2048} request parameter and 240-second deadline, without retries.
The observed reduction is @REDUCTION@\% on this suite. Eliminating two requests
accounts for 2,282 baseline tokens; response variation on the residual tasks
accounts for the remaining 153-token net difference. Provider cache state was
not controlled. There were no auxiliary workflow model calls or model-assisted
setup in this caller; experiment authoring and implementation effort are outside
that runtime denominator. The initial expired-credential attempt dispatched
zero requests and remains a separate development record. General repository
performance and full-system setup amortization remain unmeasured.

\paragraph{Supplementary scorer validation.}
A post-development audit exposes five false admissions among six crafted
incorrect candidates in the original pilot scorers. Candidate interference
with oracle helpers or premature process termination could masquerade as
passing execution. A new isolated scorer separates the oracle from the candidate
worker, restricts public dependency imports and requires observed calls and
positive completion. It rejects all six crafted candidates and all seven
unrepaired controls. All ten unique saved candidate bodies still pass, preserving
the eight routing and six context record outcomes above. This supplementary
rescore supports these saved outcomes; the small control set does not establish
general scorer robustness. Original scorers and observations remain retained.

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
The measured @PRIME@-second cold prime and @ISSUANCE@-second issuance exceed
the observed wall-time saving over these five repetitions; a net benefit at
that horizon is not demonstrated.

\paragraph{Persistent work across process termination.}
Three actual processes exercise the native session journal/checkpoint with
the same checked deterministic caller. Duplicate pending notifications coalesce.
The first process exits abruptly after one completion; the next resumes exactly
one unfinished scan, and a third restart finds no pending work. Each actual
execution passes the independent behavioral oracle, and no original attempt
executes twice. However, a fresh notification for a completed snapshot schedules
and executes analysis again. Journal continuity is supported by this case;
completed-result memoization, accepted-root publication and cross-task token
savings are not established.

\paragraph{Publication and recovery qualification.}
Forty-seven existing source-shipped tests pass in a fresh compatible native
profile. They cover immutable-root publication, stale writers, competing CAS
updates, seal storage and restart recovery at injected persistence boundaries.
These are constructed software qualifications, including placeholder proof
records and exception-based interruptions. They do not establish a newly
integrated evidence-producing workflow, actual process-kill tolerance at each
boundary, or measured parallel-sealing savings.

\paragraph{Procedure synthesis and stored candidates.}
Native ProcedureCegis adds missing validation operations to a bounded scaffold;
a new evaluation executor performs those checks on concrete integer-sequence
inputs. A development body store reuses candidates only under matching native
request bindings, including actual source-catalog bytes and policy. In eight
units, cold synthesis and stored-candidate arms each complete seven units with
3,883 correct fresh-query decisions and zero false admissions. The unsupported
parity unit yields 554 abstentions in each arm. Stored candidates reduce search
from eight to six synthesis calls and from 29 to 23 tried candidates. However,
a separately frozen post-development fixed-template control matches the same
quality with no synthesis. These cases demonstrate reusable search results,
not an advantage over simple templates. Fresh-process replay, source-binding
changes and scaffold sensitivity are checked independently. This is a new
bounded executor/store integration, not a production-certified procedure
runtime, and uses no model calls.

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

\paragraph{A real native proof relation.}
The copied native backend was built offline with locked dependencies because
the bundled binary did not implement the source's v3 circuit. Isolated
development keys support a four-leaf Event-DAG Merkle/count relation. Three
actual proofs for counts 1, 2 and 4 verify; eight witness, public-input,
proof and key mutations reject. Primary setup takes @PROOFSETUP@ seconds,
proof generation @PROVEMIN@--@PROVEMAX@ seconds, and verification
@VERIFYMIN@--@VERIFYMAX@ milliseconds; serialized proof JSON is 1,484 bytes.
The raw verifier accepts a different outer root that maps to the same field
element. The evaluation caller's exact-root/count and key/binary checks reject
that alternate statement before dispatch. This boundary is part of the result:
the native relation alone does not bind arbitrary outer metadata. Development
setup is not production trust admission, and a Merkle relation is not proof
that arbitrary tests executed. The v5 pytest-attestation circuit remains
unsupported in this backend.

\paragraph{The original bounded Horn profile.}
The source-built v2 backend also produces and verifies three honest implication
chains of lengths 1, 2 and 4. Setup takes @HORNSETUP@ seconds, proving
@HORNPROVEMIN@--@HORNPROVEMAX@ seconds, and verification
@HORNVERIFYMIN@--@HORNVERIFYMAX@ milliseconds; each proof JSON is 1,700 bytes.
The honest prover rejects the tested incomplete or inconsistent inputs.
When the scalar public inputs remain unchanged, the raw verifier accepts three
changed outer metadata fields; exact statement and source/key checks at the
evaluation caller reject them before dispatch. Honest examples and wrapper
checks do not establish that every satisfying circuit witness corresponds to
the advertised textual axioms. That stronger assurance remains unconfirmed.

\paragraph{Remaining system questions.}
These increments establish local mechanisms and expose limitations. They leave
open matched context-substitution efficacy, persistent multi-task quality/cost,
procedure and world-memory utility on real tasks, production reuse, governed
publication, integrated native proof admission, and a held-out comparison with complete
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
    dtokens = dependency["message_content_token_totals"]
    values.update(PROOFSETUP=f"{native_proof['setup_primary_seconds']:.3f}",
                  PROVEMIN=f"{min(native_proof['prove_wall_seconds']):.3f}",
                  PROVEMAX=f"{max(native_proof['prove_wall_seconds']):.3f}",
                  VERIFYMIN=f"{1000*min(native_proof['verify_wall_seconds']):.3f}",
                  VERIFYMAX=f"{1000*max(native_proof['verify_wall_seconds']):.3f}")
    values.update(HORNSETUP=f"{horn['setup_seconds']:.3f}",
                  HORNPROVEMIN=f"{min(r['prove_seconds'] for r in horn['positive_rows']):.3f}",
                  HORNPROVEMAX=f"{max(r['prove_seconds'] for r in horn['positive_rows']):.3f}",
                  HORNVERIFYMIN=f"{1000*min(r['verify_seconds'] for r in horn['positive_rows']):.3f}",
                  HORNVERIFYMAX=f"{1000*max(r['verify_seconds'] for r in horn['positive_rows']):.3f}")
    lcraw = live_context["arms"]["raw"]["usage_totals"]
    lccompact = live_context["arms"]["compact"]["usage_totals"]
    values.update(LIVEINPUTRAW=f"{lcraw['input_tokens']:,}",
                  LIVEINPUTCOMPACT=f"{lccompact['input_tokens']:,}",
                  LIVEINPUTRED=f"{100 * live_context['reduction_vs_raw']['input_tokens']:.2f}",
                  LIVETOTALRAW=f"{lcraw['total_tokens']:,}",
                  LIVETOTALCOMPACT=f"{lccompact['total_tokens']:,}",
                  LIVETOTALRED=f"{100 * live_context['reduction_vs_raw']['total_tokens']:.2f}")
    values.update(FULLCAPSULES=f"{dtokens['C_full_native_substitution']['o200k_base']:,}",
                  DEPROW=f"{dtokens['A_raw']['o200k_base']:,}",
                  EQUATIONS=f"{dtokens['D_verified_equations']['o200k_base']:,}",
                  EQUATIONRED=f"{100 * dependency['reduction_vs_raw']['D_verified_equations']['o200k_base']:.2f}",
                  ASTTOKENS=f"{dtokens['E_plain_ast_source']['o200k_base']:,}",
                  PRIME=f"{reuse['prime_wall_seconds']:.3f}",
                  ISSUANCE=f"{reuse['issuance_wall_seconds']:.3f}")
    for key, value in values.items():
        text = text.replace("@" + key + "@", str(value))
    assert "@" not in text
    generated = ROOT / "manuscript/fragments/incremental_results.tex"
    generated.write_text(text)
    shutil.copyfile(generated, snapshot / "incremental_results.tex")
    shutil.copyfile(Path(__file__), snapshot / "update_manuscript.py")
    sources.extend([str(generated.relative_to(ROOT)), "update_manuscript.py"])
    manifest = {}
    for source in sorted(set(sources)):
        p = ROOT / source
        manifest[source] = hashlib.sha256(p.read_bytes()).hexdigest()
        retained = snapshot / "inputs" / source
        retained.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, retained)
    (snapshot / "evidence_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (snapshot / "checks.json").write_text(json.dumps({"routing_totals_recomputed": True,
        "all_six_live_usage_receipts_checked": True, "paired_residual_requests_identical": True,
        "all_fourteen_saved_outcomes_preserved_on_rescore": True,
        "native_horn_honest_only_boundary_checked": True,
        "historical_cells_relabelled": False, "whole_goal_complete": False}, indent=2) + "\n")
    print(f"Generated working manuscript increment {args.increment}; full research objective remains open.")


if __name__ == "__main__":
    main()
