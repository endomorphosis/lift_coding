"""Read-only custody/typed-JSON authentication; never instantiate a model."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import time

ROOT = Path('/home/barberb/lift_coding')
TREE = ROOT / '.worktrees/normative-checkpoint-availability-datasets-20261006'
OUT = ROOT / 'artifacts/normative-checkpoint-availability-20261006/authentication'
STUDY = ROOT / 'external/ipfs_datasets/workspace/test-logs/decoder-normative-wording-r2-20261006'
EXPECTED_HEAD = '61c5db04538596ea00091cd4f013500854368397'
PUBLIC = TREE / 'docs/implementation/reports/evidence/decoder-normative-wording-20261006/results.json'
OWNER = TREE / 'ipfs_datasets_py/logic/formalization/autoencoder/contextual_legal_ir_runtime.py'
EXPECTED_OWNER = '773e30977478921c31fbc075b5357339cc13e8e920ba93be85b5160b7f442a15'
FORBIDDEN = {'torch','numpy','transformers','accelerate','datasets','huggingface_hub','safetensors','duckdb','sqlite3','tensorflow','jax'}
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
FALSE_KEYS = ('admitted','checkpoint_promoted','convergence_proven','formalized','fresh_holdout',
 'lake_executed','optimizer_resumable','proof_authority','qualified','roundtrip_ok','source_semantics_verified')

def require(condition, message):
    if not condition:
        raise ValueError(message)

def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()

def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()

def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result

def decode(data):
    return json.loads(data, object_pairs_hook=unique_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON')))

def witness(value):
    return {key: getattr(value, 'st_' + key) for key in ('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')}

def canonical(path):
    require(type(path) in (str, Path) or isinstance(path, Path), 'path type')
    value = Path(path)
    require(value.is_absolute() and '..' not in value.parts and str(value) == str(value.resolve(strict=True)), 'canonical absolute existing path required')
    item = value.lstat()
    require(stat.S_ISREG(item.st_mode) and item.st_nlink == 1, 'single-link regular file required')
    return value

observations = {}
total = 0
def authenticate(path, expected=None, *, retain=False, cap=MAX_FILE):
    global total
    path = canonical(path)
    if str(path) in observations:
        observed = observations[str(path)]
        if expected is not None:
            require(all(observed[k] == expected[k] for k in ('bytes','sha256')), 'repeat pin differs')
        if retain:
            # Independent bounded second descriptor read with the same endpoint requirements.
            saved = observations.pop(str(path))
            data, observed2 = authenticate(path, saved, retain=True, cap=cap)
            return data, observed2
        return None, observed
    before = path.lstat()
    require(before.st_size <= cap and before.st_size > 0, 'bounded file size required')
    require(total + before.st_size <= MAX_TOTAL, 'aggregate byte cap')
    total += before.st_size
    if expected is not None:
        require(type(expected['bytes']) is int and expected['bytes'] == before.st_size, 'declared size differs')
        require(type(expected['sha256']) is str and len(expected['sha256']) == 64, 'declared digest type')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    chunks = []
    try:
        start = witness(os.fstat(fd))
        require(start == witness(before), 'opened identity differs')
        sha = hashlib.sha256()
        git = hashlib.sha1(b'blob ' + str(before.st_size).encode() + b'\0')
        count = 0
        while True:
            piece = os.read(fd, min(1024 * 1024, cap + 1 - count))
            if not piece:
                break
            count += len(piece)
            require(count <= cap, 'read cap exceeded')
            sha.update(piece); git.update(piece)
            if retain:
                chunks.append(piece)
        require(count == before.st_size and witness(os.fstat(fd)) == start, 'descriptor changed while reading')
        require(canonical(path) == path and witness(path.lstat()) == start, 'path changed while reading')
    finally:
        os.close(fd)
    observed = {'path': str(path), 'bytes': count, 'sha256': sha.hexdigest(), 'git_blob_oid': git.hexdigest(), 'file_witness': start}
    if expected is not None:
        require(all(observed[k] == expected[k] for k in ('bytes','sha256')), 'authenticated bytes differ from receipt')
    observations[str(path)] = observed
    return b''.join(chunks) if retain else None, observed

def document(path, expected=None, cap=8*1024*1024):
    content, observed = authenticate(path, expected, retain=True, cap=cap)
    return decode(content), observed

def ref(pin):
    return {key: pin[key] for key in ('path','bytes','sha256')}

def process_snapshot():
    matches = []
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            pid = int(path.parent.name)
            if pid in (os.getpid(), os.getppid()):
                continue
            data = path.read_bytes()
            # Do not emit arguments, source text, environment, or arbitrary credentials.
            if len(data) <= 8192 and b'\n' not in data and b'decoder-normative-wording-r2-20261006' in data:
                matches.append({'pid': pid, 'executable_basename': Path(data.split(b'\0')[0].decode(errors='replace')).name,
                                'fixed_study_marker_present': True})
        except (OSError, ValueError):
            continue
    return {'matching_processes': matches, 'scope': 'bounded /proc cmdline snapshot; not writer exclusion or continuous attestation'}

head = subprocess.check_output(['git','rev-parse','HEAD'], cwd=TREE, text=True).strip()
require(head == EXPECTED_HEAD, 'reviewed datasets head differs')

class BlockImports:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in FORBIDDEN:
            raise ImportError('heavy/data/model import denied: ' + fullname)
        return None

sys.meta_path.insert(0, BlockImports())
def audit(event, args):
    require(event not in ('socket.connect','socket.connect_ex','socket.bind','subprocess.Popen','os.system','os.posix_spawn'), 'network/process effect denied')
sys.addaudithook(audit)
require(not (FORBIDDEN & set(sys.modules)), 'heavy imports already loaded')
started = time.time()
process_before = process_snapshot()
public, public_pin = document(PUBLIC)
_, owner_pin = authenticate(OWNER, {'bytes': OWNER.stat().st_size, 'sha256': EXPECTED_OWNER})
spec = importlib.util.spec_from_file_location('custody_metadata_owner', OWNER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
require(Path(helper.__file__).resolve() == OWNER, 'metadata helper origin differs')

prior, prior_pin = document(ROOT / 'artifacts/autoencoder-progress-reconciliation-20261006/datasets/reconciliation-findings.json')
prior_states = {item['original_complete_state_pin']['sha256']: item for item in prior['newer_normative_training_already_published']['states']}
require(len(public['panels']) == 8 and set(public['training']) == {'384','768'}, 'exact eight endpoints / two widths required')
state_rows, preprocessing_rows, completion_rows = [], [], []
selected_documents, alias_groups = {}, []
support_pins, source_pins = [], [owner_pin]
for dimension in (384, 768):
    directory = STUDY / f'training-{dimension}-r1/results'
    preprocessing, pp_pin = document(directory / 'preprocessing.json')
    helper._false_flags(preprocessing)
    helper._normalization(preprocessing['paragraph_normalization'], dimension)
    helper._normalization(preprocessing['clause_normalization'], dimension)
    summary, summary_pin = document(directory / 'summary.json')
    require(summary['complete'] is True and summary['dimension'] == dimension and summary['phase'] == 'training', 'completed training summary required')
    seal, seal_pin = document(directory / 'sealed-recipe.json')
    support_pins.extend([pp_pin, summary_pin, seal_pin])
    completion = []
    for path, key, expected in ((STUDY/f'training-{dimension}-r1-guardian-exit.json','returncode',0),
                               (STUDY/f'training-{dimension}-r1/child-exit.json','returncode',0),
                               (STUDY/f'training-{dimension}-r1/resources-final.json','status','released')):
        terminal, terminal_pin = document(path)
        require(terminal[key] == expected, 'completed terminal receipt required')
        completion.append(terminal_pin)
    completion_rows.append({'dimension': dimension, 'complete': True, 'summary_pin': summary_pin, 'terminal_pins': completion})
    normalization_metadata = {key: preprocessing[key] for key in ('dimension','initializer','input_transform','paragraph_normalization','clause_normalization','count_prior','projection_policy','representation','source_binding','source_inputs_sha256')}
    preprocessing_rows.append({'dimension': dimension, 'original_preprocessing_pin': pp_pin,
        'contains_saved_TRAIN_paragraph_and_clause_feature_vectors': True,
        'direct_public_copy_admissible': False, 'frozen_metadata': normalization_metadata,
        'paragraph_vector_binding': 'caller_pinned_asset_bytes', 'saved_paragraph_vector_producer_authenticated': False,
        'independent_clause_encoder_producer_authenticated': False})
    for arm in public['training'][str(dimension)]:
        name = arm['arm']
        require(name in ('normative-wording-zero','normative-wording-ce') and arm['budget_completed'] is True, 'fixed completed arm required')
        pinned_summary = next(item for item in summary['runs'] if item['arm'] == name)
        arm_summary, arm_pin = document(pinned_summary['summary_path'], {'bytes': Path(pinned_summary['summary_path']).stat().st_size, 'sha256': pinned_summary['summary_sha256']})
        require(raw(arm_summary) == raw(arm), 'published training summary differs from fixed run receipt')
        support_pins.append(arm_pin)
        for key in ('schedule','cache','source_inventory','bank','training_ref'):
            _, support_pin = authenticate(arm[key]['path'], arm[key])
            support_pins.append(support_pin)
        _, parent_pin = authenticate(arm['parent_state']['path'], arm['parent_state'], cap=8*1024*1024)
        _, initial_pin = authenticate(arm['states']['initial']['path'], arm['states']['initial'], cap=8*1024*1024)
        require(arm['states']['initial']['tensor_sha256'] == arm['parent_state']['tensor_sha256'], 'continued initial tensors differ from immediate parent receipt')
        support_pins.extend([parent_pin, initial_pin])
        for role in ('selected','last-attempt'):
            expected = arm['states'][role]
            panel = next(item for item in public['panels'] if (item['dimension'],item['arm'],item['role']) == (dimension,name,role))
            require(panel['state_ref'] == expected and expected['sha256'] in prior_states, 'three independent endpoint pin joins required')
            require(prior_states[expected['sha256']]['original_complete_state_pin'] == ref(expected), 'prior serialization pin differs')
            checkpoint, cp_pin = document(expected['path'], expected)
            require(checkpoint['schema'] == 'private-native-dimension-source-state/v1', 'private serialization schema')
            require(type(checkpoint['dimension']) is int and checkpoint['dimension'] == dimension and checkpoint['role'] == role and checkpoint['selected'] is True, 'dimension/role/selected header differs')
            require(checkpoint['recipe'] == {'name': name, 'weight': 0.0 if name.endswith('-zero') else 0.05}, 'preserve exact normative recipe')
            require(all(checkpoint[key] is False for key in FALSE_KEYS), 'false state authority required')
            helper._false_flags(checkpoint)
            shapes, _ = helper._shapes(dimension)
            typed_sha = helper._tensor_digest(checkpoint['model_state'], shapes, integer_buffers=True)
            require(typed_sha == checkpoint['tensor_sha256'] == expected['tensor_sha256'], 'typed tensor digest differs')
            require(helper._digest(checkpoint['model_state']) == checkpoint['weights_sha256'], 'canonical weights digest differs')
            codec = checkpoint['codec']
            require(set(codec) == {'schema','target_vocabulary'} and codec['schema'] == 'typed-json-lexical/v1' and len(codec['target_vocabulary']) == 32 and len(set(codec['target_vocabulary'])) == 32, 'exact codec inventory required')
            require(helper._digest(codec) == checkpoint['lineage']['teacher_codec_sha256'], 'codec lineage digest differs')
            require(raw(checkpoint['initializer_receipt']) == raw(preprocessing['initializer']) and raw(checkpoint['input_transform']) == raw(preprocessing['input_transform']), 'frozen initialization/transform joins differ')
            helper._receipt(checkpoint['initializer_receipt'], 'dimension-native-raw-decoder-development/v1')
            architecture = checkpoint['architecture']
            require(raw(architecture['normalization']) == raw(preprocessing['paragraph_normalization']) and raw(architecture['clause_normalization']) == raw(preprocessing['clause_normalization']), 'frozen normalization metadata join differs')
            for key, value in (('body.source_mean',preprocessing['paragraph_normalization']['mean']),('body.source_scale',preprocessing['paragraph_normalization']['scale']),('clause_source_mean',preprocessing['clause_normalization']['mean']),('clause_source_scale',preprocessing['clause_normalization']['scale']),('body.count_prior_logits',preprocessing['count_prior']['log_prior'])):
                require(helper._array(checkpoint['model_state'][key], shapes[key]) == helper._array(value, shapes[key]), 'saved float32 normalization/prior tensor differs')
            group = f'legal_ir/{dimension}/{name}/{typed_sha}'
            row = {'ir_family_id':'legal_ir','dimension':dimension,'dimension_role':'input_embedding','task_id':'semantic_IR_reconstruction',
                'native_ir_schema_version':None,'decoder_profile_id':None,'decoder_format_id':None,
                'serialization_schema':checkpoint['schema'],'arm':name,'role':role,'selected_header_value':True,
                'recipe':checkpoint['recipe'],'original_checkpoint_pin':cp_pin,'tensor_sha256':typed_sha,
                'canonical_weights_sha256':checkpoint['weights_sha256'],'full_model_state_entries':len(checkpoint['model_state']),
                'codec':codec,'codec_sha256':helper._digest(codec),'lineage':checkpoint['lineage'],
                'initializer_receipt':checkpoint['initializer_receipt'],'immediate_parent_pin':parent_pin,
                'immediate_parent_tensor_sha256':arm['parent_state']['tensor_sha256'],'continued_initial_state_pin':initial_pin,
                'preprocessing_pin':pp_pin,'completed_training_summary_pin':arm_pin,'numeric_alias_group':group,
                'checkpoint_bytes_authenticated':True,'typed_JSON_tensor_digest_authenticated':True,
                'runtime_api_recipe_supported':False,'runtime_api_role_supported':role=='selected',
                'model_loaded':False,'training_executed_by_authenticator':False,'inference_executed':False,
                'source_semantics_verified':False,'runtime_admitted':False,'teacher_qualified':False,'qualified':False,
                'checkpoint_promoted':False,'proof_authority':False,'optimizer_resumable':False,
                'public_copy_admissible':True,'suggested_dimension_repository':f'Publicus/legal-ir-autoencoder-{dimension}d',
                'suggested_repository_path':f'releases/20261006-normative-wording-v1/{name}/{role}-state.json'}
            state_rows.append(row)
            if role == 'selected':
                selected_documents[(dimension,name)] = checkpoint
            else:
                selected = selected_documents[(dimension,name)]
                require(raw({k:v for k,v in checkpoint.items() if k!='role'}) == raw({k:v for k,v in selected.items() if k!='role'}), 'selected/last alias differs beyond role')
                alias_groups.append({'numeric_alias_group':group,'dimension':dimension,'arm':name,'tensor_sha256':typed_sha,
                    'serialization_sha256s':[item['original_checkpoint_pin']['sha256'] for item in state_rows if item['numeric_alias_group']==group],
                    'only_header_difference':'role','trained_tensor_endpoint_count':1})
    for relative in ('normative_wording_training_sources.py','normative_wording_modality_auxiliary.py'):
        _, pin = authenticate(TREE/'ipfs_datasets_py/logic/formalization/autoencoder'/relative)
        source_pins.append(pin)

for relative in ('benchmark_normative_wording_training.py','prepare_normative_wording_sources.py','evaluate_normative_wording_development.py'):
    _, pin = authenticate(TREE/'scripts/ops/autoencoder'/relative)
    source_pins.append(pin)
require(len(state_rows)==8 and len(alias_groups)==4 and len({r['tensor_sha256'] for r in state_rows})==4, 'four distinct numeric endpoints required')
require(not (FORBIDDEN & set(sys.modules)), 'heavy modules were imported')
for path, observed in observations.items():
    require(canonical(path) == Path(path) and witness(Path(path).lstat()) == observed['file_witness'], 'closing protected endpoint changed')
process_after = process_snapshot()
manifest = {'schema':'normative-checkpoint-authentication/v1','complete':True,'datasets_head':head,
 'published_result_pin':public_pin,'prior_authentication_join_pin':prior_pin,'source_pins':list({p['path']:p for p in source_pins}.values()),
 'states':state_rows,'preprocessing':preprocessing_rows,'alias_groups':alias_groups,'completion':completion_rows,
 'support_pins':list({p['path']:p for p in support_pins}.values()),
 'serialization_count':8,'trained_numeric_endpoint_count':4,'checkpoint_byte_total':sum(r['original_checkpoint_pin']['bytes'] for r in state_rows),
 'observed_file_count':len(observations),'streamed_byte_total':total,'elapsed_seconds':time.time()-started,
 'max_file_bytes':MAX_FILE,'max_aggregate_bytes':MAX_TOTAL,'closing_endpoint_identity_checks_passed':True,
 'process_before':process_before,'process_after':process_after,
 'execution_context_observation':'Parent/team survey: asset and contract survey tasks completed; only root publication planning and this authentication task running. Fixed training runs have zero exits and released leases.',
 'authority':{'runtime_admitted':False,'teacher_qualified':False,'quality_qualified':False,'fresh_holdout':False,'proof_authority':False,'model_loaded':False,'training_executed':False,'inference_executed':False,'new_embeddings_generated':False},
 'input_contract':{'paragraph_embedding_shape':['batch','dimension'],'clause_embedding_shape':['batch',8,'dimension'],'clause_padding_mask_shape':['batch',8],'clause_padding_mask_dtype':'bool','decoder_output_limit_tokens':512,'observed_encoder_context_tokens':512,'8192_token_encoder_context_qualified':False,'codec_vocabulary_entries':32,'vocabulary_count_is_not_output_token_limit':True,'transform_order':'Saved TRAIN-only center/RMS transform applied once to real vectors, then clause zero padding; saved model paragraph/clause normalization remains inside model.'},
 'limits':['Cooperative before/descriptor/after/final endpoint checks are not an atomic multi-file snapshot or continuous custody guarantee.','Exact supplied receipt bytes and typed JSON float32/int64 hashes authenticated; no tensor library, tensor loader, model constructor, inference, training, proof, or quality qualification.','Last-attempt states preserve selected=True; role remains last-attempt. Four paired serialization aliases are four numeric endpoints, not eight independent trained models.','Existing contextual runtime accepts a different continuation recipe; normative headers are preserved and do not qualify that runtime.','Saved preprocessing includes TRAIN feature vectors; only extracted frozen metadata is admissible for public metadata copying by this manifest.','Prospective wording observations reuse previously exposed DEV meanings; they are not an independent semantic holdout.','Immediate continuation parent differs from original raw donor lineage; both identities are preserved.']}
OUT.mkdir(parents=True,exist_ok=True)
for item in preprocessing_rows:
    extracted={'schema':'normative-frozen-preprocessing-metadata/v1','dimension':item['dimension'],
        'original_preprocessing_pin':ref(item['original_preprocessing_pin']),'frozen_metadata':item['frozen_metadata'],
        'source_semantics_verified':False,'runtime_admitted':False,'teacher_qualified':False,'proof_authority':False,
        'saved_paragraph_vector_producer_authenticated':False,'independent_clause_encoder_producer_authenticated':False,
        'contains_embedding_feature_vectors':False,'source_binding_is_inventory_join_not_encoder_producer_authentication':True}
    metadata_path = OUT/f'preprocessing-{item["dimension"]}-metadata.json'
    metadata_path.write_text(json.dumps(extracted,indent=2,sort_keys=True,allow_nan=False)+'\n')
    _, item['metadata_pin'] = authenticate(metadata_path)
    item['metadata_public_copy_admissible'] = True
manifest['public_copy_list'] = [
    {'kind':'original_complete_checkpoint','dimension':row['dimension'],'arm':row['arm'],'role':row['role'],
     'source_pin':row['original_checkpoint_pin'],'suggested_repository_path':row['suggested_repository_path']}
    for row in state_rows] + [
    {'kind':'frozen_preprocessing_metadata_view','dimension':item['dimension'],'source_pin':item['metadata_pin'],
     'original_preprocessing_pin':item['original_preprocessing_pin'],
     'suggested_repository_path':f'releases/20261006-normative-wording-v1/preprocessing/{item["dimension"]}d-metadata.json'}
    for item in preprocessing_rows]
(OUT/'authenticated-states.json').write_text(json.dumps(manifest,indent=2,sort_keys=True,allow_nan=False)+'\n')
(OUT/'public-copy-list.json').write_text(json.dumps({'schema':'normative-checkpoint-public-copy-list/v1','files':manifest['public_copy_list'],
    'raw_embedding_caches_included':False,'raw_preprocessing_corpus_included':False,'training_transient_assets_included':False,
    'runtime_admitted':False,'proof_authority':False},indent=2,sort_keys=True,allow_nan=False)+'\n')
print(json.dumps({'complete':True,'serialized_states':8,'numeric_endpoints':4,'observed_file_count':len(observations),'checkpoint_byte_total':manifest['checkpoint_byte_total'],'heavy_imports':[],'output':str(OUT/'authenticated-states.json')}))
