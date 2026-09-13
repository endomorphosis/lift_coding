# Historical development provider and signed cold-score client

The current implementation connects `run_comparison.py` to an operator-owned historical development service. One frozen XMLtodict/A/local_cold grant produced one actual Grok 4.6 HTTP response and a 574-byte patch; after explicit AI operator source review, a separate cold scorer passed 34 visible tests and one hidden test. The signed result was imported, resumed and reverified without another model or scorer call. This is one development pipeline qualification, not a final A–D comparison, production population admission or human annotation.

The executable host installation, source/profile admission, exact queue commands, review stage, interruption rules and later NS011/NS016 responsibilities are in [host_service/README.md](../qualification/production_provider/host_service/README.md). The [scorer trust limitation](../qualification/production_provider/SCORER_TRUST_LIMITS.md) applies to this specifically reviewed candidate. Adversarial observation integrity remains unqualified; no adversarial demonstration was executed.

Run from the paper repository with the bound `production_profile.json` and retained public host receipt:

```sh
python3 papers/completion/neurosymbolic_supervision/experiments/production_gateway.py probe --out "$OUT/probe.json"
python3 papers/completion/neurosymbolic_supervision/experiments/run_comparison.py one-task --task-id ns-hist-01-xmltodict --arm A --cache local_cold --repetition 0 --record-kind development --path production --ledger "$LOCAL_LEDGER" --out "$OUT/attempt.json"
python3 papers/completion/neurosymbolic_supervision/experiments/score_runs.py --attempt "$OUT/attempt.json" --out "$OUT/rescored.json"
```

The historical development branch sends only the offered request IDs, uses no client API credential or Docker socket and never reconstructs the hidden oracle. While the operator has not returned a signed final result, `one-task` returns pending (exit 75) without publishing a terminal scientific outcome. Resume the same ledger and schedule after the signed response arrives. A completed grant imports/revalidates its existing result. `score_runs.py` verifies this signed host result; it does not perform another hidden-test run. Use a durable `host_receipts/<grant>/` record before removing the ephemeral queue.

`one-arm` and `paired` retain the NS006 CLI structure, but require separately reviewed exact grants for every development schedule cell; the one A grant does not admit another arm. NS011 owns additional arm/reuse implementation and qualification. NS016 owns the pilot/final freeze and new host admission code for locked splits. Current adapter lookup rejects the twelve pilot/final units; a changed environment variable or final record-kind flag cannot unlock them. No paired-model mixing, silent population shrinkage or automatic call retry is authorized.

NS004's proposed `gpt-5.6-terra`/`high` scientific profile through verified-quota-only fallback remains preserved. No fresh quota event or Codex scientific call is claimed. The current HTTP scientific development grant freezes `grok-4.6`, maximum one POST, request ≤64 KiB, patch ≤16 KiB, no tools, and the exact sequential Docker/scorer resources. Reasoning effort and temperature are omitted; returned API fingerprint is metadata, not an immutable model revision. Requested `max_tokens=4096` is not proof of a reasoning-token hard cap. Raw usage and API cost ticks remain retained; settled charges and aggregate client-remote CPU/memory/wait measurements are unavailable.

The older `--path development --admitted-provider` addition fixture and its separate unchanged historical materialization remain preserved draft evidence. They do not establish the real historical model-to-repair route. The old `qualification/production_provider/run_qualification.py` entry is disabled because invoking it again would create a fresh unrelated effect. NS006's explicitly labeled stub/simulated paths remain implementation controls, not scored historical results.
