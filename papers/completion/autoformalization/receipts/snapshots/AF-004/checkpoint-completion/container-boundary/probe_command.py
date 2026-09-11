import os,json,errno
targets = [('private_sentinel', '/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/research-inputs/autoformalization/af004-v1/.container-boundary-sentinel-7abfeb49e355acbae0a21a95', False), ('host_home_sentinel', '/home/barberb/.af004-host-home-sentinel-7abfeb49e355acbae0a21a95', False), ('private_research_root', '/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/research-inputs/autoformalization/af004-v1', False), ('private_raw_directory', '/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/research-inputs/autoformalization/af004-v1/raw', False), ('private_lexical_membership', '/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/research-inputs/autoformalization/af004-v1/lexical_graph.private.json', False), ('host_root_alias_sentinel', '/host/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/research-inputs/autoformalization/af004-v1/.container-boundary-sentinel-7abfeb49e355acbae0a21a95', False), ('proc_init_root_sentinel', '/proc/1/root/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/research-inputs/autoformalization/af004-v1/.container-boundary-sentinel-7abfeb49e355acbae0a21a95', False), ('proc_self_root_sentinel', '/proc/self/root/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/research-inputs/autoformalization/af004-v1/.container-boundary-sentinel-7abfeb49e355acbae0a21a95', False), ('docker_socket', '/var/run/docker.sock', False), ('workspace_positive_control', '/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/autoformalization/worktrees/workspace_b055e32f57f3_8a868dab4803/papers/completion/autoformalization/tasks.json', True), ('toolchain_positive_control', '/usr/bin/python3.12', True)]
results = []
for label,path,expected in targets:
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        accessible, failure = True, None
    except OSError as exc:
        accessible, failure = False, errno.errorcode.get(exc.errno, str(exc.errno))
    finally:
        if descriptor is not None:
            os.close(descriptor)
    results.append({'label':label,'open_succeeded':accessible,'expected_accessible':expected,'errno':failure})
print(json.dumps({'checks':results,'all_checks_match':all(x['open_succeeded']==x['expected_accessible'] for x in results),'uid':os.getuid(),'gid':os.getgid(),'HOME':os.environ.get('HOME'),'CODEX_HOME':os.environ.get('CODEX_HOME'),'file_contents_read':False,'directory_entries_enumerated':False,'network_requests':0,'providers_invoked':0}))
raise SystemExit(0 if all(x['open_succeeded']==x['expected_accessible'] for x in results) else 3)
