"""Freeze a public pre-outcome sampling plan using only approved source metadata."""
import datetime,hashlib,json
from pathlib import Path
b=Path(__file__).resolve().parent;lane=Path('/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026');private=Path('/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/research-inputs/autoformalization/af004-v1')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
s=lane/'papers/completion/autoformalization/data/splits.json';splits=json.loads(s.read_text());assert sha(private/'partitions.private.json')==splits['partition_membership_commitment_sha256']
plan={'schema':'af005-private-annotation-sampling-plan/v1','frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'outcomes_at_freeze':{'human_labels':0,'candidate_outputs_inspected':False,'source_bodies_inspected_by_model':False},
 'target_unique_units':100,'target_operational_groups':20,'population_unique_units':1913,
 'unit_identity':'AF004 normalized_source_unit_sha256; aliases are one unit, never duplicate annotation units',
 'stratum':'unchanged AF004 connected component; every one of20 final-test components included',
 'allocation':'Start n_h=1 per component. Allocate remaining80 by Hamilton largest remainder proportional to (N_h-1), bounded by N_h. Remainder ties use domain-separated HMAC group order. No retries or outcome substitutions.',
 'randomization':'Within each component, take lowest domain-separated HMAC-SHA256 ranks of canonical unique-unit digests, keyed by the existing private partition salt; tie by full unit digest. First frozen protocol seed104729 is included in canonical message. Partition salt and memberships never change.',
 'selection_domain':'AF005-independent-annotation-final-v1',
 'primary_estimand':'finite-population unit mean over the frozen1913 unique final units; not equal-group mean',
 'weights':{'inclusion_probability':'n_h/N_h','inverse_probability_weight':'N_h/n_h','estimator':'sum_h (N_h/n_h) sum_selected_y / 1913','no_missing_labels_as_failures':True,'evaluation_eligibility':'false until actual independent adjudication and all scientific/execution gates pass'},
 'coverage':'Retain all100 selected units and all denominator statuses; no outcome-driven replacement. Fail if population/group/capacity constraints differ.',
 'uncertainty':'Preregistered source-family/time-group cluster bootstrap10000 resamples must retain actual group correlation and unequal weights; report macro-edition sensitivity separately. Twenty operational components are not20 independent publishers/editions; no power or precision guarantee.',
 'slot_mapping':'Public100 provisional templates are retained unchanged. New private bound packet IDs supersede only provisional membership; annotate capacity/reallocation provenance explicitly.',
 'release':'Private owner-only packets for authorized independent annotation. No provider workspace/Git export, no candidate/teacher/prover output or invented labels.',
 'source_bindings':{'private_partition_commitment_sha256':sha(private/'partitions.private.json'),'private_final_source_file_sha256':sha(private/'final_test.private.jsonl'),'guidelines_sha256':sha(lane/'papers/completion/autoformalization/data/annotation_guidelines.md'),'public_packets_sha256':sha(lane/'papers/completion/autoformalization/data/annotation_packets.jsonl'),'public_gold_templates_sha256':sha(lane/'papers/completion/autoformalization/data/gold_facets.jsonl'),'splits_sha256':sha(s),'experiment_plan_sha256':sha(lane/'papers/completion/autoformalization/config/experiment_plan.json')}}
p=b/'sampling_plan.json'
with p.open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
print(json.dumps({'sampling_plan_sha256':sha(p),'human_labels':0,'body_or_identity_output':False}))
