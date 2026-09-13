# NS-024 methods-essential LLM use disclosure

This record restates the disclosure compiled into PDF page 13 and
`appendix/llm_usage_disclosure.tex`
(`cf7395658ce77a0872a0b914ac7b28f0173501f7ee2ee71c0f24eeed163a3ec7`). It does
not invent unrecorded model calls, fallback invocations, or independent
human checks.

## Scientific comparison (methodology-essential)

| Item | Recorded fact |
|---|---|
| Model | Grok 4.6, bound as served alias `grok-4.6` |
| Role | One proposal POST per frozen cell, structured edit response |
| Cells | 32, eight families, arms A/B, nested repetitions 104729 and 130363 |
| Output cap | 4,096 requested output tokens |
| Fallback / retry | None for the scientific comparison |
| Served seed / reasoning-effort | Not used |
| Exact served revision / weights | Unavailable (`underlying_served_revision_known`: false) |
| Independent checks | Cold, network-disabled scoring of admitted candidates; AI candidate inspection is a procedural control, not independent human assessment |

The five original draft placeholders in §K.1 (`[actual implementation
assistance]`, `[candidate goals/plans/patches]`, `[proof candidates]`,
`[data processing]`, `[manuscript preparation]`) are gone. Unused proof-candidate
generation is not implied.

## Research and manuscript assistance (configured policy)

Authoring supervisors were configured to use Grok 4.6, with Codex
`gpt-5.6-terra` at high reasoning effort as a fallback only after
independently verified primary-quota exhaustion. That statement describes
the configured policy. It does not claim that every task used a fallback, that
every interactive session used those models, or that the scientific 32-cell
comparison mixed authoring fallbacks.

AI assistance contributed to source recovery and drafting, implementation and
debugging, experiment preparation and candidate inspection, and analysis and
artifact preparation. AI-assisted checking does not measure human semantic
fidelity, expert agreement, or human effort time, and it does not discharge
the unmachine-checked arguments in Appendix A.

## Public numerical reproduction

The supplement command `python3 -B reproduce.py --root ROOT --output OUTPUT`
rechecks manifest-bound files and retained scalar summaries. It does not
generate new proposals, execute candidates or hidden tests, rerun historical
qualifications, or authenticate original signed records.

## Independent checks that were not performed

No outside reviewer was recruited. No new provider or scorer call was issued
by this packaging task. Exact served-model revision remains author- or
provider-owned and unresolved. Human evaluation remains unmeasured.
