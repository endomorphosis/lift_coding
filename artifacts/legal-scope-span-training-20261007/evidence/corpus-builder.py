#!/usr/bin/env python3
"""Author a bounded occurrence-copy engineering corpus; no legal-gold claims.

Coordinates are captured as each facet is appended. No parser, text search,
model, encoder, optimizer, or semantic reviewer creates these targets. The
existing source-scope owner checks the resulting transport and its zero masks.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib
import json
import random
from pathlib import Path
import sys
import types

SEED = 24602
COUNTS = {"train": 512, "selection": 64, "final": 64}
FACETS = ("modality", "actor", "action", "object", "condition")
TEMPLATES = (
    "actor_modal_action_object_condition",
    "condition_actor_modal_action_object",
    "actor_condition_modal_action_object",
    "modal_actor_action_object_condition",
    "condition_modal_actor_action_object",
    "actor_possessive_gerund_object_modal_condition",
    "condition_actor_possessive_gerund_object_modal",
    "gerund_object_agent_modal_condition",
)
NEGATIVE_CATEGORIES = ("modal_deletion", "modal_misspelling", "extra_exception", "second_rule")
FILES = tuple(f"{split}-{role}.json" for split in COUNTS for role in ("inputs", "references")) + (
    "corpus-protocol.json", "corpus-manifest.json",
)
LEXICONS = {
    "train": {
        "actors": (
            "cedar custodian", "birch steward", "créme clerk", "oak notary",
            "maple registrar", "pine secretary", "ash treasurer", "elm trustee",
            "fir archivist", "hazel curator", "alder examiner", "rowan porter",
            "willow courier", "laurel conservator", "aspen prefect", "yew scribe",
        ),
        "actions": (
            ("archive", "archiving"), ("deliver", "delivering"),
            ("examine", "examining"), ("preserve", "preserving"),
            ("publish", "publishing"), ("carefully sort", "carefully sorting"),
            ("quietly number", "quietly numbering"), ("swiftly inspect", "swiftly inspecting"),
        ),
        "objects": (
            "ivory parcel", "velvet charter", "opal ledger", "bamboo roster",
            "café token", "résumé sheet", "silver tablet", "coral envelope",
            "linen certificate", "mahogany card", "pearl voucher", "ebony plate",
            "copper booklet", "jade receipt", "platinum ribbon", "granite notebook",
        ),
        "conditions": (
            "lantern glows", "signal brightens", "beacon flickers", "ribbon hangs",
            "emblem rests", "pennant waves", "médaille gleams", "glyph sparkles",
        ),
        "exception": "médaille waiver applies",
    },
    "selection": {
        "actors": (
            "marble pilot", "cobalt warden", "naïve surveyor", "bronze marshal",
            "jasper supervisor", "ruby advisor", "amethyst observer", "tourmaline delegate",
            "agate monitor", "obsidian agent", "amber coordinator", "topaz superintendent",
            "beryl manager", "malachite mentor", "hematite facilitator", "lapis attendant",
        ),
        "actions": (
            ("notify", "notifying"), ("consult", "consulting"),
            ("catalogue", "cataloguing"), ("stamp", "stamping"),
            ("compare", "comparing"), ("gently label", "gently labeling"),
            ("boldly route", "boldly routing"), ("neatly arrange", "neatly arranging"),
        ),
        "objects": (
            "azurite memo", "onyx folio", "tulip docket", "dahlia mosaic",
            "jonquil diagram", "orchid summary", "violet inscription", "magnolia stencil",
            "iris medallion", "peony manifest", "fuchsia map", "camellia lithograph",
            "zinnia pamphlet", "begonia seal", "crocus placard", "lotus label",
        ),
        "conditions": (
            "anchor settles", "canvas dries", "fountain flows", "pétale falls",
            "crystal hums", "banner rises", "lattice cools", "bead rolls",
        ),
        "exception": "pétale dispensation applies",
    },
    "final": {
        "actors": (
            "saffron auditor", "citrine inspector", "façade guardian", "quartz commissioner",
            "moss custode", "teal facilitatoré", "ochre patron", "indigo liaison",
            "umber controller", "carmine administrator", "azure preserver", "vermilion councillor",
            "turquoise doyen", "sepia procurator", "lilac intendant", "cerulean emissary",
        ),
        "actions": (
            ("brief", "briefing"), ("seal", "sealing"), ("audit", "auditing"),
            ("copy", "copying"), ("submit", "submitting"),
            ("patiently register", "patiently registering"),
            ("smoothly photograph", "smoothly photographing"),
            ("precisely fold", "precisely folding"),
        ),
        "objects": (
            "papyrus packet", "tinsel scroll", "wicker abstract", "porcelain sketch",
            "terracotta ballot", "satin portfolio", "denim specimen", "chiffon transcript",
            "damask record", "felt register", "tweed index", "suede prospectus",
            "flannel requisition", "hemp outline", "burlap draft", "lambswool attestation",
        ),
        "conditions": (
            "compass steadies", "prism rotates", "feather floats", "cloche sounds",
            "velours warms", "quartz vibrates", "pendulum swings", "spiral turns",
        ),
        "exception": "cloche exemption applies",
    },
}
FINITE_TRIGGERS = {
    "O": ("shall", "must", "is required to", "has a duty to"),
    "P": ("may", "is permitted to", "is authorized to", "has permission to"),
    "F": ("must not", "shall not", "is forbidden to", "is prohibited from"),
}
INF_TRIGGERS = {"O": "is obligatory", "P": "is permissible", "F": "is forbidden"}
NOM_TRIGGERS = {"O": "is required", "P": "is permitted", "F": "is prohibited"}
MODAL_TOKENS = {
    "shall": (("shall",), 0), "must": (("must",), 0),
    "is required to": (("is", "required", "to"), 1),
    "has a duty to": (("has", "a", "duty", "to"), 2),
    "may": (("may",), 0),
    "is permitted to": (("is", "permitted", "to"), 1),
    "is authorized to": (("is", "authorized", "to"), 1),
    "has permission to": (("has", "permission", "to"), 1),
    "must not": (("must", "not"), 0), "shall not": (("shall", "not"), 0),
    "is forbidden to": (("is", "forbidden", "to"), 1),
    "is prohibited from": (("is", "prohibited", "from"), 1),
    "is obligatory": (("is", "obligatory"), 1),
    "is permissible": (("is", "permissible"), 1),
    "is forbidden": (("is", "forbidden"), 1),
    "is required": (("is", "required"), 1),
    "is permitted": (("is", "permitted"), 1),
    "is prohibited": (("is", "prohibited"), 1),
}
ZERO_MASKS = dict.fromkeys(("weak_decoder_fit", "strong_semantic_fit", "contrastive_supervision",
                           "proof_supervision", "fidelity_evaluation"), 0)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Construction:
    """Track Unicode half-open coordinates during literal source construction."""
    def __init__(self):
        self.parts = []
        self.characters = 0
        self.spans = dict.fromkeys(FACETS)

    def literal(self, value):
        self.parts.append(value)
        self.characters += len(value)

    def facet(self, name, value):
        require(name in FACETS and self.spans[name] is None and value,
                "one nonempty appended occurrence per present facet required")
        start = self.characters
        self.literal(value)
        self.spans[name] = [start, self.characters]

    def complete(self):
        text = "".join(self.parts)
        require(len(text) == self.characters, "construction coordinate drift")
        return text, dict(self.spans)


def construct(template, *, actor, action, gerund, obj, condition, modality, trigger_variant):
    """Return raw text and append-captured coordinates, with no string search."""
    c = Construction()
    ordinal = TEMPLATES.index(template)  # template lookup, never a source-text lookup
    finite = FINITE_TRIGGERS[modality][trigger_variant % 4]
    finite_action = gerund if finite == "is prohibited from" else action

    def agent():
        c.facet("actor", actor)

    def object_after(prefix=" the "):
        if obj is not None:
            c.literal(prefix)
            c.facet("object", obj)

    def condition_after(prefix=" if "):
        if condition is not None:
            c.literal(prefix)
            c.facet("condition", condition)

    def initial_condition(fallback):
        if condition is not None:
            c.literal("If ")
            c.facet("condition", condition)
            c.literal(", ")
        else:
            c.literal(fallback)

    def ordinary_body():
        c.literal("the ")
        agent()
        c.literal(" ")
        c.facet("modality", finite)
        c.literal(" ")
        c.facet("action", finite_action)
        object_after()

    def infinitive_body():
        c.literal("it ")
        c.facet("modality", INF_TRIGGERS[modality])
        c.literal(" for the ")
        agent()
        c.literal(" to ")
        c.facet("action", action)
        object_after()

    def possessive_body():
        c.literal("the ")
        agent()
        c.literal("'s ")
        c.facet("action", gerund)
        object_after()
        c.literal(" ")
        c.facet("modality", NOM_TRIGGERS[modality])

    if ordinal == 0:
        ordinary_body()
        condition_after()
    elif ordinal == 1:
        initial_condition("In this procedure, ")
        ordinary_body()
    elif ordinal == 2:
        c.literal("For the declared workflow, the ")
        agent()
        condition_after(", if ")
        if condition is not None:
            c.literal(",")
        c.literal(" ")
        c.facet("modality", finite)
        c.literal(" ")
        c.facet("action", finite_action)
        object_after()
    elif ordinal == 3:
        infinitive_body()
        condition_after(", provided that ")
    elif ordinal == 4:
        initial_condition("For the authored protocol, ")
        infinitive_body()
    elif ordinal == 5:
        possessive_body()
        condition_after(", when ")
    elif ordinal == 6:
        initial_condition("Under the fixture convention, ")
        possessive_body()
    else:
        c.facet("action", gerund)
        object_after()
        c.literal(" by the ")
        agent()
        c.literal(" ")
        c.facet("modality", NOM_TRIGGERS[modality])
        condition_after(", if ")
    c.literal(".")
    return c.complete()


def anagram_token(token, split):
    """Three fixed, nonidentity, mutually distinct byte-preserving permutations."""
    variants = {"train": token[1:] + token[:1],
                "selection": token[2:] + token[:2], "final": token[::-1]}
    require(len(token) >= 3 and len(set(variants.values())) == 3
            and token not in variants.values(), "three distinct held-out operator anagrams required")
    changed = variants[split]
    require(len(changed.encode("utf-8")) == len(token.encode("utf-8"))
            and Counter(changed.encode("utf-8")) == Counter(token.encode("utf-8")),
            "anagram changed the token's byte inventory or length")
    return changed


def unsupported_source(positive_text, spans, category, *, actor, action, exception, split):
    """Corrupt the stored modal segment or append explicitly out-of-profile text."""
    start, end = spans["modality"]
    if category == "modal_deletion":
        return positive_text[:start] + positive_text[end:]
    if category == "modal_misspelling":
        literal = positive_text[start:end]
        # The authored phrase/token annotation is fixed before mutation. Never
        # search or parse raw text to discover the trigger or its word position.
        declared_words, word_ordinal = MODAL_TOKENS[literal]
        require(" ".join(declared_words) == literal, "declared modal annotation changed")
        words = list(declared_words)
        words[word_ordinal] = anagram_token(words[word_ordinal], split)
        mutated = " ".join(words)
        require(len(mutated) == end - start and Counter(mutated.encode()) == Counter(literal.encode()),
                "token-local modal anagram changed source-byte inventory")
        return positive_text[:start] + mutated + positive_text[end:]
    if category == "extra_exception":
        return positive_text[:-1] + " unless " + exception + "."
    require(category == "second_rule", "known unsupported engineering category required")
    return positive_text[:-1] + "; additionally, the " + actor + " may " + action + "."


def _scope_owner(datasets_root):
    """Load only the pure owner leaves from the isolated checkout namespace."""
    root = Path(datasets_root).resolve()
    for name, relative in (
        ("ipfs_datasets_py", "ipfs_datasets_py"),
        ("ipfs_datasets_py.logic", "ipfs_datasets_py/logic"),
        ("ipfs_datasets_py.logic.formalization", "ipfs_datasets_py/logic/formalization"),
        ("ipfs_datasets_py.logic.formalization.autoencoder", "ipfs_datasets_py/logic/formalization/autoencoder"),
        ("ipfs_datasets_py.logic.legal_ir", "ipfs_datasets_py/logic/legal_ir"),
    ):
        if name in sys.modules:
            require(list(getattr(sys.modules[name], "__path__", ())) == [str(root / relative)],
                    "existing imported package does not match isolated source checkout")
        else:
            module = types.ModuleType(name)
            module.__path__ = [str(root / relative)]
            sys.modules[name] = module
    return importlib.import_module(
        "ipfs_datasets_py.logic.formalization.autoencoder.legal_scope_span_proposal")


def build_corpus(datasets_root, seed=SEED):
    require(type(seed) is int and seed == SEED, "fixed authored construction seed required")
    owner = _scope_owner(datasets_root)
    corpus = {}
    all_strings, groups_by_split, values_by_split = {}, {}, {}
    for split, count in COUNTS.items():
        inventory = LEXICONS[split]
        inputs, references = [], []
        values = {facet: set() for facet in ("actor", "action", "object", "condition")}
        groups = set()
        for index in range(count):
            template_ordinal, row = index % 8, index // 8
            template = TEMPLATES[template_ordinal]
            actor = inventory["actors"][(row + 3 * template_ordinal) % 16]
            action, gerund = inventory["actions"][(row // 16 + template_ordinal) % 8]
            modality = ("O", "P", "F")[(row + template_ordinal) % 3]
            has_object = (row // 2 + template_ordinal) % 2 == 0
            has_condition = (row + template_ordinal // 2) % 2 == 0
            repeated = has_object and (row // 4 + template_ordinal) % 3 == 0
            obj = (actor if repeated else inventory["objects"][(row * 5 + template_ordinal) % 16]) if has_object else None
            condition = inventory["conditions"][(row * 7 + template_ordinal) % 8] if has_condition else None
            caller_attachment = ("rule", "statement")[(row // 3 + template_ordinal) % 2]
            text, spans = construct(template, actor=actor, action=action, gerund=gerund,
                obj=obj, condition=condition, modality=modality, trigger_variant=row + template_ordinal)
            prediction = {"schema": owner.PREDICTION_SCHEMA,
                "interpretation_profile": owner.INTERPRETATION_PROFILE,
                "modality": modality, "spans": spans,
                "condition_attachment": caller_attachment if condition is not None else None}
            source_sha256 = text_sha(text)
            source_id = "source:" + source_sha256
            source_group = "group:" + digest({"split": split, "ordinal": index, "positive_sha256": source_sha256})
            require(text not in all_strings, "supported source duplicated across authored groups")
            all_strings[text] = split
            groups.add(source_group)
            proposal = owner.propose_scope_from_spans(text, prediction,
                expected_source_sha256=source_sha256)
            require(proposal["masks"] == ZERO_MASKS and proposal["formal_output"] is None
                and proposal["source_semantics_verified"] is False,
                "construction validation acquired semantic authority")
            for facet in values:
                if spans[facet] is not None:
                    values[facet].add(text[slice(*spans[facet])])
            metadata = {"source_group": source_group, "template": template,
                "condition_attachment": caller_attachment}
            inputs.append({"id": source_id, "source_text": text,
                "source_sha256": source_sha256, **metadata})
            references.append({"id": source_id, "source_group": source_group,
                "source_sha256": source_sha256, "supported": True,
                "prediction": prediction, "parent_source_id": source_id,
                "repeated_actor_object_occurrences": repeated,
                "reference_origin": "authored_engineering_construction",
                "natural_source_semantics_verified": False,
                "independent_legal_review": False, "admission_masks": dict(ZERO_MASKS)})
            category = NEGATIVE_CATEGORIES[(row + template_ordinal) % 4]
            negative_text = unsupported_source(text, spans, category, actor=actor,
                action=action, exception=inventory["exception"], split=split)
            negative_sha = text_sha(negative_text)
            require(negative_text not in all_strings, "unsupported source duplicates another authored group")
            all_strings[negative_text] = split
            negative_id = "source:" + negative_sha
            inputs.append({"id": negative_id, "source_text": negative_text,
                "source_sha256": negative_sha, **metadata})
            references.append({"id": negative_id, "source_group": source_group,
                "source_sha256": negative_sha, "supported": False,
                "prediction": None,
                "unsupported_category": category, "parent_source_id": source_id,
                "reference_origin": "authored_outside_single_rule_engineering_profile",
                "legally_false_claimed": False,
                "natural_source_semantics_verified": False,
                "independent_legal_review": False, "admission_masks": dict(ZERO_MASKS)})
        # Preserve parent groups while removing positive/negative positional cues.
        ordering = list(range(len(inputs)))
        random.Random(seed + (0, 1, 2)[list(COUNTS).index(split)]).shuffle(ordering)
        corpus[split] = {"inputs": [inputs[i] for i in ordering],
                         "references": [references[i] for i in ordering]}
        groups_by_split[split] = groups
        values_by_split[split] = values
    for left in COUNTS:
        for right in COUNTS:
            if left >= right:
                continue
            require(not groups_by_split[left] & groups_by_split[right], "source groups cross split")
            for facet in values_by_split[left]:
                normalized = lambda values: {" ".join(v.casefold().split()) for v in values}
                require(not normalized(values_by_split[left][facet]) & normalized(values_by_split[right][facet]),
                        "authored facet lexemes cross split: " + facet)
    return corpus


def training_batches(train_inputs, train_references, seed=SEED, updates=240):
    """Deterministic balanced row-ID schedule shared by both numerical arms."""
    require(seed == SEED and updates == 240, "fixed authored fit draw protocol required")
    refs = {row["id"]: row for row in train_references}
    require(len(refs) == len(train_inputs) == 1024 and set(refs) == {r["id"] for r in train_inputs},
            "complete train input/reference join required")
    pools = {supported: [row["id"] for row in train_inputs if refs[row["id"]]["supported"] is supported]
             for supported in (True, False)}
    require(all(len(pool) == 512 for pool in pools.values()), "512+512 train pool required")
    rng = random.Random(seed)
    cursors = {True: 512, False: 512}
    batches = []
    for _ in range(updates):
        batch = []
        for supported in (True, False):
            if cursors[supported] == 512:
                rng.shuffle(pools[supported])
                cursors[supported] = 0
            cursor = cursors[supported]
            batch.extend(pools[supported][cursor:cursor + 8])
            cursors[supported] += 8
        rng.shuffle(batch)
        batches.append(batch)
    return batches


def protocol():
    return {
        "schema": "legal-single-rule-occurrence-engineering-protocol/v1",
        "seed": SEED, "arms": [{"name": "bytekernel1", "byte_kernel_size": 1},
                                 {"name": "bytekernel3", "byte_kernel_size": 3}],
        "initialization": "Initialize kernel1 with seed24602 and kernel3 with the same config/seed. Copy every common-shaped parameter from kernel1 into kernel3; zero both outer Conv3 weight positions and copy Conv1 weights into the center. All biases, embeddings, GRU and heads initially match. Measure functional logit allclose/proposal parity before fitting. Kernel3 extra local weights start0 and their parameter counts are disclosed. Existing frozen models remain intact.",
        "caller_attachment": "rule|statement is an explicit caller premise, never a learned target or source-semantic claim. Copy it to predicted condition_attachment only when a condition occurrence is present; otherwise null.",
        "scope": "Raw-source, single O/P/F norm; modality/actor/action and nullable object/opaque condition occurrences. Only this authored grammar is supported.",
        "targets": "legal-scope-span-prediction/v1; opaque_condition_attachment/v1; Unicode-character half-open coordinates captured while appending source facets.",
        "learned_heads": ["support", "modality_class", "object_presence", "condition_presence",
                          "modality_start", "modality_end", "actor_start", "actor_end",
                          "action_start", "action_end", "object_start", "object_end",
                          "condition_start", "condition_end"],
        "unsupported_meaning": "Outside this single-rule engineering grammar, not legally false. Unsupported references contain no structural targets.",
        "negative_categories": list(NEGATIVE_CATEGORIES),
        "modal_anagram_protocol": "Change exactly one preannotated operator word without changing token order/spaces, full-source UTF8 length or per-token UTF8 byte multiset. TRAIN rotates that word left1, selection left2, final reverses it; all three are nonidentity and mutually distinct. These are paired outside-profile fixture controls, not legally false statements. Kernel1 mean/max token-byte pooling is invariant; kernel3 can learn within-token byte order.",
        "templates": list(TEMPLATES), "split_supported_counts": dict(COUNTS),
        "split_unsupported_counts": dict(COUNTS),
        "paired_source_accounting": "One positive and one corrupted negative per source group, kept in the same split; no duplicate raw text. No source-group or normalized facet-lexeme overlap between splits.",
        "split_lexicon_sha256": digest(LEXICONS),
        "optimizer": "AdamW", "learning_rate": 0.003, "weight_decay": 0.0,
        "updates_per_arm": 240, "batch_size": 16, "positive_per_batch": 8,
        "negative_per_batch": 8, "row_presentations_per_arm": 3840,
        "selection_steps": [0, 120, 240],
        "selection_score_descending": ["exact_positive_count+negative_learned_refusal_count",
                                       "-negative_emitted_request_count", "exact_positive_count",
                                       "-completed_updates"],
        "support_threshold": 0.5,
        "support_loss": "Binary cross entropy on all rows; structural/presence/modality/endpoint losses only on supported TRAIN rows, endpoint losses only for present facets.",
        "model_inputs": "Full raw UTF8 source bytes only. Caller condition_attachment is copied at proposal assembly; id/group/template/digest metadata and reference labels never enter source features.",
        "source_budget": "No truncation, padding-as-content, parser, search, nearest-keyword anchor recovery or cached source teacher. Preserve complete source and reject an over-budget input.",
        "context_tokens_max": 512, "output_tokens_max": 512,
        "temperature": 0, "workers": 1, "cpu_only": True,
        "final_reference_barrier": "Both arm selections/checkpoints and their hashes must be durable before the numerical runner opens/parses final-references.json. Author construction/validation and raw artifact hashing are not numerical evaluation. Final inputs are separate target-free records.",
        "selection_reference_use": "Selection only; no fit gradients or posthoc threshold adjustments.",
        "evaluation": "Report whole prediction/source-scope exactness, all five present/null facet spans, modality, presence false positives/negatives, learned negative refusals, unsafe negative emissions, incidental structural blocks, abstentions and invalid proposals with complete denominators. Validate every emitted positive against existing scope owner; all admission masks0.",
        "authorship": "Independent construction does not establish independent legal review. Every target is an authored engineering premise; no source-law accuracy, proof, qualification, admission or promotion is claimed.",
        "natural_source_semantics_verified": False, "independent_legal_review": False,
        "training_admission_granted": False, "qualified": False, "formalized": False,
        "proof_authority": False, "admission_masks": dict(ZERO_MASKS),
        "existing_8D_384D_768D_4096D_models_modified": False,
    }


def write_corpus(output, datasets_root, seed=SEED):
    output = Path(output).resolve()
    require(output.is_dir(), "existing task artifact directory required")
    require(not any((output / name).exists() for name in FILES), "corpus artifacts are immutable; choose a fresh output directory")
    corpus = build_corpus(datasets_root, seed)
    plan = protocol()
    batches = training_batches(corpus["train"]["inputs"], corpus["train"]["references"])
    plan["training_schedule_sha256"] = digest(batches)
    plan["template_renderer_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    artifacts = {}
    def save(name, value):
        path = output / name
        data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        with path.open("xb") as stream:
            stream.write(data)
        artifacts[name] = {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(),
                           "bytes": len(data), "canonical_sha256": digest(value)}
    for split, values in corpus.items():
        save(f"{split}-inputs.json", values["inputs"])
        save(f"{split}-references.json", values["references"])
    save("corpus-protocol.json", plan)
    statistics = {}
    for split, values in corpus.items():
        positive = [r for r in values["references"] if r["supported"]]
        negative = [r for r in values["references"] if not r["supported"]]
        stats = {
            "input_rows": len(values["inputs"]), "positive_rows": len(positive), "negative_rows": len(negative),
            "unique_raw_sources": len({r["source_text"] for r in values["inputs"]}),
            "source_groups": len({r["source_group"] for r in values["inputs"]}),
            "modalities": dict(Counter(r["prediction"]["modality"] for r in positive)),
            "templates_positive": dict(Counter(r["template"] for r in values["inputs"] if r["id"] in {p["id"] for p in positive})),
            "negative_categories": dict(Counter(r["unsupported_category"] for r in negative)),
            "object_present": sum(r["prediction"]["spans"]["object"] is not None for r in positive),
            "condition_present": sum(r["prediction"]["spans"]["condition"] is not None for r in positive),
            "repeated_actor_object_occurrences": sum(r["repeated_actor_object_occurrences"] for r in positive),
            "unicode_sources": sum(any(ord(char) > 127 for char in r["source_text"]) for r in values["inputs"]),
            "maximum_source_characters": max(len(r["source_text"]) for r in values["inputs"]),
            "maximum_source_UTF8_bytes": max(len(r["source_text"].encode("utf-8")) for r in values["inputs"]),
            "source_scope_transport_validated_positive": len(positive),
            "condition_attachment_caller_inputs": dict(Counter(r["condition_attachment"] for r in values["inputs"])),
        }
        statistics[split] = stats
    owner_paths = [Path(datasets_root) / "ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_span_proposal.py",
                   Path(datasets_root) / "ipfs_datasets_py/logic/legal_ir/canonical_statement_scope.py"]
    manifest = {
        "schema": "legal-single-rule-authored-corpus-manifest/v1", "complete": True,
        "construction_seed": seed, "artifacts": artifacts, "statistics": statistics,
        "construction_source": {"path": str(Path(__file__).resolve()), "sha256": plan["template_renderer_sha256"]},
        "scope_owner_bindings": [{"path": str(p.resolve()), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size} for p in owner_paths],
        "training_schedule_sha256": digest(batches),
        "training_unique_presented_sources": len({s for batch in batches for s in batch}),
        "same_text_duplicated_for_attachment_profiles": False,
        "normalized_facet_lexemes_and_source_groups_split_disjoint": True,
        "unsupported_rows_have_structural_targets": False,
        "source_semantics_verified": False, "independent_legal_review": False,
        "qualification_or_training_admission_granted": False,
        "numerical_model_encoder_optimizer_prover_calls": 0,
        "admission_masks": dict(ZERO_MASKS),
    }
    save("corpus-manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--datasets-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    manifest = write_corpus(args.output, args.datasets_root, args.seed)
    print(json.dumps({"complete": manifest["complete"], "statistics": manifest["statistics"],
                      "training_schedule_sha256": manifest["training_schedule_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
