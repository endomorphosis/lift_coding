from pathlib import Path
import datetime,hashlib,json
E=Path(__file__).resolve().parent.parent;ROOT=E.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert (E/'autoencoder/scientific_profile.json').exists()
assert (E/'assistance/frozen_natural_protocol.json').exists()
files=[E/'pipeline'/n for n in ['native_c.py','run_corpus.py','release_final.py']]
files += [E/'guidance'/n for n in ['native_b.py','learned_route.py','structural_checks.py','qualification.json']]
files += [E/'assistance'/n for n in ['run_natural_a.py','leanstral_v15.jinja','frozen_natural_protocol.json']]
files += [E/'autoencoder'/n for n in ['scientific_profile.json','source_only_eval.py','encode_sources.py','score_embeddings.py','derive_t1.py','derive_t3.py']]
files += [ROOT/'scripts/run_leanstral_ephemeral.py']
files += list((E/'pipeline/patch_overlay').rglob('*.py'))
modules=['optimizers/logic_theorem_optimizer/'+n+'.py' for n in ['modal_ir','modal_registry','legal_modal_parser','spacy_modal_codec','modal_autoencoder']]
modules += ['logic/modal/'+n+'.py' for n in ['codec','decompiler']]
modules += ['logic/legal_ir/'+n+'.py' for n in ['canonical_compiler','canonical_contracts','canonical_decompiler','canonical_roundtrip']]
files += [ROOT/'external/ipfs_datasets/ipfs_datasets_py'/n for n in modules]
# Scientific choices are fixed here, before source identities/outcomes are opened.
x={'schema':'autoformalization-final-empirical-protocol/v1','frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'ready_for_final_source_access':True,'final_source_access_before_freeze':False,
 'code_sha256':{str(p):sha(p) for p in files},
 'source_population':{'raw_records':1921,'deduplicated_units':1913,'domains':{'cfr':993,'mpep':738,'uscode':175,'guidance':7},'train':69,'selection':15,'canary':38,'source_prefix_chars':4096,'embedding_input':'full text, existing AF029 windowing contract','alias_rule':'NFKC casefold Unicode alphanumeric token sequence; lexicographic first record ID'},
 'pipeline_profiles':{'B':'actual strict native typed deontic compiler + native source-withheld roundtrip; source-derived lexical vocabulary capped1000; five seconds per record',
 'C':'actual native SpaCyLegalEncoder+SpaCyModalIRCompiler+native clause enrichment; omits KG/embedding decoration; ten seconds per record including cycle',
 'T5':'C plus original AF014 executable exception-scoping patch, selected on development data before this evaluation',
 'A':'100 units chosen by smallest SHA256(AF20260914-A100: + full normalized unit SHA); Leanstral1.5 direct formula JSON max8; temperature0,2048tokens,60s, one attempt per source; same registered operators/checks asC; separate matched100-source comparison',
 'E_T4':'qualified actual T3 obligation prior schedules both immutable structural checks, off/on/rollback; all1913 sources andthree seeds; no coverage gain possible from order alone',
 'D':'native solver/Lean proof assistance measured on separate64 constructed pairedgoals; no unsupported natural cross-view proof score fabricated'},
 'cycle_projection':'remove original normalized text, all metadata, frame fields and source IDs/maps/spans; preserve operator/predicate/conditions/exceptions semantic fields; native decompile and recompile first4096 output chars; compare semantic-field formula multiset; empty-to-empty is excluded from nonempty coverage',
 'statistics':{'primary':'counts with all planned denominators; errors,timeouts,abstentions explicit; pairedsource outcomes',
 'uncertainty':'10000 paired operational-component bootstrap draws, seed104729; 20 components/4 editions with dominant1738-record component; not20 independent legal editions; unitstratified2000draw intervals secondary conditional diagnostics',
 'ae':'T0cold,actualT1memorylookup,threeT2source-conditioned reconstruction, T3exacttieddecoder reuse plus actualfixed-contextproofheadexports; identity-copy cosine1/MSE0 control makes absence of bottleneck explicit',
 'repair':'paired semantic-field changes, exception-role correction and removal of exception-token leakage; schema/span regressions; structural repair effects not independent semantic correctness',
 'human_semantic_fidelity':'not measured, not a prerequisite for these automated experiments'},
 'resource_profile':'Bounded temporary Leanstral jobs90GiB4CPUs; persistent service masked. Corpus workers4GiB each, 4 per C/T5 arm, at most8, CPU pool4-15; AE bounded8GiB2CPUs. No retraining, no final-driven candidate repair.',
 'development_receipts':[str(p.relative_to(E)) for p in (E/'pipeline').glob('*_v2.jsonl')],
 'amendment_policy':'Preserve any failed run; later infrastructure-only fixes explicitly versioned, no candidate tuning from final outputs.'}
p=E/'FINAL_PROTOCOL_FREEZE.json'
with p.open('x') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n')
print(sha(p))
