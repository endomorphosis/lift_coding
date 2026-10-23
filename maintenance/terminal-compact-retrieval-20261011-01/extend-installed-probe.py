from pathlib import Path
old = Path('/home/barberb/lift_coding/maintenance/terminal-frontier-runtime-20261011-01/frontier-worker-probe.py').read_text()
extra = r'''

_original_production_probe = optional_production_probe


def compact_worker(request_path, request_sha256):
    from ipfs_accelerate_py.agent_supervisor.runtime import compact_code_retrieval as codec
    from ipfs_accelerate_py.agent_supervisor.runtime import verified_code_retrieval_projection as verified
    need(os.getuid() == os.geteuid() == 1001, 'actual restricted codec worker required')
    raw = Path(request_path).read_bytes()
    need(sha(raw) == request_sha256, 'protected worker request differs')
    request = json.loads(raw)
    root = Path(request['repository'])
    need(root.is_relative_to(APP) and not os.access(root, os.W_OK), 'read-only public source root required')
    source = (root / request['source_path']).read_bytes().decode('utf-8')
    wire = Path(request['wire']).read_bytes()
    need(sha(wire) == request['wire_sha256'], 'independent wire pin differs')
    packet = json.loads(wire)
    native = codec.decode_code_retrieval_prompt(packet, source)
    need(sha(native.encode()) == request['native_prompt_sha256'], 'independent native pin differs')
    os.environ['IPFS_ACCELERATE_META_INDEX_DUCKDB'] = request['inaccessible_metadata_path']
    os.environ['IPFS_ACCELERATE_META_INDEX_DUCKLAKE'] = request['inaccessible_lake_path']
    before = inventory(root)
    replay = verified.verify_code_retrieval_prompt(prompt=native, repository=root, source_text=source)
    prefix = shlex.split(request['decoder_command'])
    result = subprocess.run(prefix + ['--wire', request['wire'], '--expected-wire-sha256', request['wire_sha256']],
        cwd=Path.cwd(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
    need(result.returncode == 0 and result.stdout == native.encode(), 'actual emitted decoder CLI did not recover exact native capsule')
    need(replay['code_hit_count'] == 5 and replay['metadata_owner_suppressed'] is True, 'complete five native hits required')
    need(inventory(root) == before, 'worker modified public native cache or source')
    for private in (ROOT/'state', ROOT/'home', ROOT/'codex-auth'):
        need(all(not os.access(private, mode) for mode in (os.R_OK, os.W_OK, os.X_OK)), 'owner root accessible to codec worker')
    return {'schema': 'terminal-installed-compact-retrieval-worker@1', 'qualified': True,
        'uid': os.getuid(), 'euid': os.geteuid(), 'native_prompt_sha256': sha(native.encode()),
        'exact_decoder_native_roundtrip': True, 'native_query_replayed_from_current_public_code': True,
        'complete_native_hits': replay['code_hit_count'], 'public_cache_source_witnesses_unchanged': True,
        'metadata_owner_suppressed': replay['metadata_owner_suppressed'], 'owner_roots_inaccessible': True,
        'wire_sha256': sha(wire), 'wire_bytes': len(wire), 'provider_calls': 0,
        'signed_intent_admission_claimed': False, 'proof_authority': False, 'completion_authority': False}


def optional_production_probe(arguments, directory, modules):
    original = _original_production_probe(arguments, directory, modules)
    if original is None:
        return None
    previous_metadata = os.environ.get('IPFS_ACCELERATE_META_INDEX_DUCKDB')
    previous_lake = os.environ.get('IPFS_ACCELERATE_META_INDEX_DUCKLAKE')
    os.environ['IPFS_ACCELERATE_META_INDEX_DUCKDB'] = str(directory/'fresh-codec-metadata.duckdb')
    os.environ.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE', None)
    try:
        return _compact_production_probe(arguments, directory, modules, original)
    finally:
        for key, value in (('IPFS_ACCELERATE_META_INDEX_DUCKDB',previous_metadata),('IPFS_ACCELERATE_META_INDEX_DUCKLAKE',previous_lake)):
            if value is None: os.environ.pop(key,None)
            else: os.environ[key]=value


def _compact_production_probe(arguments, directory, modules, original):
    from ipfs_accelerate_py.agent_supervisor.runtime import compact_code_retrieval as codec
    from ipfs_accelerate_py.agent_supervisor.runtime import verified_code_retrieval_projection as verified
    from ipfs_accelerate_py.agent_supervisor.runtime.semantic_context_runtime import prepare_semantic_context, load_semantic_worker_context
    from ipfs_accelerate_py.agent_supervisor.context.context_compiler import build_text_context_references, compile_context_capsule, render_context_capsule
    from ipfs_accelerate_py.agent_supervisor.context.context_contracts import ContextBudget
    source = Path(arguments.public_instruction).read_bytes()
    write_new(directory/'public-instruction.md', source, 0o444)
    semantic = prepare_semantic_context(repository=directory, task_id='PRODUCTION-QUOTA-001',
        paths=['bottle.py', 'public-instruction.md'], output=directory/'semantic',
        required_raw_paths=['public-instruction.md'], objective='Inspect exact native code context', max_symbols=1024, worker_query=source.decode(), worker_max_bytes=32768)
    # Use the exact native worker projection, with all producer declarations.
    semantic_text = load_semantic_worker_context(repository=directory,
        artifact='semantic/worker-context.json',
        expected_sha256=semantic['worker_payload_sha256'], task_id='PRODUCTION-QUOTA-001')
    retrieval_raw = (directory/'retrieval.json').read_bytes()
    full = modules[NAMES[1]].load_code_retrieval_context(repository=directory, artifact='retrieval.json',
        expected_sha256=sha(retrieval_raw), task_id='PRODUCTION-QUOTA-001')
    binding = dict(repository_id='repository:installed-public-codec-probe', tree_id='tree:installed-public-codec-probe',
        objective_id='PRODUCTION-QUOTA-001', objective_revision='revision:public-instruction',
        policy_id='policy:passive-public-probe', policy_revision='revision:1',
        caller='supervisor:installed-codec-probe', stage='implementation')
    refs = (*build_text_context_references(semantic_text, reference_prefix='semantic', kind='semantic-context',
        path='semantic/worker-context.json', repository_id=binding['repository_id'], tree_id=binding['tree_id'],
        required=True, chunk_bytes=6144), *build_text_context_references(full, reference_prefix='code', kind='code-retrieval-context',
        path='retrieval.json', repository_id=binding['repository_id'], tree_id=binding['tree_id'], required=True, chunk_bytes=6144))
    compiled = compile_context_capsule(**binding, budget=ContextBudget(max_input_tokens=65000,max_items=64,max_item_bytes=16384,max_serialized_bytes=256000),
        goal={'objective':'Inspect exact native code context'}, authority={'mode':'candidate_only','completion_authority':False},
        scope={'allowed_paths':['bottle.py']}, acceptance={'criteria':['exact native reconstruction']}, evidence=refs)
    native = render_context_capsule(compiled.capsule)
    decoder = verified.decoder_command_prefix(repository=directory,source_path='public-instruction.md',source_sha256=sha(source),native_prompt_sha256=sha(native.encode()))
    selected, projection = verified.project_verified_code_retrieval_prompt(prompt=native,repository=directory,source_text=source.decode(),decoder_command=decoder)
    need(projection['selected_transport']=='compact', 'complete installed projection should be smaller')
    packet = codec.parse_code_retrieval_prompt(selected, decoder_command=decoder)
    wire = canonical(packet)
    write_new(directory/'compact-wire.json', wire, 0o444)
    request = {'repository':str(directory),'source_path':'public-instruction.md', 'wire':str(directory/'compact-wire.json'),
        'wire_sha256':sha(wire),'native_prompt_sha256':sha(native.encode()),'decoder_command':decoder,
        'inaccessible_metadata_path':str(ROOT/'state'/arguments.name/'fresh-metadata.duckdb'),
        'inaccessible_lake_path':str(ROOT/'state'/arguments.name/'configured-lake')}
    request_raw = canonical(request)
    request_path = directory/'compact-worker-request.json'
    write_new(request_path, request_raw, 0o444)
    for path in directory.rglob('*'):
        if path.is_file(): path.chmod(0o444)
        elif path.is_dir(): path.chmod(0o755)
    directory.chmod(0o755)
    before = inventory(directory)
    candidate = ROOT/'worktrees'/arguments.name
    binding = modules[NAMES[-2]].bind_candidate_runner([str(ROOT/'bin/validation-worker')])
    completed = modules[NAMES[-2]].run_candidate(binding,[sys.executable,'-P',str(Path(__file__).absolute()),
        '--compact-worker',str(request_path),'--compact-request-sha256',sha(request_raw)],cwd=candidate,timeout=120,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if completed.returncode:
        frames=[line.strip()[:512] for line in completed.stderr.decode(errors='replace').splitlines() if line.lstrip().startswith('File ')][:16]
        raise ValueError('installed compact worker failed: '+json.dumps({'returncode':completed.returncode,
            'stdout_sha256':sha(completed.stdout),'stderr_sha256':sha(completed.stderr),'public_traceback_frames':frames}))
    worker_receipt = json.loads(completed.stdout)
    need(worker_receipt['qualified'] and inventory(directory)==before,'installed codec cache custody differs')
    for module in (codec,verified):
        observed = pin(module.__file__,root_protected=True)
        relative = Path(observed['resolved_path']).relative_to(ROOT).as_posix()
        expected = next(row for row in json.loads(Path(arguments.runtime_manifest).read_bytes())['files'] if row['path']==relative)
        need(expected['sha256']==observed['sha256'] and expected['bytes']==observed['bytes'],'installed codec source differs from pinned archive')
    return {**original,'compact_code_retrieval':{'schema':'terminal-installed-production-codec-probe@1',
        'qualified':True,'projection':projection,'worker':worker_receipt,
        'complete_five_native_hits_retained':True,'provider_calls':0,
        'scope':'Exact protected public Bottle AST/native lexical max5, semantic source declarations and installed restricted decoder. Synthetic task labels; no signed IntentIR admission, model fit, task proof or benchmark reward.'}}
'''
# The independent owner/worker baseline remains part of this new qualification.
old = old.replace('\ndef main():', extra + '\n\ndef main():', 1)
old = old.replace("if __name__ == '__main__':\n    main()", "if __name__ == '__main__':\n    if sys.argv[1:2] == ['--compact-worker']:\n        p=argparse.ArgumentParser();p.add_argument('--compact-worker',type=Path,required=True);p.add_argument('--compact-request-sha256',required=True)\n        a=p.parse_args();print(json.dumps(compact_worker(a.compact_worker,a.compact_request_sha256),sort_keys=True),flush=True)\n    else:\n        main()")
assert 'compact_worker(a.compact_worker' in old
Path(__file__).with_name('compact-worker-probe.py').write_text(old)
