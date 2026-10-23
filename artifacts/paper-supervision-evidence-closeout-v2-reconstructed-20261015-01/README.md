# Reconstructed revision package

**Proof-Carrying Neurosymbolic Supervision: State, Reasoning, and Evidence Reuse**

Created under the author's instruction to make a local package. This is a new reconstruction from the retained `increment-016` manuscript, not a recovered copy of the missing supplied v2 package. The [source manifest](author_materials/source_manifest.json) records the selected PDF hash, all 29 verified source members and byte-identical retained copies. The selected PDF has 37 pages. Its identity relative to the originally supplied PDF remains unresolved.

Start with [main.md](manuscript/main.md), [appendices.md](manuscript/appendices.md), [abstract.txt](manuscript/abstract.txt) and [REVISION_NOTES.md](author_materials/REVISION_NOTES.md). The Markdown contains page-bounded reading views and ordered original LaTeX so extraction artifacts cannot silently redefine mathematical statements. Individual retained source files remain authoritative. The independently regenerated PDF text matches the retained text exactly; this is extraction verification, not a manuscript build.

The [new arithmetic audit](audit/numerical-01/numerical_audit_results.json) **passed** over 18 explicitly unverified handoff observations, two input/output sums, nine separate contrasts and one separately labeled manuscript aggregate. [comparison_results.csv](audit/numerical-01/comparison_results.csv) retains the contrast interpretation and unknown usage completeness. Failed observations, the configured-packet native fallback and the separate fresh no-index success are preserved. The historical 2,523,452-token subtotal remains unreconciled, and no project-wide total is calculated. Arithmetic consistency does not authenticate runs, prove delivery, deduplicate actual sessions or establish total pipeline cost.

The audit script is newly authored and uses only the Python standard library. After inspecting its imports and side effects, this exact command was run from this package directory:

```bash
python3 author_materials/verify_reported_numbers.py \
  --trials author_materials/reported_trials.jsonl \
  --audit-spec author_materials/numerical_audit.json \
  --output-dir audit/numerical-01
```

The output directory must not already exist. To repeat only this arithmetic check, use another new output directory; never overwrite retained results. [audit_execution.json](audit/audit_execution.json) binds the inspected script, inputs, outputs and exit status. It does not claim the unavailable original audit was run. [recovery_leads.json](author_materials/recovery_leads.json) records fifteen bounded path leads, of which fourteen currently exist, without promoting path existence to recovered evidence.

The package also includes a [proposed design clarification](author_materials/proposed_manuscript_changes.md). It preserves the author's intended prompt → IntentIR → source-grounded CodebaseIR → applicable SecurityIR/LegalIR/UI/UX IR joins → counterexample checks → independently authorized action. It treats repository-specific adaptation and qualification as deployment prerequisites. These insertions are explicitly proposed and do not claim that the retained historical trials exercised the complete chain. No empirical number in the original manuscript was changed.

The selected source occupies **ten main-text pages**, exceeding the required nine. [build_page_anonymity_report.json](audit/build_page_anonymity_report.json) distinguishes this observed page boundary from unperformed clean-build, official-style and anonymity checks. No build, solver, model, training, benchmark or hidden-grader execution was performed. No services or thresholds changed, and nothing was pushed or published.

The objective `paper-supervision-evidence-closeout-v2` remains **prepared, not submitted**. The [updated proposal](author_materials/objective-proposal.json) and [bounded recovery plan](author_materials/audit_plan.md) use this reconstructed package and remove obsolete missing-package gates for local preparation. The existing default paper owner is stopped and no usable admitted submission route was established by the inspected interfaces. Its revival or replacement is not implied by the reconstruction request. [missing_evidence.md](author_materials/missing_evidence.md) records the exact remaining gaps and the smallest remedies. The broader study reconciliation remains pending through the existing authorized owner.

`package_manifest.private.json` binds the completed package. `anonymous_release_inventory.json` declares that no anonymous release has been prepared. Absolute paths, stable hashes and public task IDs can permit correlation. Retained source notices are preserved; do not treat these author materials as a submission supplement.
